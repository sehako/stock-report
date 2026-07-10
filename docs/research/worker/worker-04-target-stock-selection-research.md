# 분석 대상 종목 200개 선정 기능 코드베이스 조사

## 조사 대상

- 기준 기능: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 4번 `[worker] 분석 대상 종목 200개를 선정한다`
- 요구 요약:
  - 종가 1,000원 이상 종목만 포함한다.
  - 거래량 내림차순 상위 200개 종목을 선정한다.
  - 리포트 재현을 위해 리비전별 선정 순위와 선정 기준 거래량을 저장할 수 있게 한다.
  - 분석 범위가 KRX 전체가 아님을 이후 화면에서 표시할 수 있게 한다.
- 조사 범위:
  - 3번 KRX 종목 목록 수집 구현 결과
  - 배치 실행 흐름과 `TargetStockProvider` 경계
  - 선정 결과 저장 후보 테이블과 SQLAlchemy 참조 정의
  - 테스트 구조

## 현재 worker 구조와 4번 기능의 접점

현재 worker는 one-shot 배치 구조를 갖고 있으며 정상 거래일에는 `DailyReportBatch._run_open_day()`가 `TargetStockProvider.list_for(report_date)`를 호출한 뒤 반환된 stock id 목록을 `batch_stock_run` 대상으로 등록한다.

- `worker/src/stock_report_worker/jobs/daily_report.py`
  - `_run_open_day()`에서 `target_stock_ids = [stock.id for stock in self._target_stock_provider.list_for(report_date)]`로 대상 id만 추출한다.
  - 이후 `BatchStockRunRepository.ensure_pending()`으로 종목별 실행 row를 만든다.
  - 현재 target provider 예외는 별도로 분류되지 않고 `_run_open_day()` 예외로 전파되어 배치 전체 `FAILED` 경로를 탄다.
- `worker/src/stock_report_worker/jobs/target_stocks.py`
  - `TargetStock`은 현재 `id: int`만 가진다.
  - 운영 provider는 아직 없고 테스트용 `InMemoryTargetStockProvider`만 있다.
- `worker/src/stock_report_worker/jobs/stock_runner.py`
  - 선정된 종목 id를 순차 처리한다.
  - 종목별 상태는 `daily_stock_processing_status`에 `DATA_PREPARING`, `DATA_UPDATE_FAILED`, `ANALYSIS_FAILED` 중심으로 기록한다.

4번 기능의 자연스러운 통합 지점은 `TargetStockProvider`의 실제 구현이다. 이 provider가 KRX 전체 listing 수집 결과를 받아 종가/거래량 조건으로 200개를 고른 뒤, 기존 배치가 그대로 `batch_stock_run`을 만들 수 있게 `TargetStock` 목록을 반환하는 구조가 현재 실행 흐름과 맞다.

## KRX listing 수집 구현 상태

3번 이슈 구현 결과로 KRX 전체 종목 원천 데이터를 수집하고 정규화하는 경계가 이미 있다.

- `worker/src/stock_report_worker/krx/listing_client.py`
  - `FinanceDataReaderKrxListingClient.stock_listing(market)`가 `FinanceDataReader.StockListing(market)`를 호출한다.
  - `KrxStockListingProvider.collect(now)`가 `KRX`, `KRX-DESC`를 조회하고 정규화한 뒤 `stock` 테이블을 upsert한다.
  - 반환값은 upsert된 `stock_id`를 포함한 `KrxListedStock` 목록이다.
- `worker/src/stock_report_worker/krx/normalization.py`
  - `KrxListedStock` 필드는 `stock_code`, `stock_name`, `market`, `industry_name`, `listing_close_price`, `listing_volume`, `stock_id`이다.
  - `listing_close_price`는 `Decimal`, `listing_volume`은 `int`로 정규화된다.
  - KRX listing 원천 컬럼 alias에 `Close`/`종가`, `Volume`/`거래량`이 포함되어 있다.
- `worker/src/stock_report_worker/repositories/stocks.py`
  - `stock_code` 기준으로 현재 종목 메타데이터를 upsert한다.
  - upsert 이후 입력 순서대로 `stock.id`를 반환한다.

따라서 4번 선정에 필요한 입력값인 종가, 거래량, 현재 종목명, 시장, 업종, stock id는 메모리상의 `KrxListedStock` 목록으로 확보된다. 다만 `listing_close_price`와 `listing_volume`은 현재 별도 테이블에 영속화되지 않는다. `worker/README.md`도 4번 이슈에서 이 원천값을 메모리로 이어 받아 선정과 스냅샷 저장을 수행하는 전제를 명시한다.

## 선정 로직에서 필요한 데이터와 정렬 기준

현재 DTO 기준으로 4번 필터와 정렬은 다음 데이터만으로 가능하다.

- 필터:
  - `KrxListedStock.listing_close_price >= Decimal("1000")`
  - `KrxListedStock.stock_id is not None`
- 정렬:
  - 1차: `listing_volume` 내림차순
  - 2차 tie-breaker는 제안서에 명시되어 있지 않다.

거래량이 같은 종목이 200위 경계에 걸릴 수 있으므로 구현 계획에서 결정적 tie-breaker를 정해야 한다. 현재 코드베이스에서 가장 안정적인 후보는 `stock_code` 오름차순 또는 원천 listing 순서 보존이다. 리포트 재현성을 우선하면 명시적 tie-breaker를 두고 테스트로 고정하는 편이 안전하다.

## 저장 요구와 현재 DB 스키마

요구사항의 “리비전별 선정 순위와 선정 기준 거래량”은 Flyway 스키마상 `stock_analysis`가 담당한다.

`server/src/main/resources/db/migration/V1__initial_schema.sql` 기준 `stock_analysis` 관련 컬럼은 다음과 같다.

- `report_revision_id`
- `stock_id`
- `analysis_status`
- `stock_name_snapshot`
- `market_snapshot`
- `industry_name_snapshot`
- `selection_rank`
- `selection_volume`
- `current_price`
- `last_trade_date`

제약 조건상 `selection_rank`와 `selection_volume`은 not null이고, `(report_revision_id, stock_id)` unique이다. 이 구조는 “리비전별 200개 분석 대상과 그 당시의 선정 스냅샷”을 저장하기에 맞다.

하지만 현재 worker의 SQLAlchemy 참조 정의 `worker/src/stock_report_worker/repositories/schema.py`에는 `stock_analysis` table이 없다. `report_revision`도 운영 Flyway 스키마의 집계 컬럼(`target_stock_count` 등)을 일부 반영하지 않고 있다. 따라서 선정 결과를 실제로 저장하려면 최소한 `stock_analysis` 참조 정의와 repository가 필요하다.

## 리비전 생성 경계와 저장 시점

현재 리포트 게시 경계는 아직 placeholder이다.

- `worker/src/stock_report_worker/jobs/report_publisher.py`
  - `InitialReportPublisher` Protocol과 `NoopInitialReportPublisher`만 있다.
- `DailyReportBatch._run_open_day()`
  - 모든 `batch_stock_run`이 종료된 뒤 `publish_initial(report_date, job_id)`를 호출한다.
  - 현재 기본 publisher는 아무 작업도 하지 않는다.

이 때문에 4번의 저장 요구는 두 가지 방식 중 하나로 경계를 정해야 한다.

1. 4번에서 리포트 리비전 생성과 `stock_analysis` 초기 row 저장까지 함께 구현한다.
   - 장점: “리비전별 선정 순위/거래량 저장” 요구를 이슈 4에서 직접 만족한다.
   - 부담: 리비전 게시 정책인 11번 이슈의 일부를 앞당겨야 하고, 현재 `NoopInitialReportPublisher` 경계를 확장해야 한다.
2. 4번에서는 선정 결과 DTO와 `batch_stock_run` 연결까지만 구현하고, 저장은 11번 리포트 리비전 게시 이슈에서 수행한다.
   - 장점: 현재 배치 구조 변경 폭이 작다.
   - 부담: 이슈 4의 저장 요구를 “저장할 수 있게 한다” 수준으로만 만족하게 되며, 선정 결과를 게시 시점까지 전달하거나 재구성할 방법이 필요하다.

3번 구현 계획 문서에는 4번 이슈에서 `stock_analysis.selection_volume` 스냅샷을 확정한다고 되어 있다. 따라서 구현 계획 단계에서는 4번이 `stock_analysis` 초기 스냅샷 저장까지 포함하는지, 아니면 11번과의 경계를 다시 조정하는지 명시해야 한다.

## 분석 범위 표시 요구

“분석 범위가 KRX 전체가 아님을 이후 화면에서 표시”하려면 API 응답에서 분석 범위 메타데이터를 제공할 수 있어야 한다. 현재 스키마에는 직접적인 `scope_label` 같은 컬럼은 없다.

현재 활용 가능한 저장 지점은 다음이다.

- `report_revision.target_stock_count`
  - Flyway에는 존재하지만 worker `schema.py`에는 아직 없다.
  - 200개 선정 결과의 수량을 저장해 “분석 대상 200개” 표시에 활용할 수 있다.
- `stock_analysis`
  - 실제 포함 종목 200개만 저장되므로 API는 해당 리비전의 분석 범위가 KRX 전체가 아니라 선정된 종목 집합임을 추론할 수 있다.

다만 화면 문구에 필요한 “KRX 전체 중 종가 1,000원 이상, 거래량 상위 200개” 같은 범위 설명은 현재 별도 스키마 컬럼으로 저장되지 않는다. 이 설명이 동적으로 바뀔 가능성이 없다면 서버/API에서 고정 정책으로 노출할 수 있지만, 정책 변경 이력을 리비전별로 보존하려면 별도 스키마 변경이 필요하다. 스키마 변경은 현재 원칙상 명시 승인 없이는 수행할 수 없다.

## 예외 처리와 배치 상태 영향

`KrxStockListingProvider.collect()`는 다음 실패를 `KrxStockListingUnavailable`로 분류한다.

- `KRX_LISTING_FETCH_FAILED`
- `KRX_DESC_FETCH_FAILED`
- `SOURCE_COLUMNS_MISSING`
- `SOURCE_VALUES_INVALID`
- `STOCK_UPSERT_FAILED`

현재 `DailyReportBatch.run()`은 `_run_open_day()`에서 발생한 모든 예외를 `batch_job_run.status = 'FAILED'`로 기록한다. 하지만 README와 이전 구현 계획에는 “종목 목록 자체를 가져오지 못한 경우 `DELAYED` 전이를 후속 선정 이슈에서 연결”한다는 전제가 있다.

따라서 4번 구현 계획에서는 KRX listing 수집 실패를 `FAILED`로 둘지, `DELAYED`로 별도 처리할지 확정해야 한다. 제안서 11번은 종목 목록 자체를 가져오지 못하면 당일 리포트 리비전을 만들지 않고 생성 지연 상태로 처리한다고 되어 있어, `DELAYED`가 더 일관된 방향이다.

## 테스트 구조

현재 worker 테스트는 SQLite in-memory 기반 단위/통합 테스트와 선택적 PostgreSQL/Flyway 검증으로 나뉜다.

- `worker/tests/test_krx_stock_listing.py`
  - pandas DataFrame fixture로 KRX listing 정규화, 오류 분류, stock upsert를 검증한다.
  - `FakeListingClient`로 FinanceDataReader 호출을 대체한다.
  - `WORKER_POSTGRES_TEST_URL`이 있으면 실제 Flyway SQL을 적용한 PostgreSQL schema에서 upsert를 검증한다.
- `worker/tests/test_daily_report_job.py`
  - `InMemoryTargetStockProvider`를 통해 선정된 stock id가 입력 순서대로 처리되는지 검증한다.
  - 재시도, timeout, 중복 실행, 상태 전이를 검증한다.

4번 기능 테스트는 기존 패턴을 따르면 다음 경계로 나눌 수 있다.

- 순수 선정 로직 단위 테스트
  - 종가 1,000원 미만 제외
  - 거래량 내림차순 상위 200개 제한
  - 동률 tie-breaker 고정
  - `selection_rank`가 1부터 연속 부여되는지 검증
- provider 통합 테스트
  - fake KRX listing client가 반환한 DataFrame으로 stock upsert 후 200개 target만 반환하는지 검증
  - `DailyReportBatch`가 실제 선정 provider 결과만 `batch_stock_run`으로 등록하는지 검증
- 저장소 테스트
  - `stock_analysis` repository를 추가한다면 SQLite 기반 insert/upsert 테스트
  - PostgreSQL/Flyway 선택 테스트로 실제 제약 조건과 SQLAlchemy 참조 정의 정합성 검증
- 실패 처리 테스트
  - KRX listing 수집 실패 시 `batch_job_run.status`를 `DELAYED` 또는 계획에서 정한 상태로 기록하는지 검증

## 구현 시 주의할 기존 제약

- Python worker는 Spring Flyway가 생성한 승인된 테이블만 사용한다.
- DB 스키마, API 스펙, 외부 의존성 변경은 명시 승인 없이 수행할 수 없다.
- `listing_close_price`와 `listing_volume`은 현재 영속화되지 않는다. 선정과 스냅샷 저장은 같은 실행 흐름 안에서 처리해야 한다.
- `TargetStock`이 현재 id만 가지므로 선정 순위와 거래량을 후속 단계에서 쓰려면 DTO 확장 또는 별도 선정 결과 객체가 필요하다.
- `DailyReportBatch`는 현재 `TargetStock.id`만 사용한다. 선정 메타데이터를 게시/저장 단계까지 전달하려면 배치 오케스트레이터 경계 변경이 필요하다.
- `stock_analysis` row를 만들려면 `report_revision_id`가 필요하다. 현재 리비전 생성 repository는 없다.
- `stock_analysis.analysis_status`는 not null이다. 4번 시점에 아직 종목별 분석이 끝나지 않았다면 초기값은 `DATA_PREPARING` 같은 상태를 사용할지 계획에서 정해야 한다.
- 분석 범위 문구를 리비전별로 영속화할 컬럼은 없다. 정책 고정 노출로 충분한지 확인이 필요하다.

## 확인된 미구현 지점

- 거래량/종가 기준 실제 `TargetStockProvider` 구현 없음.
- 선정 로직 전용 DTO 또는 service 없음.
- `TargetStock`에 `selection_rank`, `selection_volume`, 종목 스냅샷 필드 없음.
- `stock_analysis` SQLAlchemy table 정의 없음.
- `stock_analysis` repository 없음.
- `report_revision` 생성/조회 repository 없음.
- `KrxStockListingUnavailable`를 배치 `DELAYED` 상태로 연결하는 처리 없음.
- 분석 범위 메타데이터를 API가 노출할 수 있게 하는 worker 저장/게시 경계 없음.

## 조사 결론

현재 worker는 4번 기능을 구현할 수 있는 핵심 입력 경계가 준비되어 있다. `KrxStockListingProvider.collect()`가 KRX 전체 종목의 현재 메타데이터를 upsert하고, 선정에 필요한 `listing_close_price`, `listing_volume`, `stock_id`를 포함한 `KrxListedStock` 목록을 반환한다.

가장 작은 구현 경로는 이 목록을 받아 종가 1,000원 이상 필터와 거래량 내림차순 상위 200개 선정을 수행하는 실제 `TargetStockProvider`를 추가하는 것이다. 다만 요구사항의 리비전별 순위/거래량 저장까지 완료하려면 `stock_analysis` 참조 정의, repository, 리비전 생성/게시 경계를 함께 다뤄야 한다. 이 부분은 11번 리포트 리비전 게시 정책과 겹치므로, 계획 단계에서 4번의 완료 범위를 명확히 확정해야 한다.
