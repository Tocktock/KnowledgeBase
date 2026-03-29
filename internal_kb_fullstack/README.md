# Internal KB Fullstack

워크스페이스 팀이 이미 쓰고 있는 Google Drive, GitHub, Notion, 내부 문서를 하나의 검색 가능한 지식 레이어로 묶는 애플리케이션입니다.

제품 기능의 정식 SoT는 저장소 루트의 문서를 사용합니다.

- `../docs/README.md`
- `../docs/specs/`
- `../docs/decisions/`
- `../docs/memories/`

## 구성

- `backend/`: FastAPI, worker, Postgres migration
- `frontend/`: Next.js 16, React 19, Tailwind CSS 4, TanStack Query, Tiptap 3
- `docker-compose.yml`: Postgres / migrate / api / worker / web

## Canonical specs

- 제품 개요: `../docs/specs/system-overview/spec.md`
- 워크스페이스 인증: `../docs/specs/workspace-auth/spec.md`
- 홈/내비게이션/운영 화면: `../docs/specs/home-navigation-admin/spec.md`
- 데이터 소스 연결: `../docs/specs/connectors/spec.md`
- 검색과 문서 탐색: `../docs/specs/search-and-docs/spec.md`
- 문서 작성: `../docs/specs/document-authoring/spec.md`
- 핵심 개념: `../docs/specs/concepts/spec.md`
- 용어집 검증: `../docs/specs/glossary-validation/spec.md`
- 동기화 상태: `../docs/specs/sync-status/spec.md`

## 실행

```bash
cp .env.example .env
# 필요한 OAuth / embedding 설정을 채운 뒤

docker compose up --build
```

접속:

- 프론트엔드: `http://localhost:3000`
- 백엔드 OpenAPI: `http://localhost:8000/docs`

## Runtime notes

프론트엔드는 브라우저에서 직접 FastAPI를 치지 않고, Next.js Route Handlers(`/app/api/...`)가 백엔드로 프록시합니다. 제품 동작과 공용 계약은 이 README가 아니라 루트 `docs/specs/`를 기준으로 봐야 합니다.

## Decision records and memory

- `../docs/decisions/`
- `../docs/memories/`

## Useful commands

```bash
make up
make down
make logs
make migrate
make backend-compile
make openapi-export
```
