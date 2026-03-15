#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR="$ROOT_DIR/internal_kb_fullstack"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
BACKEND_ENV_FILE="$PROJECT_DIR/backend/.env"
BACKEND_ENV_EXAMPLE="$PROJECT_DIR/backend/.env.example"

say() {
  printf '%s\n' "$*"
}

die() {
  say "error: $*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || die "docker is required"
docker compose version >/dev/null 2>&1 || die "docker compose is required"
[ -d "$PROJECT_DIR" ] || die "project directory not found: $PROJECT_DIR"
[ -f "$ENV_EXAMPLE" ] || die "missing env example: $ENV_EXAMPLE"
[ -f "$BACKEND_ENV_EXAMPLE" ] || die "missing backend env example: $BACKEND_ENV_EXAMPLE"

port_is_in_use() {
  port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
    return $?
  fi

  return 1
}

choose_postgres_port() {
  port=5432
  while port_is_in_use "$port"; do
    port=$((port + 1))
  done
  printf '%s\n' "$port"
}

write_env_from_example() {
  src="$1"
  dest="$2"
  postgres_port="$3"

  awk -v postgres_port="$postgres_port" '
    BEGIN { wrote_port = 0 }
    /^POSTGRES_PORT=/ {
      print "POSTGRES_PORT=" postgres_port
      wrote_port = 1
      next
    }
    { print }
    END {
      if (!wrote_port) {
        print "POSTGRES_PORT=" postgres_port
      }
    }
  ' "$src" > "$dest"
}

read_postgres_port() {
  file="$1"
  value=$(awk -F= '/^POSTGRES_PORT=/{print $2; exit}' "$file")
  if [ -n "${value:-}" ]; then
    printf '%s\n' "$value"
  else
    printf '5432\n'
  fi
}

ensure_env_file() {
  src="$1"
  dest="$2"
  postgres_port="$3"
  display_path="$dest"

  if [ -f "$dest" ]; then
    say "using existing $display_path"
    return
  fi

  write_env_from_example "$src" "$dest" "$postgres_port"
  say "created $display_path with POSTGRES_PORT=$postgres_port"
}

wait_for_http() {
  name="$1"
  url="$2"
  attempts=60

  if ! command -v curl >/dev/null 2>&1; then
    say "curl not found; skipping $name check"
    return
  fi

  while [ "$attempts" -gt 0 ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      say "$name is ready: $url"
      return
    fi
    attempts=$((attempts - 1))
    sleep 1
  done

  die "$name did not become ready: $url"
}

if [ -f "$ENV_FILE" ]; then
  POSTGRES_PORT=$(read_postgres_port "$ENV_FILE")
else
  POSTGRES_PORT=$(choose_postgres_port)
fi

ensure_env_file "$ENV_EXAMPLE" "$ENV_FILE" "$POSTGRES_PORT"
ensure_env_file "$BACKEND_ENV_EXAMPLE" "$BACKEND_ENV_FILE" "$POSTGRES_PORT"

say "starting internal_kb_fullstack with POSTGRES_PORT=$POSTGRES_PORT"
(
  cd "$PROJECT_DIR"
  docker compose up -d --build
)

wait_for_http "api health" "http://localhost:8000/healthz"
wait_for_http "api readiness" "http://localhost:8000/readyz"
wait_for_http "web" "http://localhost:3000"

say ""
say "internal_kb_fullstack is up."
say "web: http://localhost:3000"
say "api docs: http://localhost:8000/docs"
say "postgres host port: $POSTGRES_PORT"
say "stop: cd \"$PROJECT_DIR\" && docker compose down"
