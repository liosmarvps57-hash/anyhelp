#!/usr/bin/env python3
"""Transforma um checkout do RustDesk no AnyHelp.

    python scripts/apply_branding.py <pasta-do-rustdesk>

Variáveis de ambiente (obrigatórias para um build de verdade):
    ANYHELP_SERVER   IP ou domínio da VPS com hbbs/hbbr   (ex.: 203.0.113.10)
    ANYHELP_KEY      chave pública do servidor (conteúdo de id_ed25519.pub)

Cada alteração procura um trecho exato do código original. Se o RustDesk mudar
esse trecho numa versão nova, o script PARA com erro dizendo qual arquivo e
qual trecho — nunca gera um build pela metade. Ao atualizar a versão em
anyhelp.json, rode o script; se algo quebrar, ajuste o trecho aqui.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
BRAND = PROJECT / "branding"
GEN = BRAND / "generated"

# Paleta oficial — Manual da Marca RZ System, seção 3.1
NEON = "00CFFF"
ELETRICO = "008DFF"
MARINHO = "061B3D"
PRETO = "020B18"
CINZA = "BFC9D9"


class BrandingError(Exception):
    pass


class Tree:
    def __init__(self, root: Path):
        self.root = root
        self.changed: list[str] = []

    def path(self, rel: str) -> Path:
        p = self.root / rel
        if not p.exists():
            raise BrandingError(f"arquivo não encontrado no RustDesk: {rel}")
        return p

    def sub(self, rel: str, old: str, new: str, count: int | None = 1):
        """Troca texto exato. count=None troca todas as ocorrências (mínimo 1)."""
        p = self.path(rel)
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n == 0 or (count is not None and n != count):
            raise BrandingError(
                f"{rel}: esperado {count or '>=1'} ocorrência(s) de:\n    {old!r}\n  encontrado {n}. "
                "O RustDesk mudou este trecho; ajuste scripts/apply_branding.py."
            )
        p.write_text(text.replace(old, new), encoding="utf-8")
        self.changed.append(rel)

    def resub(self, rel: str, pattern: str, repl: str, flags=0, min_count: int = 1):
        p = self.path(rel)
        text = p.read_text(encoding="utf-8")
        text2, n = re.subn(pattern, repl, text, flags=flags)
        if n < min_count:
            raise BrandingError(f"{rel}: padrão {pattern!r} não encontrado. Ajuste scripts/apply_branding.py.")
        p.write_text(text2, encoding="utf-8")
        self.changed.append(rel)
        return n

    def copy(self, src: Path, rel: str):
        dst = self.root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self.changed.append(rel)


def rust_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def rust_map(d: dict[str, str]) -> str:
    items = ", ".join(f"({rust_str(k)}.to_owned(), {rust_str(v)}.to_owned())" for k, v in d.items())
    return f"RwLock::new(HashMap::from([{items}]))"


def dart_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$") + "'"


# ---------------------------------------------------------------------------
# 1. Núcleo (Rust): nome, servidor, chave e configurações travadas
# ---------------------------------------------------------------------------
def patch_core(t: Tree, cfg: dict, server: str, key: str):
    name = cfg["app_name"]
    rel = "libs/hbb_common/src/config.rs"
    t.sub(rel,
          'pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
          f'pub static ref APP_NAME: RwLock<String> = RwLock::new({rust_str(name)}.to_owned());')
    t.resub(rel, r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
            f'pub const RENDEZVOUS_SERVERS: &[&str] = &[{rust_str(server)}];')
    t.resub(rel, r'pub const RS_PUB_KEY: &str = "[^"]*";',
            f'pub const RS_PUB_KEY: &str = {rust_str(key)};')
    t.sub(rel,
          "pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
          f"pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = {rust_map(cfg['hard_settings'])};")
    t.sub(rel,
          "pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
          f"pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = {rust_map(cfg['builtin_settings'])};")

    # Nome do emissor no app autenticador (2FA)
    t.sub("src/auth_2fa.rs", 'const ISSUER: &str = "RustDesk";', f"const ISSUER: &str = {rust_str(name)};")


# ---------------------------------------------------------------------------
# 2. Metadados do executável Windows (Propriedades > Detalhes)
# ---------------------------------------------------------------------------
def patch_windows_metadata(t: Tree, cfg: dict):
    name, company = cfg["app_name"], cfg["company"]
    year = date.today().year
    copyright_ = f"Copyright © {year} {company}. Baseado no RustDesk (AGPL-3.0)."
    for rel in ("Cargo.toml", "libs/portable/Cargo.toml"):
        t.resub(rel, r'^LegalCopyright = ".*"$', f'LegalCopyright = "{copyright_}"', flags=re.M)
        t.resub(rel, r'^ProductName = "RustDesk"$', f'ProductName = "{name}"', flags=re.M)
        t.resub(rel, r'^FileDescription = "RustDesk Remote Desktop"$', f'FileDescription = "{name} Acesso Remoto"', flags=re.M)
        t.resub(rel, r'^OriginalFilename = "rustdesk.exe"$', f'OriginalFilename = "{name}.exe"', flags=re.M)

    rc = "flutter/windows/runner/Runner.rc"
    t.resub(rc, r'VALUE "CompanyName", ".*?" "\\0"', f'VALUE "CompanyName", "{company}" "\\\\0"')
    t.resub(rc, r'VALUE "FileDescription", ".*?" "\\0"', f'VALUE "FileDescription", "{name} Acesso Remoto" "\\\\0"')
    t.resub(rc, r'VALUE "InternalName", ".*?" "\\0"', f'VALUE "InternalName", "{name}" "\\\\0"')
    t.resub(rc, r'VALUE "LegalCopyright", ".*?" "\\0"', f'VALUE "LegalCopyright", "{copyright_}" "\\\\0"')
    t.resub(rc, r'VALUE "OriginalFilename", ".*?" "\\0"', f'VALUE "OriginalFilename", "{name}.exe" "\\\\0"')
    t.resub(rc, r'VALUE "ProductName", ".*?" "\\0"', f'VALUE "ProductName", "{name}" "\\\\0"')

    # O executável final passa a se chamar AnyHelp.exe (a DLL interna continua librustdesk.dll)
    t.sub("flutter/windows/CMakeLists.txt", 'set(BINARY_NAME "rustdesk")', f'set(BINARY_NAME "{name}")')


# ---------------------------------------------------------------------------
# 3. Ícones, logos e fontes
# ---------------------------------------------------------------------------
def copy_assets(t: Tree):
    for f in ("icon.ico", "tray-icon.ico", "icon.png", "mac-icon.png",
              "32x32.png", "64x64.png", "128x128.png", "128x128@2x.png"):
        t.copy(GEN / f, f"res/{f}")
    t.copy(GEN / "icon.ico", "flutter/windows/runner/resources/app_icon.ico")
    t.copy(BRAND / "source/icon.svg", "res/scalable.svg")
    t.copy(BRAND / "source/icon.svg", "res/logo.svg")

    t.copy(GEN / "asset-icon.png", "flutter/assets/icon.png")
    t.copy(BRAND / "source/icon-small.svg", "flutter/assets/icon.svg")
    for f in ("logo.png", "logo_dark.png", "logo_light.png"):
        t.copy(GEN / f, f"flutter/assets/{f}")
    for f in sorted((BRAND / "fonts").iterdir()):
        t.copy(f, f"flutter/assets/fonts/{f.name}")

    t.sub("flutter/pubspec.yaml",
          "  fonts:\n    - family: GestureIcons\n",
          "  fonts:\n"
          "    - family: Inter\n"
          "      fonts:\n"
          "        - asset: assets/fonts/Inter-Regular.ttf\n"
          "        - asset: assets/fonts/Inter-Medium.ttf\n"
          "          weight: 500\n"
          "        - asset: assets/fonts/Inter-SemiBold.ttf\n"
          "          weight: 600\n"
          "        - asset: assets/fonts/Inter-Bold.ttf\n"
          "          weight: 700\n"
          "    - family: Sora\n"
          "      fonts:\n"
          "        - asset: assets/fonts/Sora-SemiBold.ttf\n"
          "          weight: 600\n"
          "        - asset: assets/fonts/Sora-Bold.ttf\n"
          "          weight: 700\n"
          "    - family: GestureIcons\n")


# ---------------------------------------------------------------------------
# 4. Tema visual (Flutter): paleta, fontes e tema escuro padrão
# ---------------------------------------------------------------------------
RECOLOR = {
    # azul padrão do RustDesk -> Azul Elétrico
    "0xFF0071FF": f"0xFF{ELETRICO}",
    "0x770071FF": f"0x77{ELETRICO}",
    "0xAA0071FF": f"0xAA{ELETRICO}",
    "0xFF2C8CFF": f"0xFF{ELETRICO}",
    # cor do ID -> Azul Neon
    "0xFF00B6F0": f"0xFF{NEON}",
    # fundos do tema escuro -> Preto Tecnológico / Azul Marinho
    "0xFF18191E": f"0xFF{PRETO}",
    "0xFF24252B": f"0xFF{MARINHO}",
}


def patch_theme(t: Tree, cfg: dict):
    lib = t.root / "flutter/lib"
    totals = {k: 0 for k in RECOLOR}
    for dart in lib.rglob("*.dart"):
        text = dart.read_text(encoding="utf-8")
        new = text
        for old, rep in RECOLOR.items():
            new, n = re.subn(re.escape(old), rep, new, flags=re.I)
            totals[old] += n
        if new != text:
            dart.write_text(new, encoding="utf-8")
            t.changed.append(str(dart.relative_to(t.root)))
    missing = [k for k in ("0xFF0071FF", "0xFF18191E", "0xFF24252B") if totals[k] == 0]
    if missing:
        raise BrandingError(f"cores do tema não encontradas em flutter/lib: {missing}")

    c = "flutter/lib/common.dart"
    # Fonte de apoio (Inter) em todo o app; títulos em Sora
    t.sub(c, "    brightness: Brightness.light,\n", "    brightness: Brightness.light,\n    fontFamily: 'Inter',\n")
    t.sub(c, "    brightness: Brightness.dark,\n", "    brightness: Brightness.dark,\n    fontFamily: 'Inter',\n")
    t.sub(c, "titleLarge: TextStyle(fontSize: 19, color: Colors.black87),",
          "titleLarge: TextStyle(fontSize: 19, color: Colors.black87, fontFamily: 'Sora', fontWeight: FontWeight.w600),")
    t.sub(c, "titleLarge: TextStyle(fontSize: 19),",
          "titleLarge: TextStyle(fontSize: 19, fontFamily: 'Sora', fontWeight: FontWeight.w600),")
    # Cor primária: azul da marca no lugar do azul genérico do Material
    t.sub(c, "primary: Colors.blue,", f"primary: Color(0xFF{ELETRICO}),", count=None)
    # Tema claro mais frio (Cinza Frio da marca nas bordas)
    t.sub(c, "static const Color grayBg = Color(0xFFEFEFF2);", "static const Color grayBg = Color(0xFFF1F4F9);")
    t.sub(c, "    border: Color(0xFFCCCCCC),\n    border2: Color(0xFFBBBBBB),",
          f"    border: Color(0xFF{CINZA}),\n    border2: Color(0xFFA9B6CB),")
    # Tema escuro: hover, bordas e destaques em tons de azul-marinho
    t.sub(c, "hoverColor: Color.fromARGB(255, 45, 46, 53),", "hoverColor: Color(0xFF0B2A57),")
    t.sub(c, "    border: Color(0xFF555555),", "    border: Color(0xFF1C3A66),")
    t.sub(c, "    highlight: Color(0xFF3F3F3F),", "    highlight: Color(0xFF0E2A52),")

    if cfg.get("default_theme") in ("dark", "light"):
        theme = cfg["default_theme"]
        t.sub(c,
              "    return themeModeFromString(bind.mainGetLocalOption(key: kCommConfKeyTheme));",
              "    final v = bind.mainGetLocalOption(key: kCommConfKeyTheme);\n"
              f"    return themeModeFromString(v.isEmpty ? '{theme}' : v);")


# ---------------------------------------------------------------------------
# 5. Textos e links: Sobre, privacidade, créditos (AGPL)
# ---------------------------------------------------------------------------
def patch_links(t: Tree, cfg: dict):
    links, name, company = cfg["links"], cfg["app_name"], cfg["company"]
    s = "flutter/lib/desktop/pages/desktop_setting_page.dart"
    t.sub(s, "launchUrlString('https://rustdesk.com/privacy.html');", f"launchUrlString({dart_str(links['privacy'])});")
    t.sub(s, "launchUrlString('https://rustdesk.com');", f"launchUrlString({dart_str(links['website'])});")
    t.sub(s, "decoration: const BoxDecoration(color: Color(0xFF2c8cff)),".replace("2c8cff", ELETRICO),
          f"decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF{NEON}), Color(0xFF{ELETRICO})])),")
    credit = (f"{name} © ${{DateTime.now().toString().substring(0, 4)}} {company}\\n"
              "Baseado no RustDesk © Purslane Tech Pte. Ltd., licença AGPL-3.0\\n"
              f"{links['source_code']}\\n$license")
    t.sub(s,
          "'Copyright © ${DateTime.now().toString().substring(0, 4)} Purslane Tech Pte. Ltd.\\n$license',",
          f"'{credit}',")
    t.sub(s, "translate('Slogan_tip'),", f"{dart_str(cfg['slogan'])},")

    i = "flutter/lib/desktop/pages/install_page.dart"
    t.sub(i, "'https://rustdesk.com/privacy.html'", dart_str(links["privacy"]), count=None)
    t.sub("flutter/lib/common.dart", "launchUrl(Uri.parse('https://rustdesk.com'));",
          f"launchUrl(Uri.parse({dart_str(links['website'])}));")


# ---------------------------------------------------------------------------
# 6. Comportamento: instalador, servidor próprio, escala, textos de status
# ---------------------------------------------------------------------------
def patch_behavior(t: Tree):
    # O AnyHelp.exe baixado abre direto na tela de instalação
    # (que já oferece "Executar sem instalar"). Antes, só abria assim se o
    # arquivo se chamasse ...install.exe.
    t.sub("libs/portable/src/main.rs",
          'let click_setup = args.is_empty() && arg_exe.to_lowercase().ends_with("install.exe");',
          "let click_setup = args.is_empty();")

    # O servidor vem gravado no código, então o app achava que estava no servidor
    # público do RustDesk: mostrava "configure seu próprio servidor" e limitava
    # qualidade/FPS em conexões via relay.
    t.sub("src/common.rs",
          '    crate::get_custom_rendezvous_server(get_option("custom-rendezvous-server")).is_empty()\n}',
          "    false\n}")

    # Reforço: remove da tela o link "configure seu próprio servidor" (levava ao pricing do RustDesk)
    t.sub("flutter/lib/desktop/pages/connection_page.dart",
          "            if (!isIncomingOnly) setupServerWidget(),\n", "")

    # Escala adaptada como padrão no desktop (a tela remota cabe na janela)
    t.sub("libs/hbb_common/src/config.rs",
          'keys::OPTION_VIEW_STYLE => self.get_string(key, "original", vec!["adaptive"]),',
          'keys::OPTION_VIEW_STYLE => self.get_string(key, "adaptive", vec!["original"]),')

    # Status do rodapé e estado vazio da lista de sessões
    t.sub("src/lang/pt_BR.rs", '("Ready", "Pronto"),', '("Ready", "Pronto para conexão."),')
    t.sub("src/lang/pt_PT.rs", '("Ready", "Pronto"),', '("Ready", "Pronto para ligação."),')
    t.resub("src/lang/pt_BR.rs", r'\("empty_recent_tip", "[^"]*"\),',
            '("empty_recent_tip", "Nenhuma sessão recente.\\\\nDigite acima o ID de um computador para começar."),')
    t.sub("src/lang/en.rs",
          '        ("desk_tip", "Your desktop can be accessed with this ID and password."),\n',
          '        ("desk_tip", "Your desktop can be accessed with this ID and password."),\n'
          '        ("Ready", "Ready to connect."),\n')
    t.resub("src/lang/en.rs", r'\("empty_recent_tip", "[^"]*"\),',
            '("empty_recent_tip", "No recent sessions yet.\\\\nType a remote ID above to get started."),')


# ---------------------------------------------------------------------------
# 7. Layout da tela principal: janela maior, cartões de ID/senha, dicas
# ---------------------------------------------------------------------------
GRAD_BAR = (f"decoration: const BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, "
            f"end: Alignment.bottomCenter, colors: [Color(0xFF{NEON}), Color(0xFF{ELETRICO})])),")

HOME_HELPERS = f"""

// ---- AnyHelp: estilos da tela principal ----
bool _ahDark(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark;

BoxDecoration _ahCard(BuildContext context) {{
  final dark = _ahDark(context);
  return BoxDecoration(
    color: dark ? const Color(0x66{PRETO}) : Colors.white,
    borderRadius: BorderRadius.circular(12),
    border: Border.all(
        color: dark ? const Color(0x40{NEON}) : const Color(0xFF{CINZA})),
    boxShadow: dark
        ? const [BoxShadow(color: Color(0x22{NEON}), blurRadius: 18)]
        : null,
  );
}}

BoxDecoration _ahLeftPane(BuildContext context) {{
  return BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: _ahDark(context)
          ? const [Color(0xFF07214A), Color(0xFF{PRETO})]
          : const [Color(0xFFF1F4F9), Color(0xFFFFFFFF)],
    ),
  );
}}

Widget _ahHint(BuildContext context) {{
  final muted =
      Theme.of(context).textTheme.bodySmall?.color?.withOpacity(0.75);
  Widget row(IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 16, color: const Color(0xFF{NEON})),
            const SizedBox(width: 10),
            Expanded(
              child: Text(text,
                  style: TextStyle(fontSize: 12.5, height: 1.4, color: muted)),
            ),
          ],
        ),
      );
  return Padding(
    padding: const EdgeInsets.fromLTRB(20, 6, 16, 8),
    child: Column(
      children: [
        row(Icons.support_agent_rounded,
            'Para receber suporte, informe o ID e a senha acima ao técnico.'),
        row(Icons.verified_user_outlined,
            'Ninguém acessa sem a senha ou sem você aceitar a conexão.'),
        row(Icons.lock_outline_rounded,
            'Conexão criptografada de ponta a ponta.'),
      ],
    ),
  );
}}
"""


def patch_layout(t: Tree):
    # Janela inicial maior (era 800x600)
    t.sub("flutter/windows/runner/main.cpp",
          "Win32Window::Size size(800u, 600u);", "Win32Window::Size size(1080u, 720u);")

    h = "flutter/lib/desktop/pages/desktop_home_page.dart"
    # Painel esquerdo mais largo, com degradê azul-marinho -> preto
    t.sub(h,
          "        width: isIncomingOnly ? 280.0 : 200.0,\n"
          "        color: Theme.of(context).colorScheme.background,",
          "        width: 300.0,\n"
          "        decoration: _ahLeftPane(context),")
    # Dicas abaixo do cartão de senha
    t.sub(h,
          "      if (!isOutgoingOnly) buildPasswordBoard(context),\n",
          "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
          "      if (!isOutgoingOnly) _ahHint(context),\n")
    # Cartão do ID
    t.sub(h,
          "      margin: const EdgeInsets.only(left: 20, right: 11),\n      height: 57,",
          "      margin: const EdgeInsets.only(left: 16, right: 16, top: 10),\n"
          "      padding: const EdgeInsets.fromLTRB(14, 8, 8, 10),\n"
          "      decoration: _ahCard(context),\n"
          "      height: 100,")
    t.sub(h, "decoration: const BoxDecoration(color: MyTheme.accent),", GRAD_BAR)
    t.sub(h,
          "                        style: TextStyle(\n                          fontSize: 22,\n                        ),",
          "                        style: TextStyle(\n"
          "                          fontSize: 30,\n"
          "                          fontFamily: 'Sora',\n"
          "                          fontWeight: FontWeight.w700,\n"
          "                          letterSpacing: 1.5,\n"
          f"                          color: _ahDark(context) ? const Color(0xFF{NEON}) : const Color(0xFF{ELETRICO}),\n"
          f"                          shadows: _ahDark(context) ? const [Shadow(color: Color(0x66{NEON}), blurRadius: 14)] : null,\n"
          "                        ),")
    # Cartão da senha
    t.sub(h,
          "      margin: EdgeInsets.only(left: 20.0, right: 16, top: 13, bottom: 13),",
          "      margin: EdgeInsets.only(left: 16.0, right: 16, top: 12, bottom: 12),\n"
          "      padding: const EdgeInsets.fromLTRB(14, 10, 6, 6),\n"
          "      decoration: _ahCard(context),")
    t.sub(h, "decoration: BoxDecoration(color: MyTheme.accent),", GRAD_BAR)
    t.sub(h, "style: TextStyle(fontSize: 15),",
          "style: TextStyle(fontSize: 21, fontFamily: 'Sora', fontWeight: FontWeight.w600, letterSpacing: 2),")
    # Cartão de aviso (era rosa) nas cores da marca, com cantos arredondados
    t.sub(h,
          "          margin: EdgeInsets.fromLTRB(\n"
          "              0, marginTop, 0, bind.isIncomingOnly() ? marginTop : 0),\n"
          "          child: Container(\n"
          "              decoration: BoxDecoration(\n"
          "                  gradient: LinearGradient(\n"
          "                begin: Alignment.centerLeft,\n"
          "                end: Alignment.centerRight,\n"
          "                colors: [\n"
          "                  Color.fromARGB(255, 226, 66, 188),\n"
          "                  Color.fromARGB(255, 244, 114, 124),\n"
          "                ],\n"
          "              )),",
          "          margin: EdgeInsets.fromLTRB(\n"
          "              16, marginTop, 16, bind.isIncomingOnly() ? marginTop : 16),\n"
          "          child: Container(\n"
          "              decoration: BoxDecoration(\n"
          "                  borderRadius: BorderRadius.circular(12),\n"
          "                  gradient: LinearGradient(\n"
          "                begin: Alignment.topLeft,\n"
          "                end: Alignment.bottomRight,\n"
          "                colors: [\n"
          f"                  Color(0xFF{ELETRICO}),\n"
          "                  Color(0xFF0A2F6B),\n"
          "                ],\n"
          "              )),")
    p = t.path(h)
    p.write_text(p.read_text(encoding="utf-8") + HOME_HELPERS, encoding="utf-8")

    # Estado vazio da lista de sessões: ícone da marca no lugar da carinha triste
    t.sub("flutter/lib/common/widgets/peers_view.dart",
          "                  Icons.sentiment_very_dissatisfied_rounded,\n"
          "                  color: Theme.of(context).tabBarTheme.labelColor,\n"
          "                  size: 40,",
          "                  Icons.devices_other_rounded,\n"
          f"                  color: const Color(0xFF{NEON}),\n"
          "                  size: 44,")


def validate_server(server: str, key: str, allow_placeholder: bool):
    if not server or not key:
        if allow_placeholder:
            print("AVISO: ANYHELP_SERVER/ANYHELP_KEY vazios — build só para teste, não conecta em lugar nenhum.")
            return "127.0.0.1", "COLOQUE_A_CHAVE_PUBLICA_AQUI"
        raise BrandingError(
            "defina ANYHELP_SERVER (IP/domínio da VPS) e ANYHELP_KEY (conteúdo de id_ed25519.pub). "
            "No GitHub: Settings > Secrets and variables > Actions > Variables.")
    if not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]+", server):
        raise BrandingError(f"ANYHELP_SERVER inválido: {server!r} (use só IP ou domínio, sem http://)")
    if not re.fullmatch(r"[A-Za-z0-9+/]{43}=", key):
        raise BrandingError("ANYHELP_KEY não parece uma chave do RustDesk (44 caracteres terminando em '=').")
    return server, key


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rustdesk_dir", type=Path)
    ap.add_argument("--allow-placeholder-server", action="store_true",
                    help="permite rodar sem ANYHELP_SERVER/ANYHELP_KEY (só para testar o script)")
    args = ap.parse_args()

    cfg = json.loads((PROJECT / "anyhelp.json").read_text(encoding="utf-8"))
    root = args.rustdesk_dir.resolve()
    marker = root / ".anyhelp-branded"
    try:
        if not (root / "Cargo.toml").exists() or not (root / "libs/hbb_common/src/config.rs").exists():
            raise BrandingError(f"{root} não parece um checkout do RustDesk com submódulos (git submodule update --init).")
        if marker.exists():
            raise BrandingError("este checkout já recebeu a marca AnyHelp. Use um clone limpo.")
        server, key = validate_server(os.environ.get("ANYHELP_SERVER", "").strip(),
                                      os.environ.get("ANYHELP_KEY", "").strip(),
                                      args.allow_placeholder_server)
        t = Tree(root)
        patch_core(t, cfg, server, key)
        patch_windows_metadata(t, cfg)
        copy_assets(t)
        patch_theme(t, cfg)
        patch_links(t, cfg)
        patch_behavior(t)
        patch_layout(t)
    except BrandingError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

    marker.write_text(f"{cfg['app_name']} sobre RustDesk {cfg['upstream']['tag']}\n", encoding="utf-8")
    files = sorted(set(t.changed))
    print(f"{cfg['app_name']}: marca aplicada em {len(files)} arquivos do RustDesk {cfg['upstream']['tag']}.")
    print(f"Servidor: {server}")


if __name__ == "__main__":
    main()
