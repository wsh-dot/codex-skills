# Codex Skills

Personal Codex skills for reusable workflows.

## Skills

- `building-c-concept-html-guides`: creates polished standalone HTML lessons for
  C programming concepts, with visual diagrams, runnable examples, common
  mistakes, responsive QA, and optional Cloudflare Pages deployment checks.
- `clarify-search`: clarifies ambiguous search intent, builds an evidence plan,
  and runs scoped web or image research with persistent, local-only Doubao
  Search credentials.

## Install Locally

Copy a skill directory into your Codex skills folder:

```powershell
Copy-Item -Recurse -Force `
  .\skills\<skill-name> `
  "$env:USERPROFILE\.codex\skills\<skill-name>"
```

Then invoke it as:

```text
Use $building-c-concept-html-guides to create a polished HTML lesson for a C programming concept.
Use $clarify-search to research a current topic with Doubao Search.
```
