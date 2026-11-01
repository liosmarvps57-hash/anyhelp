#!/usr/bin/env bash
# Instala o servidor AnyHelp numa VPS Ubuntu/Debian limpa.
#   sudo bash instalar.sh 203.0.113.10
# Idempotente: pode rodar de novo para atualizar.
set -euo pipefail

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  echo "uso: sudo bash instalar.sh <IP-ou-domínio-público-da-VPS>" >&2
  exit 1
fi
if [[ $EUID -ne 0 ]]; then
  echo "rode como root (sudo)." >&2
  exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> Configuração (.env)"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
sed -i "s|^ANYHELP_HOST=.*|ANYHELP_HOST=${HOST}|" .env

echo "==> Firewall (portas do AnyHelp)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH >/dev/null
  ufw allow 21115/tcp >/dev/null   # teste de NAT
  ufw allow 21116/tcp >/dev/null   # ID / rendezvous
  ufw allow 21116/udp >/dev/null   # ID / conexão direta (hole punching)
  ufw allow 21117/tcp >/dev/null   # relay
  ufw --force enable >/dev/null
  ufw status | grep -E '2111[5-7]' || true
else
  echo "   ufw não encontrado: libere manualmente 21115/tcp, 21116/tcp, 21116/udp, 21117/tcp"
fi

echo "==> Buffer UDP (recomendado pelo RustDesk para muitas conexões)"
if ! grep -q '^net.core.rmem_max' /etc/sysctl.conf; then
  echo 'net.core.rmem_max=52428800' >> /etc/sysctl.conf
fi
sysctl -p >/dev/null || true

echo "==> Subindo hbbs + hbbr"
docker compose pull
docker compose up -d

echo "==> Aguardando a chave do servidor..."
for _ in $(seq 1 30); do
  [[ -s data/id_ed25519.pub ]] && break
  sleep 1
done
if [[ ! -s data/id_ed25519.pub ]]; then
  echo "A chave não apareceu. Veja os logs: docker compose logs hbbs" >&2
  exit 1
fi

cat <<EOF

=====================================================================
 Servidor AnyHelp no ar.

 Cadastre no GitHub (Settings > Secrets and variables > Actions > Variables):
   ANYHELP_SERVER = ${HOST}
   ANYHELP_KEY    = $(cat data/id_ed25519.pub)

 FAÇA BACKUP de data/id_ed25519 (chave privada). Se ela se perder,
 todos os AnyHelp já distribuídos param de conectar.
=====================================================================
EOF
