# AnyHelp e antivírus (Windows Defender)

## Por que acontece

O alerta `Behavior:Win32/Persistence.A!ml` não é assinatura de vírus. É o
**modelo de comportamento** do Defender (o `!ml` significa machine learning). Ele
vê três coisas juntas e desconfia:

1. um executável **novo**, que ninguém no mundo rodou ainda;
2. **sem assinatura digital**;
3. que faz o que todo acesso remoto precisa fazer: instala um **serviço do
   Windows** e se registra para **iniciar com o sistema** (é isso que permite o
   acesso sem ninguém na frente). É esse o comportamento chamado "Persistence".

O AnyDesk, o TeamViewer e o RustDesk passam pelo mesmo problema. O que os livra é
**assinatura digital + reputação** acumulada junto à Microsoft.

## Como resolver (em ordem de impacto)

### 1. Enviar para a Microsoft como falso positivo (grátis, 1–3 dias)

1. Acesse https://www.microsoft.com/en-us/wdsi/filesubmission
2. Escolha **Software developer** e faça login com uma conta Microsoft.
3. Produto: **Microsoft Defender Antivirus**. Envie o `AnyHelp.exe`.
4. Classificação: **Incorrectly detected as malware/malicious**.
5. No campo de detalhes, informe o nome do alerta
   (`Behavior:Win32/Persistence.A!ml`) e explique: *"Remote support software
   (based on open-source RustDesk) by RZ System. Installs a Windows service for
   unattended access."*

Repita a cada versão nova até ganhar reputação. Com assinatura (item 2), isso
para de ser necessário.

### 2. Assinar o executável (resolve de vez)

Com um certificado de **Code Signing** em nome da RZ System, o Windows passa a
ligar o arquivo à empresa, e a reputação acumula entre versões. O build já assina
sozinho quando o certificado é cadastrado. Veja o passo 5 de
[PUBLICAR-VERSAO.md](PUBLICAR-VERSAO.md).

- **OV** (validação da organização): mais barato. A reputação no SmartScreen
  cresce com os downloads.
- **EV** (validação estendida): mais caro, mas a reputação é imediata.
- **Azure Trusted Signing**: assinatura gerenciada pela Microsoft, com preço
  mensal baixo. Exige empresa com alguns anos de existência.

### 3. Enquanto isso, para testar

No Defender: **Proteção contra vírus e ameaças > Histórico de proteção**, abra o
alerta do AnyHelp e escolha **Permitir no dispositivo**. Não use "Iniciar ações",
que apaga o arquivo.
