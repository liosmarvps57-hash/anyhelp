# Gerar e publicar o AnyHelp.exe

O executável é compilado pelo **GitHub Actions**, em máquinas Windows do próprio
GitHub. Ninguém precisa instalar Rust, Flutter ou Visual Studio.

## 1. Criar o repositório (uma vez só)

1. No GitHub, crie o repositório `anyhelp` (de preferência na organização da RZ System).
   - **Público** é o recomendado: a licença AGPL do RustDesk exige que o
     código-fonte do AnyHelp fique disponível para quem usa o app. Repositório
     público resolve isso. A chave **privada** do servidor nunca vai para o
     repositório, então não há risco.
2. Envie esta pasta com o script pronto (precisa do [Git](https://git-scm.com/download/win)):

   ```powershell
   cd C:\Users\thais\Desktop\projects\AnyHelp
   powershell -ExecutionPolicy Bypass -File scripts\preparar-repositorio.ps1 -Repo https://github.com/SUA-ORG/anyhelp.git
   ```

   Ele move `_github\` para `.github\` (pasta dos workflows do GitHub Actions),
   faz o commit inicial e o push.

3. Em `anyhelp.json`, ajuste `links.source_code` para a URL real do repositório
   (ela aparece na tela "Sobre" do app).

## 2. Cadastrar o servidor (uma vez só)

No repositório: **Settings > Secrets and variables > Actions > aba Variables >
New repository variable**

| Nome | Valor |
|---|---|
| `ANYHELP_SERVER` | IP público da VPS (ex.: `203.0.113.10`) |
| `ANYHELP_KEY` | conteúdo de `data/id_ed25519.pub` na VPS |

São **Variables**, não Secrets: a chave pública não é segredo e fica visível
dentro do app de qualquer forma.

## 3. Gerar uma versão de teste

**Actions > Build AnyHelp (Windows) > Run workflow**

- O primeiro build leva de **60 a 90 minutos** (compila o FFmpeg e outras
  bibliotecas nativas). Os seguintes usam cache e levam ~25–40 min.
- No fim, baixe o artefato **AnyHelp-windows-x64** na página da execução. Ele
  traz `AnyHelp.exe` e `AnyHelp-<versão>-x64.exe`.

## 4. Publicar para os clientes

Crie uma tag. O workflow gera uma **Release** pública com o executável:

```powershell
git tag v1.5.1-rz1
git push origin v1.5.1-rz1
```

Link fixo para o site, que sempre aponta para a última versão:

```
https://github.com/SUA-ORG/anyhelp/releases/latest/download/AnyHelp.exe
```

É esse link que a página `site/index.html` usa no botão "Baixar".

### Convenção de versão

A versão interna do app acompanha a do RustDesk (ex.: `1.5.1`), porque os
clientes usam esse número para negociar recursos entre si. Mudar para `1.0.0`
quebraria a compatibilidade. Use o sufixo da tag para as revisões da RZ System:
`v1.5.1-rz1`, `v1.5.1-rz2`...

## 5. Assinatura de código (recomendado antes de divulgar)

Sem assinatura, o Windows mostra o aviso azul do **SmartScreen** ("O Windows
protegeu o computador") e alguns antivírus desconfiam de ferramentas de acesso
remoto. Para remover isso:

1. Compre um certificado de **Code Signing** (OV ou, melhor, EV) em nome da RZ
   System (Certum, Sectigo, DigiCert, SSL.com...).
2. Exporte como `.pfx` e converta para base64:

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("rzsystem.pfx")) | Set-Clipboard
   ```

3. Cadastre em **Secrets** (não Variables):
   `WINDOWS_PFX_BASE64` (o texto copiado) e `WINDOWS_PFX_PASSWORD`.

Daí em diante, o workflow assina tudo automaticamente.

> Certificados EV novos costumam vir em token físico/HSM na nuvem, sem `.pfx`.
> Nesse caso o passo de assinatura precisa usar a ferramenta do fornecedor
> (ex.: Azure Trusted Signing, SSL.com eSigner). Dá para trocar depois.

## Problemas comuns

| Erro no build | Causa / solução |
|---|---|
| `defina ANYHELP_SERVER ... ANYHELP_KEY` | As Variables do passo 2 não foram cadastradas |
| `ANYHELP_KEY não parece uma chave` | Copie o conteúdo inteiro de `id_ed25519.pub` (44 caracteres, termina com `=`) |
| `esperado 1 ocorrência(s) de: ...` | O RustDesk mudou aquele trecho numa versão nova. Veja [ATUALIZAR-RUSTDESK.md](ATUALIZAR-RUSTDESK.md) |
| App abre mas fica "Conectando à rede..." | Portas da VPS bloqueadas (firewall do provedor) ou IP/chave errados |
