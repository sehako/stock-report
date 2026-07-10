# KRX 종목 목록과 업종 정보 수집 기능 코드베이스 조사

## 조사 대상

- 기준 기능: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 3번 `[worker] KRX 종목 목록과 업종 정보를 수집한다`
- 요구 요약:
  - FinanceDataReader `StockListing("KRX")`로 종목 목록과 당일 거래량을 조회한다.
  - FinanceDataReader `StockListing("KRX-DESC")`로 종목 설명과 업종을 조회한다.
  - 현재 종목 메타데이터 갱신과 리비전별 종목명, 시장, 업종 스냅샷 저장을 분리한다.
- 조사 범위:
  - 현재 worker 배치 실행 기반
  - Flyway 관리 DB 스키마 중 종목 메타데이터와 리비전 스냅샷 관련 테이블
  - 테스트 구조와 PostgreSQL/Flyway 검증 방식

## 현재 worker 구조

현재 worker는 Python 3.12 `src` 레이아웃 패키지이며 one-shot CLI 실행 기반이 구현되어 있다.

- `worker/src/stock_report_worker/cli.py`
  - `stock-report-worker` console script 진입점이다.
  - `--report-date YYYY-MM-DD`를 받거나 현재 시각을 `WORKER_TIMEZONE` 기준으로 변환해 `report_date`를 정한다.
  - `WorkerSettings`와 SQLAlchemy engine을 만든 뒤 `DailyReportBatch.run(report_date)`를 호출한다.
- `worker/src/stock_report_worker/jobs/daily_report.py`
  - advisory lock 획득, `batch_job_run` 생성/갱신, 거래일 가드, 종목 목록 조회, `batch_stock_run` 초기화, 종목별 순차 실행, 재시도 루프, 최초 게시 경계 호출을 담당한다.
  - `TargetStockProvider.list_for(report_date)`가 반환한 `TargetStock.id` 목록을 `batch_stock_run`의 처리 대상으로 사용한다.
- `worker/src/stock_report_worker/jobs/target_stocks.py`
  - 현재는 `TargetStock(id: int)`와 `TargetStockProvider` Protocol, 테스트용 `InMemoryTargetStockProvider`만 있다.
  - FinanceDataReader 기반 실제 provider는 아직 없다.
- `worker/src/stock_report_worker/jobs/stock_runner.py`
  - `batch_stock_run` 단위 순차 실행을 담당한다.
  - 처리 시작 시 `daily_stock_processing_status.analysis_status = 'DATA_PREPARING'`으로 갱신한다.
  - timeout/일반 예외는 재시도 가능 실패로 처리하고, 재시도 소진 시 `DATA_UPDATE_FAILED`로 갱신한다.
  - `PermanentAnalysisError`는 `ANALYSIS_FAILED`, `PermanentDataUpdateError`는 `DATA_UPDATE_FAILED`로 최종 실패 처리한다.
- `worker/src/stock_report_worker/repositories/schema.py`
  - 운영 코드에서 스키마를 생성하지 않고, Flyway가 만든 테이블을 SQLAlchemy Core로 참조하기 위한 table 정의를 둔다.
  - 현재 `stock`, `batch_job_run`, `batch_stock_run`, `daily_stock_processing_status`, `report_revision` 일부 컬럼만 정의되어 있다.
  - `stock_analysis` table 정의는 아직 없다.

## 현재 DB 스키마에서 관련 테이블

Spring Flyway 마이그레이션 `server/src/main/resources/db/migration/V1__initial_schema.sql` 기준이다.

### `stock`

현재 종목 메타데이터 저장 테이블이다.

- 주요 컬럼:
  - `id`
  - `stock_code`
  - `stock_name`
  - `market`
  - `industry_name`
  - `created_at`
  - `updated_at`
- 제약:
  - `stock_code` unique
  - `stock_code`, `stock_name`, `market` not null
  - `market in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN')`

3번 기능에서 FinanceDataReader 원천 데이터로 갱신할 직접 대상은 이 테이블이다. worker의 SQLAlchemy `schema.py`에는 `created_at`, `updated_at` 컬럼 정의가 빠져 있지만, PostgreSQL에서는 기본값이 있어 insert 자체는 가능하다. 다만 명시적 upsert와 테스트 일관성을 위해 참조 정의 확장이 필요할 수 있다.

### `report_revision`

리포트 리비전과 활성 상태, 계산 버전, 커버리지 집계를 저장한다.

- 주요 컬럼:
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

현재 worker의 `schema.py`에는 집계 컬럼이 정의되어 있지 않다. 3번 기능 자체가 리비전을 게시하는 단계는 아니지만, “리비전별 종목명, 시장, 업종 스냅샷 저장”을 다루려면 `report_revision`과 `stock_analysis`의 관계를 함께 고려해야 한다.

### `stock_analysis`

리비전별 분석 대상, 분석 상태, 종목 메타데이터 스냅샷, 선정 기준 스냅샷을 저장한다.

- 관련 스냅샷 컬럼:
  - `stock_name_snapshot`
  - `market_snapshot`
  - `industry_name_snapshot`
- 선정 관련 필수 컬럼:
  - `selection_rank`
  - `selection_volume`
- 제약:
  - `report_revision_id` -> `report_revision(id)`
  - `stock_id` -> `stock(id)`
  - unique `(report_revision_id, stock_id)`
  - `selection_rank >= 1`
  - `market_snapshot in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN')`

현재 worker에는 `stock_analysis` repository가 없다. 또한 3번 이슈만으로는 “분석 대상 200개 선정”과 `selection_rank`, `selection_volume` 값을 확정하지 않는다. 따라서 스냅샷 저장을 이번 이슈에서 어디까지 구현할지 계획 단계에서 경계를 명확히 해야 한다.

## 기존 배치 흐름과 3번 기능의 접점

현재 정상 거래일 흐름은 다음과 같다.

1. CLI가 `report_date`를 결정한다.
2. `DailyReportBatch`가 `report_date` advisory lock을 획득한다.
3. `batch_job_run`을 `RUNNING`으로 생성 또는 갱신한다.
4. `TradingCalendar`가 `OPEN`이면 `_run_open_day()`로 진입한다.
5. `TargetStockProvider.list_for(report_date)`가 반환한 stock id 목록을 받는다.
6. `batch_stock_run`을 `PENDING`으로 초기화한다.
7. `SequentialStockRunner`가 각 stock id에 대해 주입된 `stock_task`를 실행한다.
8. 모든 종목이 `SUCCEEDED` 또는 `FAILED_PERMANENT`가 되면 placeholder 최초 게시 경계를 호출하고 `PUBLISHED_INITIAL`로 종료한다.

3번 기능은 이 흐름에서 5번 이전 또는 5번 내부에 들어갈 가능성이 높다.

- FinanceDataReader에서 KRX 목록과 KRX-DESC를 조회한다.
- 원천 데이터를 정규화한다.
- `stock.stock_code` 기준으로 현재 메타데이터를 upsert한다.
- upsert된 `stock.id` 목록을 `TargetStockProvider` 결과로 반환한다.

다만 3번 기능 설명에 “당일 거래량”이 포함되어 있고, 4번 기능이 “분석 대상 종목 200개 선정”을 담당한다. 거래량은 4번 선정 기준으로 이어지는 데이터이지만 현재 `stock` 테이블에는 거래량 저장 컬럼이 없다. 따라서 3번 구현 계획에서는 거래량을 영속화하지 않고 provider 내부 DTO로만 보존할지, 4번과 함께 별도 구조로 넘길지 결정이 필요하다. DB 스키마 변경은 현재 원칙상 명시 승인 없이는 할 수 없다.

## FinanceDataReader 의존성 상태

현재 `worker/pyproject.toml`과 `worker/requirements.txt` 런타임 의존성은 다음뿐이다.

- `SQLAlchemy>=2.0`
- `psycopg[binary]>=3.0`
- `pydantic-settings>=2.0`

FinanceDataReader와 pandas는 아직 추가되어 있지 않다. 3번 기능은 외부 의존성 추가가 필요하므로 계획 단계에서 명시적으로 포함되어야 한다.

## 트랜잭션 경계

- 공통 DB helper는 `worker/src/stock_report_worker/db.py`의 `transaction(engine)`이며 `engine.begin()`으로 짧은 transaction-scoped connection을 연다.
- 기존 종목별 실행기는 종목 하나의 상태 변경을 별도 transaction으로 처리한다.
- 3번 기능의 종목 메타데이터 upsert는 외부 공급자 호출과 DB 갱신을 분리하는 것이 기존 패턴과 맞다.
  - FinanceDataReader 호출은 transaction 밖에서 수행한다.
  - 정규화된 목록을 DB transaction 안에서 upsert한다.
  - upsert 결과로 `stock.id`를 조회 또는 반환한다.

## 예외 처리와 배치 상태 영향

현재 `DailyReportBatch._run_open_day()` 안에서 발생한 예외는 상위 `run()`에서 잡혀 `batch_job_run.status = 'FAILED'`, `last_error = str(exc)`로 기록되고 exit code 1로 종료된다.

2번 계획 문서에는 `DELAYED` 상태가 “종목 목록 자체를 가져오지 못해 생성 지연이 필요한 경우”에만 사용된다고 되어 있다. 현재 구현에는 `DELAYED` 전이가 없다. 3번 기능에서 KRX 목록 조회 실패를 `FAILED`로 둘지, 계획 문서의 의도대로 `DELAYED`로 둘지 계획 단계에서 확정해야 한다.

현재 `SequentialStockRunner`의 timeout/retry 정책은 `TargetStockProvider.list_for()` 전체에는 적용되지 않는다. provider 조회 자체가 실패하면 종목별 재시도 루프가 아니라 배치 전체 실패 경로로 간다. KRX 목록 조회는 종목별 작업이 아니므로 별도 실패 정책이 필요하다.

## 현재 테스트 구조

- `worker/tests/test_cli.py`
  - CLI help와 Asia/Seoul 기준 `report_date` 결정을 검증한다.
- `worker/tests/test_daily_report_job.py`
  - SQLite 기반으로 비거래일, 거래일 판정 불가, 중복 실행 스킵, 순차 처리, timeout, 연속 timeout, 재시도 소진, 성공 커밋 보존을 검증한다.
  - `WORKER_POSTGRES_TEST_URL`이 있으면 실제 PostgreSQL에 임시 schema를 만들고 Flyway SQL을 적용해 advisory lock과 실제 제약 조건을 검증한다.

3번 기능 테스트는 기존 패턴을 따르면 다음 경계를 나눌 수 있다.

- FinanceDataReader 호출 wrapper는 fake callable 또는 fake client로 대체해 DataFrame 형태 차이를 검증한다.
- 정규화 로직은 pandas DataFrame fixture로 단위 테스트한다.
- `stock` repository는 SQLite upsert 테스트와 PostgreSQL/Flyway 제약 검증 테스트를 분리한다.
- `TargetStockProvider` 통합 테스트는 provider가 upsert 후 `stock.id` 목록을 반환하고 `DailyReportBatch`가 해당 id로 `batch_stock_run`을 초기화하는지 검증한다.

## 구현 시 주의할 기존 제약

- Python worker는 Spring Flyway가 생성한 테이블만 사용한다. DB 테이블, 컬럼, 인덱스, 제약 추가는 명시 승인 없이 할 수 없다.
- `stock.stock_code`가 현재 메타데이터의 자연키다. FinanceDataReader 원천의 code 컬럼명을 정규화해 이 키에 매핑해야 한다.
- `market`은 Flyway check constraint 값인 `KOSPI`, `KOSDAQ`, `KONEX`, `UNKNOWN` 중 하나여야 한다.
- `industry_name`은 nullable이다. KRX-DESC에서 업종을 못 찾은 종목을 어떻게 표현할지 정해야 한다.
- `stock_analysis` 스냅샷은 `selection_rank`와 `selection_volume`이 not null이라, 분석 대상 선정 전에는 완전한 row를 만들기 어렵다.
- 현재 `TargetStock`은 `id`만 가진다. 3번/4번 연결을 위해 거래량, 시장, 업종 같은 정보를 함께 전달하려면 DTO 확장이 필요하다.
- `stock_task`는 stock id만 받는다. 종목 메타데이터 갱신과 종목별 분석 작업의 책임을 섞지 않는 편이 기존 구조와 맞다.
- 현재 기본 `WeekdayTradingCalendar`는 임시 구현이다. 3번 기능이 실제 KRX 목록 조회를 추가하더라도 휴장일 판정 소스를 대체하는 것은 별도 의사결정이다.

## 확인된 미구현 지점

- FinanceDataReader 의존성 없음.
- KRX/KRX-DESC 조회 wrapper 없음.
- FinanceDataReader DataFrame 컬럼 정규화 로직 없음.
- `stock` upsert repository 없음.
- `TargetStockProvider`의 실제 구현 없음.
- `stock_analysis` SQLAlchemy table 정의와 repository 없음.
- KRX 목록 조회 실패 시 `DELAYED` 처리 없음.
- README에 FinanceDataReader 기반 KRX 종목 목록 수집 관련 환경/실행 설명 없음.

## 조사 결론

현재 worker는 3번 기능을 붙일 수 있는 실행 기반과 `TargetStockProvider` 확장 지점을 이미 갖고 있다. 가장 자연스러운 통합 방식은 FinanceDataReader 기반 provider가 KRX 목록과 KRX-DESC를 조회해 `stock` 테이블을 `stock_code` 기준으로 upsert하고, upsert된 stock id 목록을 기존 배치 오케스트레이터에 반환하는 구조다.

다만 “리비전별 종목명, 시장, 업종 스냅샷 저장”은 현재 `stock_analysis`의 필수 선정 컬럼 때문에 3번 기능 단독으로 완결하기 어렵다. 4번 분석 대상 선정 또는 11번 리포트 리비전 게시 정책과의 경계를 계획 단계에서 먼저 확정해야 한다.
