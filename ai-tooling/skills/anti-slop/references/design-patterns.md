# Design / UI slop patterns

Complements writing patterns. Criterion from [`../../../../docs/anti-slop.md`](../../../../docs/anti-slop.md): **point of view + structural variety** — not a theme swap of the same generic page.

## Visual defaults to reject

| Pattern | Why it reads as slop | Prefer |
| --- | --- | --- |
| Inter + purple/lavender gradients | Default “AI SaaS” look | Distinct type + product color with intent |
| Cream/sage “tasteful” palette swap | Still a stock aesthetic | Palette grounded in brand or content |
| Centered eyebrow badge over hero | Landing-page template cue | Direct headline; skip decorative badge |
| Three identical feature cards | Forced triad + card grid | Uneven content blocks; real hierarchy |
| Glassmorphism everywhere | Decorative blur without meaning | Solid surfaces; blur only if product needs it |
| Numbered 1-2-3 step strips | Canonical onboarding chrome | Steps only when sequential work requires them |
| Canonical section order | Hero → logos → features → how-it-works → CTA with no product logic | Order that mirrors how this product is understood |
| Generic empty/error copy | “Something went wrong” / “No data yet” for any app | Actionable, product-specific next step |
| Identical icon+title+blurb tiles | Template symmetry | Vary length, density, and media |

## Diagram / layout copy

- Labels name real components; no filler (“seamless pipeline”, “powerful insights”).
- Legends explain decisions, not importance puffery.
- Avoid three equal swimlanes or boxes “for balance” when the system is asymmetric.

## Self-check

1. Could this layout belong to another product after a color swap? If yes, redesign structure.
2. Is every section earning its place for *this* audience?
3. Are empty/error states specific and actionable?
