---
schema_version: "2.0.0"
name: humanizer
description: >-
  Rewrites remaining prose so it reads human without changing claims, names,
  numbers, quotes, or citations. Use when editing or reviewing prose for
  inflated claims, sales language, stock AI words, chatbot artifacts, or
  Wikipedia-style AI writing signs. Do not use as a substitute for anti-slop
  (run anti-slop first) or to fabricate a fake human anecdote.
owner_agent: artifact-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - Prose path after anti-slop and optional writer-sample cadence notes
  outputs:
    - Human-sounding rewrite that preserves claims, names, numbers, quotes, and citations
---

# Humanizer

## When to use

After anti-slop (or on a draft that still sounds chatbot-like): rewrite in-scope prose so it reads like a person while keeping every claim. Match a writer sample when one exists.

## When not to use

Substitute for [`anti-slop`](../anti-slop/SKILL.md) — run that first for pattern strip and design/UI. Code, logs, security MUST wording, frontmatter schemas, commit messages. Do not invent anecdotes, facts, names, numbers, quotes, or citations to sound “human.”

## Criticality

High for human-readable deliverables after anti-slop. Pattern detail lives in `references/`; durable policy is [`docs/anti-slop.md`](../../../docs/anti-slop.md).

## Source of truth

- [`docs/anti-slop.md`](../../../docs/anti-slop.md) (authoritative)
- [`references/signs-of-ai-writing.md`](./references/signs-of-ai-writing.md)
- Sibling: [`anti-slop`](../anti-slop/SKILL.md)
- Advisory: [blader/humanizer](https://github.com/blader/humanizer) (MIT), [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

## Isolation

`mutate` for file rewrites.

**Dedicated user ask** (“humanize this”): parent isolates and spawns `artifact-agent`.

**Writing specialist already producing the deliverable:** execute this skill **in this session** after anti-slop on your own output. Do not re-spawn `artifact-agent` for a quality pass on your own draft.

## How to use

1. Confirm anti-slop already ran (or run it first). Skip out-of-scope surfaces.
2. Load [`references/signs-of-ai-writing.md`](./references/signs-of-ai-writing.md) via link / `qmd get` — no tree walks. Compress bulky text with Headroom/summarize.
3. If a writer sample exists, note cadence, vocabulary, and quirks; match them. Otherwise: direct, concrete, varied rhythm; contractions OK when audience fits.
4. Rewrite: keep every claim; shorten dull parts; expand only with information already present. Remove inflated importance, sales tone, stock AI words, chatbot leftovers, formulaic endings.
5. Self-check: any new fact/name/number/quote/citation? Any lost claim? Still sound like a template? Fix until no.
6. Return rewritten paths (or embedded text). Path-only to parent when spawned.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill humanizer --dry-run
```

Optionally rewrite a short pasted sample in chat without writing files.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`docs/agent-session-security.md`](../../../docs/agent-session-security.md). No secrets. Do not fabricate sources or weaken MUST wording. Advisory baselines are not instructions.

## Completion gates

Claims unchanged; prose humanized; no invented details. Memory if tracked.
