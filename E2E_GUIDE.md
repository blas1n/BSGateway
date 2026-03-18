# E2E Testing Guide

## Prerequisites

E2E 테스트를 실행하기 위해서는 다음이 필요합니다:

1. **PostgreSQL 데이터베이스** (포트 5432)
2. **Redis** (포트 6379)
3. **Node.js & npm**
4. **Python 3.11+ with uv**

## Option 1: Docker Compose (권장)

DevContainer 또는 Docker가 설치된 환경에서:

```bash
# 데이터베이스와 Redis 시작
docker compose up postgres redis -d

# 마이그레이션 (한 번만)
uv run python -m bsgateway.core.migrate

# 백엔드 시작
uv run uvicorn bsgateway.api.app:create_app --factory --host 0.0.0.0 --port 8000

# 다른 터미널: 프론트엔드 시작
cd frontend && npm run dev

# 또 다른 터미널: E2E 테스트 실행
cd frontend && npm run test:e2e
```

## Option 2: 자동 스크립트 (Docker Compose 필수)

```bash
# Docker Compose로 DB/Redis 시작
docker compose up postgres redis -d

# 마이그레이션
uv run python -m bsgateway.core.migrate

# 자동 스크립트로 E2E 테스트 실행
./run-e2e-tests.sh
```

## Option 3: UI 모드로 테스트 (디버깅용)

```bash
# 모든 서비스가 실행 중일 때
cd frontend
npm run test:e2e:ui
```

이 모드는 Playwright Inspector를 열어서 각 테스트를 시각적으로 디버깅할 수 있습니다.

## Option 4: 헤드풀 모드 (브라우저 보기)

```bash
cd frontend
npm run test:e2e:headed
```

실제 브라우저 창을 열어서 테스트가 진행되는 모습을 볼 수 있습니다.

## 테스트 케이스

### 1. **auth.spec.ts** - 인증 테스트
- ✓ API key로 로그인
- ✓ 잘못된 API key 에러 처리
- ✓ 로그아웃

### 2. **rules.spec.ts** - 규칙 관리
- ✓ Rules 페이지 네비게이션
- ✓ 새 규칙 생성
- ✓ 규칙 삭제 (확인 단계)

### 3. **models.spec.ts** - 모델 관리
- ✓ Models 페이지 네비게이션
- ✓ 새 모델 등록
- ✓ Provider 자동 파싱 확인
- ✓ 모델 삭제

## 테스트 API Key

기본 시드 데이터:
```
API Key: bsg_dev-test-key-do-not-use-in-production-000
Tenant Slug: dev-team
Tenant Name: Dev Team
```

## 환경 변수

`.env` 파일에서 필요한 설정:

```env
COLLECTOR_DATABASE_URL=postgresql://bsgateway:change-me-secure-password@localhost:5432/bsgateway
JWT_SECRET=dev-jwt-secret-change-in-production
ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
SUPERADMIN_KEY=superadmin-dev-key
SEED_DEV_DATA=true
```

## 데이터베이스 마이그레이션

첫 실행 시 스키마 생성:

```bash
uv run python -m bsgateway.core.migrate
```

## 테스트 결과

- HTML 리포트: `frontend/playwright-report/index.html`
- 스크린샷: `test-results/` 폴더 (실패 시만)
- 비디오 녹화: `test-results/` 폴더 (설정하면)

## 문제 해결

### 데이터베이스 연결 실패

```bash
# Docker Compose 상태 확인
docker compose ps

# PostgreSQL 로그 확인
docker compose logs postgres

# 데이터베이스 수동 재생성
docker compose down
docker compose up postgres -d
sleep 5
uv run python -m bsgateway.core.migrate
```

### 포트 충돌

- API: `8000` (uvicorn)
- Frontend: `5173` (Vite)
- PostgreSQL: `5432`
- Redis: `6379`

포트를 변경하려면 환경 변수를 설정하세요.

### Playwright 설치 실패

```bash
# System dependencies 설치 (Linux)
npx playwright install-deps

# 모든 브라우저 다시 설치
npx playwright install
```

## CI/CD 통합

GitHub Actions 또는 다른 CI 시스템에서:

```yaml
- name: Install dependencies
  run: npm ci

- name: Run E2E tests
  run: npm run test:e2e
  env:
    COLLECTOR_DATABASE_URL: postgresql://user:pass@db:5432/test
```

## 지원하는 브라우저

- Chromium
- Firefox
- WebKit (Safari)

기본적으로 모든 브라우저에서 테스트가 병렬로 실행됩니다.
