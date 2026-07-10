# KRX 종목 목록과 업종 정보 수집 구현 계획

상태: 설계 보완 완료 및 구현 전 계획

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 3번 `[worker] KRX 종목 목록과 업종 정보를 수집한다`

원격 이슈: [#9 [Feature] KRX 종목 목록과 업종 정보 수집](https://github.com/sehako/stock-report/issues/9)

## 1. 목적

FinanceDataReader의 KRX 종목 목록과 KRX 설명 목록을 조회해 worker가 사용할 현재 종목 메타데이터를 갱신한다. 갱신된 `stock.id`, KRX listing 종가 원천값, KRX listing 거래량 원천값은 후속 4번 분석 대상 선정 이슈에서 사용할 수 있는 별도 KRX listing 경계로 제공한다.

이번 이슈는 KRX 전체 종목의 현재 메타데이터를 `stock` 테이블에 반영하는 작업이다. 리비전별 종목명, 시장, 업종 스냅샷은 `stock_analysis`에 저장되어야 하지만, 현재 스키마상 `selection_rank`, `selection_volume`이 필수이므로 4번 분석 대상 선정 이슈에서 완성한다. 3번에서는 후속 스냅샷 생성이 현재 메타데이터, 선정용 종가 원천값, 거래량 원천값을 안정적으로 사용할 수 있게 경계를 준비한다.

이 계획은 4번 분석 대상 선정 이슈의 입력 경계를 준비하는 계획이며, 운영 배치 연결은 포함하지 않는다.

## 2. 기준 문서

- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/research/worker/worker-krx-stock-listing-research.md`
- `docs/implementation/worker/worker-batch-execution-foundation-plan.md`
- `docs/implementation/server/server-data-model-flyway-plan.md`
- `docs/adr/0002-share-database-with-single-schema-owner.md`
- `docs/adr/0003-version-published-report-results.md`
- `CONTEXT.md`

## 3. 현재 구조 요약

- `DailyReportBatch._run_open_day()`는 `TargetStockProvider.list_for(report_date)`를 호출해 `TargetStock.id` 목록을 받은 뒤 `batch_stock_run`을 초기화한다.
- `worker/src/stock_report_worker/jobs/target_stocks.py`에는 현재 테스트용 `InMemoryTargetStockProvider`만 있다.
- `worker/src/stock_report_worker/repositories/schema.py`에는 `stock` 참조 정의가 있으나 `created_at`, `updated_at` 컬럼 정의는 빠져 있다.
- `stock` 테이블은 Spring Flyway가 생성하며 `stock_code` unique key, `market` check constraint를 가진다.
- `stock_analysis`는 리비전별 스냅샷 컬럼을 갖지만 선정 순위와 선정 기준 거래량이 필수라서 종목 선정 전에는 완전한 row를 만들 수 없다.
- worker 런타임 의존성에는 아직 `FinanceDataReader`와 `pandas`가 없다.

## 4. 결정 사항

- FinanceDataReader 호출은 DB transaction 밖에서 수행한다.
- DB 갱신은 정규화가 끝난 데이터만 짧은 transaction 안에서 수행한다.
- 현재 종목 메타데이터 갱신 기준은 `stock.stock_code`다.
- `stock.stock_name`, `stock.market`, `stock.industry_name`, `stock.updated_at`은 KRX 원천 데이터 기준으로 갱신한다.
- 신규 종목은 `stock_code`, `stock_name`, `market`, `industry_name`, `created_at`, `updated_at`을 저장한다.
- KRX 목록에는 있으나 KRX-DESC에 없는 종목의 `industry_name`은 `null`로 둔다.
- 시장 값은 DB 제약에 맞춰 `KOSPI`, `KOSDAQ`, `KONEX`, `UNKNOWN` 중 하나로 정규화한다.
- FinanceDataReader 원천 컬럼명 차이는 전용 정규화 계층에서 흡수한다.
- KRX listing 종가와 거래량은 4번 분석 대상 선정의 입력이지만 3번에서는 영속화하지 않는다. `stock` 테이블에는 종가나 거래량 컬럼이 없고, 스키마 변경은 이번 범위가 아니다.
- `listing_close_price`는 KRX listing에서 온 선정용 종가 원천값이다. 일봉 저장용 `daily_price.close_price`와 혼동하지 않는다.
- 이번 이슈에서 KRX 전체 종목을 `TargetStockProvider`로 직접 반환하지 않는다.
- `TargetStockProvider`는 현재 코드상 반환한 stock id를 곧바로 `batch_stock_run` 대상으로 만들기 때문에, 4번 분석 대상 선정 이슈에서 종가 1,000원 이상과 거래량 상위 200개 조건을 적용한 뒤 연결한다.
- 이번 이슈의 기본 경계 이름은 `KrxStockListingProvider`로 고정한다.
- `stock_analysis` row 생성과 리비전 스냅샷 저장은 이번 이슈에서 구현하지 않는다. 4번 이슈에서 선정 순위와 선정 기준 거래량을 확정하면서 함께 저장한다.
- KRX 종목 목록 또는 설명 목록 조회 자체가 실패하면 종목별 실패가 아니라 배치 전체 생성 지연 사유로 분류한다.
- 이번 이슈에서는 `KrxStockListingUnavailable` 같은 생성 지연 사유 예외와 분류 기준까지만 만든다.
- 실제 `batch_job_run.status = 'DELAYED'`, `last_error`, exit code 전이 연결은 4번 분석 대상 선정 이슈에서 KRX listing 경계를 배치 흐름에 연결할 때 구현한다.
- 생성 지연은 `TradingCalendar.UNKNOWN`의 `FAILED`와 구분한다.
- Spring Flyway 마이그레이션, DB 테이블, 컬럼, 인덱스, 제약은 변경하지 않는다.

## 5. 구현 후보 파일

- `worker/pyproject.toml`
- `worker/requirements.txt`
- `worker/README.md`
- `worker/src/stock_report_worker/repositories/schema.py`
- `worker/src/stock_report_worker/repositories/stocks.py`
- `worker/src/stock_report_worker/krx/__init__.py`
- `worker/src/stock_report_worker/krx/listing_client.py`
- `worker/src/stock_report_worker/krx/normalization.py`
- `worker/tests/test_krx_stock_listing.py`

파일명과 모듈 경계는 구현 시 기존 코드 구조에 맞춰 조정할 수 있다. 단, 계획 밖의 서버 스키마 변경은 하지 않는다.

## 6. 구현 절차

1. worker 의존성을 추가한다.
   - `FinanceDataReader`
   - `pandas`
   - `requirements.txt`와 `pyproject.toml`을 같은 의미로 갱신한다.

2. FinanceDataReader 호출 wrapper를 만든다.
   - `StockListing("KRX")` 호출로 종목 목록, 선정용 종가 원천값, 거래량 원천값을 포함한 DataFrame을 가져온다.
   - `StockListing("KRX-DESC")` 호출로 종목 설명과 업종 원천 DataFrame을 가져온다.
   - 테스트에서는 FinanceDataReader를 직접 호출하지 않고 fake callable 또는 fake client를 주입한다.

3. KRX 원천 정규화 로직을 만든다.
   - 종목 코드를 문자열 6자리로 정규화한다.
   - 종목명을 공백 정리 후 `stock_name`으로 매핑한다.
   - 시장 구분을 DB 허용값으로 매핑한다.
   - KRX-DESC의 업종 값을 `industry_name`으로 매핑한다.
   - KRX 목록과 KRX-DESC는 종목 코드 기준으로 left join한다.
   - 종가와 거래량은 정규화하되 이번 이슈에서는 반환 DTO에만 둔다.
   - 필수값인 종목 코드, 종목명, 시장을 만들 수 없는 row는 제외하거나 명시 예외로 처리한다. 기본 방침은 row 단위 silently drop이 아니라 원천 형식 오류 예외로 배치 생성 지연 처리한다.

4. KRX listing 원천 항목 DTO를 정의한다.
   - DTO 이름은 `KrxListedStock`으로 고정한다.
   - `KrxListedStock`은 KRX 전체 listing 원천 항목이며, `TargetStock` 또는 **분석 종목**을 의미하지 않는다.
   - `stock_code`
   - `stock_name`
   - `market`
   - `industry_name`
   - `listing_close_price`
   - `listing_volume`
   - `listing_close_price`는 KRX listing에서 온 선정용 종가 원천값이다. 4번 이슈에서 종가 1,000원 이상 필터에 사용한다.
   - `listing_volume`은 KRX listing에서 온 거래량 원천값이다. 4번 이슈에서 분석 대상 선정이 끝난 뒤 `stock_analysis.selection_volume` 스냅샷으로 확정한다.

5. `stock` repository를 만든다.
   - `stock_code` 기준 upsert를 구현한다.
   - PostgreSQL에서는 `insert ... on conflict (stock_code) do update`를 사용한다.
   - SQLite 테스트에서는 SQLAlchemy dialect upsert 또는 portable fallback을 사용한다.
   - upsert 후 `stock_code -> stock.id` 매핑을 조회한다.
   - 반환 순서는 정규화된 입력 순서를 유지한다.

6. `schema.py`의 `stock` 참조 정의를 보강한다.
   - `created_at`, `updated_at` 컬럼을 추가한다.
   - 운영 스키마 생성은 하지 않으며 SQLAlchemy Core 참조 정의만 확장한다.
   - 필요한 경우 `stock_analysis` 참조 정의는 4번 이슈에서 추가한다.

7. `KrxStockListingProvider`를 추가한다.
   - FinanceDataReader client로 KRX/KRX-DESC를 조회한다.
   - 정규화된 종목 목록을 `stock` 테이블에 upsert한다.
   - upsert된 `stock.id`, 정규화된 KRX listing 종가 원천값, 정규화된 KRX listing 거래량 원천값을 후속 선정 로직이 사용할 수 있는 `KrxListedStock` DTO로 반환한다.
   - 기존 `TargetStockProvider`와 `InMemoryTargetStockProvider`는 이번 이슈에서 운영 기본 경로로 바꾸지 않는다.

8. 생성 지연 사유 예외를 정의한다.
   - KRX 조회 또는 정규화 또는 upsert 실패 중 배치 생성 지연으로 분류할 예외 타입을 정의한다.
   - 예외 타입은 단일 `KrxStockListingUnavailable`로 두되, 원인별 표준 reason을 함께 제공한다.
   - 표준 reason 후보는 `KRX_LISTING_FETCH_FAILED`, `KRX_DESC_FETCH_FAILED`, `SOURCE_COLUMNS_MISSING`, `SOURCE_VALUES_INVALID`, `STOCK_UPSERT_FAILED`다.
   - `KrxStockListingProvider`는 해당 예외를 발생시켜 4번 선정 provider가 `DELAYED` 전이를 연결할 수 있게 한다.
   - 이번 이슈에서는 `batch_job_run.status = 'DELAYED'` 전이를 `DailyReportBatch`에 연결하지 않는다.
   - 이번 이슈에서는 `batch_stock_run`, `stock_analysis`, `report_revision`을 만들지 않는다.
   - 그 외 예상하지 못한 예외는 기존 전체 실패 경로를 유지한다.

9. CLI 기본 provider 연결은 유지한다.
   - 3번 이슈만으로 KRX 전체 종목을 `batch_stock_run` 대상으로 만들지 않는다.
   - 운영 CLI에서 실제 분석 대상 provider를 교체하는 작업은 4번 분석 대상 선정 이슈에서 수행한다.
   - 필요하면 이번 이슈에서는 `KrxStockListingProvider`를 주입 가능한 dependency로만 준비한다.

10. README를 갱신한다.
    - FinanceDataReader 기반 `KrxStockListingProvider`의 역할을 설명한다.
    - 해당 경계는 4번 분석 대상 선정 이슈에서 운영 배치 흐름에 연결된다는 점을 명시한다.
    - 종목 목록 조회 실패는 생성 지연 사유 예외로 분류된다는 의미를 적는다.
    - 의존성 설치 안내를 최신화한다.

## 7. 상태 전이 기준

### 성공

- `KrxStockListingProvider`가 KRX 종목 메타데이터를 upsert한다.
- upsert된 `stock.id`, KRX listing 종가 원천값, KRX listing 거래량 원천값을 후속 4번 선정 로직이 사용할 수 있는 DTO로 반환한다.
- 이번 이슈만으로 KRX 전체 종목에 대한 `batch_stock_run` 초기화와 종목별 순차 처리를 시작하지 않는다.

### 생성 지연

- FinanceDataReader KRX 또는 KRX-DESC 조회 실패
- 필수 원천 컬럼 부재
- 필수값 정규화 불가
- stock upsert 불가

이번 이슈에서 처리:

- 위 오류를 `KrxStockListingUnavailable` 같은 생성 지연 사유 예외로 분류한다.
- 해당 예외는 4번 분석 대상 선정 이슈에서 `DailyReportBatch`의 `DELAYED` 전이로 연결한다.

4번 이슈에서 연결할 처리:

- `batch_job_run.status = 'DELAYED'`
- `batch_job_run.last_error`에 원인 요약 기록
- `finished_at` 기록
- exit code `1`
- `batch_stock_run` 미생성
- `report_revision` 미생성

### 기존 실패 유지

- 거래일 판정 불가: `FAILED`
- 거래일이 아님: `SKIPPED_MARKET_CLOSED`
- 종목별 일봉/분석 실패: 기존 `batch_stock_run`과 `daily_stock_processing_status` 경로

## 8. 제외 범위

- 분석 대상 200개 선정
- 종가 1,000원 이상 필터
- 거래량 기준 순위 확정
- `stock_analysis` row 생성
- 리비전별 종목명, 시장, 업종, 선정 순위, 선정 기준 거래량 스냅샷 저장의 실제 insert
- 일봉 가격 수집
- KRX 휴장일 판정 소스 교체
- Spring Flyway 마이그레이션 변경
- DB 테이블, 컬럼, 인덱스, 제약 추가
- 서버 API, JPA, 프론트엔드 변경

## 9. 검증 계획

- 정규화 단위 테스트
  - KRX 목록과 KRX-DESC DataFrame을 종목 코드 기준으로 병합한다.
  - 종목 코드는 6자리 문자열로 유지된다.
  - 시장 값은 DB 허용값으로 매핑된다.
  - 설명 목록에 없는 업종은 `None`이 된다.
  - 필수 컬럼이 없으면 생성 지연 분류 예외가 발생한다.

- repository 테스트
  - 신규 종목을 insert한다.
  - 같은 `stock_code`를 다시 넣으면 이름, 시장, 업종, `updated_at`이 갱신된다.
  - upsert 후 입력 순서대로 `stock.id`를 반환한다.
  - SQLite 기반 단위 테스트와 PostgreSQL/Flyway 검증을 분리한다.

- provider 통합 테스트
  - fake FinanceDataReader client를 주입해 KRX/KRX-DESC 조회 없이 provider를 검증한다.
  - provider가 upsert 후 `stock.id`, KRX listing 종가 원천값, KRX listing 거래량 원천값을 포함한 DTO 목록을 반환한다.
  - 이번 이슈에서 KRX 전체 종목이 `batch_stock_run` 대상으로 초기화되지 않는지는 변경 금지와 코드리뷰 기준으로 확인한다.

- 생성 지연 테스트
  - KRX 목록 조회 실패 시 생성 지연 사유 예외가 발생한다.
  - KRX-DESC 조회 실패 시 생성 지연 사유 예외가 발생한다.
  - 정규화 필수 컬럼 누락 시 생성 지연 사유 예외가 발생한다.
  - `DailyReportBatch`의 `DELAYED` 전이는 이번 이슈의 테스트 대상이 아니라 변경 금지와 코드리뷰 기준으로 확인한다.

- PostgreSQL/Flyway 검증
  - `WORKER_POSTGRES_TEST_URL`이 있을 때 실제 Flyway SQL을 임시 schema에 적용한다.
  - PostgreSQL unique/check 제약 아래에서 stock upsert가 통과하는지 검증한다.

## 10. 구현 완료 조건

구현 중 완료된 항목은 테스트 또는 수동 검증까지 끝난 뒤 체크한다.

- [x] `KrxStockListingProvider`가 FinanceDataReader 기반으로 구현된다.
- [x] KRX와 KRX-DESC 원천 데이터가 정규화되어 `stock` 테이블에 upsert된다.
- [x] KRX-DESC 업종이 `stock.industry_name`에 반영된다.
- [x] upsert된 `stock.id`, KRX listing 종가 원천값, KRX listing 거래량 원천값이 후속 선정 로직용 DTO로 반환된다.
- [x] KRX 목록 수집 실패는 생성 지연 사유 예외로 분류된다.
- [x] 실제 `batch_job_run.status = 'DELAYED'` 전이 연결은 4번 이슈로 남긴다.
- [x] 이번 이슈만으로 KRX 전체 종목이 `batch_stock_run` 대상으로 초기화되지 않는다.
- [x] 이번 이슈에서 `stock_analysis`와 DB 스키마는 변경하지 않는다.
- [x] 관련 단위 테스트와 가능한 PostgreSQL/Flyway 통합 테스트가 통과한다.
- [x] README에 `KrxStockListingProvider`와 후속 운영 배치 연결 전제가 반영된다.

## 11. 변경 금지 범위

- `server/src/main/resources/db/migration/` 변경 금지
- `stock_analysis` insert 구현 금지
- 분석 대상 200개 선정 구현 금지
- KRX 전체 종목을 운영 `TargetStockProvider`로 연결하는 변경 금지
- `worker/src/stock_report_worker/jobs/target_stocks.py` 운영 경로 변경 금지
- `worker/src/stock_report_worker/jobs/daily_report.py` 운영 흐름 변경 금지
- `DailyReportBatch`에 실제 `DELAYED` 상태 전이를 연결하는 변경 금지
- 일봉 가격 수집 구현 금지
- 시장 지수 수집 구현 금지
- 지표 계산과 신호 판정 구현 금지
- 리포트 리비전 게시 정책 구현 금지
- 외부 의존성은 `FinanceDataReader`, `pandas` 외 추가 금지

## 12. 남은 리스크와 확인 필요 사항

- FinanceDataReader의 KRX/KRX-DESC DataFrame 컬럼명은 버전에 따라 달라질 수 있다. 구현 승인 전 `StockListing("KRX")`와 `StockListing("KRX-DESC")`의 실제 관측 컬럼을 fixture 또는 문서 근거로 고정해야 한다. fake fixture는 이 실제 관측 컬럼을 기준으로 만든다.
- FinanceDataReader 네트워크 실패와 원천 형식 오류는 단일 생성 지연 사유 예외로 묶되, 예외의 표준 reason으로 원인을 구분한다. 4번에서 `last_error`로 남길 메시지는 이 reason을 기준으로 짧고 안정적인 원인 요약을 남겨야 한다.
- 이번 이슈에서 반환하는 `KrxListedStock` DTO는 KRX 전체 listing 원천 결과다. 4번 이슈에서 거래량 상위 200개로 좁힌 뒤에만 `TargetStockProvider`와 `batch_stock_run` 대상으로 연결해야 한다.
- `listing_close_price`와 `listing_volume`은 이번 이슈에서 영속화하지 않는다. 4번 이슈에서는 같은 실행 흐름 안에서 `KrxStockListingProvider`가 반환한 `KrxListedStock` 목록을 메모리로 전달받아 분석 대상 선정과 `stock_analysis` 생성을 처리한다. 선정 완료 후 `listing_volume`을 `stock_analysis.selection_volume`으로 스냅샷 저장한다. 이 재사용은 별도 DB 저장, 임시 테이블, 캐시 추가를 의미하지 않는다.
