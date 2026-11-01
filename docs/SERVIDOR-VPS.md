# Servidor AnyHelp na VPS

O AnyHelp precisa de um servidor próprio para que as máquinas se encontrem. Ele é
o **RustDesk Server OSS**, com dois serviços:

| Serviço | Função | Porta |
|---|---|---|
| **hbbs** | Cadastro de IDs e intermediação. Cada AnyHelp aberto se registra aqui com seu ID. | 21115/tcp, 21116/tcp, **21116/udp** |
| **hbbr** | Relay. Repassa a tela quando as duas máquinas não conseguem se conectar direto. | 21117/tcp |

Na maioria dos atendimentos a conexão é **direta** entre as máquinas (P2P) e a VPS
só faz a apresentação. O relay entra quando um dos lados está atrás de uma rede
restritiva (rede corporativa, 4G com CGNAT etc.).

## Requisitos

- VPS Linux (Ubuntu 22.04/24.04 ou Debian 12), **IP público fixo**
- 1 vCPU e 1 GB de RAM atendem milhares de máquinas cadastradas. O que pesa é a
  **banda** do relay (veja "Escalar" abaixo)
- Acesso root por SSH

## Instalação (5 minutos)

1. Copie a pasta `server/` para a VPS:

   ```bash
   scp -r server/ root@45.42.162.228:/opt/anyhelp-server
   ```

2. Na VPS, rode o instalador passando o IP público:

   ```bash
   cd /opt/anyhelp-server
   sudo bash instalar.sh 45.42.162.228
   ```

   Ele instala o Docker, libera as portas no firewall (`ufw`), sobe o hbbs e o
   hbbr e, no fim, mostra os dois valores para o GitHub:

   ```
   ANYHELP_SERVER = 45.42.162.228
   ANYHELP_KEY    = AbCd...=        (44 caracteres)
   ```

3. Se a VPS tiver **firewall no painel do provedor** (Security Group na AWS,
   Firewall na Hetzner/DigitalOcean/Contabo etc.), libere lá também:
   `21115/tcp`, `21116/tcp`, `21116/udp`, `21117/tcp`.

4. Cadastre os dois valores no GitHub e gere o executável. Veja
   [PUBLICAR-VERSAO.md](PUBLICAR-VERSAO.md).

## A chave do servidor (importante)

- Na primeira vez, o hbbs gera `data/id_ed25519` (privada) e
  `data/id_ed25519.pub` (pública).
- A **pública** vai gravada dentro do AnyHelp. O servidor roda com `-k _`, então
  só aceita clientes com essa chave. Um RustDesk comum, ou um AnyHelp de outra
  empresa, não consegue usar o seu servidor.
- **Faça backup da pasta `data/`.** Se a chave privada se perder ou mudar, todos
  os AnyHelp já instalados nos clientes param de conectar, e será preciso
  recompilar e redistribuir.

## Trocar de VPS

Como o AnyHelp foi compilado com o **IP**, mudar de IP obriga a recompilar e
redistribuir o app. Para trocar sem dor:

1. Copie a pasta `data/` da VPS antiga para a nova (a chave continua a mesma).
2. Se o IP mudou, atualize `ANYHELP_SERVER` no GitHub e publique uma versão nova.

> Recomendação: assim que possível, crie um subdomínio (ex.:
> `anyhelp.rzsystem.com.br`) apontando para a VPS e use-o em `ANYHELP_SERVER`.
> Daí em diante, trocar de VPS é só mudar o DNS, sem recompilar.

## Operação do dia a dia

```bash
cd /opt/anyhelp-server
docker compose ps              # status
docker compose logs -f hbbs    # logs de cadastro/conexão
docker compose logs -f hbbr    # logs do relay
docker compose pull && docker compose up -d   # atualizar o servidor
```

Teste rápido de porta a partir do seu PC (PowerShell):

```powershell
Test-NetConnection 192.168.1.122 -Port 21116
Test-NetConnection SEU_IP -Port 21117
```

## Escalar

O hbbs é leve: uma VPS pequena aguenta dezenas de milhares de IDs cadastrados. O
gargalo é a **banda do relay**. Uma sessão relayed usa em média de 0,5 a 3 Mb/s
(até ~10 Mb/s em tela cheia com movimento).

| Fase | Sugestão |
|---|---|
| Início | 1 VPS com hbbs + hbbr, ajustar `TOTAL_BANDWIDTH` no `.env` para ~80% do link |
| Crescendo | VPS com mais banda/tráfego incluso; monitorar `docker stats` e o tráfego mensal |
| Grande volume | Relays extras em outras VPS (só `hbbr`) e hbbs com vários relays: `-r relay1:21117,relay2:21117` no `docker-compose.yml` |

Os limites do relay (`TOTAL_BANDWIDTH`, `SINGLE_BANDWIDTH`, `LIMIT_SPEED`, em
Mb/s) ficam no `.env`. Depois de mudar, rode `docker compose up -d`.

## Segurança

- Mantenha o sistema atualizado (`apt upgrade`) e o SSH só com chave.
- As sessões são criptografadas ponta a ponta (NaCl). O relay só repassa bytes
  cifrados.
- Cada acesso exige o **ID + senha** da máquina, ou o clique em "Aceitar" de
  quem está nela.
