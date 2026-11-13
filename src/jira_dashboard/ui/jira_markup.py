"""Converts Jira wiki markup to a small, safe subset of HTML for display.

All input text is HTML-escaped before any markup is applied, so the output contains only tags
produced here. No links, images or other resources are ever emitted.
"""

import html
import re

_BLOCK = re.compile(r"\{(code|noformat)(?::[^}]*)?\}(.*?)\{\1\}", re.DOTALL)
_TOKEN = re.compile(r"\x00(\d+)\x00")
_HEADING = re.compile(r"^h([1-6])\.\s+(.*)$")
_LIST = re.compile(r"^([*#-]+)\s+(.*)$")
_RULE = re.compile(r"^-{4,}$")
_PANEL_OPEN = re.compile(r"\{panel(?::([^}]*))?\}")
_IMAGE = re.compile(r"!([^!\s|]+)(?:\|[^!]*)?!")
_LINK = re.compile(r"\[([^\]|]+)\|([^\]]+)\]")
_BARE_LINK = re.compile(r"\[(https?://[^\]\s]+)\]")
_MENTION = re.compile(r"\[~([^\]]+)\]")
_MONO = re.compile(r"\{\{(.+?)\}\}")
_BOLD = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])")
_ITALIC = re.compile(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])")
_COLOR = re.compile(r"\{color(?::[^}]*)?\}")
_QUOTE = re.compile(r"\{quote\}")
_INDENT_PX = 18


def _panel(match: re.Match[str]) -> str:
    for part in (match.group(1) or "").split("|"):
        if part.startswith("title="):
            return f"<br><b>{part[len('title=') :]}</b><br>"
    return "<br>"


def _link(match: re.Match[str]) -> str:
    text, target = match.group(1), match.group(2)
    return f"{text} ({target})" if target.startswith(("http://", "https://")) else text


def _inline(text: str) -> str:
    text = _PANEL_OPEN.sub(_panel, text).replace("{panel}", "<br>")
    text = _COLOR.sub("", text)
    text = _QUOTE.sub("<br>", text)
    text = _IMAGE.sub(lambda m: f"<i>[image: {m.group(1)}]</i>", text)
    text = _MENTION.sub(lambda m: f"@{m.group(1)}", text)
    text = _LINK.sub(_link, text)
    text = _BARE_LINK.sub(lambda m: m.group(1), text)
    text = _MONO.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _ITALIC.sub(lambda m: f"<i>{m.group(1)}</i>", text)
    return text.replace("\\\\", "<br>")


def _table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        header = line.startswith("||")
        separator = "||" if header else "|"
        cells = [c.strip() for c in line.strip().strip("|").split(separator)]
        tag = "th" if header else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
    return '<table border="1" cellspacing="0" cellpadding="3">' + "".join(rows) + "</table>"


def to_html(text: str) -> str:
    blocks: list[str] = []

    def stash(match: re.Match[str]) -> str:
        blocks.append(html.escape(match.group(2).strip("\n"), quote=False))
        return f"\x00{len(blocks) - 1}\x00"

    lines = html.escape(_BLOCK.sub(stash, text.replace("\r\n", "\n")), quote=False).split("\n")
    out: list[str] = []
    counters: dict[int, int] = {}
    table: list[str] = []
    blank = False

    def flush_table() -> None:
        if table:
            out.append(_table(table))
            table.clear()

    for raw in lines:
        line = raw.strip()
        if line.startswith("|"):
            table.append(line)
            continue
        flush_table()
        if not line:
            if not blank:
                out.append("<br>")
            blank = True
            counters.clear()
            continue
        blank = False
        heading = _HEADING.match(line)
        listing = _LIST.match(line)
        if _RULE.match(line):
            out.append("<hr>")
        elif heading:
            level = min(int(heading.group(1)) + 2, 6)
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif listing:
            marker, body = listing.groups()
            depth = len(marker)
            if marker[-1] == "#":
                counters[depth] = counters.get(depth, 0) + 1
                label = f"{counters[depth]}."
            else:
                label = "•"
            margin = (depth - 1) * _INDENT_PX
            out.append(f'<div style="margin-left:{margin}px">{label} {_inline(body)}</div>')
        else:
            counters.clear()
            out.append(f"<div>{_inline(line)}</div>")
    flush_table()
    result = "".join(out)
    return _TOKEN.sub(lambda m: f"<pre>{blocks[int(m.group(1))]}</pre>", result)
