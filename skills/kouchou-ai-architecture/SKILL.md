---
name: kouchou-ai-architecture
description: "Project architecture, core services, key directories, data flow, and tech stack for the kouchou-ai repository. Use when you need an overview of components, pipeline structure, or where code lives."
---

# Kouchou-AI Architecture

## Overview
Use this skill to orient yourself in the repo and explain how the system fits together.
Remember that Kouchou-AI is a broadlistening system for the Digital Democracy 2030 project, adapted from Talk to the City for Japanese municipal use cases.

## Core services and ports
- Locate the API (FastAPI) in `apps/api/` and expect it on port 8000.
- Locate the public viewer (Next.js) in `apps/public-viewer/` and expect it on port 3000.
- Locate the admin app (Next.js) in `apps/admin/` and expect it on port 4000.
- Locate the static site builder in `apps/static-site-builder/` and expect it on port 3200.
- Expect the optional Ollama service on port 11434 for local LLM usage.
- Expect Ollama to use the ELYZA-JP model by default.

## Key directories
- Use `apps/api/broadlistening/pipeline/` for pipeline steps, services, and outputs.
- Use `apps/public-viewer/components/charts/` and `apps/public-viewer/components/report/` for report UI and charts.
- Use `apps/admin/app/create/` and `apps/admin/app/create/hooks/` for report creation UI.
- Use `apps/api/src/routers/`, `apps/api/src/services/`, `apps/api/src/schemas/`, and `apps/api/src/repositories/` for API layers.

## Pipeline architecture and report flow
- Follow the flow: CSV upload -> API validation -> pipeline run -> hierarchical output -> public viewer.
- Start pipeline orchestration at `apps/api/broadlistening/pipeline/hierarchical_main.py`.
- Expect outputs under `apps/api/broadlistening/pipeline/outputs/{report_id}/`.

## Technology stack
- Treat the backend as FastAPI + OpenAI GPT models + sentence-transformers + pandas/numpy/scipy.
- Treat the frontend as Next.js 15 + TypeScript + Chakra UI + Plotly.js.
- Use pytest, Jest, and Playwright for testing.
- Use Biome (frontend) and Ruff (backend) for linting and formatting.
- Expect Azure Blob Storage support for storage needs.
- Use Lefthook for Git hooks (pre-push) as configured in `lefthook.yml`.

## Configuration pointers
- Check `biome.json`, `apps/api/pyproject.toml`, `lefthook.yml`, and `.env.example` for core config.

## Operational notes
- Require an OpenAI API key or local LLM for full pipeline runs.
- Validate LLM output for bias before acting on results.
- Back up report data before upgrading or applying breaking changes.
- Expect breaking changes between versions.
