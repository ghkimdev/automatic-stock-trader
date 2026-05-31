# 프로젝트 구조 및 빌드 가이드

이 문서는 저장소 전체 구조, 개발 환경 준비, Backend/Frontend 실행, Docker Compose 운영, 테스트 및 배포 전 검증 절차를 정리합니다.

## 1. 전체 프로젝트 구조

```text
automatic-stock-trader/
├─ README.md
├─ Dockerfile
├─ docker-compose.yml
├─ pyproject.toml
├─ requirements.txt
├─ config/
│  └─ settings.example.env
├─ docs/
│  ├─ architecture.md
│  ├─ business_logic.md
│  └─ build_guide.md
├─ trading_system/
│  └─ app/
│     ├─ api/
│     │  ├─ main.py
│     │  └─ dashboard.py
│     ├─ backtest/
│     │  ├─ engine.py
│     │  ├─ metrics.py
│     │  └─ walk_forward.py
│     ├─ brokers/
│     │  ├─ base.py
│     │  ├─ kis.py
│     │  └─ mock.py
│     ├─ data_collector/
│     │  └─ collectors.py
│     ├─ database/
│     │  ├─ models.py
│     │  ├─ repositories.py
│     │  └─ session.py
│     ├─ factors/
│     │  └─ engine.py
│     ├─ notifications/
│     │  └─ telegram.py
│     ├─ orders/
│     │  └─ engine.py
│     ├─ portfolio/
│     │  └─ engine.py
│     ├─ risk/
│     │  └─ engine.py
│     ├─ scheduler/
│     │  └─ jobs.py
│     ├─ strategies/
│     │  ├─ base.py
│     │  └─ multifactor.py
│     └─ utils/
│        ├─ config.py
│        └─ logging.py
├─ dashboard/
│  ├─ package.json
│  ├─ index.html
│  ├─ vite.config.ts
│  ├─ tailwind.config.js
│  ├─ postcss.config.js
│  ├─ tsconfig.json
│  └─ src/
│     ├─ App.tsx
│     ├─ main.tsx
│     ├─ index.css
│     ├─ api/client.ts
│     ├─ components/
│     │  ├─ DataTable.tsx
│     │  └─ Layout.tsx
│     ├─ pages/
│     │  ├─ Overview.tsx
│     │  ├─ Portfolio.tsx
│     │  └─ Tables.tsx
│     └─ store/ui.ts
└─ tests/
   └─ test_platform.py
```

## 2. 사전 요구사항

권장 버전:

- Python 3.12+
- Docker Engine 및 Docker Compose v2
- Node.js 20+ 또는 22+
- npm 10+
- PostgreSQL 클라이언트 도구는 선택 사항

## 3. 환경 변수 구성

```bash
cp config/settings.example.env .env
```

주요 환경 변수:

| 변수 | 설명 |
| --- | --- |
| `APP_ENV` | local, staging, production 등 실행 환경 |
| `DATABASE_URL` | SQLAlchemy DB URL |
| `KIS_APP_KEY` | 한국투자 Open API App Key |
| `KIS_APP_SECRET` | 한국투자 Open API Secret |
| `KIS_ACCOUNT_NO` | 계좌번호. 예: `12345678-01` |
| `KIS_BASE_URL` | 한국투자 Open API URL |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

## 4. Docker Compose 빌드 및 실행

```bash
docker compose up --build
```

기본 포트:

| 서비스 | 포트 | 설명 |
| --- | --- | --- |
| `api` | 8000 | FastAPI Backend |
| `dashboard` | 5173 | Vite Dashboard |
| `postgres` | 5432 | TimescaleDB/PostgreSQL |

중지:

```bash
docker compose down
```

데이터 볼륨까지 삭제:

```bash
docker compose down -v
```

## 5. Backend 로컬 개발

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn trading_system.app.api.main:app --reload --host 0.0.0.0 --port 8000
```

정상 확인:

```bash
curl http://localhost:8000/health
```

API 문서:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

## 6. Dashboard 로컬 개발

```bash
cd dashboard
npm install
npm run dev
```

브라우저에서 <http://localhost:5173> 접속합니다.

환경 변수로 API URL을 지정할 수 있습니다.

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

프로덕션 빌드:

```bash
npm run build
npm run preview
```

## 7. 테스트 및 정적 검증

Python 컴파일 검증:

```bash
python -m compileall trading_system tests
```

Pytest:

```bash
pytest -q
```

Frontend 빌드 검증:

```bash
cd dashboard
npm install
npm run build
```

Git whitespace 검증:

```bash
git diff --check
```

## 8. 초기 데이터 적재 순서

1. `symbols` 적재: FinanceDataReader/KRX 기반 종목 마스터와 상장폐지 이력 적재
2. `prices` 적재: pykrx/FDR 기반 일봉, 거래량, 거래대금, 시가총액 적재
3. `fundamentals` 적재: DART 공시 재무제표를 표준 지표로 변환해 `announcement_date`와 함께 적재
4. 데이터 품질 점검: 결측, 중복, 음수/0 분모, 거래정지 기간, 상장폐지 전후 가격 확인
5. `/dashboard/factors`로 팩터 산출 확인
6. `/dashboard/backtest`와 `/dashboard/walkforward`로 연구 결과 확인

## 9. 운영 배포 체크리스트

- `.env`가 production 값으로 설정되었는가?
- `DATABASE_URL`이 운영 DB를 가리키는가?
- DB 백업과 복구 절차가 준비되었는가?
- 한국투자 API 키가 모의/실전 계정에 맞게 분리되었는가?
- Dashboard Admin의 live 전환 권한이 제한되었는가?
- `system.log`, `trade.log`, `error.log` 보존 정책이 설정되었는가?
- Telegram 오류 알림이 실제 수신되는가?
- Emergency Stop 전체 청산 계획이 모의투자에서 검증되었는가?

## 10. 문제 해결

### Python 패키지 설치 실패

사내망/프록시/패키지 인덱스 제한이 있는 경우 `pip`가 403 또는 timeout을 반환할 수 있습니다. 내부 PyPI mirror를 설정하거나 네트워크 정책을 확인하세요.

### npm 패키지 설치 실패

`npm install`이 403을 반환하면 npm registry 접근 정책 또는 프록시 설정을 확인하세요.

### Dashboard가 API에 연결되지 않음

- FastAPI가 `localhost:8000`에서 실행 중인지 확인합니다.
- `VITE_API_BASE_URL` 값을 확인합니다.
- CORS 허용 origin에 Dashboard 주소가 포함되어 있는지 확인합니다.

### 백테스트 결과가 비어 있음

- 해당 기간의 `prices` 데이터가 적재되어 있는지 확인합니다.
- `fundamentals.announcement_date`가 백테스트 기간 이전/중간에 존재하는지 확인합니다.
- 유니버스 필터가 모든 종목을 제외하고 있지 않은지 확인합니다.
