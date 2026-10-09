# 広聴 AI / kouchou-ai

English | [日本語](./README.md) | [한국어](./README.ko.md)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/digitaldemocracy2030/kouchou-ai)

This is the repository of "広聴 AI" (kouchou-ai), software for broad listening developed in the Digital Democracy 2030 project.

> This README is an English translation of [README.md](./README.md) (Japanese). If the two differ, the Japanese version takes precedence. Most of the guides and documents linked from this page are written in Japanese.

The project is based on [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports), developed by the [AI Objectives Institute](https://www.aiobjectivesinstitute.org/), and improves its features to fit the practical needs of Japanese local governments and politicians.

- Example features
  - Features that are easy to use for non-developers (CSV upload)
  - Dense cluster extraction
  - Analysis for public comments (planned)
  - Defense against majority attacks (planned)

## Prerequisites

- For general users:
  - Download the stable release (see the guide for [Windows](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/windows-setup) / [Mac](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/mac-setup) / [Linux](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/linux-setup))
  - Docker (install it by following each guide)
  - An OpenAI API key
- For developers:
  - docker
  - git
  - An OpenAI API key

## Setup and launch

### Overview

- 広聴 AI is built as a web application. You start the application and operate it in your browser to generate and view reports
- The steps below describe how to set it up locally with docker compose
- To host it in a remote environment, host each service (public-viewer, admin, api) separately with the appropriate environment variables
  - The environment variables for each service are described in `.env.example`

### Recommended number of clusters

Guidelines for the number of opinion groups (clusters) when creating a report:

- We recommend using the cube root of the number of comments (∛n) as a baseline
- Examples:
  - 1000 comments: 10→100 (first level → second level)
  - 8000 comments: 20→400
  - 125 comments: 5→25
  - 400 comments: 7→50
- The defaults are set based on the above, but adjusting them to the number of comments gives the best results

### Steps

- If you are not a developer, see the user guides below:

  - [User guide for Windows](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/windows-setup)
  - [User guide for Mac](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/mac-setup)
  - [User guide for Linux](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/linux-setup)

- For developers:
  - Clone the repository
  - Run `cp .env.example .env` in a terminal
    - After copying, set each environment variable. The meaning of each variable is described in `.env.example`
  - Run `docker compose up` in a terminal
    - Open http://localhost:3000 in a browser to see the report list
    - Open http://localhost:4000 in a browser to see the admin screen
    - If you edit the environment variables (`.env`), run `docker compose down` and then `docker compose up --build` to start the application
      - Some environment variables are embedded when the Docker images are built, so you need to rebuild after changing them
    - If starting all modules is slow, you can start only what you need, e.g. `docker compose up --no-deps public-viewer api`

### Using a local LLM

To use a local LLM on a machine with a GPU, follow these steps:

1. Set `WITH_GPU=true` in your `.env` file
2. Run the following command to start the services including Ollama:
   ```sh
   docker compose --profile ollama up -d
   ```
3. The Ollama service starts and is available from the host on the port set by `OLLAMA_HOST_PORT` in `.env` (default: 11434). The app still connects to `ollama:11434`
   - If another Ollama or other process on the host already uses port 11434, startup fails with `failed to bind host port ... address already in use`. In that case, change `OLLAMA_HOST_PORT` in `.env` to a free port (e.g. `11435`). The app connects via container-to-container networking (`ollama:11434`), so you do not need to change `NEXT_PUBLIC_LOCAL_LLM_ADDRESS`
4. By default, the `hf.co/elyza/Llama-3-ELYZA-JP-8B-GGUF` model is downloaded automatically
5. Once downloaded, the model can be selected when generating a report

**Prerequisites**:

- **Linux** / **Windows**:

  - An NVIDIA GPU
  - An appropriate NVIDIA driver
  - The equivalent of the NVIDIA Container Toolkit
    - On Linux: nvidia-docker2 / NVIDIA Container Toolkit
    - On Windows: GPU support settings in Docker Desktop
  - About 5GB or more of free disk space to download and install the default model

- **macOS**:
  - Apple Silicon (M1/M2/M3) and most Intel Macs basically do not support NVIDIA GPUs

**Notes**:

- Using a local LLM requires enough GPU memory (8GB or more recommended)
- The first launch may take a while to download the model

### Google Analytics

- You can use Google Analytics 4 (GA4) to analyze user access
- Setup:
  1. Create a Google Analytics account, set up a data stream, and get a measurement ID (in the form G-XXXXXXXXXX)
  2. Set the following environment variables in your `.env` file:
     - `NEXT_PUBLIC_GA_MEASUREMENT_ID`: measurement ID for the client app (port 3000)
     - `NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID`: measurement ID for the admin app (port 4000)
  3. Google Analytics is enabled only in production (`ENVIRONMENT=production` or `NODE_ENV=production`)
     - It is automatically disabled in development, so access during development is not counted

For how to use the app after it starts, see [How to use 広聴 AI](https://digitaldemocracy2030.github.io/kouchou-ai/user-guide/how-to-use) (Japanese).

### Setting up metadata files

To customize information about the report author (logo image, links, etc.), configure it as follows.

1. Default environment

   - In the default environment (`apps/api/public/meta/default`), no images or links are shown
   - This is a setting for test environments; do not use it in production

2. How to customize

   - Place the following files in the `apps/api/public/meta/custom` directory to customize the report author information:
     - `metadata.json`: basic information about the report author
     - `reporter.png`: logo image of the report author
     - `icon.png`: icon image of the report
     - `ogp.png`: OGP image of the report

3. Display conditions
   - Image: shown only if `reporter.png` exists in the `custom` directory
   - Links: each link in `metadata.json` (webLink, privacyLink, termsLink) is shown only if it has a value
   - If a value is empty or a file does not exist, the corresponding element is not shown

### Setting up on Azure

For how to set up on Azure, see [Setting up on Azure](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/azure) (Japanese).

### Static file export

The report viewer can also be exported as static files.
By placing the exported files on a web server, reports can be viewed without running the app.

To generate static files, run:

```sh
make client-build-static
```

The static files are written to the `out/` directory; place them on your web server.

For hosting exported reports on GitHub Pages, see [Hosting static files on GitHub Pages](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/github-pages) (Japanese).

If you add a CSP in a static hosting environment, also see the [CSP guide for static hosting](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/static-hosting-csp) (Japanese). Plotly's `scattergl` requires `script-src 'unsafe-eval'`, and without `blob:` in `img-src` the browser blocks PNG downloads.

## Architecture overview

The system consists of the following services.

### api

- Port: 8000
- Role: backend API service
- Main features:
  - Retrieving and managing report data
  - Running the report generation pipeline
  - Providing admin APIs
- Tech stack:
  - Python (FastAPI)
  - Docker

### public-viewer

- Port: 3000
- Role: frontend for viewing reports
- Main features:
  - Report visualization
  - Interactive data analysis
  - User-friendly interface
- Tech stack:
  - Next.js
  - TypeScript
  - Docker

### admin

- Port: 4000
- Role: admin frontend
- Main features:
  - Creating and editing reports
  - Managing pipeline settings
  - Managing system settings
- Tech stack:
  - Next.js
  - TypeScript
  - Docker

### utils/dummy-server

- Role: dummy API for development
- Usage: used as an API mock in the development environment

## Setting up the public-viewer development environment

Steps to start the frontend applications (public-viewer and admin) with the development dummy server (dummy-server) as the backend.

### 1. Set up public-viewer, admin, and dummy-server

```sh
make client-setup
```

### 2. Start the development servers

```sh
make client-dev -j 3
```

## Disclaimer

Large language models (LLMs) are known to have biases and to produce unreliable results. We are actively working on ways to mitigate these issues, but at this stage we cannot provide any guarantees. Especially when making important decisions, do not rely solely on the output of this app; always verify the content.

## Notes

This app is in an early stage of development, and changes that are incompatible with previous versions may be made as development continues.
When updating the app, if you have important data (reports), we recommend backing up the app and data before updating.

## Guidelines for developers

広聴 AI is developed as OSS, and we welcome contributions from developers.
If you want to participate without writing code, see [Getting started with feedback, questions, and sharing use cases](./CONTRIBUTING.md#コードを書かずに参加する) (Japanese).

For details, see the [Contribution guide](https://digitaldemocracy2030.github.io/kouchou-ai/development/contributing) (Japanese).
This project is also developed in collaboration with the AI engineer "[Devin](https://cognition.ai)".
Our collaboration with Devin is still being explored; see [Collaborating with Devin](https://digitaldemocracy2030.github.io/kouchou-ai/development/devin-collaboration) (Japanese).

## Feature requests and bug reports

- If you have a GitHub account, please post bugs and improvement requests to [Issues](https://github.com/digitaldemocracy2030/kouchou-ai/issues)
- If you do not have a GitHub account, please use the Google Form below
  - [Bug report / improvement request form](https://docs.google.com/forms/d/e/1FAIpQLSf43rpi8N1hGQmECDOBOmiV3c-Buwf4gWSj2sYc2KbZL9NOBA/viewform?usp=dialog)

## Credits

This project is developed with reference to [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports), developed by the [AI Objectives Institute](https://www.aiobjectivesinstitute.org/). It partially uses its source code under its license and adds features and improvements. We express our gratitude for the original authors' contributions.
