# Doubao Search Custom API

Use this reference only when executing a Search Brief with Doubao Search.

Official sources:

- Product overview: https://docs.volcengine.com/docs/87772/2272949?lang=zh
- Custom API reference: https://docs.volcengine.com/docs/87772/2272953?lang=zh
- Authority levels: https://docs.volcengine.com/docs/87772/2518319?lang=zh

Verified against the official Custom API reference on 2026-07-29.

## Authentication and endpoint

- Method: `POST`
- URL: `https://open.feedcoopapi.com/search_api/web_search`
- Content type: `application/json`
- Header: `Authorization: Bearer <API_KEY>`
- Environment variable used by this skill: `DOUBAO_SEARCH_API_KEY`

Never put the key in prompts, command-line arguments, source code, output, or
files intended for publication. The bundled script may load it from the process
environment or the per-user configuration directory.

## Persistent credential setup

Check configuration without revealing or validating the key:

```powershell
python scripts/doubao_search.py --credential-status
```

Configure or replace a key through hidden interactive input:

```powershell
python scripts/doubao_search.py --configure-key
```

The configuration command persists the key outside the publishable skill folder:

- Windows: `%LOCALAPPDATA%\clarify-search\.env`
- Linux/macOS: `$XDG_CONFIG_HOME/clarify-search/.env`, falling back to
  `~/.config/clarify-search/.env`

It verifies the key first when Doubao is reachable. If a non-authentication
problem prevents validation, it retains the key for a later search; an explicit
credential rejection does not replace the current saved key. A legacy ignored
`clarify-search/.env` remains readable for migration compatibility.

Validate an existing key only when troubleshooting:

```powershell
python scripts/doubao_search.py --check-key
```

Exit code `3` means Doubao explicitly rejected the credential, so the user should
run `--configure-key` again. Network failures, timeouts, rate limits, and exhausted
quota are not credential failures and must not trigger a request for a new key.

The production endpoint is locked to the official host. The optional
`DOUBAO_SEARCH_API_URL` override accepts HTTP only for localhost testing.

## Search Brief mapping

| Search Brief decision | Custom API field |
|---|---|
| Target query | `Query` |
| Web or image | `SearchType` (`web` or `image`) |
| Result count | `Count` (web default 10/max 50; image default/max 5) |
| Require extractable body | `Filter.NeedContent` |
| Require source URL | `Filter.NeedUrl` |
| Allowlisted domains | `Filter.Sites`, pipe-delimited, max 20 |
| Blocked domains | `Filter.BlockHosts`, pipe-delimited, max 5 |
| Very authoritative only | `Filter.AuthInfoLevel=1` |
| Freshness | `TimeRange` |
| Query expansion | `QueryControl.QueryRewrite=true` |
| Body representation | `ContentFormats` (`text` or `markdown`) |
| Vertical scope | `Industry` (`finance`, `game`, or `gov`) |

`TimeRange` accepts `OneDay`, `OneWeek`, `OneMonth`, `OneYear`, or an inclusive
`YYYY-MM-DD..YYYY-MM-DD` interval.

Image filters support minimum and maximum width and height plus shape. The CLI
maps `landscape`, `portrait`, and `square` to the API's localized enum values.

## Bundled CLI

Run from the skill directory:

```powershell
python scripts/doubao_search.py "Python 3.15 release date" --sites python.org --auth-level 1 --need-url --query-rewrite --output markdown
```

For current official material with full Markdown:

```powershell
python scripts/doubao_search.py "query" --time-range OneWeek --auth-level 1 --need-content --need-url --content-format markdown --output json
```

For images:

```powershell
python scripts/doubao_search.py "Volcano Engine logo" --search-type image --count 3 --image-shapes landscape,square --output json
```

Use `--raw` only when the normalized output omits a response field required by
the task. The normalized output limits each body to 6,000 characters by default;
change this with `--max-content-chars`.

## Response use

For model input, prefer `Summary` over `Snippet` when full `Content` is
unnecessary. The official reference describes `Snippet` as a short display
fragment and recommends `Summary` for model use.

Treat `AuthInfoLevel` as a ranking/filtering signal, not independent proof.
Inspect the underlying source and cross-check important claims.

The default account limit documented for Custom is 5 QPS. Error `700429`
indicates rate limiting. The CLI retries it twice by default with bounded
exponential backoff and honors a bounded `Retry-After`; change this with
`--max-retries 0..5`. Error `10406` indicates that the free quota is exhausted
and is not retried as an authentication failure.

## Deterministic validation

Run without contacting Doubao or reading the configured key:

```powershell
python scripts/test_doubao_search.py
```

The suite covers web/image defaults, count limits, calendar ranges, atomic
credential persistence, authentication classification, and rate-limit retry.
