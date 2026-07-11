"""One-off builder: emits dark_mode.svg / light_mode.svg for Varke/Varke."""
import html

import os
REPO = os.path.dirname(os.path.abspath(__file__))
ART = open(f"{REPO}/ascii_source.txt").read().split("\n")

# geometry
ART_X, ART_Y0, ART_FS, ART_LH = 15, 24, 10, 12
PAN_X, PAN_FS, PAN_LH = 575, 16, 20
LINE_W = 56          # panel width in chars
SVG_W = 1130
SVG_H = 545

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", stroke="", text="#c9d1d9", key="#ffa657",
                          value="#a5d6ff", cc="#616e7f", add="#3fb950",
                          delc="#f85149"),
    "light_mode.svg": dict(bg="#ffffff", stroke="#d0d7de", text="#24292f", key="#953800",
                           value="#0a3069", cc="#6e7781", add="#1a7f37",
                           delc="#cf222e"),
}


def esc(s):
    return html.escape(s, quote=False)


def kv(key, value, key_cls="key", vid=None, did=None):
    """'. Key: .... value' justified to LINE_W chars."""
    prefix = f". {key}: "
    ndots = LINE_W - len(prefix) - len(value) - 1
    dots = "." * max(ndots, 2)
    did_attr = f' id="{did}"' if did else ""
    vid_attr = f' id="{vid}"' if vid else ""
    return (f'<tspan class="cc">. </tspan><tspan class="{key_cls}">{esc(key)}</tspan>:'
            f'<tspan class="cc"{did_attr}> {dots} </tspan>'
            f'<tspan class="value"{vid_attr}>{esc(value)}</tspan>')


def kv2(key1, v1, key2, v2, ids1, ids2, left_w=26):
    """Two stats on one line: '. K1: .. v1 | K2: .. v2'."""
    p1 = f". {key1}: "
    d1 = "." * max(left_w - len(p1) - len(v1) - 1, 2)
    p2 = f" | {key2}: "
    d2 = "." * max(LINE_W - left_w - len(p2) - len(v2) - 1, 2)
    return (f'<tspan class="cc">. </tspan><tspan class="key">{esc(key1)}</tspan>:'
            f'<tspan class="cc" id="{ids1}_dots"> {d1} </tspan>'
            f'<tspan class="value" id="{ids1}">{esc(v1)}</tspan>'
            f' | <tspan class="key">{esc(key2)}</tspan>:'
            f'<tspan class="cc" id="{ids2}_dots"> {d2} </tspan>'
            f'<tspan class="value" id="{ids2}">{esc(v2)}</tspan>')


def header(label):
    if label:
        pad = LINE_W - len(label) - 3
        return f'{esc(label)} ' + "—" * pad + "-"
    return ""


def panel_lines():
    L = []
    L.append(('plain', 'alexey@dobrikov ' + "—" * (LINE_W - 17) + '-'))
    L.append(('raw', kv("OS", "macOS, Linux")))
    L.append(('raw', kv("Uptime", "27 years, 4 months, 28 days", vid="age_data", did="age_data_dots")))
    L.append(('raw', kv("Kernel", "Backend Software Engineer")))
    L.append(('raw', kv("IDE", "PyCharm, VS Code")))
    L.append(('gap', ''))
    L.append(('raw', kv("Languages.Programming", "Python, TypeScript, SQL")))
    L.append(('raw', kv("Languages.Real", "Russian, English")))
    L.append(('gap', ''))
    L.append(('plain', '- Contact ' + "—" * (LINE_W - 11) + '-'))
    L.append(('raw', kv("Telegram", "t.me/og_daddy")))
    L.append(('gap', ''))
    L.append(('plain', '- GitHub Stats ' + "—" * (LINE_W - 16) + '-'))
    L.append(('raw', kv2("Repos", "0", "Contributed", "0", "repo_data", "contrib_data")))
    L.append(('raw', kv2("Stars", "0", "Followers", "0", "star_data", "follower_data")))
    L.append(('raw', kv("Commits", "0", vid="commit_data", did="commit_data_dots")))
    L.append(('raw', (f'<tspan class="cc">. </tspan><tspan class="key">Lines of Code</tspan>:'
                      f'<tspan class="cc" id="loc_data_dots"> .. </tspan>'
                      f'<tspan class="value" id="loc_data">0</tspan>'
                      f' ( <tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>,'
                      f' <tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )')))
    return L


def build(theme):
    t = THEMES[theme]
    stroke = f' stroke="{t["stroke"]}" stroke-width="1"' if t["stroke"] else ""
    parts = []
    parts.append("<?xml version='1.0' encoding='UTF-8'?>")
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,Menlo,monospace" width="{SVG_W}px" height="{SVG_H}px" font-size="{PAN_FS}px">')
    parts.append(f'''<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {t["key"]};}}
.value {{fill: {t["value"]};}}
.addColor {{fill: {t["add"]};}}
.delColor {{fill: {t["delc"]};}}
.cc {{fill: {t["cc"]};}}
text, tspan {{white-space: pre;}}
</style>''')
    parts.append(f'<rect x="0.5" y="0.5" width="{SVG_W - 1}px" height="{SVG_H - 1}px" fill="{t["bg"]}" rx="15"{stroke}/>')

    # ascii art
    parts.append(f'<text x="{ART_X}" y="{ART_Y0}" fill="{t["text"]}" font-size="{ART_FS}px" class="ascii">')
    y = ART_Y0
    for line in ART:
        parts.append(f'<tspan x="{ART_X}" y="{y}">{esc(line) if line else " "}</tspan>')
        y += ART_LH
    parts.append('</text>')

    # info panel
    lines = panel_lines()
    n_rows = sum(1 for k, _ in lines if k != 'gap')
    n_gaps = sum(1 for k, _ in lines if k == 'gap')
    block_h = (n_rows - 1) * PAN_LH + n_gaps * (PAN_LH // 2)
    y = (SVG_H - block_h) // 2
    parts.append(f'<text x="{PAN_X}" y="{y}" fill="{t["text"]}">')
    for kind, content in lines:
        if kind == 'gap':
            y += PAN_LH // 2
            continue
        if kind == 'plain':
            parts.append(f'<tspan x="{PAN_X}" y="{y}">{esc(content)}</tspan>')
        else:
            parts.append(f'<tspan x="{PAN_X}" y="{y}">{content}</tspan>')
        y += PAN_LH
    parts.append('</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


for name in THEMES:
    with open(f"{REPO}/{name}", "w") as f:
        f.write(build(name))
    print("wrote", name)
