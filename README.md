# Korean KOSPI/KOSDAQ Multifactor Quant Trading Platform

대한민국 개인투자자가 접근 가능한 공개 데이터와 국내 증권사 API를 사용해 KOSPI/KOSDAQ 멀티팩터 전략을 연구, 검증, 모의운영, 실거래 전환까지 수행하기 위한 자동매매 플랫폼입니다.

> 이 프로젝트는 투자 자문이나 수익 보장을 제공하지 않습니다. 실계좌 투입 전에는 데이터 정합성, 주문 API, 리스크 제한, 세금/수수료, 장애 대응을 반드시 독립적으로 검증하세요.

## 핵심 기능

- **멀티팩터 전략**: Value, 12-1 Momentum, Quality를 40/30/30 기본 가중치로 결합합니다.
- **편향 통제**: `listing_date`, `delisting_date`, `announcement_date`를 사용해 생존자 편향과 룩어헤드 바이어스를 줄입니다.
- **백테스트/실거래 전략 일치**: `BaseStrategy.generate_signals()` 계약을 백테스트와 운영 신호 생성에서 공통 사용합니다.
- **워크포워드 검증**: 3년 학습/1년 테스트 구간과 파라미터 민감도 분석을 지원합니다.
- **운영 Dashboard**: React 기반 화면에서 계좌/포트폴리오/주문/거래/팩터/백테스트/워크포워드/리스크/로그/관리 기능을 제공합니다.
- **브로커 추상화**: Mock Broker와 한국투자 Open API 어댑터를 포함하며 키움 등 추가 브로커를 동일 인터페이스로 확장할 수 있습니다.
- **Docker 개발 환경**: FastAPI, TimescaleDB/PostgreSQL, Vite Dashboard를 Docker Compose로 실행합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy, Pandas, NumPy, APScheduler, Loguru |
| Database | PostgreSQL, TimescaleDB 이미지 |
| Backtest | 자체 백테스트 엔진, vectorbt 의존성 포함 |
| Broker | 한국투자 Open API, Mock Broker |
| Frontend | React, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS, Recharts |
| DevOps/Test | Docker, Docker Compose, Pytest |

## 저장소 구조

```text
.
├─ trading_system/
│  └─ app/
│     ├─ api/              FastAPI 및 Dashboard API
│     ├─ backtest/         백테스트, 성과지표, 워크포워드
│     ├─ brokers/          Broker 인터페이스, 한국투자, Mock
│     ├─ data_collector/   DART/KRX/pykrx/FDR 어댑터
│     ├─ database/         SQLAlchemy 모델, 세션, Repository
│     ├─ factors/          Value/Momentum/Quality 팩터 엔진
│     ├─ notifications/    Telegram 알림
│     ├─ orders/           주문 엔진
│     ├─ portfolio/        목표비중 → 주문 변환
│     ├─ risk/             손절/트레일링/시장위험 필터
│     ├─ scheduler/        장마감 후 작업 스케줄러
│     └─ strategies/       전략 플러그인
├─ dashboard/              React + TypeScript 운영 Dashboard
├─ docs/
│  ├─ architecture.md      전체 아키텍처 및 운영 설계
│  ├─ business_logic.md   유지보수용 핵심 비즈니스 로직 문서
│  └─ build_guide.md      전체 프로젝트 구조와 빌드/실행 가이드
├─ tests/                  단위/통합 테스트
├─ config/                 환경변수 예시
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ pyproject.toml
```

## 빠른 시작

### 1. 환경 변수 준비

```bash
cp config/settings.example.env .env
```

주요 값:

- `DATABASE_URL`: PostgreSQL/TimescaleDB 연결 문자열
- `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO`, `KIS_BASE_URL`: 한국투자 Open API 설정
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 운영 알림 설정

### 2. Docker Compose 실행

```bash
docker compose up --build
```

서비스:

- FastAPI: <http://localhost:8000>
- Dashboard: <http://localhost:5173>
- PostgreSQL/TimescaleDB: `localhost:5432`

### 3. 로컬 Backend 개발

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn trading_system.app.api.main:app --reload
```

### 4. 로컬 Dashboard 개발

```bash
cd dashboard
npm install
npm run dev
```

## 주요 API

### 기본 API

- `GET /health`
- `GET /portfolio`
- `GET /positions`
- `GET /orders`
- `GET /trades`
- `GET /factors`
- `GET /backtest?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `POST /strategy/run`
- `POST /rebalance`

### Dashboard API

- `GET /dashboard/overview`
- `GET /dashboard/portfolio`
- `GET /dashboard/orders?period=today|7d|30d`
- `GET /dashboard/trades`
- `GET /dashboard/factors`
- `GET /dashboard/risk`
- `GET /dashboard/backtest?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /dashboard/walkforward?start_year=2014&end_year=2024`
- `GET /dashboard/rebalance`
- `POST /dashboard/rebalance?execute=true`
- `POST /dashboard/strategy/{stop|resume|emergency_stop|paper|live}`
- `POST /dashboard/emergency-stop`
- `GET /dashboard/logs?log_name=system.log&query=...`
- `POST /dashboard/admin/settings`

## 테스트와 검증

```bash
python -m compileall trading_system tests
pytest -q
```

Dashboard 빌드 검증:

```bash
cd dashboard
npm install
npm run build
```

## 운영 전 체크리스트

- 상장/상장폐지/관리/거래정지 이력이 백테스트 시점 기준으로 복원되는지 확인합니다.
- 재무 데이터가 `announcement_date` 이후에만 사용되는지 확인합니다.
- 백테스트 체결이 T일 종가 신호, T+1 시가 체결, 수수료/슬리피지/거래세를 반영하는지 확인합니다.
- 모의투자에서 주문, 취소, 체결조회, 잔고조회, 알림이 정상 동작하는지 확인합니다.
- Emergency Stop과 전체 청산 계획이 Dashboard에서 즉시 확인되는지 검증합니다.
- 무료 데이터의 결측/정정/상장폐지 누락 가능성을 운영 리스크로 관리합니다.

## 추가 문서

- [전체 아키텍처 설계서](docs/architecture.md)
- [핵심 비즈니스 로직 설계 문서](docs/business_logic.md)
- [프로젝트 구조 및 빌드 가이드](docs/build_guide.md)
