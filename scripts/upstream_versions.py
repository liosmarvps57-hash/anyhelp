#!/usr/bin/env python3
"""Lê as versões de ferramentas (Flutter, Rust, vcpkg...) que o próprio RustDesk usa
na tag escolhida, para o build do AnyHelp ficar idêntico ao oficial.

    python scripts/upstream_versions.py <pasta-do-rustdesk>   -> imprime KEY=valor
"""
import re
import sys
from pathlib import Path


def env_value(text: str, key: str) -> str:
    m = re.search(rf'^\s*{key}:\s*"?([^"\s#]+)"?', text, re.M)
    if not m:
        sys.exit(f"ERRO: {key} não encontrado no workflow do RustDesk")
    return m.group(1)


def main():
    root = Path(sys.argv[1])
    build = (root / ".github/workflows/flutter-build.yml").read_text(encoding="utf-8")
    bridge = (root / ".github/workflows/bridge.yml").read_text(encoding="utf-8")
    m = re.search(r'flutter-version:\s*"([0-9.]+)"', bridge)
    if not m:
        sys.exit("ERRO: versão do Flutter do bridge não encontrada")
    values = {
        "flutter_version": env_value(build, "FLUTTER_VERSION"),
        "llvm_version": env_value(build, "LLVM_VERSION"),
        "vcpkg_commit_id": env_value(build, "VCPKG_COMMIT_ID"),
        # o job Windows/Flutter do RustDesk compila com esta toolchain
        "windows_rust_version": env_value(build, "SCITER_RUST_VERSION"),
        "version": env_value(build, "VERSION"),
        "bridge_rust_version": env_value(bridge, "RUST_VERSION"),
        "bridge_flutter_version": m.group(1),
        "cargo_expand_version": env_value(bridge, "CARGO_EXPAND_VERSION"),
        "frb_version": env_value(bridge, "FLUTTER_RUST_BRIDGE_VERSION"),
    }
    for k, v in values.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
