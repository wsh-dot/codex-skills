---
name: building-c-concept-html-guides
description: >
  Use when creating or improving a standalone HTML/CSS illustrated lesson for a
  C programming concept, especially Chinese-language requests for an illustrated
  HTML explanation of C pointers, custom functions, arrays, structs, file I/O,
  workflow, and common mistakes.
---

# Building C Concept HTML Guides

Create polished single-file HTML lessons that teach one C concept through
visual flow, runnable code, and wrong/right error comparisons.

**Failure pattern:** A generic article page looks readable but lacks a teaching
path: no first-screen mental model, diagrams are decorative instead of
explanatory, code blocks feel unfinished, mobile navigation hides content, and
verification stops at "file exists."

**Verified by:** The pointer and custom-function lessons rendered locally in
Chrome at desktop and mobile sizes with HTTP/file content checks, no console
errors, no page-level horizontal overflow, intact navigation anchors, expected
section counts, code block counts, SVG diagrams, and error-card counts.

## Workflow

1. **Anchor the lesson in one C concept.** Choose a single topic such as
   pointers, custom functions, arrays, structs, or file I/O. Do not mix multiple
   concepts unless the user asks for a comparison.
2. **Design the teaching path before writing HTML.** Use this section order by
   default:
   - Hero with a plain-language thesis.
   - Four-step learning path cards.
   - Core concept diagram.
   - Standard workflow.
   - Syntax/variant breakdown.
   - One or two deeper mechanics sections.
   - Eight common errors with wrong/right code.
   - Final self-check list.
3. **Make diagrams explain execution, not decorate.** Use inline SVG for memory
   boxes, call arrows, data flow, parameter flow, stack-like layouts, or return
   paths. Every arrow should answer "what moves where?"
4. **Use code as the source of truth.** Include one minimal runnable example near
   the top, then keep later snippets small enough to scan on mobile.
5. **Pair every common error with the corrected pattern.** Each error card must
   include a red wrong-code block and a green correct-code block, labelled in
   the page's target language. Prefer bugs that students actually hit: missing
   declaration, type mismatch, invalid address, missing return, off-by-one,
   forgotten `&`, wrong pointer level, or missing recursion base case.
6. **Keep the technical-course visual system.** Use a light grid background,
   white content surfaces, blue/green semantic accents, dark editor-style code
   blocks, red/green comparison panels, 8px radii, and clear mobile breakpoints.
7. **Verify visually and structurally before handoff.** Run desktop and mobile
   browser checks. Confirm title, hero text, navigation targets, section count,
   code block count, SVG count, error-card count, console health, and no
   page-level horizontal overflow.

## Concept Routing

Route the page around the invisible runtime relationship students usually miss:

| Concept | Diagram That Must Exist | Code Contrast That Teaches | Highest-Value Mistakes |
| --- | --- | --- | --- |
| Pointers | Address boxes, arrows, pointer levels, dereference path | Value vs address vs pointed value | Missing `&`, dangling pointer, wrong pointer level, uninitialized pointer |
| Custom functions | Call stack, argument copy, return path, declaration-definition-call chain | Prototype/definition/call with one runnable example | Missing prototype, wrong return type, pass-by-value surprise, missing return |
| Arrays | Contiguous memory cells, index path, array-to-pointer decay boundary | Loop over fixed array plus one function parameter example | Off-by-one, using `sizeof` after decay, writing past end, wrong index base |
| Structs | Field layout, object copy vs pointer-to-struct, `.` vs `->` branch | Direct object access compared with pointer access | Wrong operator, uninitialized fields, shallow copy assumptions, padding confusion |
| File I/O | Open-read/write-close pipeline, file pointer state, error branch | `fopen` guard plus one read or write loop | Missing null check, forgotten close, wrong mode string, assuming read succeeded |

If a concept is not in the table, first identify the hidden movement: memory
movement, control flow, type conversion, resource ownership, or lifetime. Make
that movement the main SVG.

## Content Model

Use these defaults unless the concept needs different language:

| Page Part | Purpose | Pattern |
| --- | --- | --- |
| Hero | Give the mental model | "X is..." plus four path cards |
| Core concept | Make abstraction concrete | SVG boxes/arrows + runnable code |
| Workflow | Show order | Numbered cards with tiny code labels |
| Syntax | Prevent confusion | Declaration/definition/call or equivalent split |
| Mechanics | Explain the tricky part | Two-column visual + code |
| Errors | Teach diagnostics | Eight red/green comparison cards |
| Checklist | Convert lesson into habit | Three questions before coding |

## Visual System

- Use CSS variables for `--bg`, `--ink`, `--muted`, `--panel`, `--line`,
  `--blue`, `--green`, `--red`, and `--code-bg`.
- Keep cards at `border-radius: 8px`; avoid nested decorative card stacks.
- Use a subtle grid background to reinforce "technical diagram" without
  lowering text contrast.
- Use dark code cards with a small editor title bar. This makes snippets feel
  intentional and separates code from prose.
- On mobile, let the nav strip scroll internally and add a gradient mask to hint
  more items exist. The page itself must not horizontally scroll.
- Add `prefers-reduced-motion` to neutralize transitions for users who request
  reduced motion.

## Verification

Use a browser check, not just static grep. When Browser/IAB cannot access a
local file or times out, use local Chrome with Playwright and record that reason.

Minimum checks:

```text
desktop: 1440x900
mobile: 390x844
assert:
- document title is correct
- h1 is correct
- nav hrefs resolve to ids
- expected section/code/error/svg counts match
- documentElement.scrollWidth <= innerWidth + 1
- console warning/error list is empty or explained
```

For deployed Cloudflare Pages versions, also check:

```powershell
Invoke-WebRequest -Uri 'https://<project>.pages.dev/' -UseBasicParsing
```

Only deploy when the user asks for deployment. For Pages, copy the HTML to a
publish directory as `index.html` and use `wrangler pages deploy`.

## Quality Gate

Before considering the artifact done, answer these checks in the final handoff:

- Which single C concept is being taught?
- Which diagram proves the main runtime movement or memory relationship?
- Which eight common mistakes are covered, and does each one have a fix?
- Which desktop and mobile viewport checks were run?
- If deployed, what URL was checked after deploy?

## Pressure Scenarios

Use these as mental tests before finalizing the skill output:

| Scenario | Passing Behavior | Failure To Catch |
| --- | --- | --- |
| User asks for "custom functions" after a pointer lesson | Rebuilds the page around call flow, return values, prototypes, and parameter passing | Keeps pointer memory arrows as generic decoration |
| User asks for "arrays" with common mistakes | Includes contiguous memory, index bounds, `sizeof`, decay, and loop examples | Only lists syntax and forgets array-to-pointer decay |
| User asks to deploy after visual changes | Re-verifies the deployed URL after Wrangler succeeds | Reports deploy success without checking the live page |
| Terminal shows mojibake for Chinese text | Uses UTF-8/browser DOM checks before assuming corruption | Rewrites good files because the shell rendered text incorrectly |

## Never Do

- Never rely on PowerShell's default text decoding for Chinese HTML. Use
  `Get-Content -Encoding UTF8` or browser-rendered checks; mojibake in terminal
  does not necessarily mean the file is corrupt.
- Never treat an internally scrollable nav as a page overflow bug. Check
  `document.documentElement.scrollWidth`, not only a child `scrollWidth`.
- Never use `file://` in the in-app Browser if its URL policy blocks local
  files. Use a safer alternative such as local Chrome/Playwright or a static
  HTTP server.
- Never paste Cloudflare API tokens or other secrets into the HTML, skill, or
  deployment files. Use Wrangler OAuth or environment variables.
- Never add a landing page around the lesson. The first screen should be the
  usable teaching experience.

## What Didn't Work

- Checking only that the HTML file exists was insufficient; layout issues only
  showed up after desktop/mobile screenshot checks.
- Direct `file://` verification in the in-app Browser was blocked by URL policy,
  so local Chrome/Playwright was the reliable fallback for local static files.
- Matching Chinese strings inside shell-embedded JavaScript sometimes produced
  false negatives due to command encoding. Reading DOM text and inspecting
  screenshots was more reliable.
- A plain text answer did not satisfy the user's illustrated-HTML goal; the
  reusable path is a complete standalone HTML artifact with diagrams and QA.
