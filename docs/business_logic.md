# 핵심 비즈니스 로직 설계 문서

이 문서는 유지보수자가 전략의 의도, 데이터 경계, 편향 통제, 주문/리스크 동작을 빠르게 이해하고 안전하게 변경하기 위한 기준 문서입니다.

## 1. 비즈니스 목표와 불변 원칙

플랫폼의 핵심 목표는 KOSPI/KOSDAQ 보통주를 대상으로 공개 데이터 기반 멀티팩터 포트폴리오를 구성하고, 백테스트와 운영 신호 생성의 의사결정 경로를 최대한 동일하게 유지하는 것입니다.

반드시 지켜야 할 불변 원칙은 다음과 같습니다.

1. **시점 일관성**: 백테스트의 모든 데이터는 리밸런싱 시점에 실제로 알 수 있었던 정보만 사용합니다.
2. **전략 계약 단일화**: 전략은 `BaseStrategy.generate_signals(as_of, prices, fundamentals)`로만 종목과 목표비중을 산출합니다.
3. **데이터 소스 교체 가능성**: 무료/유료 데이터 플러그인은 Repository 스키마에 맞춰 적재하고, 팩터/전략 로직을 직접 수정하지 않습니다.
4. **실거래 보호 우선**: Emergency Stop, 손절, 시장위험 필터, 주문 추적은 수익률 로직보다 우선합니다.
5. **운영 관측성**: 주문, 체결, 리밸런싱, 오류는 Dashboard와 Loguru 로그로 추적 가능해야 합니다.

## 2. 도메인 데이터 모델

### 2.1 Symbols

`symbols`는 유니버스 편향 통제의 기준 테이블입니다.

주요 필드:

- `symbol`: 종목코드
- `market`: KOSPI/KOSDAQ 구분
- `sector`: 섹터/업종
- `listing_date`: 상장일
- `delisting_date`: 상장폐지일
- `security_type`, `is_spac`, `is_preferred`, `is_administrative`, `is_halted`: 제외 필터

유지보수 규칙:

- 현재 상장종목 목록만으로 과거 백테스트를 수행하면 안 됩니다.
- 상장폐지 종목은 삭제하지 말고 `delisting_date`를 채웁니다.
- ETF, ETN, SPAC, 우선주, 관리종목, 거래정지 종목은 시점 기준 플래그로 관리합니다.

### 2.2 Prices

`prices`는 일봉, 거래량, 거래대금, 시가총액을 저장합니다.

유지보수 규칙:

- 리밸런싱 신호는 T일 종가 이하의 가격 데이터만 사용합니다.
- 체결 시뮬레이션은 다음 거래일 시가를 사용합니다.
- 수정주가 정책이 바뀌면 백테스트 결과가 바뀔 수 있으므로 데이터 버전을 운영 로그에 남겨야 합니다.

### 2.3 Fundamentals

`fundamentals`는 공시 이후 사용 가능한 재무지표를 저장합니다.

핵심 필드는 `announcement_date`입니다. 결산일이나 회계연도만 보고 팩터에 투입하면 룩어헤드가 발생합니다.

유지보수 규칙:

- 재무 데이터 조회는 항상 `announcement_date <= as_of` 조건을 포함해야 합니다.
- 정정공시는 별도 적재 정책을 정해야 하며, 과거 리밸런싱 시점에 정정 전/후 어떤 값이 사용 가능했는지 추적해야 합니다.
- DART 계정과목 매핑을 변경할 때는 PER/PBR/PSR/EV_EBITDA, ROE/ROA/영업이익률/부채비율 회귀 테스트를 추가합니다.

## 3. 유니버스 선정 로직

리밸런싱 시점 `as_of` 기준으로 아래 조건을 모두 만족해야 합니다.

1. 시장: KOSPI 또는 KOSDAQ
2. 상장기간: `listing_date <= as_of - 183일`
3. 상장폐지: `delisting_date is null or delisting_date > as_of`
4. 보통주: `security_type == COMMON_STOCK`
5. 제외 플래그: SPAC, 우선주, 관리종목, 거래정지 제외
6. 유동성/규모: 최근 60거래일 평균 거래대금 10억 원 이상, 시가총액 500억 원 이상

현재 Repository는 날짜/상태 기반 필터를 담당하고, 유동성/시가총액 필터는 전략 실행 전 가격 데이터 기반으로 확장하는 것이 권장됩니다.

## 4. 팩터 계산 로직

### 4.1 공통 표준화

팩터 값은 횡단면 기준으로 winsorize 후 z-score 합니다.

- 상위/하위 5% clipping
- 표준편차가 0이거나 결측만 있는 경우 0점 처리
- 낮을수록 좋은 지표는 부호를 반전한 뒤 표준화

### 4.2 Value Factor

사용 지표:

- `1 / PER`
- `1 / PBR`
- `1 / PSR`
- `1 / EV_EBITDA`

각 지표를 z-score 후 평균합니다. 음수 이익, 0 또는 결측 분모는 결측 처리 후 중립값에 수렴합니다.

### 4.3 Momentum Factor

12-1 모멘텀을 사용합니다.

```text
momentum = price(as_of - 1개월) / price(as_of - 12개월) - 1
```

최근 1개월을 제외하는 이유는 단기 반전 효과와 리밸런싱 직전 과열을 줄이기 위해서입니다.

### 4.4 Quality Factor

높을수록 좋은 지표:

- ROE
- ROA
- Operating Margin

낮을수록 좋은 지표:

- Debt Ratio

각 지표를 z-score 후 평균합니다.

### 4.5 종합 점수

기본 가중치:

```text
total_score = 0.40 * momentum + 0.30 * value + 0.30 * quality
```

Dashboard Admin에서 가중치를 변경할 수 있지만, 가중치 합이 0 이하가 되면 기본값으로 복구해야 합니다.

## 5. 전략과 포트폴리오 로직

### 5.1 전략 신호

`MultiFactorStrategy`는 종합점수 상위 `top_n` 종목을 선택합니다. 기본값은 20개입니다.

반환 필드:

- `symbol`
- `target_weight`
- `score`
- `momentum`
- `value`
- `quality`

### 5.2 목표비중

기본 목표비중은 동일가중이며 종목당 최대 5%입니다.

```text
target_weight = min(0.05, 1 / top_n)
```

### 5.3 리밸런싱

기본 주기는 매월 마지막 거래일입니다. 운영 스케줄은 한국 장마감 이후 15:40 KST 실행을 기본으로 합니다.

신호/체결 규칙:

1. T일 종가와 T일까지 공시된 재무 데이터로 신호 생성
2. T+1 거래일 시가로 매수/매도 체결 시뮬레이션
3. 거래비용 반영: 수수료, 슬리피지, 매도 거래세

## 6. 리스크 관리 로직

### 6.1 종목 단위 리스크

- 손절: 평균단가 대비 -10%
- 트레일링 스탑: 고점 대비 -15%

조건 발생 시 신규 신호보다 강제 청산이 우선합니다.

### 6.2 시장 위험 회피

KOSPI200 가격 기준:

```text
if MA50 < MA200:
    신규 진입 금지 및 현금 100% 전환
```

### 6.3 Dashboard Risk 경고

Dashboard는 다음 경고를 표시해야 합니다.

- 현재 MDD -15% 돌파
- 손절 조건 발생
- 월말 리밸런싱 필요
- Emergency Stop 활성화

## 7. 백테스트와 워크포워드 로직

### 7.1 백테스트 엔진

백테스트 엔진은 운영 전략과 같은 `BaseStrategy` 구현체를 받습니다. 따라서 전략 변경은 백테스트와 운영에 동시에 반영됩니다.

계산 지표:

- CAGR
- MDD
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Information Ratio
- Turnover
- Win Rate

### 7.2 워크포워드

기본 구조:

```text
Train 3년 / Test 1년
2014~2016 → 2017
2015~2017 → 2018
2016~2018 → 2019
```

워크포워드 결과는 테스트 구간의 안정성을 보는 용도입니다. 특정 한 해 또는 특정 파라미터에서만 성과가 좋으면 과최적화 가능성이 높습니다.

### 7.3 파라미터 스윕

Momentum Weight 예시:

```text
20%, 30%, 40%, 50%, 60%
```

넓은 범위에서 성과가 유지되는지 Heatmap으로 확인합니다.

## 8. 주문과 브로커 로직

### 8.1 Broker 인터페이스

모든 브로커는 아래 계약을 구현해야 합니다.

- `buy(symbol, quantity, price, order_type)`
- `sell(symbol, quantity, price, order_type)`
- `cancel(broker_order_id)`
- `positions()`
- `balance()`

### 8.2 Order Engine

Order Engine은 포트폴리오 엔진이 만든 주문 계획을 Broker에 전달하고 DB에 저장합니다.

저장 필드:

- 주문수량
- 체결수량
- 주문가격
- 체결가격
- 주문상태
- 브로커 주문번호

### 8.3 Paper/Live 전환

Dashboard Admin의 `paper`/`live` 전환은 런타임 상태를 바꿉니다. 실운영에서는 이 상태를 실제 Broker DI 설정과 연결하고, live 전환 전 확인 모달 또는 다중 승인 절차를 추가해야 합니다.

## 9. Emergency Stop 로직

Emergency Stop이 활성화되면 다음이 적용됩니다.

1. `strategy_enabled = false`
2. `emergency_stop = true`
3. 신규 리밸런싱 주문 차단
4. 현재 포지션 전체 매도 계획 생성

실거래 환경에서는 전체 청산 계획을 즉시 시장가 주문으로 보낼지, 운영자 확인 후 보낼지 정책을 명확히 해야 합니다.

## 10. 변경 시 회귀 테스트 기준

비즈니스 로직 변경 시 최소한 다음 테스트를 추가하거나 갱신해야 합니다.

- 유니버스 시점 필터 테스트
- `announcement_date` 룩어헤드 방지 테스트
- 팩터 점수 정렬/결측 처리 테스트
- T+1 시가 체결 테스트
- 거래비용 반영 테스트
- 손절/트레일링/시장위험 필터 테스트
- Dashboard 필수 라우트 등록 테스트
- Rebalance 시뮬레이션 주문 수량 테스트

## 11. 확장 가이드

### 새 전략 추가

1. `trading_system/app/strategies/`에 `BaseStrategy`를 상속하는 클래스를 추가합니다.
2. `generate_signals()`가 표준 컬럼을 반환하도록 구현합니다.
3. 백테스트와 Dashboard에서 전략 인스턴스 주입 위치를 확장합니다.
4. 기존 전략 코드를 수정하지 말고 플러그인 방식으로 추가합니다.

### 새 데이터 공급자 추가

1. `data_collector`에 어댑터를 추가합니다.
2. 원천 데이터를 표준 `symbols`, `prices`, `fundamentals` 스키마로 변환합니다.
3. Repository 메서드는 그대로 사용합니다.
4. 데이터 품질 리포트와 결측 검사를 추가합니다.

### 새 브로커 추가

1. `Broker` 인터페이스를 구현합니다.
2. 주문/취소/잔고/포지션 조회를 모의투자에서 먼저 검증합니다.
3. 주문 상태 매핑을 `OrderStatus`와 일치시킵니다.
4. 체결 이벤트를 `trade.log`와 Dashboard Orders에 노출합니다.
