#!/usr/bin/env python3
"""Rasteriza os SVGs de branding/source em PNG/ICO, em branding/generated.

Uso:  python branding/tools/make_icons.py
Requer: Pillow  +  (rsvg-convert no PATH  OU  pip install cairosvg)

O apply_branding.py copia os arquivos gerados para dentro do RustDesk.
Só rode isto se mudar algum SVG; os arquivos gerados já vão versionados.
"""
import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source"
OUT = ROOT / "generated"


def render(svg: str, width: int, height: int | None = None) -> Image.Image:
    path = SRC / svg
    if shutil.which("rsvg-convert"):
        args = ["rsvg-convert", "-w", str(width)]
        if height:
            args += ["-h", str(height)]
        png = subprocess.run(args + [str(path)], check=True, capture_output=True).stdout
    else:
        import cairosvg  # type: ignore

        png = cairosvg.svg2png(url=str(path), output_width=width, output_height=height)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def app_icon(size: int) -> Image.Image:
    # até 32 px usa a versão simplificada (legível); acima, a versão neon completa
    return render("icon-small.svg" if size <= 32 else "icon.svg", size)


def save_ico(path: Path, frames: list[Image.Image]):
    frames = sorted(frames, key=lambda im: im.width, reverse=True)
    frames[0].save(path, format="ICO", sizes=[(f.width, f.height) for f in frames],
                   append_images=frames[1:])


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Ícone do executável / instalador / atalhos do Windows
    save_ico(OUT / "icon.ico", [app_icon(s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
    # Bandeja do sistema (fundo azul sólido, máximo contraste em 16 px)
    save_ico(OUT / "tray-icon.ico", [render("tray.svg", s) for s in (16, 20, 24, 32, 48, 64)])

    # PNGs usados pelo RustDesk em res/
    app_icon(1024).save(OUT / "icon.png")
    app_icon(1024).save(OUT / "mac-icon.png")
    app_icon(32).save(OUT / "32x32.png")
    app_icon(64).save(OUT / "64x64.png")
    app_icon(128).save(OUT / "128x128.png")
    app_icon(256).save(OUT / "128x128@2x.png")

    # Assets do Flutter: ícone interno (também vira o ícone da bandeja) e logos da tela inicial
    render("icon-small.svg", 256).save(OUT / "asset-icon.png")
    render("logo-dark.svg", 600, 120).save(OUT / "logo_dark.png")
    render("logo-light.svg", 600, 120).save(OUT / "logo_light.png")
    render("logo-dark.svg", 600, 120).save(OUT / "logo.png")

    # Site
    render("icon.svg", 512).save(OUT / "site-icon-512.png")
    render("icon-small.svg", 180).save(OUT / "apple-touch-icon.png")
    save_ico(OUT / "favicon.ico", [render("icon-small.svg", s) for s in (16, 32, 48)])

    for f in sorted(OUT.iterdir()):
        print("gerado", f.relative_to(ROOT.parent))


if __name__ == "__main__":
    main()
