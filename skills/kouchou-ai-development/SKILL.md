---
name: kouchou-ai-development
description: "Local development setup, build and lint commands, environment configuration, and deployment helpers for the kouchou-ai repo. Use when starting services, building images, running lint/format, or working with Azure/static builds."
---

# Kouchou-AI Development

## Overview
Use this skill for setup, build, and operational commands.

## Local development setup
- Copy `.env.example` to `.env` before starting services.
- Start all services with `docker compose up`.
- Initialize frontend dependencies with `make client-setup`.
- Run the public viewer, admin, and dummy server with `make client-dev -j 3`.

## Build and static exports
- Build all Docker images with `make build`.
- Generate static exports with `make client-build-static`.
- Build individual frontends with `pnpm run build` in `apps/public-viewer/` or `apps/admin/`.

## Linting and formatting
- Run root lint/format with `pnpm run lint` and `pnpm run format`.
- Run frontend linting with `pnpm run lint` inside each frontend app.
- Run backend linting with `rye run ruff check .` inside `apps/api/`.

## Server development
- Run the API locally with `rye run uvicorn src.main:app --reload --port 8000` in `apps/api/`.
- Use `make lint/check` and `make lint/format` in `apps/api/`.
- Use `make lint/api-check` and `make lint/api-format` for Docker-based linting.

## Environment configuration
- Keep `.env` files scoped per service directory and reference `.env.example` for defaults.
- Restart and rebuild Docker images if you change environment variables that are baked at build time.

## Pull Request workflow
- Follow `.github/PULL_REQUEST_TEMPLATE.md` when creating a PR.

## Documentation conventions
- Add language identifiers to fenced code blocks in docs (for example, `bash` or `text`).

## Azure deployment helpers
- Use `make azure-setup-all` for full Azure setup.
- Use `make azure-build`, `make azure-push`, `make azure-deploy`, and `make azure-info` for individual steps.

## Local LLM notes
- Enable Ollama with `docker compose --profile ollama up -d` when GPU support is available.
- Plan for 8GB+ GPU memory for local LLM usage.
