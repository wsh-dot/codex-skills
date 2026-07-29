#!/usr/bin/env python3
"""Call the Doubao Search Custom API without external dependencies."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_ENDPOINT = "https://open.feedcoopapi.com/search_api/web_search"
SKILL_ROOT = Path(__file__).resolve().parent.parent
LEGACY_ENV_PATH = SKILL_ROOT / ".env"
if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
    CONFIG_ROOT = Path(os.environ["LOCALAPPDATA"])
else:
    CONFIG_ROOT = Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    )
ENV_PATH = CONFIG_ROOT / "clarify-search" / ".env"
SHAPE_ALIASES = {
    "landscape": "\u6a2a\u957f\u65b9\u5f62",
    "portrait": "\u7ad6\u957f\u65b9\u5f62",
    "square": "\u65b9\u5f62",
}


class SearchError(RuntimeError):
    """A safe user-facing search error that never contains credentials."""


class CredentialError(SearchError):
    """The configured credential was explicitly rejected by Doubao Search."""


def read_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    """Read simple KEY=VALUE pairs from a local environment file."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def persistent_env() -> dict[str, str]:
    """Merge legacy and current local configuration without exposing values."""
    values = read_env_file(LEGACY_ENV_PATH)
    values.update(read_env_file(ENV_PATH))
    return values


def load_env_file() -> None:
    """Load persistent KEY=VALUE pairs without overriding process variables."""
    for key, value in persistent_env().items():
        os.environ.setdefault(key, value)


def has_usable_key(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() != "replace_with_a_rotated_key")


def credential_source() -> str:
    """Return a non-secret description of the configured credential source."""
    process_key = os.environ.get("DOUBAO_SEARCH_API_KEY")
    local_key = persistent_env().get("DOUBAO_SEARCH_API_KEY")
    if has_usable_key(process_key):
        return "environment"
    if has_usable_key(local_key):
        return "local"
    return "missing"


def save_local_key(api_key: str, path: Path = ENV_PATH) -> None:
    """Atomically persist a key without printing it or changing unrelated settings."""
    api_key = api_key.strip()
    if not has_usable_key(api_key) or "\n" in api_key or "\r" in api_key:
        raise CredentialError("The supplied Doubao Search API key is empty or invalid.")

    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    output: list[str] = []
    replaced = False
    for line in existing:
        if line.strip().startswith("DOUBAO_SEARCH_API_KEY="):
            if not replaced:
                output.append(f"DOUBAO_SEARCH_API_KEY={api_key}")
                replaced = True
            continue
        output.append(line)
    if not replaced:
        if output and output[-1].strip():
            output.append("")
        output.append(f"DOUBAO_SEARCH_API_KEY={api_key}")
    if not any(line.strip().startswith("DOUBAO_SEARCH_API_URL=") for line in output):
        output.append(f"DOUBAO_SEARCH_API_URL={DEFAULT_ENDPOINT}")

    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
        if os.name != "nt":
            os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def credential_was_rejected(code: Any, message: Any, http_status: int | None = None) -> bool:
    if http_status in {401, 403}:
        return True
    combined = f"{code or ''} {message or ''}".lower()
    credential_words = ("api key", "apikey", "credential", "authorization", "鉴权", "认证")
    rejection_words = (
        "invalid",
        "expired",
        "unauthorized",
        "forbidden",
        "rejected",
        "无效",
        "过期",
        "失败",
    )
    return any(word in combined for word in credential_words) and any(
        word in combined for word in rejection_words
    )


def validation_payload() -> dict[str, Any]:
    return {"Query": "豆包搜索 API 连通性测试", "SearchType": "web", "Count": 1}


def split_domains(value: str | None, limit: int, option: str) -> str | None:
    if not value:
        return None
    domains = [part.strip() for part in re.split(r"[|,]", value) if part.strip()]
    if len(domains) > limit:
        raise SearchError(f"{option} accepts at most {limit} domains")
    for domain in domains:
        if "://" in domain or "/" in domain or not re.fullmatch(
            r"(?:[A-Za-z0-9-]+\.)+[A-Za-z0-9-]+", domain
        ):
            raise SearchError(
                f"{option} expects bare full domains, for example docs.python.org"
            )
    return "|".join(domains)


def validate_time_range(value: str | None) -> str | None:
    if not value:
        return None
    if value in {"OneDay", "OneWeek", "OneMonth", "OneYear"}:
        return value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}", value):
        start_text, end_text = value.split("..", 1)
        try:
            start = date.fromisoformat(start_text)
            end = date.fromisoformat(end_text)
        except ValueError:
            raise SearchError("--time-range contains an invalid calendar date") from None
        if start > end:
            raise SearchError("--time-range start date must not be after end date")
        return value
    raise SearchError(
        "--time-range must be OneDay, OneWeek, OneMonth, OneYear, "
        "or YYYY-MM-DD..YYYY-MM-DD"
    )


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    query = args.query.strip()
    if not 1 <= len(query) <= 100:
        raise SearchError("query must contain 1 to 100 characters")

    max_count = 50 if args.search_type == "web" else 5
    count = args.count if args.count is not None else (10 if args.search_type == "web" else 5)
    if not 1 <= count <= max_count:
        raise SearchError(
            f"--count must be between 1 and {max_count} for {args.search_type}"
        )

    payload: dict[str, Any] = {
        "Query": query,
        "SearchType": args.search_type,
        "Count": count,
    }
    query_control = {}
    if args.query_rewrite:
        query_control["QueryRewrite"] = True
    if query_control:
        payload["QueryControl"] = query_control

    if args.search_type == "web":
        filter_value: dict[str, Any] = {}
        if args.need_content:
            filter_value["NeedContent"] = True
        if args.need_url:
            filter_value["NeedUrl"] = True

        sites = split_domains(args.sites, 20, "--sites")
        blocked = split_domains(args.block_hosts, 5, "--block-hosts")
        if sites:
            filter_value["Sites"] = sites
        if blocked:
            filter_value["BlockHosts"] = blocked
        if args.auth_level is not None:
            filter_value["AuthInfoLevel"] = args.auth_level
        if filter_value:
            payload["Filter"] = filter_value

        time_range = validate_time_range(args.time_range)
        if time_range:
            payload["TimeRange"] = time_range
        if args.content_format:
            payload["ContentFormats"] = args.content_format
        if args.industry:
            payload["Industry"] = args.industry
    else:
        image_filter: dict[str, Any] = {}
        for arg_name, api_name in (
            ("image_width_min", "ImageWidthMin"),
            ("image_height_min", "ImageHeightMin"),
            ("image_width_max", "ImageWidthMax"),
            ("image_height_max", "ImageHeightMax"),
        ):
            value = getattr(args, arg_name)
            if value is not None:
                if value < 1:
                    raise SearchError(f"--{arg_name.replace('_', '-')} must be positive")
                image_filter[api_name] = value
        if args.image_shapes:
            aliases = [
                part.strip().lower()
                for part in args.image_shapes.split(",")
                if part.strip()
            ]
            invalid = [shape for shape in aliases if shape not in SHAPE_ALIASES]
            if invalid:
                raise SearchError(
                    "--image-shapes accepts landscape, portrait, and square"
                )
            image_filter["ImageShapes"] = [SHAPE_ALIASES[shape] for shape in aliases]
        if image_filter:
            payload["Filter"] = image_filter

    return payload


def validate_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if (
        parsed.scheme == "https"
        and parsed.hostname == "open.feedcoopapi.com"
        and parsed.path == "/search_api/web_search"
    ):
        return
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}:
        return
    raise SearchError(
        "DOUBAO_SEARCH_API_URL must be the official Doubao Search endpoint "
        "or an HTTP localhost URL used for testing"
    )


def is_rate_limit(code: Any, http_status: int | None = None) -> bool:
    return http_status == 429 or str(code or "") == "700429"


def retry_delay(attempt: int, retry_after: str | None = None) -> float:
    """Return a bounded delay; attempt is zero-based."""
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 10.0)
        except ValueError:
            pass
    return min(0.5 * (2**attempt), 4.0)


def call_api(
    payload: dict[str, Any],
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> dict[str, Any]:
    validate_endpoint(endpoint)
    if not 0 <= max_retries <= 5:
        raise SearchError("--max-retries must be between 0 and 5")

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "clarify-search/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body)
            except json.JSONDecodeError:
                detail = {}
            error = (detail.get("ResponseMetadata") or {}).get("Error") or {}
            code = error.get("Code") or exc.code
            message = error.get("Message") or exc.reason
            if credential_was_rejected(code, message, exc.code):
                raise CredentialError(
                    "The saved Doubao Search API key was rejected or has expired."
                ) from None
            if is_rate_limit(code, exc.code) and attempt < max_retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                time.sleep(retry_delay(attempt, retry_after))
                continue
            raise SearchError(f"Doubao Search HTTP error {code}: {message}") from None
        except urllib.error.URLError as exc:
            raise SearchError(f"Doubao Search connection failed: {exc.reason}") from None

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise SearchError("Doubao Search returned invalid JSON") from None

        error = (data.get("ResponseMetadata") or {}).get("Error")
        if not error:
            return data
        code = error.get("Code") or error.get("CodeN") or "unknown"
        message = error.get("Message") or "request failed"
        if credential_was_rejected(code, message):
            raise CredentialError(
                "The saved Doubao Search API key was rejected or has expired."
            )
        if is_rate_limit(code) and attempt < max_retries:
            time.sleep(retry_delay(attempt))
            continue
        raise SearchError(f"Doubao Search API error {code}: {message}")

    raise SearchError("Doubao Search retry limit reached")


def truncate(value: Any, limit: int) -> Any:
    if isinstance(value, str) and limit >= 0 and len(value) > limit:
        return value[:limit] + "\n...[truncated]"
    return value


def normalize_response(data: dict[str, Any], max_content_chars: int) -> dict[str, Any]:
    metadata = data.get("ResponseMetadata") or {}
    result = data.get("Result") or {}
    output: dict[str, Any] = {
        "request_id": metadata.get("RequestId"),
        "result_count": result.get("ResultCount", 0),
        "time_cost_ms": result.get("TimeCost"),
        "search_context": result.get("SearchContext"),
    }

    web_results = []
    for item in result.get("WebResults") or []:
        web_results.append(
            {
                "id": item.get("Id"),
                "rank": item.get("SortId"),
                "title": item.get("Title"),
                "site_name": item.get("SiteName"),
                "url": item.get("Url"),
                "publish_time": item.get("PublishTime"),
                "rank_score": item.get("RankScore"),
                "authority": item.get("AuthInfoDes"),
                "authority_level": item.get("AuthInfoLevel"),
                "content_format": item.get("ContentFormats"),
                "snippet": item.get("Snippet"),
                "summary": truncate(item.get("Summary"), max_content_chars),
                "content": truncate(item.get("Content"), max_content_chars),
            }
        )
    if web_results:
        output["web_results"] = web_results

    image_results = []
    for item in result.get("ImageResults") or []:
        image = item.get("Image") or {}
        image_results.append(
            {
                "id": item.get("Id"),
                "rank": item.get("SortId"),
                "title": item.get("Title"),
                "site_name": item.get("SiteName"),
                "source_url": item.get("Url"),
                "publish_time": item.get("PublishTime"),
                "image_url": image.get("Url"),
                "width": image.get("Width"),
                "height": image.get("Height"),
                "shape": image.get("Shape"),
                "clarity": image.get("BlurDes"),
                "category": image.get("Category"),
                "watermark": image.get("Watermark"),
            }
        )
    if image_results:
        output["image_results"] = image_results
    return output


def escape_markdown(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace("]", "\\]")


def to_markdown(data: dict[str, Any]) -> str:
    lines = [
        f"Results: {data.get('result_count', 0)}",
        f"Time: {data.get('time_cost_ms', 'unknown')} ms",
        "",
    ]
    for index, item in enumerate(data.get("web_results") or [], start=1):
        title = escape_markdown(item.get("title") or f"Result {index}")
        url = item.get("url")
        lines.append(f"## {index}. [{title}]({url})" if url else f"## {index}. {title}")
        details = [
            item.get("site_name"),
            item.get("publish_time"),
            item.get("authority"),
        ]
        details = [str(value) for value in details if value]
        if details:
            lines.append(" | ".join(details))
        text = item.get("content") or item.get("summary") or item.get("snippet")
        if text:
            lines.extend(["", str(text).strip()])
        lines.append("")

    for index, item in enumerate(data.get("image_results") or [], start=1):
        title = escape_markdown(item.get("title") or f"Image {index}")
        image_url = item.get("image_url")
        lines.append(f"## {index}. {title}")
        if image_url:
            lines.append(f"![{title}]({image_url})")
        details = [
            item.get("site_name"),
            f"{item.get('width')}x{item.get('height')}"
            if item.get("width") and item.get("height")
            else None,
            item.get("shape"),
            item.get("clarity"),
        ]
        details = [str(value) for value in details if value]
        if details:
            lines.append(" | ".join(details))
        if item.get("source_url"):
            lines.append(f"[Source]({item['source_url']})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search the web or images with Doubao Search Custom."
    )
    parser.add_argument("query", nargs="?", help="Search query, 1 to 100 characters")
    credential_actions = parser.add_mutually_exclusive_group()
    credential_actions.add_argument(
        "--credential-status",
        action="store_true",
        help="Report whether a credential is configured without contacting the API",
    )
    credential_actions.add_argument(
        "--configure-key",
        action="store_true",
        help="Securely prompt for, verify, and persist a Doubao Search API key",
    )
    credential_actions.add_argument(
        "--check-key",
        action="store_true",
        help="Verify the configured credential without revealing it",
    )
    parser.add_argument(
        "--search-type", choices=("web", "image"), default="web"
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Result count; defaults to 10 for web and 5 for image",
    )
    parser.add_argument("--need-content", action="store_true")
    parser.add_argument("--need-url", action="store_true")
    parser.add_argument("--sites", help="Comma- or pipe-separated full domains; max 20")
    parser.add_argument(
        "--block-hosts", help="Comma- or pipe-separated full domains; max 5"
    )
    parser.add_argument("--auth-level", type=int, choices=(0, 1))
    parser.add_argument("--time-range")
    parser.add_argument("--query-rewrite", action="store_true")
    parser.add_argument("--content-format", choices=("text", "markdown"))
    parser.add_argument("--industry", choices=("finance", "game", "gov"))
    parser.add_argument("--image-width-min", type=int)
    parser.add_argument("--image-height-min", type=int)
    parser.add_argument("--image-width-max", type=int)
    parser.add_argument("--image-height-max", type=int)
    parser.add_argument(
        "--image-shapes", help="Comma-separated: landscape,portrait,square"
    )
    parser.add_argument("--output", choices=("json", "markdown"), default="json")
    parser.add_argument("--raw", action="store_true", help="Return the full API response")
    parser.add_argument("--max-content-chars", type=int, default=6000)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Rate-limit retries, 0 to 5",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = make_parser()
    args = parser.parse_args()
    try:
        if args.credential_status:
            source = credential_source()
            if source == "missing":
                print("Doubao Search credential: not configured")
                return 1
            print(f"Doubao Search credential: configured ({source})")
            return 0

        if args.configure_key:
            try:
                api_key = getpass.getpass(
                    "Enter Doubao Search API key (input hidden): "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                raise SearchError(
                    "Secure credential input was cancelled. Run --configure-key "
                    "in an interactive local terminal."
                ) from None
            if not has_usable_key(api_key):
                raise CredentialError("The supplied Doubao Search API key is empty.")
            endpoint = persistent_env().get(
                "DOUBAO_SEARCH_API_URL", DEFAULT_ENDPOINT
            ).strip()
            try:
                call_api(
                    validation_payload(),
                    api_key,
                    endpoint,
                    args.timeout,
                    args.max_retries,
                )
            except CredentialError:
                raise
            except SearchError as exc:
                save_local_key(api_key)
                print(
                    "Doubao Search credential saved locally, but validation could "
                    f"not complete: {exc}"
                )
                return 0
            save_local_key(api_key)
            print("Doubao Search credential verified and saved locally.")
            return 0

        load_env_file()
        api_key = os.environ.get("DOUBAO_SEARCH_API_KEY", "").strip()
        if not has_usable_key(api_key):
            raise SearchError(
                "Doubao Search credential is not configured. Run this script with "
                "--configure-key in an interactive local terminal."
            )
        endpoint = os.environ.get("DOUBAO_SEARCH_API_URL", DEFAULT_ENDPOINT).strip()
        if args.check_key:
            call_api(
                validation_payload(),
                api_key,
                endpoint,
                args.timeout,
                args.max_retries,
            )
            print("Doubao Search credential is valid.")
            return 0
        if not args.query:
            parser.error("query is required unless a credential action is used")
        payload = build_payload(args)
        response = call_api(
            payload,
            api_key,
            endpoint,
            args.timeout,
            args.max_retries,
        )
        if args.raw:
            output: Any = response
        else:
            output = normalize_response(response, args.max_content_chars)
        if args.output == "markdown" and not args.raw:
            sys.stdout.write(to_markdown(output))
        else:
            json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        return 0
    except CredentialError as exc:
        print(f"Credential error: {exc}", file=sys.stderr)
        return 3
    except SearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
