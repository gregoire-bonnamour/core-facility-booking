#!/usr/bin/env bash
set -euo pipefail

# --- Configs ---
APP_DIR="/home/gregoire/apps/core-facility-booking"
ENV_FILE="$APP_DIR/.env.prod"
VENV_BIN="$APP_DIR/.venv/bin"
MANAGE_PY="$APP_DIR/manage.py"
SERVICE="gunicorn-core-facility"
TEST_RECIPIENT="${TEST_RECIPIENT:-admin@youruniversity.ca}"  # changeable via env

SMTP_HOST="${SMTP_HOST:-mail.youruniversity.ca}"
SMTP_PORT="${SMTP_PORT:-25}"
SMTP_USE_TLS="${SMTP_USE_TLS:-False}"
SMTP_USE_SSL="${SMTP_USE_SSL:-False}"
DEFAULT_FROM_OK='Booking Platform <admin@youruniversity.ca>'
SERVER_EMAIL_OK='admin@youruniversity.ca'

usage() {
  cat <<EOF
Usage:
  $0 on      # switch to SMTP (mail.youruniversity.ca:25, no auth), restart, and send test email
  $0 off     # switch back to filebased backend, restart
  $0 status  # show current email backend and key mail settings

Optional variables (export before running):
  TEST_RECIPIENT       (default: $TEST_RECIPIENT)
  SMTP_HOST            (default: $SMTP_HOST)
  SMTP_PORT            (default: $SMTP_PORT)
  SMTP_USE_TLS         (default: $SMTP_USE_TLS)
  SMTP_USE_SSL         (default: $SMTP_USE_SSL)
EOF
}

ts() { date +'%F-%H%M%S'; }

backup_env() {
  cp -v "$ENV_FILE" "$ENV_FILE.bak_$(ts)"
}

# set_or_add KEY VALUE  -> remplace la ligne KEY=... ou l'ajoute à la fin
set_or_add() {
  local key="$1" val="$2"
  if grep -qE "^[[:space:]]*${key}=" "$ENV_FILE"; then
    sed -i "s#^[[:space:]]*${key}=.*#${key}=${val}#g" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

get_backend() {
  awk -F= '/^[[:space:]]*EMAIL_BACKEND=/{print $2}' "$ENV_FILE" | tail -n1
}

reload_app() {
  sudo systemctl restart "$SERVICE"
}

status() {
  echo "== STATUS (.env.prod) =="
  echo "EMAIL_BACKEND=$(get_backend)"
  grep -E '^(DEFAULT_FROM_EMAIL|SERVER_EMAIL|EMAIL_HOST=|EMAIL_PORT=|EMAIL_USE_(TLS|SSL)=|EMAIL_HOST_USER=|EMAIL_HOST_PASSWORD=)' "$ENV_FILE" || true
  echo "== systemd =="
  systemctl is-active "$SERVICE" || true
}

require_layout() {
  [[ -x "$VENV_BIN/python" ]] || { echo "ERR: venv absent: $VENV_BIN"; exit 1; }
  [[ -f "$MANAGE_PY" ]] || { echo "ERR: manage.py introuvable: $MANAGE_PY"; exit 1; }
}

case "${1:-}" in
  on)
    require_layout
    echo "[+] Switching to SMTP (no auth, port ${SMTP_PORT})"
    backup_env
    set_or_add EMAIL_BACKEND "django.core.mail.backends.smtp.EmailBackend"
    set_or_add EMAIL_HOST "$SMTP_HOST"
    set_or_add EMAIL_PORT "$SMTP_PORT"
    set_or_add EMAIL_USE_TLS "$SMTP_USE_TLS"
    set_or_add EMAIL_USE_SSL "$SMTP_USE_SSL"
    set_or_add EMAIL_HOST_USER ""
    set_or_add EMAIL_HOST_PASSWORD ""
    set_or_add DEFAULT_FROM_EMAIL "\"${DEFAULT_FROM_OK}\""
    set_or_add SERVER_EMAIL "$SERVER_EMAIL_OK"

    echo "[+] Restarting service..."
    reload_app

    echo "[+] Sending test email to: $TEST_RECIPIENT"
    "$VENV_BIN/python" "$MANAGE_PY" sendtestemail "$TEST_RECIPIENT"
    echo "[OK] Test email sent (check your inbox)."
    ;;

  off)
    require_layout
    echo "[+] Switching back to filebased backend"
    backup_env
    set_or_add EMAIL_BACKEND "django.core.mail.backends.filebased.EmailBackend"

    echo "[+] Restarting service..."
    reload_app

    echo "[i] Emails will be written to: $APP_DIR/sent_emails"
    ls -lh "$APP_DIR/sent_emails" 2>/dev/null | tail || true
    ;;

  status)
    status
    ;;

  *)
    usage
    exit 1
    ;;
esac
