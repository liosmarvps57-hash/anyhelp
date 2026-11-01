# Atualizar a base RustDesk

O AnyHelp não guarda uma cópia do RustDesk. Ele guarda só a **camada de marca**,
aplicada em cima da versão escolhida em `anyhelp.json`:

```json
"upstream": { "repo": "https://github.com/rustdesk/rustdesk.git", "tag": "1.5.1" }
```

## Passo a passo

1. Veja as versões em https://github.com/rustdesk/rustdesk/releases e leia as notas.
2. Troque `"tag"` em `anyhelp.json` (ex.: `"1.5.2"`) e faça push.
3. O workflow **Verificar marca** roda em ~1 minuto e diz se a marca ainda
   encaixa na versão nova.
   - Passou: rode o build completo e teste o executável.
   - Falhou: a mensagem mostra o arquivo e o trecho que mudou, por exemplo:

     ```
     ERRO: flutter/lib/common.dart: esperado 1 ocorrência(s) de:
         'hoverColor: Color.fromARGB(255, 45, 46, 53),'
       encontrado 0.
     ```

     Abra o arquivo na tag nova do RustDesk, ache o trecho equivalente e ajuste a
     linha correspondente em `scripts/apply_branding.py`.
4. As versões de Flutter, Rust e vcpkg **não** precisam ser ajustadas à mão: o
   build lê do próprio pipeline do RustDesk daquela tag
   (`scripts/upstream_versions.py`).
5. Se o RustDesk mudar muito o próprio pipeline de build do Windows, compare
   `.github/workflows/build-windows.yml` com o job `build-for-windows-flutter`
   de `.github/workflows/flutter-build.yml` do RustDesk.

## Testar o script de marca no seu PC (opcional)

Precisa só de Git e Python:

```powershell
git clone --depth 1 --branch 1.5.1 --recurse-submodules https://github.com/rustdesk/rustdesk.git teste-rustdesk
python scripts\apply_branding.py teste-rustdesk --allow-placeholder-server
```

## O que a camada de marca altera

| Área | O que muda | Onde no script |
|---|---|---|
| Nome | `AnyHelp` em janelas, bandeja, instalador, pasta de instalação, protocolo `anyhelp://` | `patch_core` |
| Servidor | IP/chave da VPS gravados; tela de servidor escondida para o usuário não trocar | `patch_core` |
| Contas | Login e catálogo de endereços desligados (modelo ID + senha) | `hard_settings` no `anyhelp.json` |
| Executável | `AnyHelp.exe`, ícone e Propriedades > Detalhes com RZ System | `patch_windows_metadata` |
| Visual | Paleta do manual, Inter no texto e Sora nos títulos, tema escuro padrão, ícone e logos | `copy_assets`, `patch_theme` |
| Textos | Sobre, privacidade, site, créditos AGPL | `patch_links` |

Para ligar/desligar recursos sem mexer em código, use `hard_settings` e
`builtin_settings` em `anyhelp.json`. Exemplos úteis (lista completa em
`libs/base/src/config/keys.rs` do RustDesk):

| Onde | Chave | Efeito |
|---|---|---|
| `builtin_settings` | `"hide-help-cards": "Y"` | esconde os cartões de dica da tela inicial |
| `builtin_settings` | `"hide-proxy-settings": "Y"` | esconde a configuração de proxy |
| `hard_settings` | `"conn-type": "incoming"` | app só para **receber** acesso (versão "cliente final") |
| `hard_settings` | `"conn-type": "outgoing"` | app só para **acessar** (versão "técnico") |
| `hard_settings` | `"disable-installation": "Y"` | só modo portátil, sem botão Instalar |
