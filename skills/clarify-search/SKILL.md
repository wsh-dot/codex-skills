---
name: clarify-search
description: Clarify ambiguous search intent into a compact Search Brief, then execute scoped, evidence-backed web or image research, primarily with Doubao Search Custom. Use for exploratory research, comparisons, production selection, "latest/current" questions, source-sensitive or high-stakes searches, domain/freshness filtering, official-source verification, image discovery, and persistent Doubao API-key setup. Search directly for clear low-risk factual or navigational lookups.
---

# Clarify Search

Resolve only ambiguity that would change retrieval. Use this test:

> If plausible answers to the missing detail would produce materially different queries, filters, or source standards, clarify it; otherwise choose a safe default and search.

Own the clarification and search phase. Do not invoke `grilling` or another discovery orchestrator inside this workflow.

## 1. Route by retrieval divergence

| Route | Signal | Action |
|---|---|---|
| Direct | Interpretations converge on the same sources | Search immediately |
| Focused | One user-owned decision changes retrieval | Ask one question, recommend a default, then search |
| Research contract | Several decisions affect a comparison, purchase, policy, medical, legal, financial, or production choice | Resolve one decision per turn; stop as soon as remaining ambiguity cannot change the plan |

Ask only about user-owned choices. Discover terminology, release dates, available filters, and source availability yourself.

For exploratory topics whose vocabulary the user cannot yet know, run one small reconnaissance query first. Summarize the real branches it exposes, then ask the single decision that separates them. Do not make users choose from invented categories.

## 2. Form the Search Brief

Keep only fields that affect retrieval:

```text
Goal/decision:
Target and boundaries:
Freshness and geography:
Required/excluded sources:
Content type:
Deliverable:
Stop when:
```

Infer safe defaults from the request, conversation, and stable user preferences. Keep persistent preferences separate from request-specific constraints. Show the brief only when confirmation could prevent a materially different search.

Every clarification question must:

- isolate one decision;
- state briefly how it changes the search;
- offer a recommended answer that is easy to accept;
- allow an override.

## 3. Convert intent into an evidence plan

Use the request type to choose queries and proof:

| Request type | Retrieval strategy | Evidence rule |
|---|---|---|
| Current landscape | Discover competing names broadly, then query each serious candidate against official sources | Repetition in results is discovery evidence, not market-share evidence |
| "Latest" | Apply an explicit time boundary and search official release/status pages | Distinguish publication date from event, release, or version date |
| Comparison/selection | Use symmetric queries and the same source standard for every candidate | Separate sourced facts from architecture or purchasing judgment |
| Popularity | Agree on or state a proxy: adoption survey, usage telemetry, job demand, repository activity, or ecosystem support | Never convert search rank or mention count into a popularity percentage |
| High stakes | Start with regulator, standards body, official guideline, or primary record; add independent corroboration | Syndicated copies and articles repeating one upstream claim are one source, not several |
| Known item | Target the canonical owner/domain directly | Prefer the canonical page over summaries |

Treat a broad query as vocabulary discovery. For decision-critical claims, follow with entity-specific or domain-restricted queries. Stop when each claim that could change the decision has adequate evidence or is explicitly marked as a gap.

## 4. Select and configure the provider

Use Doubao Search Custom when the user requests it or when its domain, freshness, authority, query-rewrite, content, or image controls fit the brief. Before the first Doubao operation or any credential troubleshooting, read [references/doubao-api.md](references/doubao-api.md) completely. Do not load that reference when another provider is used.

The Doubao reference owns exact CLI arguments, persistent credential setup, exit-code handling, retry behavior, and API limits. Security invariant: never request or expose an API key in chat, prompts, command arguments, logs, or publishable files.

If the user requires only Doubao, do not silently supplement with another provider. Report a Doubao coverage gap instead. Use another provider only when the user allows it or Doubao cannot satisfy a required content type or source.

Do not send a sensitive query to any third-party search service without the user's authorization.

## 5. Execute with evidence-aware adaptation

1. Run the minimum query set implied by the evidence plan.
2. Use snippets to triage; fetch full content when wording, context, or qualification matters.
3. Inspect the underlying source even when the provider supplies an authority label.
4. Check whether apparently independent results share the same upstream source.
5. Search an identified evidence gap only if closing it could change the answer.
6. Stop at the Search Brief's condition; do not spend queries merely to increase result count.

When results contradict, prefer the source closest to the event or claim, explain the conflict, and avoid averaging incompatible facts.

## 6. Deliver decision support

Lead with the requested answer. Place links beside supported claims. State:

- which conclusions are sourced facts versus inference or recommendation;
- material freshness, access, and coverage limits;
- unresolved gaps that could change the decision.

Ask a follow-up only if the evidence exposes a new user-owned decision. Otherwise finish without reopening clarification.

## NEVER

- NEVER force every Search Brief field to be filled; ceremony delays clear searches without improving retrieval.
- NEVER ask for a discoverable fact; reconnaissance is cheaper and more reliable than making the user guess.
- NEVER claim a tool or product is "most popular" from result ordering or repeated mentions; ranking systems and duplicated content bias both.
- NEVER count mirrors, syndication, or articles citing one announcement as independent corroboration.
- NEVER treat a provider authority score as proof; it is a retrieval signal, not evidence validation.
- NEVER request a replacement API key for timeouts, rate limits, exhausted quota, or malformed queries; only explicit credential rejection justifies reconfiguration.
- NEVER claim clarification improved quality without comparing against an unclarified baseline.
