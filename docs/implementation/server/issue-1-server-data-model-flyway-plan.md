# 서버 데이터 모델과 Flyway 마이그레이션 구현 계획

상태: 계획 보완

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 1번 이슈

## 1. 목적

Stock Reports Lab MVP의 금융 원천 데이터, 분석 결과, 리포트 리비전, 업종 분석, AI 요약, Python 배치 실행 상태를 저장할 PostgreSQL 스키마를 Spring Flyway 마이그레이션으로 정의한다.

이번 작업은 데이터베이스 구조를 만드는 데 한정한다. Spring 조회 API, JPA Entity, Repository, Python worker 로직, 프론트엔드 변경은 포함하지 않는다.

## 2. 기준 문서

- `docs/proposal/stock-report-mvp-product-architecture-baseline.md`
- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/proposal/python_batch_retry_consistency_design.md`
- `docs/adr/0002-share-database-with-single-schema-owner.md`
- `docs/adr/0003-version-published-report-results.md`
- `docs/adr/0004-isolate-batch-failures-per-stock.md`
- `docs/adr/0005-python-batch-retry-consistency.md`
- `CONTEXT.md`

기준 문서와 충돌하는 `build/` 산출물의 기존 SQL 초안은 정본으로 사용하지 않는다. 특히 RSI, Stoch RSI, MA10, MA200은 MVP 스키마에 포함하지 않는다.

## 3. 범위

### 포함

- `server/src/main/resources/db/migration/V1__initial_schema.sql` 작성
- 핵심 업무 테이블 9개 생성
  - `stock`
  - `daily_price`
  - `daily_indicator`
  - `market_index_price`
  - `report_revision`
  - `stock_analysis`
  - `signal_event`
  - `industry_analysis`
  - `market_ai_summary`
- Python 배치 처리 상태 테이블 3개 생성
  - `batch_job_run`
  - `batch_stock_run`
  - `daily_stock_processing_status`
- 총 12개 테이블 생성. `daily_stock_processing_status`는 기준 문서의 재시도 정합성을 만족하기 위한 필수 처리 상태 테이블로 포함한다.
- foreign key, unique key, check constraint, index 정의
- 거래일별 활성 리비전 1건 보장 partial unique index 정의
- worker upsert 기준이 되는 unique key 정의
- worker upsert와 상태 전이에 필요한 `not null` 컬럼 정의

### 제외

- JPA Entity, Repository, Service, Controller 작성
- 조회 API 구현
- Python worker DB 접근, 수집, 계산, upsert 로직 구현
- AI 요약 생성 로직 구현
- 배치 실행 이력 테이블, AI 요약 이력 테이블, AI 시도 이력 테이블
- 프론트엔드 변경
- 운영 계정 권한 분리
- 기존 `build/` 산출물 복사

## 4. 설계 원칙

- 스키마 변경은 Spring Flyway만 수행한다.
- Python worker는 Flyway가 생성한 승인된 테이블만 사용한다.
- DB 수준 PostgreSQL enum은 사용하지 않는다.
- 상태값과 코드값은 `varchar`와 `check constraint`로 제한한다.
- 업무 테이블의 종목 참조는 `stock_id` foreign key 중심으로 둔다.
- worker는 `stock.stock_code` unique key로 종목을 upsert한 뒤 `stock_id`를 참조한다.
- 계산 버전은 별도 테이블로 정규화하지 않고 문자열 컬럼 `calculation_version`으로 저장한다.
- 계산 버전이 다른 지표와 신호는 기존 값을 덮어쓰지 않고 별도 행으로 저장한다.
- 과거 리포트 재현을 위해 리비전별 스냅샷 필드는 `stock_analysis`에 저장한다.
- 가격 일봉은 리비전마다 복제하지 않는다.
- AI 요약은 거래일별 1건만 유지하며, 금융 데이터 리비전과 별도 수명주기지만 요약 입력으로 사용한 `report_revision`을 참조한다.
- 배치 실행 상태와 종목 처리 업무 상태는 분리한다. `batch_stock_run`은 실행 회차 안의 재시도 상태를 저장하고, `daily_stock_processing_status`는 거래일별 종목 업무 상태의 최신 복구 기준을 저장한다.

## 5. 공통 컬럼과 타입 기준

- 식별자: `bigserial primary key`
- 거래일: `date`
- 생성/수정 시각: `timestamptz`
- 가격: `numeric(18,4)`
- 거래량: `bigint`
- 거래대금, 시가총액: `numeric(24,2)`
- 기술지표, 등락률, 비율: `numeric(18,8)`
- 건수, 순위: `integer`
- 상태값, 코드값: `varchar`
- unique key, foreign key, check constraint 판정에 필요한 업무 식별자와 상태값은 `not null`로 정의한다.

`not null` 필수 컬럼:

- 모든 테이블의 `id`
- 모든 foreign key 컬럼. 단, 명시적으로 nullable이라고 적은 컬럼은 제외한다.
- 모든 unique key 구성 컬럼
- 모든 check constraint 대상 상태값과 코드값
- `created_at`
- `updated_at`. 단, 생성 후 수정 개념이 없는 이벤트 테이블은 제외한다.

## 6. 테이블 설계

### 6.1 `stock`

현재 종목 메타데이터를 저장한다.

주요 컬럼:

- `id`
- `stock_code`
- `stock_name`
- `market`
- `industry_name`
- `created_at`
- `updated_at`

제약:

- `stock_code` unique
- `stock_code` not null
- `stock_name` not null
- `market` not null
- `market in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN')`

### 6.2 `daily_price`

종목별 수정주가 OHLCV와 일간 등락률, 거래대금을 저장한다.

주요 컬럼:

- `id`
- `stock_id`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `change_rate`
- `trade_value`
- `created_at`
- `updated_at`

제약:

- foreign key: `stock_id` -> `stock(id)`
- `stock_id` not null
- `trade_date` not null
- unique: `(stock_id, trade_date)`

### 6.3 `daily_indicator`

계산 버전별 기술지표를 저장한다.

주요 컬럼:

- `id`
- `stock_id`
- `trade_date`
- `calculation_version`
- `macd_line`
- `macd_signal`
- `macd_histogram`
- `stoch_macd_k`
- `stoch_macd_d`
- `ma5`
- `ma20`
- `ma60`
- `ma120`
- `ma240`
- `created_at`
- `updated_at`

제약:

- foreign key: `stock_id` -> `stock(id)`
- `stock_id` not null
- `trade_date` not null
- `calculation_version` not null
- unique: `(stock_id, trade_date, calculation_version)`

제외 컬럼:

- RSI
- Stoch RSI
- MA10
- MA200

### 6.4 `market_index_price`

KOSPI와 KOSDAQ 지수 일봉을 저장한다.

주요 컬럼:

- `id`
- `index_code`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `change_rate`
- `created_at`
- `updated_at`

제약:

- `index_code in ('KOSPI', 'KOSDAQ')`
- `index_code` not null
- `trade_date` not null
- unique: `(index_code, trade_date)`

### 6.5 `report_revision`

거래일별 리포트 리비전과 활성 상태, 참조 계산 버전, 커버리지 집계를 저장한다.

주요 컬럼:

- `id`
- `report_date`
- `revision_no`
- `revision_type`
- `is_active`
- `calculation_version`
- `target_stock_count`
- `completed_stock_count`
- `failed_stock_count`
- `insufficient_stock_count`
- `no_trading_stock_count`
- `created_at`
- `published_at`

제약:

- `report_date` not null
- `revision_no` not null
- `revision_type` not null
- `is_active` not null
- `calculation_version` not null
- `revision_type in ('INITIAL', 'FINAL', 'CORRECTION')`
- `revision_no >= 1`
- unique: `(report_date, revision_no)`
- partial unique index: `report_date` where `is_active = true`

공개 상태 해석:

- 공개 완료: 활성 `report_revision` 존재
- 생성 지연: `batch_job_run.status = 'DELAYED'`
- 휴장일: `batch_job_run.status = 'SKIPPED_MARKET_CLOSED'`
- 공개 전: 활성 리비전도 없고 완료/실패성 배치 상태도 없음

리비전 타입 해석:

- `INITIAL`: 첫 수집 회차 종료 후 공개하는 최초 리비전
- `FINAL`: 실패 종목 재시도 종료 후 변경분을 모아 공개하는 최종 리비전
- `CORRECTION`: 데이터 정정용 명시 재실행으로 공개하는 사후 정정 리비전

### 6.6 `signal_event`

종목별 골든크로스 발생 사건을 저장한다.

주요 컬럼:

- `id`
- `stock_id`
- `signal_type`
- `cross_date`
- `calculation_version`
- `stoch_macd_k`
- `stoch_macd_d`
- `created_at`

제약:

- foreign key: `stock_id` -> `stock(id)`
- `stock_id` not null
- `signal_type` not null
- `cross_date` not null
- `calculation_version` not null
- `signal_type in ('STOCH_MACD_GOLDEN_CROSS')`
- unique: `(stock_id, signal_type, cross_date, calculation_version)`

### 6.7 `stock_analysis`

리비전별 분석 대상, 분석 상태, 종목 메타데이터 스냅샷, 선정 기준 스냅샷, 리비전에서 노출할 신호 참조를 저장한다.

주요 컬럼:

- `id`
- `report_revision_id`
- `stock_id`
- `signal_event_id`
- `analysis_status`
- `stock_name_snapshot`
- `market_snapshot`
- `industry_name_snapshot`
- `selection_rank`
- `selection_volume`
- `market_cap`
- `trade_value`
- `current_price`
- `last_trade_date`
- `created_at`
- `updated_at`

제약:

- foreign key: `report_revision_id` -> `report_revision(id)`
- foreign key: `stock_id` -> `stock(id)`
- nullable foreign key: `signal_event_id` -> `signal_event(id)`
- `report_revision_id` not null
- `stock_id` not null
- `analysis_status` not null
- `stock_name_snapshot` not null
- `market_snapshot` not null
- `selection_rank` not null
- `selection_volume` not null
- unique: `(report_revision_id, stock_id)`
- `selection_rank >= 1`
- `analysis_status in ('SIGNAL_FOUND', 'NO_SIGNAL', 'INSUFFICIENT_DATA', 'DATA_PREPARING', 'DATA_UPDATE_FAILED', 'NO_TRADING_TODAY', 'ANALYSIS_FAILED')`
- `market_snapshot in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN')`

### 6.8 `industry_analysis`

리비전별 업종 통계를 저장한다.

주요 컬럼:

- `id`
- `report_revision_id`
- `industry_name`
- `area_basis`
- `stock_count`
- `market_cap_sum`
- `trade_value_sum`
- `average_change_rate`
- `signal_count`
- `signal_denominator_count`
- `excluded_count`
- `signal_ratio`
- `created_at`
- `updated_at`

제약:

- foreign key: `report_revision_id` -> `report_revision(id)`
- `report_revision_id` not null
- `industry_name` not null
- `area_basis` not null
- `stock_count` not null
- `signal_count` not null
- `signal_denominator_count` not null
- `excluded_count` not null
- unique: `(report_revision_id, industry_name)`
- `area_basis in ('market_cap', 'trade_value', 'stock_count')`
- count 컬럼은 0 이상
- `signal_ratio`는 0 이상 1 이하

### 6.9 `market_ai_summary`

거래일별 시장 전체 AI 요약 상태와 결과를 저장한다. AI 요약은 금융 데이터 리비전과 별도 수명주기지만, 어떤 금융 데이터 기준으로 생성됐는지 추적하기 위해 요약 입력으로 사용한 `report_revision`을 참조한다. 정정 리비전이 활성화되면 같은 `report_date` row의 `report_revision_id`, `input_hash`, `status`, `summary_text`를 최신 활성 리비전 기준으로 갱신한다.

주요 컬럼:

- `id`
- `report_date`
- `report_revision_id`
- `status`
- `summary_text`
- `input_hash`
- `error_message`
- `created_at`
- `updated_at`

제약:

- foreign key: `report_revision_id` -> `report_revision(id)`
- `report_date` not null
- `report_revision_id` not null
- `status` not null
- `input_hash` not null
- unique: `(report_date)`
- `status in ('PENDING', 'RUNNING', 'COMPLETED', 'DELAYED')`

상태 전이:

- 요약 생성 전 또는 재생성 대기: `PENDING`
- AI 요약 생성 또는 재시도 중: `RUNNING`
- AI 요약 생성 완료: `COMPLETED`
- 허용된 재시도 안에 AI 요약을 생성하지 못함: `DELAYED`

### 6.10 `batch_job_run`

거래일별 Python 배치 실행 상태를 저장한다. 같은 거래일의 동시 중복 실행은 advisory lock으로 차단하고, DB에서는 거래일별 실행 상태 해석이 모호하지 않도록 1행만 유지한다. 같은 거래일의 순차 재실행은 기본적으로 허용하지 않고, 데이터 정정을 위한 명시적 실행 옵션이 있을 때만 기존 row를 갱신한다.

주요 컬럼:

- `id`
- `report_date`
- `status`
- `started_at`
- `finished_at`
- `last_error`
- `created_at`
- `updated_at`

제약:

- `report_date` not null
- `status` not null
- unique: `(report_date)`
- `status in ('RUNNING', 'PUBLISHED_INITIAL', 'RETRYING', 'PUBLISHED_FINAL', 'FAILED', 'DELAYED', 'SKIPPED_MARKET_CLOSED')`

인덱스:

- `report_date`
- `(report_date, status)`

### 6.11 `batch_stock_run`

배치 실행 안에서 종목별 처리와 재시도 상태를 저장한다.

`batch_stock_run.status`는 배치 실행 제어 상태이며 사용자에게 노출할 업무 상태가 아니다. 사용자와 리포트 관점의 종목 업무 상태는 `daily_stock_processing_status.analysis_status`와 `stock_analysis.analysis_status`에 저장한다.

주요 컬럼:

- `id`
- `batch_job_run_id`
- `stock_id`
- `report_date`
- `status`
- `attempt_count`
- `next_retry_at`
- `last_error`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

제약:

- foreign key: `batch_job_run_id` -> `batch_job_run(id)`
- foreign key: `stock_id` -> `stock(id)`
- `batch_job_run_id` not null
- `stock_id` not null
- `report_date` not null
- `status` not null
- `attempt_count` not null
- unique: `(batch_job_run_id, stock_id)`
- `attempt_count >= 0`
- `status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'RETRYABLE', 'FAILED_PERMANENT')`

인덱스:

- `(report_date, status)`
- `(batch_job_run_id, status)`
- `next_retry_at`

### 6.12 `daily_stock_processing_status`

거래일별 분석 종목의 최신 업무 처리 상태를 저장한다. 이 테이블은 프로세스 중단 후 재실행할 때 종목별 업무 상태를 복구하는 기준이며, 공개 리비전의 스냅샷인 `stock_analysis`와 분리한다.

주요 컬럼:

- `id`
- `report_date`
- `stock_id`
- `analysis_status`
- `last_batch_job_run_id`
- `last_error`
- `created_at`
- `updated_at`

제약:

- foreign key: `stock_id` -> `stock(id)`
- nullable foreign key: `last_batch_job_run_id` -> `batch_job_run(id)`
- `report_date` not null
- `stock_id` not null
- `analysis_status` not null
- unique: `(report_date, stock_id)`
- `analysis_status in ('SIGNAL_FOUND', 'NO_SIGNAL', 'INSUFFICIENT_DATA', 'DATA_PREPARING', 'DATA_UPDATE_FAILED', 'NO_TRADING_TODAY', 'ANALYSIS_FAILED')`

인덱스:

- `(report_date, analysis_status)`

상태 초기화와 갱신:

- 분석 대상 200개 선정 직후 `(report_date, stock_id)`를 `DATA_PREPARING`으로 upsert한다.
- 종목 처리 성공 시 `SIGNAL_FOUND`, `NO_SIGNAL`, `INSUFFICIENT_DATA`, `NO_TRADING_TODAY` 중 하나로 갱신한다.
- 종목 처리 실패 시 실패 원인에 따라 `DATA_UPDATE_FAILED` 또는 `ANALYSIS_FAILED`로 갱신한다.
- `stock_analysis`는 리비전 공개 시점의 `daily_stock_processing_status`를 스냅샷으로 복사한다.

`batch_stock_run.status`와의 관계:

- `PENDING`, `RUNNING`, `SUCCEEDED`, `RETRYABLE`, `FAILED_PERMANENT`는 실행 회차 안의 제어 상태다.
- `DATA_PREPARING`, `DATA_UPDATE_FAILED`, `NO_TRADING_TODAY` 등은 리포트 업무 상태다.
- 두 상태 축은 서로 대체하지 않는다.

## 7. 주요 인덱스

조회와 worker upsert 기준을 위해 다음 인덱스를 둔다.

- `stock(stock_code)` unique
- `daily_price(stock_id, trade_date)` unique
- `daily_indicator(stock_id, trade_date, calculation_version)` unique
- `market_index_price(index_code, trade_date)` unique
- `report_revision(report_date, revision_no)` unique
- `report_revision(report_date) where is_active = true` unique
- `stock_analysis(report_revision_id, stock_id)` unique
- `stock_analysis(report_revision_id, analysis_status)`
- `stock_analysis(report_revision_id, selection_rank)`
- `signal_event(stock_id, signal_type, cross_date, calculation_version)` unique
- `signal_event(cross_date, calculation_version)`
- `industry_analysis(report_revision_id, industry_name)` unique
- `market_ai_summary(report_date)` unique
- `batch_job_run(report_date)` unique
- `batch_stock_run(batch_job_run_id, stock_id)` unique
- `daily_stock_processing_status(report_date, stock_id)` unique

## 8. 구현 절차

1. `server/src/main/resources/db/migration/V1__initial_schema.sql` 파일을 생성한다.
2. 테이블 생성 순서를 foreign key 의존성에 맞춘다.
   - `stock`
   - `report_revision`
   - `batch_job_run`
   - `daily_price`
   - `daily_indicator`
   - `market_index_price`
   - `signal_event`
   - `stock_analysis`
   - `industry_analysis`
   - `market_ai_summary`
   - `batch_stock_run`
   - `daily_stock_processing_status`
3. 각 테이블의 primary key, foreign key, unique key, check constraint를 정의한다.
4. partial unique index를 사용해 거래일별 활성 리비전을 1건으로 제한한다.
5. worker upsert 대상 unique key와 필수 `not null` 컬럼을 빠뜨리지 않았는지 확인한다.
6. 마이그레이션 검증 테스트를 추가해 PostgreSQL 문법 기준으로 Flyway 마이그레이션이 적용되는지 확인한다.

## 9. 검증 계획

이번 계획의 구현 완료 후 다음을 검증한다.

- Spring 테스트 프로필에서 Flyway가 `V1__initial_schema.sql`을 적용한다.
- 핵심 테이블 12개가 생성된다.
- `daily_price(stock_id, trade_date)` 중복이 거부된다.
- `daily_indicator(stock_id, trade_date, calculation_version)` 중복이 거부된다.
- `signal_event(stock_id, signal_type, cross_date, calculation_version)` 중복이 거부된다.
- `report_revision`은 같은 `report_date`에 active row를 2개 가질 수 없다.
- `stock_analysis`는 리비전별 같은 종목을 중복 저장할 수 없다.
- `market_ai_summary`는 거래일별 1건만 저장할 수 있다.
- `batch_job_run`은 거래일별 1건만 저장할 수 있다.
- `daily_stock_processing_status`는 거래일별 같은 종목을 중복 저장할 수 없다.
- check constraint가 허용하지 않는 상태값과 코드값을 거부한다.
- unique key 구성 컬럼과 상태값 컬럼에 null을 저장할 수 없다.

## 10. 위험 요소

- 첫 마이그레이션이 후속 worker와 server API의 장기 계약이 되므로 컬럼명과 unique key 변경 비용이 크다.
- Python worker가 SQLAlchemy Core로 직접 쓰기 때문에 nullable, numeric precision, check constraint가 후속 구현의 실제 FDR 데이터 형태와 충돌할 수 있다.
- `batch_job_run`이 공개 상태의 source of truth 일부를 담당하므로, 후속 worker 구현은 같은 거래일의 동시 실행을 advisory lock으로 차단하고 `PUBLISHED_FINAL` 이후 재실행은 데이터 정정 옵션에서만 허용해야 한다.
- 배치와 AI의 전체 실행 이력은 MVP 범위 밖으로 두며, 현재 상태 테이블에는 마지막 실행 시각, 마지막 오류, 시도 횟수, 입력 해시 등 최소 추적 정보만 저장한다.
- `stock_analysis.signal_event_id`는 nullable이므로 `analysis_status = 'SIGNAL_FOUND'`와의 정합성은 이번 마이그레이션에서 완전히 강제하지 않고 worker 로직과 테스트에서 검증해야 한다.
- `market_cap`과 `trade_value`는 FDR 데이터 가용성에 따라 null 가능성이 있으므로, 업종 면적 기준 fallback 로직은 후속 worker 이슈에서 확정해야 한다.

## 11. 완료 기준

- `server/src/main/resources/db/migration/V1__initial_schema.sql`이 존재한다.
- MVP 기준에 맞는 12개 테이블이 생성된다.
- RSI, Stoch RSI, MA10, MA200 컬럼이 없다.
- DB enum 타입이 없다.
- 주요 unique key, check constraint, foreign key, partial unique index, `not null` 제약이 정의되어 있다.
- Spring Flyway가 마이그레이션을 적용할 수 있다.
