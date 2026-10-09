# 広聴 AI / kouchou-ai

[日本語](./README.md) | 한국어

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/digitaldemocracy2030/kouchou-ai)

디지털 민주주의 2030 프로젝트에서 브로드 리스닝(broad listening)을 실현하기 위한 소프트웨어 ‘広聴 AI(코초 AI, kouchou-ai)’의 저장소입니다.

> 이 문서는 [README.md](./README.md)(일본어)의 한국어 번역입니다. 내용이 다를 경우 일본어판이 우선합니다. 본문에서 링크하는 가이드와 문서는 대부분 일본어로 작성되어 있습니다.

이 프로젝트는 [AI Objectives Institute](https://www.aiobjectivesinstitute.org/)가 개발한 [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)를 참고하여, 일본의 지방자치단체와 정치인의 실무에 맞춘 기능 개선을 진행하고 있습니다.

- 기능 예시
  - 개발자가 아니어도 다루기 쉬운 기능 (CSV 업로드)
  - 밀도 높은 클러스터 추출 기능
  - 퍼블릭 코멘트(의견 공모)용 분석 기능 (예정)
  - 다수파 공격에 대한 방어 기능 (예정)

## 사전 요구 사항

- 일반 사용자:
- 안정판 릴리스를 다운로드 ([Windows](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/windows-setup)/[Mac](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/mac-setup)/[Linux](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/linux-setup) 각 가이드 참조)
  - Docker (각 가이드에 따라 설치)
  - OpenAI API 키
- 개발자:
  - docker
  - git
  - OpenAI API 키
## 설정 및 실행

### 전제

- 広聴 AI는 웹 애플리케이션으로 만들어져 있으며, 애플리케이션을 실행한 뒤 브라우저에서 조작하여 리포트를 생성하고 열람할 수 있습니다
- 아래 절차는 로컬 환경에서 docker compose를 사용해 설정하는 방법입니다
- 원격 환경에서 호스팅하는 경우에는 각 서비스(public-viewer, admin, api)에 환경 변수를 적절히 설정한 뒤 각각 호스팅해 주세요
  - 서비스별로 설정할 환경 변수는 .env.example에 적혀 있습니다

### 권장 클러스터 수 설정

리포트를 만들 때 의견 그룹 수(클러스터 수)의 기준은 다음과 같습니다:

- 코멘트 수의 세제곱근(∛n)을 기준으로 설정하기를 권장합니다
- 예:
  - 코멘트 1000건: 10→100 (1층 → 2층)
  - 코멘트 8000건: 20→400
  - 코멘트 125건: 5→25
  - 코멘트 400건: 7→50
- 기본 설정은 위 기준에 따라 정해지지만, 코멘트 수에 맞게 조정하면 더 좋은 분석 결과를 얻을 수 있습니다

### 절차

- 개발자가 아닌 분은 아래 사용자 가이드를 참조해 주세요:

  - [Windows 환경 사용자 가이드](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/windows-setup)
  - [Mac 환경 사용자 가이드](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/mac-setup)
  - [Linux 환경 사용자 가이드](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/linux-setup)

- 개발자:
  - 저장소를 클론
  - 콘솔에서 `cp .env.example .env` 실행
    - 복사한 뒤 각 환경 변수를 설정합니다. 각 환경 변수의 의미는 .env.example에 적혀 있습니다.
  - 콘솔에서 `docker compose up` 실행
    - 브라우저에서 http://localhost:3000 에 접속하면 리포트 목록 화면을 볼 수 있습니다
    - 브라우저에서 http://localhost:4000 에 접속하면 관리 화면을 볼 수 있습니다
    - 환경 변수(.env)를 수정한 경우에는 `docker compose down`을 실행한 뒤 `docker compose up --build`로 애플리케이션을 실행해 주세요
      - 일부 환경 변수는 Docker 이미지를 빌드할 때 포함되므로, 환경 변수를 바꾼 경우에는 다시 빌드해야 합니다
    - 모든 모듈을 실행하면 느린 경우에는 `docker compose up --no-deps public-viewer api`처럼 필요한 것만 골라 실행할 수 있습니다

### 로컬 LLM 사용

GPU가 탑재된 머신에서 로컬 LLM을 사용하려면 다음 절차를 따르세요:

1. `.env` 파일에 `WITH_GPU=true`를 설정합니다
2. 다음 명령을 실행하여 Ollama를 포함한 서비스를 실행합니다:
   ```sh
   docker compose --profile ollama up -d
   ```
3. Ollama 서비스가 실행되면, 호스트에서는 `.env`의 `OLLAMA_HOST_PORT`로 지정한 포트(기본값 11434)로 사용할 수 있습니다. 앱에서 접속하는 주소는 계속 `ollama:11434`입니다
   - 호스트에서 이미 다른 Ollama 등이 11434번 포트를 사용하고 있으면 `failed to bind host port ... address already in use`로 실행되지 않습니다. 이 경우 `.env`의 `OLLAMA_HOST_PORT`를 비어 있는 번호(예: `11435`)로 바꿔 주세요. 앱은 컨테이너 간 통신(`ollama:11434`)으로 접속하므로 `NEXT_PUBLIC_LOCAL_LLM_ADDRESS`는 바꿀 필요가 없습니다
4. 기본적으로 `hf.co/elyza/Llama-3-ELYZA-JP-8B-GGUF` 모델이 자동으로 다운로드됩니다
5. 다운로드가 끝난 모델은 리포트를 생성할 때 선택하여 사용할 수 있습니다

**사전 요구 사항**:

- **Linux** / **Windows**:

  - NVIDIA GPU가 탑재되어 있을 것
  - 적절한 NVIDIA 드라이버가 설치되어 있을 것
  - NVIDIA Container Toolkit에 해당하는 것이 설치되어 있을 것
    - Linux에서는 nvidia-docker2 / NVIDIA Container Toolkit
    - Windows에서는 Docker Desktop의 GPU 지원 설정
  - 기본 모델 데이터의 다운로드와 설치에 약 5GB 이상의 여유 디스크 공간이 필요

- **macOS**:
  - Apple Silicon (M1/M2/M3)과 대부분의 Intel Mac에서는 NVIDIA GPU를 기본적으로 사용할 수 없습니다

**주의**:

- 로컬 LLM을 사용하려면 충분한 GPU 메모리가 필요합니다 (8GB 이상 권장)
- 처음 실행할 때는 모델 다운로드에 시간이 걸릴 수 있습니다

### Google Analytics 설정

- Google Analytics 4(GA4)를 사용하여 사용자 접속을 분석할 수 있습니다
- 설정 절차:
  1. Google Analytics 계정을 만들고 데이터 스트림을 설정하여 측정 ID를 받습니다 (G-XXXXXXXXXX 형식)
  2. `.env` 파일에 다음 환경 변수를 설정합니다:
     - `NEXT_PUBLIC_GA_MEASUREMENT_ID`: 클라이언트 앱(포트 3000)용 측정 ID
     - `NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID`: 관리 화면 앱(포트 4000)용 측정 ID
  3. 운영 환경(`ENVIRONMENT=production` 또는 `NODE_ENV=production`)에서만 Google Analytics가 활성화됩니다
     - 개발 환경에서는 자동으로 비활성화되므로, 개발 중의 접속은 집계되지 않습니다

앱을 실행한 뒤의 조작 방법은 [広聴 AI 사용법](https://digitaldemocracy2030.github.io/kouchou-ai/user-guide/how-to-use)을 참조하세요

### 메타데이터 파일 설정

리포트 작성자 정보(로고 이미지, 링크 등)를 바꾸려면 다음 절차로 설정해 주세요.

1. 기본 환경

  - 기본 환경(`apps/api/public/meta/default`)에서는 이미지와 링크가 표시되지 않습니다
   - 이는 테스트 환경용 설정이므로 운영 환경에서는 사용하지 마세요

2. 바꾸는 방법

  - `apps/api/public/meta/custom` 디렉터리에 다음 파일을 두면 리포트 작성자 정보를 바꿀 수 있습니다:
     - `metadata.json`: 리포트 작성자의 기본 정보
     - `reporter.png`: 리포트 작성자의 로고 이미지
     - `icon.png`: 리포트 아이콘 이미지
     - `ogp.png`: 리포트의 OGP 이미지

3. 표시 조건
   - 이미지 표시: `reporter.png`가 `custom` 디렉터리에 있을 때만 표시됩니다
   - 링크 표시: `metadata.json`의 각 링크(webLink, privacyLink, termsLink)에 값이 설정되어 있을 때만 표시됩니다
   - 값이 비어 있거나 파일이 없으면 해당 요소는 표시되지 않습니다

### Azure 환경 설정

Azure 환경에 설정하는 방법은 [Azure 환경 설정 방법](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/azure)을 참조하세요

### 정적 파일 출력

리포트를 열람하는 화면은 정적 파일로도 출력할 수 있습니다.  
출력한 파일을 웹 서버에 두면 앱을 실행하지 않고도 리포트를 열람할 수 있습니다.

정적 파일을 생성하려면 다음 명령을 실행하세요.

```sh
make client-build-static
```

`out/` 디렉터리에 정적 파일이 출력되므로 웹 서버에 배치해 주세요.

정적으로 내보낸 리포트를 GitHub Pages에서 호스팅하는 방법은 [GitHub Pages 정적 파일 호스팅 절차](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/github-pages)를 참조하세요.

정적 호스팅 환경에서 CSP를 적용하는 경우에는 [정적 호스팅용 CSP 설정 가이드](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/static-hosting-csp)도 참조하세요. Plotly의 `scattergl`에는 `script-src 'unsafe-eval'`이 필요하고, `img-src`에 `blob:`이 없으면 PNG 다운로드가 브라우저에서 차단됩니다.

## 아키텍처 개요

이 시스템은 다음 서비스로 구성되어 있습니다.

### api

- 포트: 8000
- 역할: 백엔드 API 서비스
- 주요 기능:
  - 리포트 데이터 조회 및 관리
  - 리포트 생성 파이프라인 실행
  - 관리용 API 제공
- 기술 스택:
  - Python (FastAPI)
  - Docker

### public-viewer

- 포트: 3000
- 역할: 리포트 표시용 프런트엔드
- 주요 기능:
  - 리포트 시각화
  - 인터랙티브한 데이터 분석
  - 사용하기 쉬운 인터페이스
- 기술 스택:
  - Next.js
  - TypeScript
  - Docker

### admin

- 포트: 4000
- 역할: 관리용 프런트엔드
- 주요 기능:
  - 리포트 작성 및 편집
  - 파이프라인 설정 관리
  - 시스템 설정 관리
- 기술 스택:
  - Next.js
  - TypeScript
  - Docker

### utils/dummy-server

- 역할: 개발용 더미 API
- 용도: 개발 환경에서 API 목(mock)으로 사용

## public-viewer 개발 환경 구축 절차

프런트엔드 애플리케이션(public-viewer와 admin)을 개발용 더미 서버(dummy-server)를 백엔드로 하여 실행하는 절차입니다.

### 1. public-viewer, admin, dummy-server 환경 구축

```sh
make client-setup
```

### 2. 개발 서버 실행

```sh
make client-dev -j 3
```

## 면책 사항

대규모 언어 모델(LLM)에는 편향이 있으며, 신뢰도가 낮은 결과를 생성할 수 있다고 알려져 있습니다. 저희는 이러한 문제를 줄이는 방법에 적극적으로 힘쓰고 있지만, 현 단계에서는 어떠한 보증도 드릴 수 없습니다. 특히 중요한 결정을 내릴 때는 이 앱의 출력 결과에만 의존하지 말고 반드시 내용을 검증해 주세요.

## 주의 사항

이 앱은 개발 초기 단계이며, 앞으로 개발을 진행하는 과정에서 이전 버전과 호환되지 않는 변경이 이루어질 수 있습니다.
앱을 업데이트할 때 중요한 데이터(리포트)가 있다면, 앱과 데이터를 백업한 뒤 업데이트하기를 권장합니다.

## 개발자 가이드라인

広聴 AI는 OSS로 개발되고 있으며, 개발자 여러분의 기여를 기다리고 있습니다.
코드를 작성하지 않고 참여하려는 분은 [감상, 질문, 사례 공유부터 시작하는 안내](./CONTRIBUTING.md#コードを書かずに参加する)(일본어)를 확인해 주세요.

자세한 내용은 [기여 가이드](https://digitaldemocracy2030.github.io/kouchou-ai/development/contributing)를 참조하세요.
또한 이 프로젝트는 AI 엔지니어 ‘[Devin](https://cognition.ai)’과 협업하여 개발하고 있습니다.
현재 Devin과의 협업 방식은 아직 모색 중이지만, [Devin과의 협업](https://digitaldemocracy2030.github.io/kouchou-ai/development/devin-collaboration)을 참조해 주세요.

## 기능 요청 및 버그 보고

- GitHub 계정이 있는 분은 [Issue](https://github.com/digitaldemocracy2030/kouchou-ai/issues)에 버그나 개선 요청을 올려 주세요
- GitHub 계정이 없는 분은 아래 Google 폼으로 버그나 개선 요청을 보내 주세요
  - [버그 보고 및 개선 요청 폼](https://docs.google.com/forms/d/e/1FAIpQLSf43rpi8N1hGQmECDOBOmiV3c-Buwf4gWSj2sYc2KbZL9NOBA/viewform?usp=dialog)

## 크레디트

이 프로젝트는 [AI Objectives Institute](https://www.aiobjectivesinstitute.org/)가 개발한 [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)를 참고하여 개발되었으며, 라이선스에 따라 소스 코드의 일부를 활용하고 기능 추가와 개선을 하고 있습니다. 원저작자의 공헌에 감사드립니다.
