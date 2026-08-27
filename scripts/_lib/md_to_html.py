"""Stdlib Markdown → structured HTML for results report pages.

Not indexed (``scripts/_lib/``). Used by ``build_foundation_site``,
``build_threat_model``, and ``build_document --html``.

Handles: YAML frontmatter strip, GFM tables, blockquotes→callouts,
headings/lists/fenced code, inline code/bold/links. Escapes text; no secrets.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from safe_href import is_safe_href, neutralize_href

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
UL_RE = re.compile(r"^[-*+]\s+(.*)$")
OL_RE = re.compile(r"^(\d+)\.\s+(.*)$")
FENCE_RE = re.compile(r"^```(\w*)\s*$")
BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SEVERITY_CELL_RE = re.compile(
    r"(?i)^(?:\*\*)?(H|M|L|C|P|F|High|Medium|Low|Critical|Informational|Info|Pass|Fail|Open|Closed)(?:\*\*)?$"
)
# Leftover GFM pipe-table row as visible text (not inside a real <table>)
PIPE_ROW_LEAK_RE = re.compile(
    r"(?<![|>])\|[^\n|]{1,120}\|[^\n|]{0,120}\|",
)
DOC_KIND_LEAK_RE = re.compile(r"(?i)\bdoc_kind\b")
FINDING_BLOCK_RE = re.compile(
    r"(<h3[^>]*>.*?</h3>)\s*(<ul class=\"report-list\">.*?</ul>)",
    re.DOTALL | re.IGNORECASE,
)
FINDING_LI_RE = re.compile(r"<li>\s*<strong>[^<]+</strong>", re.IGNORECASE)


@dataclass
class ConvertResult:
    """Structured conversion output."""

    title: str | None = None
    body_html: str = ""
    nav: list[tuple[str, str, int]] = field(default_factory=list)
    lead_callouts_html: str = ""
    frontmatter: dict[str, str] = field(default_factory=dict)


def strip_frontmatter(md_text: str) -> tuple[str, dict[str, str]]:
    """Remove leading YAML frontmatter; return (body, simple key→str map)."""
    text = md_text.lstrip("\ufeff")
    match = FRONTMATTER_RE.match(text)
    meta: dict[str, str] = {}
    if not match:
        return text, meta
    block = match.group(1)
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key and not key.startswith("#"):
            meta[key] = val
    return text[match.end() :], meta


def slugify(text: str) -> str:
    bare = re.sub(r"<[^>]+>", "", text)
    bare = re.sub(r"[*_`]", "", bare)
    slug = re.sub(r"[^a-z0-9]+", "-", bare.lower()).strip("-")
    return slug or "section"


def format_inline(text: str) -> str:
    """Escape text; apply safe inline code / bold / italic / link transforms."""
    placeholders: list[str] = []

    def hold(snippet: str) -> str:
        placeholders.append(snippet)
        return f"\x00PH{len(placeholders) - 1}\x00"

    def code_sub(m: re.Match[str]) -> str:
        return hold(f"<code>{html.escape(m.group(1))}</code>")

    def bold_sub(m: re.Match[str]) -> str:
        return hold(f"<strong>{html.escape(m.group(1))}</strong>")

    def italic_sub(m: re.Match[str]) -> str:
        return hold(f"<em>{html.escape(m.group(1))}</em>")

    def link_sub(m: re.Match[str]) -> str:
        label = html.escape(m.group(1))
        href = neutralize_href(m.group(2).strip())
        if href == "#" and not is_safe_href(m.group(2).strip()) and not m.group(2).strip().startswith("#"):
            # Drop unsafe links entirely (show label only as escaped text)
            return label
        return hold(f'<a href="{html.escape(href, quote=True)}">{label}</a>')

    work = INLINE_CODE_RE.sub(code_sub, text)
    work = BOLD_RE.sub(bold_sub, work)
    work = LINK_RE.sub(link_sub, work)
    work = ITALIC_RE.sub(italic_sub, work)
    work = html.escape(work)
    for i, snippet in enumerate(placeholders):
        work = work.replace(f"\x00PH{i}\x00", snippet)
    return work


def callout_class(text: str) -> str:
    """Pick Foundation callout tone from leading advisory words."""
    plain = re.sub(r"[*_`]", "", text).strip()
    lower = plain.lower()
    if lower.startswith(("warning", "danger", "critical", "do not")):
        return "alert"
    if lower.startswith(("advisory", "mock", "note", "caution")):
        return "warning"
    if lower.startswith(("success", "ok", "accepted")):
        return "success"
    if lower.startswith(("info", "tip")):
        return "primary"
    return "secondary"


def format_table_cell(cell: str) -> str:
    """Inline-format a cell; optional severity label badges."""
    raw = cell.strip()
    sev = SEVERITY_CELL_RE.match(raw)
    if sev:
        token = sev.group(1)
        key = token.lower()
        if key in {"critical", "c", "fail", "f"}:
            tone = "alert"
        elif key in {"high", "h", "open"}:
            tone = "alert"
        elif key in {"medium", "m", "warn", "warning"}:
            tone = "warning"
        elif key in {"low", "l", "pass", "p", "closed", "success"}:
            tone = "success"
        elif key in {"info", "informational"}:
            tone = "primary"
        else:
            tone = "secondary"
        label = html.escape(token)
        return f'<span class="label {tone}">{label}</span>'
    # Highlight **H** / High embedded at start of otherwise longer cells
    if re.match(r"(?i)^\*\*(H|High|Critical)\*\*", raw):
        return format_inline(raw)
    return format_inline(raw)


def _split_table_row(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def _is_table_start(lines: list[str], i: int) -> bool:
    if i + 1 >= len(lines):
        return False
    if not TABLE_ROW_RE.match(lines[i]):
        return False
    return bool(TABLE_SEP_RE.match(lines[i + 1]))


def text_without_tags(html_text: str) -> str:
    """Strip tags/script/style/pre/code for leak checks on visible text."""
    no_script = re.sub(r"(?is)<(script|style|pre|code)[^>]*>.*?</\1>", " ", html_text)
    return re.sub(r"<[^>]+>", " ", no_script)


def assert_html_clean(html_text: str) -> None:
    """Fail if GFM pipe-table rows or frontmatter keys leaked as visible text."""
    visible = text_without_tags(html_text)
    # Collapse whitespace for clearer matching
    flat = re.sub(r"\s+", " ", visible)
    if DOC_KIND_LEAK_RE.search(flat):
        raise ValueError(
            "conversion leak: 'doc_kind' appears as text in HTML "
            "(frontmatter was not stripped cleanly)"
        )
    # Ignore pipe characters that only appear inside code-like remnants; require
    # multi-cell GFM shape: | a | b |
    if PIPE_ROW_LEAK_RE.search(flat):
        raise ValueError(
            "conversion leak: leftover GFM pipe-table row text in HTML "
            "(table was not converted to <table>)"
        )


def maybe_wrap_finding_cards(body_html: str) -> str:
    """Cheap optional wrap: h3 + short strong-keyed list → Foundation card."""

    def repl(match: re.Match[str]) -> str:
        heading, ul = match.group(1), match.group(2)
        items = re.findall(r"<li\b.*?</li>", ul, flags=re.DOTALL | re.IGNORECASE)
        if not (2 <= len(items) <= 6):
            return match.group(0)
        if not all(FINDING_LI_RE.search(li) for li in items):
            return match.group(0)
        # Extract bare title text for card-divider
        title_html = re.sub(r"^<h3[^>]*>|</h3>$", "", heading, flags=re.IGNORECASE)
        return (
            '<div class="card finding-card">'
            f'<div class="card-divider">{title_html}</div>'
            f'<div class="card-section">{ul}</div>'
            "</div>"
        )

    return FINDING_BLOCK_RE.sub(repl, body_html)


def convert_markdown(
    md_text: str,
    *,
    table_class: str = "hover stack",
    wrap_h2_sections: bool = True,
    wrap_finding_cards: bool = False,
) -> ConvertResult:
    """Convert Markdown to structured HTML fragments."""
    body_md, meta = strip_frontmatter(md_text)
    lines = body_md.splitlines()
    out: list[str] = []
    nav: list[tuple[str, str, int]] = []
    lead_callouts: list[str] = []
    title: str | None = None
    i = 0
    in_para = False
    list_type: str | None = None
    section_open = False
    saw_h2 = False

    def close_para() -> None:
        nonlocal in_para
        if in_para:
            out.append("</p>")
            in_para = False

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    def close_section() -> None:
        nonlocal section_open
        if section_open and wrap_h2_sections:
            out.append("</section>")
            section_open = False

    def emit_callout(chunks: list[str]) -> None:
        text = " ".join(chunks).strip()
        if not text:
            return
        cls = callout_class(text)
        tone_map = {
            "alert": "callout-alert alert",
            "warning": "callout-warning warning",
            "success": "callout-success success",
            "primary": "callout-info primary info",
            "secondary": "callout-note secondary note",
        }
        callout_classes = tone_map.get(cls, f"callout-{cls} {cls}")
        block = (
            f'<div class="callout {callout_classes}" role="note">'
            f"<p>{format_inline(text)}</p></div>"
        )
        out.append(block)

    while i < len(lines):
        line = lines[i]

        # Fenced code
        fence = FENCE_RE.match(line)
        if fence:
            close_para()
            close_list()
            lang = fence.group(1) or ""
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            escaped = html.escape("\n".join(code_lines))
            out.append(f"<pre><code{cls}>{escaped}</code></pre>")
            continue

        # GFM table
        if _is_table_start(lines, i):
            close_para()
            close_list()
            headers = _split_table_row(lines[i])
            i += 2  # skip header + separator
            rows: list[list[str]] = []
            while i < len(lines) and TABLE_ROW_RE.match(lines[i]):
                rows.append(_split_table_row(lines[i]))
                i += 1
            ths = "".join(f"<th>{format_inline(h)}</th>" for h in headers)
            trs: list[str] = []
            for row in rows:
                # pad/truncate to header width
                cells = row + [""] * max(0, len(headers) - len(row))
                cells = cells[: len(headers)]
                tds = "".join(f"<td>{format_table_cell(c)}</td>" for c in cells)
                trs.append(f"<tr>{tds}</tr>")
            out.append(
                f'<div class="table-scroll"><table class="{html.escape(table_class)}">'
                f"<thead><tr>{ths}</tr></thead>"
                f"<tbody>{''.join(trs)}</tbody></table></div>"
            )
            continue

        # Blank line
        if not line.strip():
            close_para()
            close_list()
            i += 1
            continue

        # Blockquote (possibly multi-line)
        bq = BLOCKQUOTE_RE.match(line)
        if bq:
            close_para()
            close_list()
            chunks = [bq.group(1)]
            i += 1
            while i < len(lines):
                nxt = BLOCKQUOTE_RE.match(lines[i])
                if not nxt:
                    break
                chunks.append(nxt.group(1))
                i += 1
            emit_callout(chunks)
            continue

        # Heading
        heading = HEADING_RE.match(line)
        if heading:
            close_para()
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            slug = slugify(text)
            clean_text = re.sub(r"[*_`]", "", text).strip()
            if level == 1 and title is None:
                title = clean_text
                # Title lives in the page hero — skip duplicate H1 in article body
                i += 1
                continue
            if level == 2:
                saw_h2 = True
                close_section()
                nav.append((slug, clean_text, 2))
                if wrap_h2_sections:
                    out.append(f'<section class="report-section" id="{html.escape(slug)}">')
                    section_open = True
                    out.append(f"<h2>{format_inline(text)}</h2>")
                else:
                    out.append(
                        f'<h2 id="{html.escape(slug)}">{format_inline(text)}</h2>'
                    )
            elif level == 3:
                nav.append((slug, clean_text, 3))
                out.append(
                    f'<h3 id="{html.escape(slug)}">{format_inline(text)}</h3>'
                )
            else:
                tag = f"h{level}"
                out.append(
                    f'<{tag} id="{html.escape(slug)}">{format_inline(text)}</{tag}>'
                )
            i += 1
            continue

        # Lists
        ul = UL_RE.match(line)
        ol = OL_RE.match(line)
        if ul or ol:
            close_para()
            wanted = "ul" if ul else "ol"
            if list_type != wanted:
                close_list()
                list_type = wanted
                out.append(f'<{list_type} class="report-list">')
            item = ul.group(1) if ul else ol.group(2)  # type: ignore[union-attr]
            out.append(f"<li>{format_inline(item)}</li>")
            i += 1
            continue

        # Horizontal rule (not frontmatter — already stripped)
        if HR_RE.match(line):
            close_para()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        # Paragraph
        close_list()
        if not in_para:
            out.append("<p>")
            in_para = True
            out.append(format_inline(line.strip()))
        else:
            out.append(" " + format_inline(line.strip()))
        i += 1

    close_para()
    close_list()
    close_section()

    body = "\n".join(out)
    if wrap_finding_cards:
        body = maybe_wrap_finding_cards(body)
    lead = "\n".join(lead_callouts)
    # Validate body + lead (not title alone)
    assert_html_clean(f"{lead}\n{body}")

    return ConvertResult(
        title=title,
        body_html=body,
        nav=nav,
        lead_callouts_html=lead,
        frontmatter=meta,
    )


def wrap_simple_document(
    *,
    page_title: str,
    md_text: str,
    subtitle: str | None = None,
) -> str:
    """Standalone structured HTML (no external JS) for build_document / threat-model."""
    result = convert_markdown(md_text, table_class="data", wrap_h2_sections=True)
    title = html.escape(page_title or result.title or "Report")
    subtitle_html = (
        f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ""
    )
    
    meta_chips = []
    if result.frontmatter:
        label_map = {
            "doc_kind": "Kind",
            "document_type": "Type",
            "canonical_id": "Doc ID",
            "topic": "Topic",
            "date": "Date",
            "purpose": "Purpose",
            "generator": "Generator",
            "advisory": "Advisory",
        }
        priority_keys = [
            "doc_kind",
            "document_type",
            "canonical_id",
            "topic",
            "date",
            "purpose",
            "generator",
            "advisory",
        ]
        seen = set()
        for k in priority_keys:
            if k in result.frontmatter:
                seen.add(k)
                v = result.frontmatter[k]
                label = label_map.get(k, k.replace("_", " ").title())
                meta_chips.append(
                    f'<span class="meta-chip"><span class="meta-key">{html.escape(label)}</span> <span class="meta-val">{html.escape(str(v))}</span></span>'
                )
        for k, v in result.frontmatter.items():
            if k not in seen:
                label = label_map.get(k, k.replace("_", " ").title())
                meta_chips.append(
                    f'<span class="meta-chip"><span class="meta-key">{html.escape(label)}</span> <span class="meta-val">{html.escape(str(v))}</span></span>'
                )

    metadata_html = ""
    if meta_chips:
        chips_str = "\n      ".join(meta_chips)
        preview_tokens = []
        for pk in ["doc_kind", "document_type", "canonical_id", "topic"]:
            if pk in result.frontmatter:
                lbl = label_map.get(pk, pk.title())
                preview_tokens.append(f"{lbl}: {result.frontmatter[pk]}")
        summary_preview = f' &middot; <span class="meta-preview">{html.escape(" | ".join(preview_tokens))}</span>' if preview_tokens else ""
        metadata_html = (
            '  <details class="hero-meta">\n'
            f'    <summary><span class="meta-summary-label">Document metadata</span>{summary_preview}</summary>\n'
            f'    <div class="meta-chips-wrap">\n      {chips_str}\n    </div>\n'
            '  </details>\n'
        )

    nav_html = ""
    if result.nav:
        items = []
        for nav_item in result.nav:
            if len(nav_item) == 3:
                s, lab, level = nav_item
            else:
                s, lab = nav_item
                level = 2
            cls = ' class="toc-h3"' if level == 3 else ""
            items.append(f'<li{cls}><a href="#{html.escape(s)}">{html.escape(lab)}</a></li>')
        items_str = "\n".join(items)
        nav_html = (
            '<nav class="toc" aria-label="Contents">\n'
            '  <p class="toc-title">On this page</p>\n'
            f"  <ul>\n{items_str}\n  </ul>\n"
            "</nav>\n"
        )

    html_out = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n"
        "<style>\n"
        ":root {\n"
        "  color-scheme: light dark;\n"
        "  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;\n"
        "  --font-mono: ui-monospace, 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', monospace;\n"
        "  --bg-canvas: #f8fafc;\n"
        "  --bg-surface: #ffffff;\n"
        "  --bg-subtle: #f1f5f9;\n"
        "  --bg-hover: #f1f5f9;\n"
        "  --border-subtle: #e2e8f0;\n"
        "  --border-strong: #cbd5e1;\n"
        "  --text-primary: #0f172a;\n"
        "  --text-secondary: #334155;\n"
        "  --text-muted: #64748b;\n"
        "  --accent: #2563eb;\n"
        "  --accent-hover: #1d4ed8;\n"
        "  --critical-bg: #fef2f2; --critical-border: #fecaca; --critical-text: #991b1b; --critical-dot: #ef4444;\n"
        "  --warn-bg: #fffbeb;     --warn-border: #fef3c7;     --warn-text: #92400e;     --warn-dot: #f59e0b;\n"
        "  --success-bg: #f0fdf4;  --success-border: #bbf7d0;  --success-text: #166534;  --success-dot: #22c55e;\n"
        "  --info-bg: #eff6ff;     --info-border: #dbeafe;     --info-text: #1e40af;     --info-dot: #3b82f6;\n"
        "  --neutral-bg: #f8fafc;  --neutral-border: #e2e8f0;  --neutral-text: #334155;  --neutral-dot: #94a3b8;\n"
        "  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);\n"
        "  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px; --radius-pill: 9999px;\n"
        "}\n"
        "@media (prefers-color-scheme: dark) {\n"
        "  :root {\n"
        "    --bg-canvas: #0b0f17;\n"
        "    --bg-surface: #111827;\n"
        "    --bg-subtle: #1f2937;\n"
        "    --bg-hover: #1e293b;\n"
        "    --border-subtle: #1e293b;\n"
        "    --border-strong: #334155;\n"
        "    --text-primary: #f8fafc;\n"
        "    --text-secondary: #cbd5e1;\n"
        "    --text-muted: #94a3b8;\n"
        "    --accent: #3b82f6;\n"
        "    --accent-hover: #60a5fa;\n"
        "    --critical-bg: rgba(239, 68, 68, 0.12);  --critical-border: rgba(239, 68, 68, 0.3);  --critical-text: #fca5a5;\n"
        "    --warn-bg: rgba(245, 158, 11, 0.12);    --warn-border: rgba(245, 158, 11, 0.3);    --warn-text: #fde68a;\n"
        "    --success-bg: rgba(34, 197, 94, 0.12);  --success-border: rgba(34, 197, 94, 0.3);  --success-text: #86efac;\n"
        "    --info-bg: rgba(59, 130, 246, 0.12);    --info-border: rgba(59, 130, 246, 0.3);    --info-text: #93c5fd;\n"
        "    --neutral-bg: rgba(148, 163, 184, 0.12);--neutral-border: rgba(148, 163, 184, 0.3);--neutral-text: #cbd5e1;\n"
        "    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.4);\n"
        "  }\n"
        "}\n"
        "*, *::before, *::after { box-sizing: border-box; }\n"
        "body {\n"
        "  margin: 0;\n"
        "  font-family: var(--font-sans);\n"
        "  font-size: 1rem;\n"
        "  line-height: 1.65;\n"
        "  color: var(--text-primary);\n"
        "  background-color: var(--bg-canvas);\n"
        "  -webkit-font-smoothing: antialiased;\n"
        "}\n"
        ".skip-link { position: absolute; left: -999px; top: auto; width: 1px; height: 1px; overflow: hidden; }\n"
        ".skip-link:focus { left: 1rem; top: 1rem; width: auto; height: auto; padding: .5rem .75rem; background: var(--accent); color: #fff; border-radius: var(--radius-sm); z-index: 100; text-decoration: none; }\n"
        ".page { max-width: 76rem; margin: 0 auto; padding: 1.75rem 1.5rem 4rem; }\n"
        ".hero { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.25rem 1.75rem; margin-bottom: 1.5rem; box-shadow: var(--shadow-sm); }\n"
        ".hero h1 { font-size: clamp(1.4rem, 2.2vw, 1.85rem); font-weight: 700; line-height: 1.25; margin: 0 0 .25rem; letter-spacing: -0.02em; color: var(--text-primary); }\n"
        ".subtitle { margin: 0 0 .5rem; color: var(--text-muted); font-size: .92rem; }\n"
        ".hero-meta { margin-top: .6rem; border-top: 1px solid var(--border-subtle); padding-top: .5rem; font-size: .8rem; }\n"
        ".hero-meta summary { cursor: pointer; user-select: none; color: var(--text-muted); font-weight: 600; display: flex; align-items: center; gap: .5rem; list-style: none; }\n"
        ".hero-meta summary::-webkit-details-marker { display: none; }\n"
        ".hero-meta summary::before { content: '▸'; display: inline-block; font-size: .75rem; transition: transform .15s ease; }\n"
        ".hero-meta[open] summary::before { transform: rotate(90deg); }\n"
        ".meta-preview { font-weight: 400; color: var(--text-muted); font-family: var(--font-mono); font-size: .75rem; }\n"
        ".meta-chips-wrap { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .6rem; }\n"
        ".meta-chip { display: inline-flex; align-items: center; gap: .3rem; background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-pill); padding: .15rem .55rem; font-size: .75rem; font-family: var(--font-mono); }\n"
        ".meta-key { color: var(--text-muted); font-weight: 600; }\n"
        ".meta-val { color: var(--text-primary); }\n"
        ".layout { display: grid; grid-template-columns: 15rem minmax(0, 1fr); gap: 1.75rem; align-items: start; }\n"
        "@media (max-width: 56rem) { .layout { grid-template-columns: 1fr; } }\n"
        ".toc { position: sticky; top: 1.25rem; max-height: calc(100vh - 2.5rem); overflow-y: auto; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.15rem; box-shadow: var(--shadow-sm); }\n"
        ".toc-title { font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--text-muted); margin: 0 0 .65rem; }\n"
        ".toc ul { list-style: none; margin: 0; padding: 0; font-size: .88rem; }\n"
        ".toc li { margin: .25rem 0; }\n"
        ".toc li.toc-h3 { padding-left: .85rem; font-size: .82rem; }\n"
        ".toc a { display: block; color: var(--text-secondary); text-decoration: none; padding: .3rem .45rem; border-radius: var(--radius-sm); transition: background-color .15s ease, color .15s ease; line-height: 1.35; }\n"
        ".toc a:hover { background: var(--bg-hover); color: var(--accent); }\n"
        ".article { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 2rem 2.25rem; box-shadow: var(--shadow-sm); min-width: 0; }\n"
        ".report-section { scroll-margin-top: 1.5rem; }\n"
        ".report-section + .report-section { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--border-subtle); }\n"
        "h2, h3, h4 { color: var(--text-primary); font-weight: 600; letter-spacing: -0.015em; line-height: 1.3; }\n"
        "h2 { font-size: 1.4rem; margin: 0 0 .85rem; }\n"
        "h3 { font-size: 1.18rem; margin: 1.4rem 0 .55rem; }\n"
        "h4 { font-size: 1.02rem; margin: 1.15rem 0 .45rem; }\n"
        "p, ul.report-list, ol.report-list { margin: .75rem 0; color: var(--text-secondary); }\n"
        "p { max-width: 68ch; }\n"
        "ul.report-list, ol.report-list { max-width: 68ch; padding-left: 1.35rem; }\n"
        "a { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }\n"
        "a:hover { color: var(--accent-hover); }\n"
        "code { font-family: var(--font-mono); font-size: .88em; background: var(--bg-subtle); color: var(--text-primary); padding: .15em .35em; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); }\n"
        "pre { background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem 1.25rem; overflow-x: auto; font-family: var(--font-mono); font-size: .88rem; line-height: 1.5; }\n"
        "pre code { background: none; border: none; padding: 0; color: inherit; }\n"
        ".table-scroll { overflow-x: auto; margin: 1.15rem 0; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); max-width: 100%; }\n"
        "table.data { width: 100%; border-collapse: collapse; font-size: .9rem; text-align: left; }\n"
        "table.data th { background: var(--bg-subtle); color: var(--text-muted); font-weight: 600; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; padding: .7rem .9rem; border-bottom: 1px solid var(--border-subtle); }\n"
        "table.data td { padding: .7rem .9rem; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); vertical-align: top; }\n"
        "table.data tbody tr:last-child td { border-bottom: none; }\n"
        "table.data tbody tr:hover { background: var(--bg-hover); }\n"
        ".callout { border-radius: var(--radius-md); padding: .9rem 1.15rem; margin: 1.15rem 0; border: 1px solid transparent; border-left-width: 4px; font-size: .95rem; }\n"
        ".callout p { margin: 0; color: inherit; max-width: none; }\n"
        ".callout.alert, .callout-alert { background: var(--critical-bg); border-color: var(--critical-border); border-left-color: var(--critical-dot); color: var(--critical-text); }\n"
        ".callout.warning, .callout-warning { background: var(--warn-bg); border-color: var(--warn-border); border-left-color: var(--warn-dot); color: var(--warn-text); }\n"
        ".callout.success, .callout-success { background: var(--success-bg); border-color: var(--success-border); border-left-color: var(--success-dot); color: var(--success-text); }\n"
        ".callout.primary, .callout.info, .callout-info { background: var(--info-bg); border-color: var(--info-border); border-left-color: var(--info-dot); color: var(--info-text); }\n"
        ".callout.secondary, .callout.note, .callout-note { background: var(--neutral-bg); border-color: var(--neutral-border); border-left-color: var(--neutral-dot); color: var(--neutral-text); }\n"
        ".label, .badge { display: inline-flex; align-items: center; gap: .35rem; padding: .15rem .55rem; border-radius: var(--radius-pill); font-size: .72rem; font-weight: 600; letter-spacing: .03em; text-transform: uppercase; border: 1px solid transparent; white-space: nowrap; }\n"
        ".label::before, .badge::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; }\n"
        ".label.alert { background: var(--critical-bg); border-color: var(--critical-border); color: var(--critical-text); }\n"
        ".label.alert::before { background-color: var(--critical-dot); }\n"
        ".label.warning { background: var(--warn-bg); border-color: var(--warn-border); color: var(--warn-text); }\n"
        ".label.warning::before { background-color: var(--warn-dot); }\n"
        ".label.success { background: var(--success-bg); border-color: var(--success-border); color: var(--success-text); }\n"
        ".label.success::before { background-color: var(--success-dot); }\n"
        ".label.primary, .label.info { background: var(--info-bg); border-color: var(--info-border); color: var(--info-text); }\n"
        ".label.primary::before, .label.info::before { background-color: var(--info-dot); }\n"
        ".label.secondary { background: var(--neutral-bg); border-color: var(--neutral-border); color: var(--neutral-text); }\n"
        ".label.secondary::before { background-color: var(--neutral-dot); }\n"
        ".finding-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-left: 4px solid var(--accent); border-radius: var(--radius-md); margin: 1.25rem 0; box-shadow: var(--shadow-sm); overflow: hidden; }\n"
        ".finding-card .card-divider { background: var(--bg-subtle); padding: .75rem 1.15rem; font-weight: 600; font-size: .98rem; color: var(--text-primary); border-bottom: 1px solid var(--border-subtle); }\n"
        ".finding-card .card-section { padding: .9rem 1.15rem; }\n"
        ".finding-card ul { margin: 0; padding-left: 1.2rem; }\n"
        "@media print {\n"
        "  body { background: #fff !important; color: #000 !important; font-size: 10pt; }\n"
        "  .toc, .skip-link { display: none !important; }\n"
        "  .layout { display: block !important; }\n"
        "  .hero, .article, .table-scroll, .finding-card { border: none !important; box-shadow: none !important; padding: 0 !important; }\n"
        "  .callout, table, .finding-card { break-inside: avoid; }\n"
        "  a { color: #000 !important; text-decoration: underline; }\n"
        "}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<a class="skip-link" href="#main-content">Skip to content</a>\n'
        '<div class="page">\n'
        f'<header class="hero">\n  <div class="hero-title-wrap"><h1>{title}</h1>{subtitle_html}</div>\n{metadata_html}</header>\n'
        '<div class="layout">\n'
        f"{nav_html}"
        f'<article class="article" id="main-content">\n{result.body_html}\n</article>\n'
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )
    assert_html_clean(html_out)
    return html_out
