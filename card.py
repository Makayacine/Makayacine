"""Build card.svg: an LED name banner, the contribution heatmap, and the ASCII portrait (art.py)
"printing" line by line beside a neofetch-style panel, all in terminal green.

Everything comes from public GitHub pages and the REST API, so no token is needed; the Action
passes its GITHUB_TOKEN to the API only to stay clear of the anonymous rate limit.

    python card.py
"""
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
USER = "Makayacine"
WIDTH = 54                 # info panel width in characters; every dotted line is padded to it
ART_PX, ART_LINE = 13, 16  # portrait font size and line height
INFO_PX = 15
CHAR_W = 0.6               # monospace advance in em (Consolas 0.55, Menlo/DejaVu 0.6): size for the wider
C = dict(bg="#0d1117", text="#3fb950", key="#56d364", value="#aff5b4", dots="#2c5d36", led="#3fb950")
HEAT = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]  # GitHub's dark contribution levels 0-4

NAME = "VINCE MBANZE"
PITCH = 14  # px between LED dots in the name banner
GLYPHS = {  # 5x7 dot-matrix letters, top row first
    "V": "10001 10001 10001 10001 10001 01010 00100",
    "I": "01110 00100 00100 00100 00100 00100 01110",
    "N": "10001 11001 10101 10011 10001 10001 10001",
    "C": "01110 10001 10000 10000 10000 10001 01110",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "B": "11110 10001 10001 11110 10001 10001 11110",
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "Z": "11111 00001 00010 00100 01000 10000 11111",
    " ": "00000 00000 00000 00000 00000 00000 00000",
}
BANNER_H = 7 * PITCH + 30
CELL, STEP = 13, 17         # heatmap square and its pitch
HEAT_H = 54 + 7 * STEP + 10  # title + month labels + 7 weekday rows


def get(url, token=False):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    if token and os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def api(path):
    return json.loads(get(f"https://api.github.com/{path}", token=True))


def contributions():
    """The public calendar GitHub draws on the profile: (total, [(date, level 0-4), ...])."""
    html = get(f"https://github.com/users/{USER}/contributions")
    days = sorted((dt.date.fromisoformat(d), int(l))
                  for d, l in re.findall(r'<td[^>]*data-date="([\d-]+)"[^>]*data-level="(\d)"', html))
    total = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    assert days and total, "GitHub changed its contribution calendar markup"
    return total.group(1), days


def info():
    user = api(f"users/{USER}")
    commits = api(f"search/commits?q=author:{USER}")["total_count"]  # public commits on default branches
    return [
        "vince@mbanze",
        ("OS", "Windows 11, Linux containers"),
        ("Host", "Nexusnode Research"),
        ("Kernel", "Quantitative Developer"),
        ("IDE", "VS Code, Jupyter"),
        ("Location", "Johannesburg, South Africa"),
        None,
        ("Languages.Programming", "Python, SQL, Bash"),
        ("Stack.Data", "pandas, PySpark, DuckDB, Delta Lake"),
        ("Cloud.AWS", "Glue, ECS, Lambda, Redshift, DynamoDB"),
        ("Cloud.Azure", "SQL Database, Blob Storage"),
        ("Domains", "credit risk, rates, market data"),
        None,
        "- Contact",
        ("GitHub", USER),
        None,
        "- GitHub Stats",
        ("Repos", f"{user['public_repos']:,}"),
        ("Commits", f"{commits:,}"),
        ("Followers", f"{user['followers']:,}"),
    ]


def banner(width):
    """NAME as an LED panel: lit dots glow, unlit ones stay faint."""
    rows = ["0".join(GLYPHS[ch].split()[r] for ch in NAME) for r in range(7)]
    x0 = (width - (len(rows[0]) - 1) * PITCH) / 2
    lit, unlit = [], []
    for r, row in enumerate(rows):
        for i, bit in enumerate(row):
            (lit if bit == "1" else unlit).append(f'<circle cx="{x0 + i * PITCH:.0f}" cy="{25 + r * PITCH}" r="5"/>')
    return [f'<g fill="{C["dots"]}" opacity="0.5">', *unlit, "</g>",
            f'<g fill="{C["led"]}" filter="url(#glow)">', *lit, "</g>"]


def heatmap(width, top):
    total, days = contributions()
    weeks = (days[-1][0] - days[0][0]).days // 7 + 1
    x0 = (width - weeks * STEP + 40) / 2  # 40 px of weekday labels on the left
    grid = top + 34
    out = [f'<text x="{x0 - 40}" y="{top + 4}" font-size="15" fill="{C["text"]}">'
           f'{total} contributions in the last year</text>']
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{x0 - 40}" y="{grid + row * STEP + 11}" font-size="11" fill="{C["dots"]}">{label}</text>')
    last_month = None
    for d, level in days:
        col, row = (d - days[0][0]).days // 7, (d.weekday() + 1) % 7  # Sunday is row 0, as on GitHub
        x = x0 + col * STEP
        if row == 0 and d.month != last_month and col < weeks - 2:
            out.append(f'<text x="{x:.0f}" y="{top + 26}" font-size="11" fill="{C["dots"]}">{d:%b}</text>')
            last_month = d.month
        glow = ' filter="url(#glow)"' if level else ""
        out.append(f'<rect x="{x:.0f}" y="{grid + row * STEP}" width="{CELL}" height="{CELL}" rx="3" '
                   f'fill="{HEAT[level]}"{glow}/>')
    return out


def tspans(entry):
    if entry is None:
        return ""
    if isinstance(entry, str):  # a heading, ruled out to the panel width
        return f'{escape(entry)} <tspan fill="{C["dots"]}">{"-" * (WIDTH - len(entry) - 1)}</tspan>'
    key, value = entry
    dots = "." * (WIDTH - len(f". {key}:  {value}"))
    assert len(dots) >= 2, f"{key} is too long for the {WIDTH}-character panel"
    return (f'<tspan fill="{C["dots"]}">. </tspan><tspan fill="{C["key"]}">{escape(key)}</tspan>:'
            f'<tspan fill="{C["dots"]}"> {dots} </tspan><tspan fill="{C["value"]}">{escape(value)}</tspan>')


def svg(art, lines):
    info_x = 15 + round(max(map(len, art)) * ART_PX * CHAR_W) + 25
    width = info_x + round(WIDTH * INFO_PX * CHAR_W) + 15
    top = BANNER_H + HEAT_H + 40
    art_h = len(art) * ART_LINE
    step = min(24, art_h / len(lines))  # spread the panel over the portrait's height
    # each portrait row is its own <text> so it can fade in: the "printer" runs once, ~2.5 s
    rows = [f'<text class="p" style="animation-delay:{i * 0.08:.2f}s" x="15" y="{top + i * ART_LINE}" '
            f'font-size="{ART_PX}" fill="{C["text"]}">{escape(l)}</text>' for i, l in enumerate(art)]
    info_rows = [f'<tspan x="{info_x}" y="{top + i * step:.0f}">{tspans(e)}</tspan>' for i, e in enumerate(lines)]
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{top + art_h + 4}" '
        f'font-family="Consolas, Menlo, \'DejaVu Sans Mono\', monospace">',
        "<style>text, tspan { white-space: pre; }"  # keeps the portrait's leading spaces
        " .p { animation: print 0.2s ease-out both; } @keyframes print { from { opacity: 0; } }"
        " @media (prefers-reduced-motion: reduce) { .p { animation: none; } }</style>",
        '<filter id="glow"><feGaussianBlur stdDeviation="2.5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        f'<rect width="100%" height="100%" rx="15" fill="{C["bg"]}"/>',
        *banner(width),
        *heatmap(width, BANNER_H + 20),
        *rows,
        f'<text font-size="{INFO_PX}" fill="{C["text"]}">', *info_rows, "</text>",
        "</svg>\n",
    ])


art = (HERE / "art.txt").read_text().splitlines()
(HERE / "card.svg").write_text(svg(art, info()), encoding="utf-8")
print("wrote card.svg")
