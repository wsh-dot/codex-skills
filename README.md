# Codex Skills

Personal Codex skills for reusable workflows.

## Skills

- `building-c-concept-html-guides`: creates polished standalone HTML lessons for
  C programming concepts, with visual diagrams, runnable examples, common
  mistakes, responsive QA, and optional Cloudflare Pages deployment checks.

## Install Locally

Copy a skill directory into your Codex skills folder:

```powershell
Copy-Item -Recurse -Force `
  .\skills\building-c-concept-html-guides `
  "$env:USERPROFILE\.codex\skills\building-c-concept-html-guides"
```

Then invoke it as:

```text
Use $building-c-concept-html-guides to create a polished HTML lesson for a C programming concept.
```
