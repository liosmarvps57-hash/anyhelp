#!/usr/bin/env python3
"""Gera os SVGs-fonte da identidade AnyHelp (ícone e logos).

Os textos viram curvas (paths) a partir da fonte Sora do manual da marca,
então os SVGs não dependem de fonte instalada.

Uso:  python branding/tools/build_svgs.py      (requer: pip install fonttools)
Depois rode make_icons.py para gerar PNG/ICO.
"""
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"
OUT = ROOT / "source"

# Paleta oficial (Manual da Marca RZ System, seção 3.1)
NEON = "#00CFFF"
ELETRICO = "#008DFF"
MARINHO = "#061B3D"
PRETO = "#020B18"
BRANCO = "#FFFFFF"
CINZA = "#BFC9D9"


def text_path(font_file: str, text: str, size: float, tracking: float = 0.0):
    """Retorna (d, largura, altura_maiusc) do texto convertido em curvas, baseline em y=0."""
    font = TTFont(FONTS / font_file)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    scale = size / upm
    pen = SVGPathPen(gs)
    x = 0.0
    for i, ch in enumerate(text):
        gname = cmap[ord(ch)]
        glyph = gs[gname]
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x, 0))
        glyph.draw(tpen)
        x += glyph.width * scale
        if i < len(text) - 1:
            x += tracking
    bp = BoundsPen(gs)
    gs[cmap[ord("H")]].draw(bp)
    cap = bp.bounds[3] * scale
    return pen.getCommands(), x, cap


def defs(uid: str, glow: float) -> str:
    return f"""
  <defs>
    <linearGradient id="{uid}g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{NEON}"/>
      <stop offset="1" stop-color="{ELETRICO}"/>
    </linearGradient>
    <linearGradient id="{uid}bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{MARINHO}"/>
      <stop offset="1" stop-color="{PRETO}"/>
    </linearGradient>
    <filter id="{uid}glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="{glow}" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>"""


def outline_letters(d, tx, ty, uid, width, W, H, glow=True, fill=None):
    """Contorno só do lado de fora das letras: a máscara esconde a parte interna do traço,
    o que também apaga as sobreposições internas dos glifos da fonte variável."""
    t = f"translate({tx:.1f} {ty:.1f})"
    inner = f'<path d="{d}" transform="{t}" fill="{fill}"/>' if fill else ""
    return f"""<mask id="{uid}m" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect width="{W}" height="{H}" fill="#fff"/>
    <path d="{d}" transform="{t}" fill="#000"/>
  </mask>
  {inner}
  <g{f' filter="url(#{uid}glow)"' if glow else ''}>
    <g mask="url(#{uid}m)"><path d="{d}" transform="{t}" fill="none" stroke="url(#{uid}g)" stroke-width="{width * 2}" stroke-linejoin="round"/></g>
  </g>"""


def frame(x, y, w, h, arm, sw, uid, notch=True, arrows=True, arrow=0):
    """Moldura de colchetes do manual: cantos abertos + setas laterais."""
    g = f"url(#{uid}g)"
    r = x + w
    b = y + h
    parts = []
    # canto sup. esquerdo (longo) e inf. direito (longo), como no logo RZ
    long_arm = arm * 1.9
    parts.append(f"M{x + long_arm} {y} H{x} V{y + arm}")
    parts.append(f"M{r - long_arm} {b} H{r} V{b - arm}")
    # canto sup. direito e inf. esquerdo (curtos)
    parts.append(f"M{r - arm} {y} H{r} V{y + arm}")
    parts.append(f"M{x + arm} {b} H{x} V{b - arm}")
    if notch:
        # degrau no topo e na base (detalhe "circuito" do manual)
        step = sw * 1.6
        parts.append(f"M{x + long_arm + sw * 2} {y} H{x + long_arm + sw * 4} L{x + long_arm + sw * 4 + step} {y + step}")
        parts.append(f"M{r - long_arm - sw * 2} {b} H{r - long_arm - sw * 4} L{r - long_arm - sw * 4 - step} {b - step}")
    d = " ".join(parts)
    out = [f'<path d="{d}" fill="none" stroke="{g}" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter"/>']
    if arrows:
        a = arrow or sw * 2.6
        cy = y + h / 2
        gap = sw * 2.2
        out.append(f'<path d="M{x - gap} {cy - a} L{x - gap - a * 1.1} {cy} L{x - gap} {cy + a} Z" fill="{NEON}"/>')
        out.append(f'<path d="M{r + gap} {cy - a} L{r + gap + a * 1.1} {cy} L{r + gap} {cy + a} Z" fill="{ELETRICO}"/>')
    return "\n    ".join(out)


def icon(small: bool) -> str:
    """Ícone do app (1024x1024). small=True é a versão simplificada para 16–32 px."""
    S = 1024
    uid = "s" if small else "i"
    radius = 230
    d, tw, cap = text_path("Sora-Bold.ttf", "AH", 400 if small else 330, tracking=22 if small else 26)
    tx = (S - tw) / 2
    ty = S / 2 + cap / 2
    if small:
        fr = frame(150, 230, 724, 564, arm=150, sw=64, uid=uid, notch=False, arrows=False)
        letters = f'<path d="{d}" transform="translate({tx:.1f} {ty:.1f})" fill="{BRANCO}"/>'
        glow = 0
    else:
        fr = frame(190, 270, 644, 484, arm=120, sw=26, uid=uid, notch=False, arrows=True, arrow=52)
        letters = outline_letters(d, tx, ty, uid, 13, S, S, fill=PRETO + "66")
        glow = 10
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">{defs(uid, glow or 1)}
  <rect x="16" y="16" width="{S - 32}" height="{S - 32}" rx="{radius}" fill="url(#{uid}bg)"/>
  <rect x="16" y="16" width="{S - 32}" height="{S - 32}" rx="{radius}" fill="none" stroke="{NEON}" stroke-opacity="0.28" stroke-width="{10 if small else 6}"/>
  <g{'' if small else f' filter="url(#{uid}glow)"'}>
    {fr}
  </g>
  {letters}
</svg>
"""


def tray() -> str:
    """Ícone da bandeja do Windows: fundo transparente, alto contraste."""
    S = 256
    d, tw, cap = text_path("Sora-Bold.ttf", "AH", 118, tracking=6)
    tx = (S - tw) / 2
    ty = S / 2 + cap / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">{defs("t", 1)}
  <rect x="8" y="8" width="{S - 16}" height="{S - 16}" rx="56" fill="url(#tg)"/>
  <path d="{d}" transform="translate({tx:.1f} {ty:.1f})" fill="{BRANCO}"/>
</svg>
"""


def logo(theme: str) -> str:
    """Logo horizontal [ ANYHELP ] para a tela inicial do app (proporção 5:1)."""
    W, H = 1000, 200
    uid = "l" + theme[0]
    d, tw, cap = text_path("Sora-SemiBold.ttf", "ANYHELP", 104, tracking=16)
    fx, fy, fw, fh = 70, 26, W - 140, H - 52
    tx = (W - tw) / 2
    ty = H / 2 + cap / 2
    if theme == "dark":
        letters = outline_letters(d, tx, ty, uid, 5, W, H)
        glow = 4
    else:
        letters = f'<path d="{d}" transform="translate({tx:.1f} {ty:.1f})" fill="url(#{uid}g)"/>'
        glow = 0.01
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{defs(uid, glow)}
  <g{' filter="url(#' + uid + 'glow)"' if theme == 'dark' else ''}>
    {frame(fx, fy, fw, fh, arm=40, sw=8, uid=uid, notch=False, arrows=True, arrow=17)}
  </g>
  {letters}
</svg>
"""


def lockup(theme: str) -> str:
    """Assinatura para site/documentos: logo + 'por RZ SYSTEM'."""
    W, H = 1000, 270
    uid = "k" + theme[0]
    base = logo(theme).split("\n", 1)[1].rsplit("</svg>", 1)[0]
    base = base.replace(f'id="l{theme[0]}', f'id="{uid}').replace(f'#l{theme[0]}', f'#{uid}')
    d, tw, cap = text_path("Sora-SemiBold.ttf", "POR RZ SYSTEM", 30, tracking=9)
    color = CINZA if theme == "dark" else MARINHO
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
{base}
  <path d="{d}" transform="translate({(W - tw) / 2:.1f} {236:.1f})" fill="{color}"/>
</svg>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "icon.svg": icon(small=False),
        "icon-small.svg": icon(small=True),
        "tray.svg": tray(),
        "logo-dark.svg": logo("dark"),
        "logo-light.svg": logo("light"),
        "lockup-dark.svg": lockup("dark"),
        "lockup-light.svg": lockup("light"),
    }
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print("gerado", OUT / name)


if __name__ == "__main__":
    main()
