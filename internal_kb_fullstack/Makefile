PROJECT_NAME := internal-kb
COMPOSE := docker compose

.PHONY: up down logs build migrate backend-compile backend-test openapi-export

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) run --rm migrate

backend-compile:
	cd backend && python -m compileall app tests

backend-test:
	cd backend && pytest -q

openapi-export:
	cd backend && python scripts/export_openapi.py
