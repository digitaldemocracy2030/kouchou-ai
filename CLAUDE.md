# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 広聴AI (Kouchou-AI) - Broadlistening System

## Overview
広聴AI (Kouchou-AI) is a comprehensive broadlistening system developed for the Digital Democracy 2030 project. This application uses AI to analyze public comments and opinions, organizing them into meaningful clusters for better understanding of public sentiment. It's based on the "Talk to the City" project by AI Objectives Institute, adapted for Japanese government and municipal use cases.

## Architecture

### Core Services
1. **API (Server)** - Port 8000
   - FastAPI-based Python backend
   - Handles report generation and data management
   - Located in `/apps/api/`

2. **Public Viewer (Client)** - Port 3000
   - Next.js frontend for report viewing
   - Interactive data visualization
   - Located in `/apps/public-viewer/`

3. **Admin** - Port 4000
   - Next.js admin interface for report creation
   - Pipeline configuration management
   - Located in `/apps/admin/`

4. **Static Site Builder** - Port 3200
   - Static site generation service
   - Located in `/apps/static-site-builder/`

5. **Ollama (Optional)** - Port 11434
   - Local LLM support for GPU-enabled environments
   - Uses ELYZA-JP model by default

## Development Commands

### Local Development Setup
```bash
# Copy environment configuration
cp .env.example .env

# Start all services
docker compose up

# Client development environment
make client-setup
make client-dev -j 3

# Access applications
# - Main app: http://localhost:3000
# - Admin panel: http://localhost:4000
# - API: http://localhost:8000
```

### Build Commands
```bash
# Build all Docker images
make build

# Static build generation
make client-build-static

# Client development builds
cd apps/public-viewer && pnpm run build
cd apps/admin && pnpm run build
```

### Code Quality & Linting
```bash
# Root level (all projects)
pnpm run lint
pnpm run format

# Individual projects
cd apps/public-viewer && pnpm run lint
cd apps/admin && pnpm run lint
cd apps/api && rye run ruff check .
```

### Testing Commands
```bash
# Server tests
make test/api
# OR
cd apps/api && rye run pytest tests/

# Client tests
cd apps/public-viewer && pnpm test

# E2E tests
cd test/e2e && pnpm test
cd test/e2e && pnpm run test:ui  # with UI
cd test/e2e && pnpm run test:debug  # debug mode
```

### Server Development
```bash
# Run server locally (development)
cd apps/api && rye run uvicorn src.main:app --reload --port 8000

# Server linting and formatting
cd apps/api && make lint/check
cd apps/api && make lint/format

# Using Docker for server operations
make lint/api-check
make lint/api-format
```

## Key Directories

### Core Processing Pipeline
- `/apps/api/broadlistening/pipeline/` - AI processing pipeline
  - `steps/` - Individual pipeline steps (embedding, clustering, labeling)
  - `services/` - Shared services (LLM, category classification)
  - `hierarchical_main.py` - Main pipeline orchestrator

### Frontend Structure
- `/apps/public-viewer/components/charts/` - Data visualization (Plotly.js)
- `/apps/public-viewer/components/report/` - Report display components
- `/apps/admin/app/create/` - Report creation interface
- `/apps/admin/app/create/hooks/` - React hooks for form state

### API Structure
- `/apps/api/src/routers/` - FastAPI route handlers
- `/apps/api/src/services/` - Business logic layer
- `/apps/api/src/schemas/` - Pydantic data models
- `/apps/api/src/repositories/` - Data access layer

## Technology Stack

### Backend (Python)
- **Framework**: FastAPI with uvicorn
- **AI/ML**: OpenAI GPT models, sentence-transformers
- **Data**: Pandas, NumPy, scipy
- **Storage**: Azure Blob Storage support
- **Testing**: pytest with coverage

### Frontend (TypeScript/React)
- **Framework**: Next.js 15 with TypeScript
- **UI**: Chakra UI component library
- **Charts**: Plotly.js with react-plotly.js
- **Testing**: Jest + Testing Library, Playwright for E2E

### Code Quality Tools
- **Frontend**: Biome (linting/formatting, 2-space indent, 120 char width)
- **Backend**: Ruff (linting/formatting, 120 char width, Python 3.12+)
- **Git Hooks**: Lefthook for pre-push validation

## Important Development Notes

### Pipeline Architecture
The core AI processing happens in `/apps/api/broadlistening/pipeline/`:
- `hierarchical_main.py` orchestrates the entire analysis
- Pipeline processes: embedding → clustering → labeling → overview generation
- Results stored in `/apps/api/broadlistening/pipeline/outputs/{report_id}/`

### Report Data Flow
1. CSV upload via admin → API validation
2. Pipeline processing (embeddings, hierarchical clustering, LLM labeling)
3. Results stored with hierarchical structure
4. Public viewer displays interactive visualizations

### Environment Configuration
- Local: `.env` files in each service directory
- Docker: `compose.yaml` orchestrates all services
- Azure: Complex deployment via Makefile targets

### Testing Strategy
- Unit tests: Components and utilities
- Integration tests: API endpoints and services
- E2E tests: Full user workflows with Playwright
- Pipeline tests: Data processing validation

**E2E Testing Important Notes:**
- **Detailed guide**: See [test/e2e/CLAUDE.md](/test/e2e/CLAUDE.md) for comprehensive E2E testing guidelines
- **Critical**: Always use `await page.waitForLoadState("networkidle")` in all Playwright tests (Next.js hydration requirement)
- **Verification first**: Run verification tests before running main E2E tests to catch configuration issues early
- **Real data**: Use actual production data structures for test fixtures (avoid manually creating dummy data)
- **Dummy server**: Client tests require a real HTTP API server (`utils/dummy-server`) because Next.js Server Components make actual HTTP requests

## Azure Deployment
```bash
# Complete Azure setup
make azure-setup-all

# Individual operations
make azure-build          # Build images
make azure-push           # Push to ACR
make azure-deploy         # Deploy containers
make azure-info           # Get service URLs
```

## Configuration Files
- `/biome.json` - Frontend code style (2-space, 120 char)
- `/apps/api/pyproject.toml` - Python dependencies and Ruff config
- `/lefthook.yml` - Git hooks for code quality
- `/.env.example` - Environment variable template

## Important Notes
- The system requires OpenAI API key or local LLM setup
- Breaking changes may occur between versions
- LLM outputs should be verified for bias
- Backup data before updates
- GPU memory 8GB+ recommended for local LLM
