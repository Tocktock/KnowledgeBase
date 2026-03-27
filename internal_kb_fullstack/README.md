# Internal KB Fullstack

워크스페이스 팀이 이미 쓰고 있는 Google Drive, Notion, 내부 문서를 하나의 검색 가능한 지식 레이어로 묶는 제품입니다.
관리자는 데이터 소스를 한 번 연결하고, 구성원은 검색·문서 탐색·핵심 개념 화면에서 바로 최신 정보를 소비합니다.

## 구성

- `backend/`: FastAPI, worker, Postgres migration
- `frontend/`: Next.js 16, React 19, Tailwind CSS 4, TanStack Query, Tiptap 3
- `docker-compose.yml`: Postgres / migrate / api / worker / web

## Product thesis

- **Workspace knowledge layer**: 외부 팀 지식을 동기화해 워크스페이스 공용 컨텍스트로 만듭니다.
- **Sync-first**: Google Drive, Notion, 직접 작성 문서를 같은 저장소로 가져와 검색·문서·핵심 개념에 반영합니다.
- **Trust-first**: 검색 결과와 문서 상세에서 출처, 최신성, 근거 수를 함께 보여 줍니다.
- **Admin connects once, members benefit immediately**: 관리자는 데이터 소스를 관리하고, 일반 구성원은 운영 화면을 몰라도 가치를 얻습니다.

## Main surfaces

- `/` 역할 기반 홈
- `/search` 워크스페이스 검색
- `/docs` 문서 탐색
- `/glossary` 핵심 개념
- `/connectors` 데이터 소스 설정
- `/jobs` 동기화 상태
- `/glossary/review` 지식 검수
- `/login` 단일 로그인 진입점

## 실행

```bash
cp .env.example .env
# 필요한 OAuth / embedding 설정을 채운 뒤

docker compose up --build
```

접속:

- 프론트엔드: `http://localhost:3000`
- 백엔드 OpenAPI: `http://localhost:8000/docs`

## 구현 메모

프론트엔드는 브라우저에서 직접 FastAPI를 치지 않고, Next.js Route Handlers(`/app/api/...`)가 백엔드로 프록시합니다. 그래서 브라우저 CORS 설정 없이 로컬 Compose 환경에서 바로 연결됩니다.

문서 작성은 Markdown 기반이며, Tiptap의 Markdown extension을 사용해 시각 편집 모드와 소스 모드를 전환합니다. 다만 기본 제품 흐름은 “새 문서 작성”보다 “연결된 소스를 소비 가능한 지식 레이어로 만들기”에 맞춰져 있습니다.


## Decision records

- `docs/decisions/`: architectural decisions and project memory


## Useful commands

```bash
make up
make down
make logs
make migrate
make backend-compile
make openapi-export
```
