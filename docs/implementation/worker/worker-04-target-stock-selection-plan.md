# 분석 대상 종목 200개 선정 구현 계획

상태: 구현 전 계획

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 4번 `[worker] 분석 대상 종목 200개를 선정한다`

원격 이슈: [#14 [Feature] 분석 대상 종목 200개 선정](https://github.com/sehako/stock-report/issues/14)

## 1. 목적

KRX 전체 종목 목록 수집 결과에서 해당 거래일의 **분석 종목** 200개를 결정하고, 기존 배치 실행 흐름이 이 200개만 순차 처리하도록 연결한다.

이번 이슈는 다음을 완료한다.

- 종가 1,000원 이상 필터 적용
- 거래량 내림차순 상위 200개 선정
- 선정 순위와 선정 기준 거래량을 메모리 DTO에 확정
- 선정된 종목만 `batch_stock_run` 대상으로 연결
- 선정 직후 `daily_stock_processing_status`를 `DATA_PREPARING`으로 초기화
- KRX 목록 자체를 가져오지 못한 경우 `batch_job_run.status = 'DELAYED'`로 생성 지연 처리

이번 이슈는 `stock_analysis` 리비전 스냅샷을 직접 생성하지 않는다. `docs/implementation/server/server-data-model-flyway-plan.md`의 “`stock_analysis`는 리비전 공개 시점의 `daily_stock_processing_status`를 스냅샷으로 복사한다”는 기준에 맞춰, 공개 리비전 생성과 `stock_analysis` 저장은 11번 리포트 리비전 게시 정책 이슈에서 구현한다.

## 2. 기준 문서

- `docs/research/worker/worker-04-target-stock-selection-research.md`
- `docs/proposal/stock-report-mvp-product-architecture-baseline.md`
- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/implementation/worker/worker-03-krx-stock-listing-plan.md`
- `docs/implementation/server/server-data-model-flyway-plan.md`
- `docs/adr/0002-share-database-with-single-schema-owner.md`
- `docs/adr/0003-version-published-report-results.md`
- `docs/adr/0004-isolate-batch-failures-per-stock.md`
- `CONTEXT.md`

## 3. 현재 구조 요약

- `KrxStockListingProvider.collect(now)`는 KRX/KRX-DESC를 조회하고 `stock`을 upsert한 뒤 `KrxListedStock` 목록을 반환한다.
- `KrxListedStock`에는 `stock_id`, `stock_code`, `stock_name`, `market`, `industry_name`, `listing_close_price`, `listing_volume`이 있다.
- `TargetStockProvider.list_for(report_date)`는 현재 `TargetStock(id)` 목록만 반환한다.
- `DailyReportBatch._run_open_day()`는 `TargetStockProvider` 결과의 id만 뽑아 `batch_stock_run`을 만든다.
- `DailyReportBatch.run()`은 `_run_open_day()` 예외를 모두 `FAILED`로 처리한다.
- `daily_stock_processing_status`는 거래일별 분석 종목의 최신 업무 처리 상태이며, 선정 직후 `DATA_PREPARING`으로 초기화해야 한다.
- `stock_analysis`는 Flyway 스키마에 있지만 worker `schema.py` 참조 정의와 repository는 아직 없다.

## 4. 결정 사항

- 4번의 운영 provider 이름은 `KrxTargetStockProvider`로 둔다.
- `KrxTargetStockProvider`는 내부에서 `KrxStockListingProvider.collect(now)`를 호출한다.
- 종가 필터는 `listing_close_price >= Decimal("1000")`로 적용한다.
- 정렬은 `listing_volume` 내림차순, `stock_code` 오름차순으로 고정한다.
  - 거래량 동률에서 리포트 재현성을 보장하기 위한 결정적 tie-breaker다.
  - 원천 DataFrame 순서에 의존하지 않는다.
- 상위 200개보다 적게 남으면 남은 수만 분석 종목으로 사용한다.
  - KRX 시장 데이터가 비정상적으로 부족한 경우를 별도 실패로 만들지는 않는다.
  - 단, 원천 필수 컬럼 누락이나 필수값 정규화 실패는 기존 `KrxStockListingUnavailable`로 생성 지연 처리한다.
- `TargetStock`은 선정 메타데이터를 함께 갖도록 확장한다.
  - `id`
  - `selection_rank`
  - `selection_volume`
  - `stock_code`
  - `stock_name_snapshot`
  - `market_snapshot`
  - `industry_name_snapshot`
  - `selection_close_price`
- `DailyReportBatch`는 선정된 `TargetStock` 목록을 한 번만 받아 id 목록과 상태 초기화에 재사용한다.
- 선정 직후 `daily_stock_processing_status`에 모든 분석 종목을 `DATA_PREPARING`으로 upsert한다.
- `batch_stock_run` 생성은 기존처럼 선정 순서대로 수행한다.
- `KrxStockListingUnavailable`가 발생하면 `batch_job_run.status = 'DELAYED'`, `last_error` 기록, `finished_at` 기록 후 exit code 1로 종료한다.
- 생성 지연 시 `batch_stock_run`, `daily_stock_processing_status`, `report_revision`, `stock_analysis`는 만들지 않는다.
- `stock_analysis` 참조 정의와 repository는 이번 이슈에서 추가하지 않는다.
- `report_revision` 생성, 활성화, `target_stock_count` 저장은 11번 리포트 게시 정책 이슈에서 처리한다.
- DB 스키마, Spring Flyway 마이그레이션, 서버 API, 프론트엔드는 변경하지 않는다.
- 신규 외부 의존성은 추가하지 않는다.

## 5. 설계 압박 질문과 결정

질문: 4번에서 `stock_analysis`를 바로 생성해야 하는가?

확정 결정: 생성하지 않는다. `stock_analysis`는 공개 리비전 스냅샷이고, 현재 아키텍처 기준으로는 첫 수집 회차 종료 후 게시 시점에 `daily_stock_processing_status`와 선정 스냅샷을 복사해야 한다. 4번에서는 선정 결과와 상태 초기화까지 완성하고, 리비전 스냅샷 저장은 11번에서 구현한다.

질문: 거래량 동률의 순위는 어떻게 재현할 것인가?

확정 결정: `listing_volume desc, stock_code asc`로 고정한다. 원천 행 순서는 공급자 구현 변화에 취약하고, stock id는 환경별 insert 순서에 영향을 받을 수 있다.

질문: KRX 목록 수집 실패는 종목별 실패인가?

확정 결정: 아니다. 분석 대상 자체를 정할 수 없으므로 `생성 지연`이다. `batch_job_run.status = 'DELAYED'`로 남기고 당일 리포트 리비전은 만들지 않는다. 이때 `batch_stock_run`, `daily_stock_processing_status`, `report_revision`, `stock_analysis`는 생성하지 않는다.

질문: 4번에서 `stock_analysis`를 만들지 않는다면 선정 순위, 선정 기준 거래량, 종목명·시장·업종 스냅샷을 어디에 보존할 것인가?

확정 결정: 4번에서는 DB에 새로 보존하지 않고 `TargetStock` DTO와 배치 실행 메모리 안에만 둔다. 현재 승인 스키마에는 공개 전 선정 스냅샷을 저장할 테이블이나 컬럼이 없으며, `batch_stock_run`과 `daily_stock_processing_status`에 억지로 넣지 않는다. 프로세스 재시작 후 게시 스냅샷을 복구하는 문제는 11번 리포트 리비전 게시 정책에서 별도 설계한다.

질문: 분석 범위 문구를 이번 이슈에서 DB에 저장해야 하는가?

권장 결정: 저장하지 않는다. `분석 종목`의 정의가 고정 정책으로 `CONTEXT.md`와 API 구현 기준에 존재하므로, 이번 이슈는 실제 대상 200개를 안정적으로 선정하는 데 집중한다. 리비전별 정책 변경 이력 저장이 필요해지면 별도 스키마 승인 사안이다.

질문: 종가 1,000원 이상 필터 후 남은 종목이 200개 미만이면 실패 또는 생성 지연으로 볼 것인가?

확정 결정: 실패로 보지 않고 남은 수만큼 진행한다. “상위 200개”는 최대 개수 제한이며, 정확히 200개가 없으면 리포트 불가라는 의미로 다루지 않는다. 최소 종목 수 검증이나 운영 알림이 필요하면 별도 이슈로 다룬다.

## 6. 구현 후보 파일

- `worker/src/stock_report_worker/jobs/target_stocks.py`
- `worker/src/stock_report_worker/jobs/daily_report.py`
- `worker/src/stock_report_worker/repositories/processing_status.py`
- `worker/src/stock_report_worker/repositories/batch_runs.py`
- `worker/tests/test_target_stocks.py`
- `worker/tests/test_daily_report_job.py`
- `worker/README.md`

구현 중 파일 분리가 필요하면 기존 패키지 경계를 따르되, 계획 밖 서버/DB 스키마 파일은 수정하지 않는다.

## 7. 구현 절차

1. 선정 결과 DTO를 확장한다.
   - `TargetStock`에 선정 순위, 선정 기준 거래량, 종목 스냅샷 필드를 추가한다.
   - 기존 테스트용 `InMemoryTargetStockProvider`는 id 목록만 받아도 동작하도록 기본값 또는 helper 생성을 제공한다.

2. 순수 선정 함수를 추가한다.
   - 입력: `list[KrxListedStock]`
   - 출력: `list[TargetStock]`
   - `stock_id is None`인 항목은 선정 대상에서 제외하거나 명시 오류로 처리한다. 기본 방침은 provider upsert 이후 불가능한 상태이므로 명시 오류로 둔다.
   - 종가 1,000원 이상 필터를 적용한다.
   - `listing_volume desc, stock_code asc` 정렬 후 200개로 자른다.
   - 1부터 시작하는 `selection_rank`를 부여한다.
   - `listing_volume`을 `selection_volume`으로 확정한다.

3. 실제 운영 provider를 추가한다.
   - `KrxTargetStockProvider`는 `TargetStockProvider`를 구현한다.
   - `KrxStockListingProvider`와 `now` callable을 주입받는다.
   - `list_for(report_date)`에서 KRX listing을 수집한 뒤 순수 선정 함수를 호출한다.
   - `report_date`는 인터페이스 일관성을 위해 받되, 현재 KRX listing 수집 자체에는 직접 사용하지 않는다.

4. `DailyReportBatch`의 target 처리 흐름을 조정한다.
   - `target_stocks = self._target_stock_provider.list_for(report_date)`로 한 번만 호출한다.
   - `target_stock_ids = [stock.id for stock in target_stocks]`를 기존 `batch_stock_run` 생성에 사용한다.
   - 선정 직후 같은 transaction에서 `batch_stock_run.ensure_pending()`과 `daily_stock_processing_status` 초기화를 수행한다.
   - 상태 초기화는 `ProcessingStatusRepository.upsert_status(..., analysis_status='DATA_PREPARING')`를 재사용하거나 bulk helper를 추가한다.

5. 생성 지연 전이를 추가한다.
   - `DailyReportBatch.run()`에서 `KrxStockListingUnavailable`을 일반 예외보다 먼저 잡는다.
   - `batch_job_run.status = 'DELAYED'`, `last_error`에 안정적인 reason/message를 기록하고 `finished_at`을 채운다.
   - 결과는 `DailyReportResult(exit_code=1, status='DELAYED', batch_job_run_id=job.id)`로 반환한다.
   - advisory lock release는 기존 `finally` 경로를 유지한다.

6. CLI 기본 provider를 운영 provider로 연결한다.
   - `DailyReportBatch`의 기본 `target_stock_provider`를 `KrxTargetStockProvider(KrxStockListingProvider(engine), now=self._now)`로 바꾼다.
   - 테스트에서는 기존처럼 fake 또는 in-memory provider를 주입한다.
   - KRX 전체 종목이 아니라 선정된 상위 200개만 `batch_stock_run` 대상이 되도록 검증한다.

7. README를 갱신한다.
   - 운영 배치가 KRX listing 수집 후 종가/거래량 기준으로 분석 종목 200개를 선정한다고 설명한다.
   - 생성 지연 조건과 `DELAYED` 상태 의미를 반영한다.
   - `stock_analysis` 스냅샷 저장은 리포트 게시 정책 단계에서 수행한다는 경계를 명시한다.

## 8. 상태 전이 기준

### 성공

- KRX listing 수집과 stock upsert가 성공한다.
- 종가 1,000원 이상 필터와 거래량 상위 200개 선정이 완료된다.
- 선정된 종목만 `batch_stock_run`에 등록된다.
- 선정된 종목의 `daily_stock_processing_status`가 `DATA_PREPARING`으로 초기화된다.
- 이후 종목별 순차 실행과 재시도는 기존 `SequentialStockRunner` 경로를 따른다.

### 생성 지연

- KRX listing 조회 실패
- KRX-DESC 조회 실패
- 원천 필수 컬럼 누락
- 원천 필수값 정규화 실패
- stock upsert 실패

처리:

- `batch_job_run.status = 'DELAYED'`
- `batch_job_run.last_error`에 reason 기반 요약 저장
- `finished_at` 기록
- exit code 1
- `batch_stock_run` 미생성
- `daily_stock_processing_status` 미생성
- `report_revision` 미생성
- `stock_analysis` 미생성

### 기존 실패 유지

- 거래일 판정 불가: `FAILED`
- 휴장일: `SKIPPED_MARKET_CLOSED`
- 종목별 수집/분석 실패: 기존 종목별 retry와 업무 상태 경로
- 예상하지 못한 배치 예외: 기존 `FAILED`

## 9. 검증 계획

- 선정 로직 단위 테스트
  - 종가 1,000원 미만 제외
  - 종가 1,000원은 포함
  - 거래량 내림차순 상위 200개 제한
  - 거래량 동률이면 `stock_code` 오름차순
  - `selection_rank`가 1부터 연속 부여
  - `selection_volume`이 원천 `listing_volume`과 동일

- provider 테스트
  - fake `KrxStockListingProvider` 결과를 입력해 `KrxTargetStockProvider`가 선정 결과를 반환하는지 검증
  - `stock_id`가 없는 항목이 있으면 명시 오류로 실패하는지 검증

- 배치 통합 테스트
  - 기본 provider를 fake로 주입해 선정된 종목만 `batch_stock_run`으로 생성되는지 검증
  - 선정 순서대로 종목별 task가 호출되는지 검증
  - 선정 직후 `daily_stock_processing_status`가 `DATA_PREPARING`으로 생성되는지 검증
  - `KrxStockListingUnavailable` 발생 시 `DELAYED`, exit code 1, `batch_stock_run` 미생성 검증
  - 휴장일에는 provider가 호출되지 않는지 검증

- 회귀 테스트
  - 기존 timeout, 재시도, 공급자 장애, 중복 실행, stale running 복구 테스트가 유지되는지 확인

- PostgreSQL/Flyway 검증
  - 이번 이슈는 새 스키마를 쓰지 않으므로 필수는 아니다.
  - 기존 `WORKER_POSTGRES_TEST_URL` 기반 테스트가 실행 가능한 환경이면 전체 worker 테스트로 제약 정합성을 함께 확인한다.

실행 명령:

```bash
cd worker
source .venv/bin/activate
pytest
```

가능한 경우:

```bash
cd worker
source .venv/bin/activate
WORKER_POSTGRES_TEST_URL='postgresql+psycopg://user:password@localhost:5432/test_db' pytest
```

## 10. 구현 완료 조건

- [x] 운영 기본 배치가 KRX listing 수집 결과에서 분석 종목만 선정한다.
- [x] 종가 1,000원 이상 조건이 적용된다.
- [x] 거래량 내림차순 상위 200개 조건이 적용된다.
- [x] 거래량 동률 순서가 `stock_code` 오름차순으로 결정된다.
- [x] 선정 순위와 선정 기준 거래량이 `TargetStock`에 보존된다.
- [x] 선정된 종목만 `batch_stock_run` 대상으로 등록된다.
- [x] 선정된 종목의 `daily_stock_processing_status`가 `DATA_PREPARING`으로 초기화된다.
- [x] KRX 목록 수집 실패가 `DELAYED`로 기록된다.
- [x] 생성 지연 시 리포트 리비전과 종목별 실행 row가 생성되지 않는다.
- [x] 관련 단위 테스트와 배치 통합 테스트가 통과한다.
- [x] README에 운영 배치 선정 흐름과 이번 이슈의 저장 경계가 반영된다.

## 11. 변경 금지 범위

- `server/src/main/resources/db/migration/` 변경 금지
- DB 테이블, 컬럼, 인덱스, 제약 추가 금지
- `stock_analysis` insert/update 구현 금지
- `report_revision` 생성/활성화 구현 금지
- `signal_event`, `daily_price`, `daily_indicator`, `industry_analysis`, `market_ai_summary` 구현 금지
- 일봉 가격 수집 구현 금지
- 기술지표 계산 구현 금지
- 골든크로스 신호 판정 구현 금지
- 업종 분석 구현 금지
- 서버 API/JPA 변경 금지
- 프론트엔드 변경 금지
- 신규 외부 의존성 추가 금지

## 12. 남은 리스크와 확인 필요 사항

- `stock_analysis` 저장은 11번 이슈로 넘긴다. 4번에서는 선정 스냅샷을 `TargetStock` DTO와 배치 실행 메모리에만 둔다. 프로세스 재시작 후 게시 스냅샷 복구는 11번 구현 계획에서 반드시 다시 다뤄야 한다.
- 현재 `DailyReportBatch` 기본 provider를 실제 KRX provider로 바꾸면 로컬 실행은 네트워크와 FinanceDataReader 상태에 영향을 받는다. 테스트는 반드시 fake provider 주입으로 격리한다.
- 분석 종목이 200개 미만으로 선정되는 비정상 상황은 이번 계획에서 실패로 보지 않기로 확정했다. 운영 알림이나 최소 종목 수 검증이 필요하면 별도 요구로 다룬다.
- 분석 범위 문구는 DB에 저장하지 않고 제품 고정 정책으로 노출하는 전제다. 리비전별 정책 변경 이력을 요구하면 스키마 변경 승인이 필요하다.
