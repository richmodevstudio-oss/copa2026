#!/usr/bin/env bash
# Configura o serviço systemd + nginx para o Previsor Copa 2026 na VPS.
# Executar no servidor como root, após o código estar em /opt/copa2026 com venv.
set -euo pipefail

APP_DIR=/opt/copa2026
DOMAIN=palpites.richmo.media
LETSENCRYPT_EMAIL=richmo.devstudio@gmail.com

echo "== systemd unit =="
cat > /etc/systemd/system/copa2026.service <<'EOF'
[Unit]
Description=Previsor Copa 2026 (Streamlit)
After=network.target

[Service]
User=copa
Group=copa
WorkingDirectory=/opt/copa2026
Environment=HOME=/opt/copa2026
Environment=PYTHONPATH=/opt/copa2026/src
ExecStart=/opt/copa2026/.venv/bin/streamlit run app.py \
    --server.port 8501 --server.address 127.0.0.1 \
    --server.headless true --browser.gatherUsageStats false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "== nginx site HTTP (server_name = $DOMAIN) =="
# vhost HTTP only; o certbot --nginx adiciona o bloco 443 + redirect com cert real.
# server_name especifico (nao default_server): a app responde so para $DOMAIN,
# requisicoes para a raiz richmo.media ou outros hosts caem no default abaixo.
cat > /etc/nginx/sites-available/copa2026 <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}

# catch-all: hosts desconhecidos (incl. a raiz richmo.media, sem nada por enquanto)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 404;
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/copa2026 /etc/nginx/sites-enabled/copa2026
nginx -t

echo "== habilitando servicos =="
systemctl daemon-reload
systemctl enable --now copa2026.service
systemctl reload nginx

echo "== certificado Let's Encrypt =="
# Requer DNS de $DOMAIN ja apontando para este servidor.
if ! command -v certbot >/dev/null; then
    apt-get update && apt-get install -y certbot python3-certbot-nginx
fi
certbot --nginx -d "$DOMAIN" \
    --non-interactive --agree-tos -m "$LETSENCRYPT_EMAIL" --redirect
systemctl reload nginx

echo "== firewall =="
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
    echo "ufw: portas 80 e 443 liberadas"
else
    echo "ufw inativo; nada a fazer"
fi

echo "== status =="
sleep 4
systemctl is-active copa2026.service && echo "servico ativo"
curl -sS -o /dev/null -w "redirect 80 -> %{http_code} (%{redirect_url})\n" "http://$DOMAIN/" || true
curl -sS -o /dev/null -w "HTTPS %{http_code}\n" "https://$DOMAIN/" || true
echo "DONE"
