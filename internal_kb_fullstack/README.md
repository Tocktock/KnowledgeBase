# Internal KB Fullstack

백엔드(FastAPI + Postgres + pgvector) 위에 Next.js 기반 프론트엔드를 붙인 전체 예제입니다.

## 구성

- `backend/`: FastAPI, worker, Postgres migration
- `frontend/`: Next.js 16, React 19, Tailwind CSS 4, TanStack Query, Tiptap 3
- `docker-compose.yml`: Postgres / migrate / api / worker / web

## UX 컨셉

- **Notion 같은 점**: 여백이 넓고 집중감 있는 작성 경험, 시각 편집, 문서 속성 메타데이터
- **나무위키 같은 점**: slug 중심 URL, 문서 간 링크, backlinks / related docs / 목차 사이드바

## 실행

```bash
cp .env.example .env
# EMBEDDING_API_KEY를 채운 뒤

docker compose up --build
```

접속:

- 프론트엔드: `http://localhost:3000`
- 백엔드 OpenAPI: `http://localhost:8000/docs`

## 주요 프론트 페이지

- `/` 홈 대시보드
- `/search` 시맨틱 검색
- `/docs` 문서 탐색
- `/docs/[slug]` 문서 상세
- `/new` 새 문서 작성 / 파일 업로드
- `/jobs` 임베딩 작업 현황

## 구현 메모

프론트엔드는 브라우저에서 직접 FastAPI를 치지 않고, Next.js Route Handlers(`/app/api/...`)가 백엔드로 프록시합니다. 그래서 브라우저 CORS 설정 없이 로컬 Compose 환경에서 바로 연결됩니다.

문서 작성은 기본적으로 Markdown 기반이며, Tiptap의 Markdown extension을 사용해 시각 편집 모드와 소스 모드를 전환합니다.


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
