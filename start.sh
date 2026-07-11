#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${PROJECT_ROOT}/soc_server"
VENV_DIR="${PROJECT_ROOT}/.venv"
ENV_FILE="${PROJECT_ROOT}/.env"

cd "${SERVER_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

export SOC_SENTINEL_ENV="${SOC_SENTINEL_ENV:-production}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-5000}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r requirements.txt

exec "${VENV_DIR}/bin/gunicorn" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --bind "${HOST}:${PORT}" \
  --access-logfile "-" \
  --error-logfile "-" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  "wsgi:application"
