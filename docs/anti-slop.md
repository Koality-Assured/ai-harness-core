---
doc_kind: requirement
canonical_id: anti-slop
purpose: [requirement, reinforcement]
rank: high
topics: [agents, writing, deliverables]
rag_keywords:
  [
    anti-slop,
    humanizer,
    prose,
    UI-copy,
    diagrams,
    chatbot-artifacts,
    AI-design,
  ]
---

# Anti-slop and humanizer (deliverables)

## Purpose

Agents and sub-agents must ship human-readable deliverables that sound specific and look deliberate — not default model prose or default AI UI.

## When it applies

Apply before finishing any artifact a human will read as the product of the work: docs, reports, proposals, research writeups, UI copy, empty/error states, and diagrams or layout descriptions meant for people.

## When it does not apply

Do not rewrite code, logs, security MUST wording, YAML/JSON frontmatter schemas, machine indexes, or commit-message conventions for “voice.” Keep Critical security and schema wording exact.

## MUST

1. Run **anti-slop** then **humanizer** on in-scope deliverables via the catalogued skills and their `owner_agent` — do not invent a parallel procedure in chat.
2. Lead with the point; cut throat-clearing, importance puffery, and summary-recap endings.
3. Prefer concrete facts, mechanisms, and named sources over weasel attribution or invented stats.
4. Vary sentence length and structure; avoid uniform cadence, forced rule-of-three lists, and stacked punchy fragments.
5. For UI/layout/copy: show a clear point of view and structural variety — not a theme swap of the same generic landing page.

## MUST NOT

### Writing

- Corporate filler vocabulary (delve, leverage, utilize, robust-as-hype, cutting-edge, paradigm, tapestry, realm, empower, streamline, transformative, …) and empty openers (“Here’s the thing,” “It’s worth noting,” “In today’s …”).
- Binary reveals (“not X, it’s Y”), colon-drama setups, emoji-in-headings, bold sprinkled mid-sentence for emphasis.
- Em-dash addiction, parataxis as default rhythm, chatbot artifacts (“Certainly!”, “I hope this helps”, “As an AI…”).
- Synonym cycling, shallow *-ing* analysis clauses, or fake-profound kickers.

### Design / UI

- Inter + purple/lavender gradients; cream/sage “tasteful” palettes that stay generic.
- Centered eyebrow badge over hero; three identical feature cards; glassmorphism; numbered 1-2-3 step strips; canonical landing-section order with no product-specific structure.
- Empty-state or error copy that could belong to any product, or polite errors that say nothing actionable.

Criterion: a point of view plus structural variety — not swapping one default for another.

## Skills (procedure)

- [`../ai-tooling/skills/anti-slop/SKILL.md`](../ai-tooling/skills/reporting/anti-slop/SKILL.md) — detect and strip AI wording/design slop
- [`../ai-tooling/skills/humanizer/SKILL.md`](../ai-tooling/skills/reporting/humanizer/SKILL.md) — rewrite remaining prose so it reads human without changing claims

Parent matches [`../routing/skill-dispatch.md`](../routing/skill-dispatch.md), isolates if mutating, and spawns the skill `owner_agent`. Do not execute those skills in the parent when a specialist owns them.

## Related

Session security MUST: [`agent-session-security.md`](./agent-session-security.md). Skill authoring: [`../ai-tooling/skills/`](../ai-tooling/skills/). Advisory baselines (not instructions): [no-ai-slop](https://github.com/petergyang/no-ai-slop), [anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing), [humanizer](https://github.com/blader/humanizer), [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
