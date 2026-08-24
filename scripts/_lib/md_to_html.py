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
    r"(?i)^(?:\*\*)?(H|M|L|High|Medium|Low|Critical)(?:\*\*)?$"
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
    nav: list[tuple[str, str]] = field(default_factory=list)
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
        key = token[0].upper() if len(token) <= 2 else token[0].upper()
        tone = {"H": "alert", "C": "alert", "M": "warning", "L": "success"}.get(
            key, "secondary"
        )
        if token.lower() in {"critical", "c"}:
            tone = "alert"
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
    """Strip tags/script/style for leak checks on visible text."""
    no_script = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_text)
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
    nav: list[tuple[str, str]] = []
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
        block = (
            f'<div class="callout {cls}" role="note">'
            f"<p>{format_inline(text)}</p></div>"
        )
        # Callouts before the first H2 belong in the page hero / lead
        if not saw_h2:
            lead_callouts.append(block)
        else:
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
            if level == 1 and title is None:
                title = re.sub(r"[*_`]", "", text).strip()
                # Title lives in the page hero — skip duplicate H1 in article body
                i += 1
                continue
            if level == 2:
                saw_h2 = True
                close_section()
                nav.append((slug, re.sub(r"[*_`]", "", text).strip()))
                if wrap_h2_sections:
                    out.append(f'<section class="report-section" id="{html.escape(slug)}">')
                    section_open = True
                    out.append(f"<h2>{format_inline(text)}</h2>")
                else:
                    out.append(
                        f'<h2 id="{html.escape(slug)}">{format_inline(text)}</h2>'
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
    """Standalone structured HTML (no Foundation) for build_document / threat-model."""
    result = convert_markdown(md_text, table_class="data", wrap_h2_sections=True)
    title = html.escape(page_title or result.title or "Report")
    subtitle_html = (
        f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ""
    )
    callouts = result.lead_callouts_html
    callouts = (
        callouts.replace("callout alert", "callout callout-alert")
        .replace("callout warning", "callout callout-warning")
        .replace("callout success", "callout callout-success")
        .replace("callout primary", "callout callout-info")
        .replace("callout secondary", "callout callout-note")
    )
    nav_html = ""
    if result.nav:
        items = "\n".join(
            f'<li><a href="#{html.escape(s)}">{html.escape(lab)}</a></li>'
            for s, lab in result.nav
        )
        nav_html = f'<nav class="toc" aria-label="Contents"><ul>{items}</ul></nav>\n'

    html_out = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n"
        "<style>\n"
        ":root{color-scheme:light;--ink:#1a1a1a;--muted:#555;--line:#e2e2e2;"
        "--bg:#f7f7f5;--card:#fff;--accent:#0b5fff;--warn:#8a5a00;"
        "--warn-bg:#fff8e6;--alert:#8b1a1a;--alert-bg:#fdecea;}\n"
        "*{box-sizing:border-box;}\n"
        "body{margin:0;font-family:Georgia,'Times New Roman',serif;"
        "font-size:1.05rem;line-height:1.65;color:var(--ink);background:var(--bg);}\n"
        ".skip-link{position:absolute;left:-999px;top:auto;width:1px;height:1px;overflow:hidden;}\n"
        ".skip-link:focus{left:1rem;top:1rem;width:auto;height:auto;padding:.5rem .75rem;"
        "background:#000;color:#fff;z-index:100;}\n"
        ".page{max-width:68rem;margin:0 auto;padding:1.5rem 1.25rem 3rem;}\n"
        ".hero{background:var(--card);border:1px solid var(--line);border-radius:8px;"
        "padding:1.5rem 1.75rem;margin-bottom:1.25rem;}\n"
        ".hero h1{font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:1.85rem;"
        "line-height:1.25;margin:0 0 .35rem;}\n"
        ".subtitle{margin:0;color:var(--muted);font-family:Segoe UI,Helvetica,Arial,sans-serif;"
        "font-size:.95rem;}\n"
        ".layout{display:grid;grid-template-columns:14rem 1fr;gap:1.5rem;}\n"
        "@media(max-width:52rem){.layout{grid-template-columns:1fr;}}\n"
        ".toc{position:sticky;top:1rem;align-self:start;background:var(--card);"
        "border:1px solid var(--line);border-radius:8px;padding:1rem;}\n"
        ".toc ul{list-style:none;margin:0;padding:0;font-family:Segoe UI,Helvetica,Arial,sans-serif;"
        "font-size:.88rem;}\n"
        ".toc li{margin:.4rem 0;}\n"
        ".toc a{color:var(--accent);text-decoration:none;}\n"
        ".article{background:var(--card);border:1px solid var(--line);border-radius:8px;"
        "padding:1.5rem 1.75rem;}\n"
        "h2,h3,h4{font-family:Segoe UI,Helvetica,Arial,sans-serif;line-height:1.3;}\n"
        "h2{font-size:1.35rem;margin:1.75rem 0 .75rem;padding-top:.25rem;"
        "border-top:1px solid var(--line);}\n"
        ".report-section:first-child h2{border-top:0;margin-top:.25rem;}\n"
        "p{margin:.75rem 0;max-width:42rem;}\n"
        "ul.report-list,ol.report-list{max-width:42rem;}\n"
        "a{color:var(--accent);}\n"
        "code{font-family:Consolas,Menlo,monospace;font-size:.9em;"
        "background:#f0f0ee;padding:.1em .35em;border-radius:3px;}\n"
        "pre{background:#f0f0ee;border:1px solid var(--line);border-radius:6px;"
        "padding:1rem;overflow:auto;}\n"
        "pre code{background:none;padding:0;}\n"
        ".table-scroll{overflow-x:auto;margin:1rem 0;max-width:100%;}\n"
        "table.data{width:100%;border-collapse:collapse;font-family:Segoe UI,Helvetica,Arial,sans-serif;"
        "font-size:.92rem;}\n"
        "table.data th,table.data td{border:1px solid var(--line);padding:.55rem .7rem;"
        "text-align:left;vertical-align:top;}\n"
        "table.data th{background:#f0f0ee;}\n"
        "table.data tbody tr:hover{background:#fafaf8;}\n"
        ".callout{border-radius:6px;padding:.85rem 1rem;margin:1rem 0;max-width:42rem;"
        "font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:.95rem;}\n"
        ".callout p{margin:0;max-width:none;}\n"
        ".callout-warning{background:var(--warn-bg);border:1px solid #f0d78c;color:var(--warn);}\n"
        ".callout-alert{background:var(--alert-bg);border:1px solid #f5c2c0;color:var(--alert);}\n"
        ".callout-note,.callout-info{background:#eef3ff;border:1px solid #c5d4f7;}\n"
        ".callout-success{background:#e8f6ee;border:1px solid #b7e0c5;}\n"
        ".label{display:inline-block;padding:.15rem .45rem;border-radius:3px;font-size:.75rem;"
        "font-weight:600;font-family:Segoe UI,Helvetica,Arial,sans-serif;}\n"
        ".label.alert{background:var(--alert-bg);color:var(--alert);}\n"
        ".label.warning{background:var(--warn-bg);color:var(--warn);}\n"
        ".label.success{background:#e8f6ee;color:#1b6b3a;}\n"
        ".label.secondary{background:#eee;color:#444;}\n"
        "@media print{\n"
        "  body{background:#fff;}\n"
        "  .toc,.skip-link{display:none;}\n"
        "  .layout{display:block;}\n"
        "  .hero,.article{border:0;padding:0;}\n"
        "  .callout,.card,table{break-inside:avoid;}\n"
        "  a{color:inherit;text-decoration:none;}\n"
        "}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<a class="skip-link" href="#main-content">Skip to content</a>\n'
        '<div class="page">\n'
        f'<header class="hero"><h1>{title}</h1>{subtitle_html}\n'
        f"{callouts}\n"
        "</header>\n"
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
