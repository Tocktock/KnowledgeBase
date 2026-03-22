#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR="$ROOT_DIR/internal_kb_fullstack"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
BACKEND_ENV_FILE="$PROJECT_DIR/backend/.env"
BACKEND_ENV_EXAMPLE="$PROJECT_DIR/backend/.env.example"
SAMPLE_DATA_HOST_DIR="$ROOT_DIR/sample-data/sendy-knowledge"
SAMPLE_DATA_CONTAINER_DIR="/workspace-sample-data/sendy-knowledge"

say() {
  printf '%s\n' "$*"
}

die() {
  say "error: $*" >&2
  exit 1
}

env_get() {
  file="$1"
  key="$2"
  awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "$file"
}

env_set_if_missing_or_default() {
  file="$1"
  key="$2"
  value="$3"
  default_value="${4:-}"
  tmp_file="$file.tmp.$$"

  awk -F= -v key="$key" -v value="$value" -v default_value="$default_value" '
    $1 == key {
      found = 1
      current = substr($0, index($0, "=") + 1)
      if (current == "" || current == "replace-me" || (default_value != "" && current == default_value)) {
        print key "=" value
      } else {
        print $0
      }
      next
    }
    { print }
    END {
      if (!found) {
        print key "=" value
      }
    }
  ' "$file" > "$tmp_file"
  mv "$tmp_file" "$file"
}

ollama_models() {
  command -v ollama >/dev/null 2>&1 || return 1
  ollama list 2>/dev/null | awk 'NR > 1 { print $1 }'
}

pick_ollama_embedding_model() {
  models=$(ollama_models || true)
  [ -n "${models:-}" ] || return 1

  for candidate in qwen3-embedding:0.6b qwen3-embedding nomic-embed-text mxbai-embed-large; do
    if printf '%s\n' "$models" | grep -Fx "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  printf '%s\n' "$models" | awk '/embed|embedding/ { print; exit }'
}

pick_ollama_generation_model() {
  models=$(ollama_models || true)
  [ -n "${models:-}" ] || return 1

  for candidate in qwen3:0.6b qwen3 llama3.2 qwen2.5:3b qwen2.5 mistral; do
    if printf '%s\n' "$models" | grep -Fx "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  printf '%s\n' "$models" | awk '!/embed|embedding/ { print; exit }'
}

known_ollama_embedding_dimensions() {
  model="$1"
  case "$model" in
    qwen3-embedding:0.6b|qwen3-embedding|mxbai-embed-large)
      printf '1024\n'
      ;;
    nomic-embed-text)
      printf '768\n'
      ;;
    *)
      return 1
      ;;
  esac
}

apply_ollama_profile_if_possible() {
  embedding_model=$(pick_ollama_embedding_model || true)
  generation_model=$(pick_ollama_generation_model || true)

  if [ -z "${embedding_model:-}" ]; then
    return
  fi

  embedding_dimensions=$(known_ollama_embedding_dimensions "$embedding_model" || true)
  ollama_base_url="http://host.docker.internal:11434/v1"

  for file in "$ENV_FILE" "$BACKEND_ENV_FILE"; do
    env_set_if_missing_or_default "$file" "EMBEDDING_API_KEY" "ollama"
    env_set_if_missing_or_default "$file" "EMBEDDING_BASE_URL" "$ollama_base_url"
    env_set_if_missing_or_default "$file" "EMBEDDING_MODEL" "$embedding_model" "text-embedding-3-small"
    if [ -n "${embedding_dimensions:-}" ]; then
      env_set_if_missing_or_default "$file" "EMBEDDING_DIMENSIONS" "$embedding_dimensions" "1536"
    fi
    if [ -n "${generation_model:-}" ]; then
      env_set_if_missing_or_default "$file" "GENERATION_MODEL" "$generation_model"
      env_set_if_missing_or_default "$file" "GENERATION_BASE_URL" "$ollama_base_url"
      env_set_if_missing_or_default "$file" "GENERATION_API_KEY" "ollama"
    fi
  done

  say "applied local Ollama defaults for missing embedding/generation env values"
}

embedding_profile_ready() {
  file="$1"
  model=$(env_get "$file" "EMBEDDING_MODEL")
  api_key=$(env_get "$file" "EMBEDDING_API_KEY")
  [ -n "${model:-}" ] && [ -n "${api_key:-}" ] && [ "$api_key" != "replace-me" ]
}

generation_profile_ready() {
  file="$1"
  model=$(env_get "$file" "GENERATION_MODEL")
  api_key=$(env_get "$file" "GENERATION_API_KEY")
  [ -n "${model:-}" ] && [ -n "${api_key:-}" ] && [ "$api_key" != "replace-me" ]
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
apply_ollama_profile_if_possible

say "starting internal_kb_fullstack with POSTGRES_PORT=$POSTGRES_PORT"
(
  cd "$PROJECT_DIR"
  docker compose up -d --build
)

wait_for_http "api health" "http://localhost:8000/healthz"
wait_for_http "api readiness" "http://localhost:8000/readyz"
wait_for_http "web" "http://localhost:3000"

if [ -d "$SAMPLE_DATA_HOST_DIR" ]; then
  if embedding_profile_ready "$ENV_FILE"; then
    say "bootstrapping sample corpus from $SAMPLE_DATA_HOST_DIR"
    (
      cd "$PROJECT_DIR"
      docker compose exec -T api python scripts/import_sample_corpus.py \
        --root "$SAMPLE_DATA_CONTAINER_DIR" \
        --skip-if-detected \
        --refresh-glossary
    )
    say "sample-data bootstrap completed; large first-time imports may continue embedding in the background"
  else
    say "sample corpus detected, but embedding profile is not configured; skipping sample-data bootstrap"
  fi
else
  say "sample corpus not found; skipping sample-data bootstrap"
fi

if ! generation_profile_ready "$ENV_FILE"; then
  say "warning: generation profile is not configured; glossary draft generation will not be available yet"
fi

say ""
say "internal_kb_fullstack is up."
say "web: http://localhost:3000"
say "api docs: http://localhost:8000/docs"
say "postgres host port: $POSTGRES_PORT"
say "stop: cd \"$PROJECT_DIR\" && docker compose down"
