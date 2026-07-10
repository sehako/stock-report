# 주식 리포트 워커

Stock Reports Lab의 장 마감 리포트 생성을 one-shot으로 실행하는 Python 워커이다.

## 로컬 환경

이 프로젝트는 Python 3.12 계열과 표준 `venv` 및 `pip`를 사용한다. 의존성은 저장소 루트가 아니라 `worker/.venv`에 격리한다.

```bash
cd worker
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

기존 `worker/.venv`가 이전 방식으로 생성된 환경이면 `pip` 실행 파일이 없을 수 있다. 이 경우 기존 `.venv`를 삭제하고 표준 `venv`로 다시 생성해야 한다.

## 실행

워커는 내부 스케줄러를 띄우지 않고 1회 실행 후 종료한다.

```bash
cd worker
source .venv/bin/activate
WORKER_DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/stock_report' stock-report-worker
```

수동 검증이나 재처리는 기준일을 명시한다.

```bash
stock-report-worker --report-date 2026-07-09
python -m stock_report_worker --report-date 2026-07-09
```

`--report-date`가 없으면 현재 시각을 `WORKER_TIMEZONE`으로 변환해 `report_date`를 결정한다. 기본 시간대는 `Asia/Seoul`이다.

종료 코드는 다음 계약을 따른다.

- `0`: 정상 종료, 비거래일 스킵, 또는 advisory lock 중복 실행 스킵
- `1`: 거래일 판정 불가 또는 배치 전체 실행 불가 오류

## 환경 변수

- `WORKER_DATABASE_URL`: SQLAlchemy DB URL
- `WORKER_TIMEZONE`: 기준 시간대, 기본값 `Asia/Seoul`
- `WORKER_STOCK_TIMEOUT_SECONDS`: 종목별 외부 공급자 조회 제한시간, 기본값 `30`
- `WORKER_RETRY_INTERVAL_SECONDS`: 재시도 간격, 기본값 `600`
- `WORKER_MAX_RETRIES`: 최초 1회 이후 허용 재시도 횟수, 기본값 `3`
- `WORKER_CONSECUTIVE_TIMEOUT_LIMIT`: 공급자 장애로 중단할 연속 timeout 수, 기본값 `5`

## 스케줄링

19:00 Asia/Seoul 실행은 worker가 아니라 `supercronic` 책임이다. 스케줄 파일은 `scheduler/supercronic.cron`에 있다. 실제 거래일 여부는 실행된 worker의 `TradingCalendar`가 최종 판단한다.

## 중복 실행과 재시도 정책

같은 `report_date` 배치는 PostgreSQL advisory lock으로 하나만 진행한다. lock 획득에 실패하면 이미 실행 중인 배치로 보고 정상 종료한다.

종목 처리는 입력 순서대로 한 종목씩 상태 전이를 확정한다. 종목별 외부 공급자 경계에는 timeout을 적용하고, 실패 또는 공급자 장애로 미뤄진 종목은 `RETRYABLE`과 `next_retry_at`으로 예약한다. 최초 처리 1회와 별도로 최대 3회 재시도하여 종목당 최대 총 4회까지만 시도한다.

5개 종목이 연속으로 timeout되면 현재 회차를 중단하고 아직 호출하지 않은 종목을 `attempt_count` 증가 없이 재시도 대상으로 예약한다. 종목별 업무 상태는 이번 단계에서 `DATA_PREPARING`, `DATA_UPDATE_FAILED`, `ANALYSIS_FAILED`만 갱신한다.

## KRX 종목 목록 수집 경계

`KrxStockListingProvider`는 FinanceDataReader `StockListing("KRX")`와 `StockListing("KRX-DESC")`를 조회해 현재 종목 메타데이터를 `stock.stock_code` 기준으로 upsert한다. 반환값에는 후속 분석 대상 선정 로직이 사용할 `stock.id`, KRX listing 종가 원천값, KRX listing 거래량 원천값이 포함된다.

KRX listing 종가와 거래량은 이 경계에서 영속화하지 않는다. 운영 배치 흐름에서 종가 1,000원 이상, 거래량 상위 200개 분석 종목을 선정하고 `batch_stock_run`으로 연결하는 작업은 후속 이슈에서 수행한다.

FinanceDataReader 조회 실패, 원천 필수 컬럼 누락, 필수값 정규화 실패, stock upsert 실패는 `KrxStockListingUnavailable` 예외로 분류한다. 실제 `batch_job_run.status = 'DELAYED'` 전이 연결은 후속 분석 대상 선정 이슈에서 수행한다.

## 테스트

```bash
cd worker
source .venv/bin/activate
pytest
```

PostgreSQL advisory lock 경계 검증은 실제 PostgreSQL URL이 있을 때만 실행한다.

```bash
cd worker
source .venv/bin/activate
WORKER_POSTGRES_TEST_URL='postgresql+psycopg://user:password@localhost:5432/test_db' pytest
```

## 후속 단계 제약

- Python 워커는 Spring Flyway가 생성한 승인된 테이블만 사용한다.
- Python 워커는 운영 코드에서 스키마 생성이나 변경을 수행하지 않는다.
- 일봉 수집, 기술지표 계산, 신호 판정, 실제 리포트 리비전 내용 생성은 후속 이슈에서 연결한다.
