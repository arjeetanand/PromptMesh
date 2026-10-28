#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PROMPTMESH_PORT:-4004}"
USER_ID="$(id -u)"
STATE_DIR="${TMPDIR:-/tmp}/promptmesh-${USER_ID}"
PID_FILE="${STATE_DIR}/promptmesh-${PORT}.pid"
LOG_FILE="${STATE_DIR}/promptmesh-${PORT}.log"
PYTHON_EXECUTABLE="${APP_ROOT}/.venv/bin/python"

if [[ ! -x "$PYTHON_EXECUTABLE" ]]; then
  PYTHON_EXECUTABLE="$(command -v python3 || true)"
fi
if [[ -z "$PYTHON_EXECUTABLE" ]]; then
  echo "Python 3 is required to run PromptMesh." >&2
  exit 1
fi

case "$PORT" in
  4004|5004|6004) ;;
  *) echo "Use port 4004 (main), 5004 (test), or 6004 (preview)." >&2; exit 2 ;;
esac

mkdir -p "$STATE_DIR"

process_matches_project() {
  local pid="$1" command working_directory
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  working_directory="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
  [[ "$command" == *"uvicorn app:app"* && "$working_directory" == "$APP_ROOT" ]]
}

if [[ -f "$PID_FILE" ]]; then
  read -r OLD_PID < "$PID_FILE"
  if [[ ! "$OLD_PID" =~ ^[0-9]+$ ]]; then
    echo "Invalid PID file at $PID_FILE; inspect it before restarting." >&2
    exit 1
  fi
  if kill -0 "$OLD_PID" 2>/dev/null; then
    if ! process_matches_project "$OLD_PID"; then
      echo "PID $OLD_PID is not an identifiable PromptMesh server from $APP_ROOT; leaving it untouched." >&2
      exit 1
    fi
    kill -TERM "$OLD_PID"
    for _ in {1..20}; do
      kill -0 "$OLD_PID" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$OLD_PID" 2>/dev/null; then
      echo "PromptMesh PID $OLD_PID did not stop after SIGTERM; leaving it for inspection." >&2
      exit 1
    fi
  fi
  rm -f "$PID_FILE"
fi

LISTENERS="$(lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$LISTENERS" ]]; then
  echo "Port $PORT is already in use by PID(s): $LISTENERS. No process was stopped." >&2
  exit 1
fi

nohup "$PYTHON_EXECUTABLE" -m uvicorn app:app --host 127.0.0.1 --port "$PORT" --no-access-log \
  >> "$LOG_FILE" 2>&1 < /dev/null &
SERVER_PID=$!
printf '%s\n' "$SERVER_PID" > "$PID_FILE"

for _ in {1..40}; do
  if curl --silent --fail "http://127.0.0.1:${PORT}/api/health" >/dev/null; then
    echo "PromptMesh is ready at http://127.0.0.1:${PORT} (PID $SERVER_PID)."
    exit 0
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if kill -0 "$SERVER_PID" 2>/dev/null && process_matches_project "$SERVER_PID"; then
  kill -TERM "$SERVER_PID"
  for _ in {1..20}; do
    kill -0 "$SERVER_PID" 2>/dev/null || break
    sleep 0.5
  done
fi
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  rm -f "$PID_FILE"
fi
echo "PromptMesh did not become healthy on port $PORT. Recent log output:" >&2
tail -n 40 "$LOG_FILE" >&2 || true
exit 1
