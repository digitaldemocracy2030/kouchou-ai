---
name: kouchou-ai-testing
description: "Testing commands and strategy for the kouchou-ai repo, including unit/integration tests and Playwright E2E rules. Use when writing, running, or debugging tests."
---

# Kouchou-AI Testing

## Overview
Use this skill to run and debug tests across the repo.

## Core test commands
- Run API tests with `make test/api` or `rye run pytest tests/` in `apps/api/`.
- Run public viewer tests with `pnpm test` in `apps/public-viewer/`.
- Run admin tests with `pnpm test` in `apps/admin/`.
- Run Playwright E2E tests with `pnpm test` in `test/e2e/`.
- Run Playwright with UI or debug mode using `pnpm run test:ui` or `pnpm run test:debug` in `test/e2e/`.

## Testing strategy
- Use unit tests for components and utilities.
- Use integration tests for API endpoints and services.
- Use E2E tests for full user workflows.
- Use pipeline tests to validate data processing outputs.

## E2E testing rules (Playwright + Next.js)
- Always call `await page.waitForLoadState("networkidle")` after `page.goto`.
- Run verification tests before main E2E runs to confirm dummy server and env are correct.
- Use production-shaped fixtures and avoid hand-crafted dummy data.
- Use the dummy server in `utils/dummy-server` because Server Components make real HTTP requests.

## E2E references
- Read `test/e2e/CLAUDE.md` for the full Playwright guide, dummy server patterns, and troubleshooting flow.
