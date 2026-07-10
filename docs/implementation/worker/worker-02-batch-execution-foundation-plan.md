# 워커 배치 실행 기반 구현 계획

상태: 설계 완료 및 구현 전 계획

## 범위

`docs/proposal/stock-report-mvp-issue-breakdown.md`의 2번 항목인 `[worker] Python 배치 실행 기반을 구성한다`를 구현하기 위한 계획이다.

이번 단계는 Python 워커가 하루 1회 장 마감 배치를 실행할 수 있는 실행 경계, 상태 전이, 중복 실행 방지, 종목별 순차 실행, 타임아웃, 공급자 장애 중단, 재시도 오케스트레이션, 최초 게시 상태 전환 경계를 마련한다.

실제 KRX 종목 목록 수집, 종목 선정, 일봉 수집, 지표 계산, 신호 판정, 실제 리포트 리비전 내용 생성, 업종 분석, AI 요약 생성은 후속 이슈에서 구현한다. 이번 단계에서는 후속 작업을 주입 가능한 인터페이스 또는 placeholder 작업 단위로 연결할 수 있게 배치 실행 뼈대를 만들고, 정상 거래일 성공 경로는 `batch_job_run.status = 'PUBLISHED_INITIAL'`까지 전환한다.

## 관련 문서

- 원격 발행 이슈: [GitHub Issue #3 - [Feature] [worker] Python 배치 실행 기반 구성](https://github.com/sehako/stock-report/issues/3)
- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/proposal/python_batch_retry_consistency_design.md`
- `docs/adr/0002-share-database-with-single-schema-owner.md`
- `docs/adr/0005-python-batch-retry-consistency.md`
- `docs/implementation/server/server-data-model-flyway-plan.md`
- `docs/implementation/worker/worker-02-scaffold-plan.md`

## 현재 구조

- `worker/`는 Python 3.12 기반 `src` 레이아웃 스캐폴드만 존재한다.
- `worker/src/stock_report_worker/cli.py`의 `main()`은 import 확인용 무부작용 stub이다.
- `worker/src/stock_report_worker/jobs/daily_report.py`의 `run()`은 placeholder job이다.
- `worker/pyproject.toml`의 런타임 의존성은 비어 있다.
- `server/src/main/resources/db/migration/V1__initial_schema.sql`에는 `batch_job_run`, `batch_stock_run`, `daily_stock_processing_status`가 이미 정의되어 있다.
- Python worker는 Spring Flyway가 생성한 승인된 테이블만 사용하며 스키마 생성이나 변경을 수행하지 않는다.

## 결정 사항

- 실행 방식: worker는 one-shot CLI로 실행한다.
- 스케줄 책임: 19:00 Asia/Seoul 호출은 컨테이너에서 실행되는 `supercronic`이 담당한다.
- worker 책임: CLI 실행 시 Asia/Seoul 기준 `report_date`를 확정하고 해당 거래일 배치를 1회 수행한다.
- 거래일 판정: 이번 단계에서는 `TradingCalendar` 인터페이스를 만들고, 결과는 `OPEN`, `CLOSED`, `UNKNOWN`으로 구분한다.
- 실제 KRX 휴장일 소스: 후속 수집 단계에서 확정한다.
- 비거래일 처리: `TradingCalendar`가 `CLOSED`를 반환하면 실패가 아니라 정상 종료로 처리하고 `batch_job_run.status = 'SKIPPED_MARKET_CLOSED'`를 기록한다.
- 거래일 판정 불가 처리: `TradingCalendar`가 `UNKNOWN`을 반환하면 휴장으로 조용히 스킵하지 않는다. `batch_job_run.status = 'FAILED'`, `last_error`에 거래일 판정 불가를 기록하고 non-zero exit code로 종료한다.
- `DELAYED` 사용 시점: `DELAYED`는 거래일 판정 불가가 아니라 후속 종목 목록 수집 단계에서 종목 목록 자체를 가져오지 못해 **생성 지연**이 필요한 경우에만 사용한다.
- 중복 실행 방지: 같은 `report_date` 배치는 PostgreSQL advisory lock으로 차단한다.
- advisory lock 획득 실패: 이미 실행 중인 배치로 보고 정상 종료한다.
- 실행 상태 저장: `batch_job_run`은 거래일별 1행만 사용한다.
- 종목별 실행 상태 저장: `batch_stock_run`은 `(batch_job_run_id, stock_id)` 1행을 갱신한다.
- 사용자 업무 상태 저장: `daily_stock_processing_status`는 종목별 업무 상태 복구 기준으로 사용하고, `batch_stock_run.status`와 혼동하지 않는다.
- 이번 단계의 사용자 업무 상태 갱신 범위: `daily_stock_processing_status`는 `DATA_PREPARING`, `DATA_UPDATE_FAILED`, `ANALYSIS_FAILED`까지만 갱신한다.
- 성공 업무 상태 유보: 실제 신호 판정과 일봉 검증이 없으므로 `SIGNAL_FOUND`, `NO_SIGNAL`, `INSUFFICIENT_DATA`, `NO_TRADING_TODAY` 전이는 후속 수집·분석 이슈에서 연결한다.
- 순차 처리: 종목별 처리는 병렬 executor 없이 입력 순서대로 처리한다.
- 종목별 트랜잭션: 한 종목의 처리는 짧은 트랜잭션으로 처리하며 한 종목 실패가 이전 성공 종목 커밋을 되돌리지 않는다.
- 요청 제한시간: 종목별 외부 공급자 조회 경계는 30초 제한시간을 둔다.
- 연속 시간 초과: 현재 실행 루프의 메모리 카운터로 관리한다.
- 연속 시간 초과 리셋: 종목 처리 성공 시 0으로 리셋한다.
- 일반 예외: 연속 시간 초과 카운트에 포함하지 않는다.
- 공급자 장애 중단: 5개 종목이 연속으로 시간 초과하면 현재 회차를 중단한다.
- 공급자 장애 중단 후 상태: 시간 초과 종목은 `RETRYABLE`로 저장하고, 아직 호출하지 않은 종목도 `RETRYABLE`로 예약한다.
- 재시도 횟수: 초기 처리 1회와 별도로 재시도 최대 3회를 허용한다. 종목당 총 시도 가능 횟수는 최대 4회다.
- `attempt_count` 의미: 실제 시도 횟수를 저장한다.
- 재시도 예약: `attempt_count < 4`이면 실패 또는 공급자 장애로 미뤄진 종목을 `RETRYABLE`, `next_retry_at = now + 10분`으로 예약한다.
- 미호출 종목 예약: 공급자 장애 중단 때문에 아직 호출하지 않은 종목은 실제 시도하지 않았으므로 `attempt_count`를 증가시키지 않는다.
- `PENDING` 의미: `PENDING`은 즉시 처리 가능한 최초 대기 상태로만 사용하고, 재시도 지연 대상에는 사용하지 않는다.
- 재시도 종료: `attempt_count >= 4`인 실패 종목은 `FAILED_PERMANENT`로 확정한다.
- 재시도 루프: 같은 프로세스가 advisory lock을 유지한 채 10분 간격 재시도 루프를 수행한다.
- 장시간 lock 관측: 재시도 대기 중에는 `batch_job_run.status = 'RETRYING'`을 유지하고 `updated_at`, `batch_stock_run.next_retry_at`으로 멈춤과 대기를 구분한다.
- 종목 목록 입력: 이번 단계에서는 `TargetStockProvider` 인터페이스와 테스트용 fake 또는 in-memory provider만 둔다.
- 실제 종목 목록: FinanceDataReader 기반 KRX 종목 목록 조회와 거래량 상위 200개 선정은 3번과 4번 이슈에서 구현한다.
- timeout 구현: 이번 단계의 기본 timeout 실행기는 `concurrent.futures.ThreadPoolExecutor(max_workers=1)`와 `future.result(timeout=30)` 기반으로 둔다.
- timeout 한계: timeout 발생 시 Python thread가 내부 블로킹 호출을 즉시 강제 종료하지 못할 수 있음을 인정하고, 더 강한 격리는 후속으로 검토한다.
- 스키마 변경: 이번 단계에서 DB 테이블, 컬럼, 제약, 인덱스를 추가하지 않는다.

## 구현 후보 파일

- `worker/pyproject.toml`
- `worker/requirements.txt`
- `worker/requirements-dev.txt`
- `worker/src/stock_report_worker/cli.py`
- `worker/src/stock_report_worker/__main__.py`
- `worker/src/stock_report_worker/config.py`
- `worker/src/stock_report_worker/db.py`
- `worker/src/stock_report_worker/repositories/batch_runs.py`
- `worker/src/stock_report_worker/repositories/processing_status.py`
- `worker/src/stock_report_worker/jobs/daily_report.py`
- `worker/src/stock_report_worker/jobs/trading_calendar.py`
- `worker/src/stock_report_worker/jobs/target_stocks.py`
- `worker/src/stock_report_worker/jobs/stock_runner.py`
- `worker/src/stock_report_worker/jobs/retry_policy.py`
- `worker/src/stock_report_worker/jobs/timeout.py`
- `worker/src/stock_report_worker/jobs/locks.py`
- `worker/src/stock_report_worker/jobs/report_publisher.py`
- `worker/scheduler/supercronic.cron`
- `worker/tests/`

파일명과 모듈 경계는 구현 시 기존 코드 구조에 맞춰 조정할 수 있다. 단, 계획 밖의 서버 스키마 변경은 하지 않는다.

## 구현 절차

1. `worker` 런타임 의존성을 추가한다.
   - `SQLAlchemy Core`
   - `psycopg 3`
   - `pydantic-settings`
   - 시간대 처리를 위한 Python 표준 `zoneinfo` 사용

2. 공개 실행 엔트리포인트를 만든다.
   - `stock-report-worker` console script 또는 `python -m stock_report_worker` 실행 계약을 만든다.
   - 기본 실행은 현재 시각을 Asia/Seoul로 변환해 `report_date`를 결정한다.
   - 테스트와 수동 실행을 위해 `--report-date YYYY-MM-DD` 옵션을 둘 수 있다.
   - 정상 종료와 실패 종료의 exit code 계약을 문서화한다.

3. `supercronic` 스케줄 파일을 만든다.
   - Asia/Seoul 기준 매 거래일 후보일 19:00에 one-shot CLI를 호출한다.
   - 실제 거래일 여부는 worker의 `TradingCalendar`가 최종 판단한다.
   - Dockerfile이나 배포 구성은 이번 단계에서 만들지 않는다.

4. 설정 객체를 만든다.
   - DB URL
   - timezone 기본값 `Asia/Seoul`
   - 종목 요청 timeout 30초
   - 재시도 간격 10분
   - 최대 재시도 3회
   - 연속 timeout 중단 기준 5개

5. DB 연결 경계를 만든다.
   - SQLAlchemy Engine과 transaction helper를 구성한다.
   - Python은 `create_all`이나 스키마 생성 기능을 호출하지 않는다.
   - 필요한 테이블은 Flyway가 만든 이름과 컬럼을 명시적으로 참조한다.

6. advisory lock 경계를 만든다.
   - `report_date` 기준으로 안정적인 advisory lock key를 생성한다.
   - 배치 시작 직후 lock 획득을 시도한다.
   - lock 획득 실패 시 중복 실행으로 보고 정상 종료한다.
   - 프로세스 종료 또는 예외 시 lock이 해제되도록 DB connection 수명주기를 명확히 한다.
   - 재시도 대기 중에도 같은 프로세스가 lock을 유지한다.

7. `batch_job_run` repository를 만든다.
   - 거래일별 row를 생성하거나 기존 row를 조회한다.
   - `report_date` unique 제약과 충돌하지 않게 같은 거래일은 같은 row를 갱신한다.
   - `RUNNING`, `RETRYING`, `FAILED`, `SKIPPED_MARKET_CLOSED`, `PUBLISHED_INITIAL` 상태 전이를 지원한다.
   - 정상 거래일 성공 경로는 최초 게시 경계가 성공한 뒤 `PUBLISHED_INITIAL`로 종료한다.
   - `PUBLISHED_FINAL` 전이는 11번 리포트 게시 이슈에서 최종 연결한다.
   - `DELAYED` 전이는 3번 이후 종목 목록 수집 실패 처리에서 연결한다.

8. 거래일 가드를 구현한다.
   - `TradingCalendar` 인터페이스를 정의한다.
   - `OPEN`, `CLOSED`, `UNKNOWN` 결과를 구분한다.
   - 구현 전 테스트에서는 fake calendar를 사용한다.
   - 비거래일이면 `batch_job_run`을 `SKIPPED_MARKET_CLOSED`로 저장하고 정상 종료한다.
   - 거래일 판정 불가이면 `batch_job_run`을 `FAILED`로 저장하고 non-zero exit code로 종료한다.

9. 종목 실행 오케스트레이터를 만든다.
   - `TargetStockProvider` 인터페이스가 제공한 분석 대상 종목 목록을 입력으로 받는 구조를 만든다.
   - 이번 단계에서는 실제 종목 선정 로직을 구현하지 않는다.
   - 이번 단계의 기본 구현은 테스트용 fake 또는 in-memory provider로 제한한다.
   - 종목 목록이 주어지면 `batch_stock_run`을 `PENDING`으로 초기화하거나 기존 상태를 복구한다.
   - `PENDING` 또는 재시도 가능 시간이 지난 `RETRYABLE`만 처리 대상으로 삼는다.
   - `PENDING`은 즉시 처리 가능한 최초 대기 상태이며, `next_retry_at`이 미래인 지연 대상은 `RETRYABLE`로만 표현한다.

10. 종목별 순차 실행기를 만든다.
   - 병렬 처리 없이 for-loop로 한 종목씩 처리한다.
   - 종목 처리 시작 시 `RUNNING`, 성공 시 `SUCCEEDED`로 갱신한다.
   - 실패 시 오류 종류와 시도 횟수에 따라 `RETRYABLE` 또는 `FAILED_PERMANENT`로 갱신한다.
   - 종목 처리 시작 또는 재시도 예약 시 `daily_stock_processing_status.analysis_status = 'DATA_PREPARING'`으로 갱신한다.
   - 재시도 소진 또는 복구 불가 데이터 갱신 실패는 `DATA_UPDATE_FAILED`로 갱신한다.
   - 데이터 수집이 아니라 placeholder 분석 callable 자체의 복구 불가 실패는 `ANALYSIS_FAILED`로 갱신한다.
   - 성공 종목의 `SIGNAL_FOUND`, `NO_SIGNAL`, `INSUFFICIENT_DATA`, `NO_TRADING_TODAY` 전이는 이번 단계에서 만들지 않는다.
   - 후속 수집·계산 작업은 주입 가능한 callable로 둔다.

11. 종목별 timeout wrapper를 만든다.
   - 외부 공급자 조회 경계에 30초 제한시간을 적용한다.
   - 기본 구현은 `ThreadPoolExecutor(max_workers=1)`로 callable을 별도 thread에서 실행하고 `future.result(timeout=30)`으로 기다린다.
   - timeout은 별도 예외 타입으로 분류한다.
   - timeout 발생 시 `attempt_count`를 증가시키고 재시도 가능하면 `RETRYABLE`로 저장한다.
   - timeout 이후 내부 thread가 즉시 종료되지 않을 수 있으므로, timeout은 배치 상태 전이 기준으로만 사용한다.

12. 연속 timeout 중단 정책을 구현한다.
   - 현재 실행 루프에서 timeout이 연속 5개 발생하면 공급자 장애로 판단한다.
   - 현재 회차의 추가 종목 처리를 중단한다.
   - 이미 성공한 종목은 유지한다.
   - 아직 호출하지 않은 종목은 `attempt_count`를 증가시키지 않고 `RETRYABLE`, `next_retry_at = now + 10분`으로 예약한다.
   - 공급자 장애로 지연된 종목의 `daily_stock_processing_status.analysis_status`는 `DATA_PREPARING`으로 둔다.
   - job 상태는 재시도 대상이 남아 있으면 `RETRYING`으로 둔다.

13. 재시도 루프를 구현한다.
   - 실패 또는 공급자 장애로 미뤄진 종목은 10분 간격으로 최대 3회 재시도한다.
   - 같은 프로세스가 advisory lock을 유지한다.
   - 재시도 대기 중 `batch_job_run.status = 'RETRYING'`과 대상 종목의 `next_retry_at`을 기록한다.
   - `next_retry_at` 이전에는 대기한다.
   - 재시도 가능 대상이 없거나 모든 대상이 최종 실패 또는 성공 상태가 되면 루프를 종료한다.

14. 종료 상태를 정리한다.
   - 모든 종목이 성공하거나 최종 실패로 확정되면 `InitialReportPublisher` 같은 주입 가능한 최초 게시 경계를 호출한다.
   - 이번 단계의 기본 최초 게시 구현은 실제 분석 결과 리비전 내용을 만들지 않는 placeholder로 제한한다.
   - 최초 게시 경계가 성공하면 `batch_job_run.status = 'PUBLISHED_INITIAL'`로 기록한다.
   - `PUBLISHED_FINAL` 상태 전환은 리포트 게시 정책 구현에서 연결한다.
   - 예기치 못한 전체 오류는 `batch_job_run.status = 'FAILED'`와 `last_error`로 기록한다.

15. README를 갱신한다.
   - 실행 명령
   - 필요한 환경 변수
   - 19:00 Asia/Seoul 스케줄링은 `supercronic` 책임이라는 점
   - 재시도와 중복 실행 정책

## 상태 전이 기준

### `batch_job_run`

- 비거래일: `RUNNING` 또는 생성 직후 상태에서 `SKIPPED_MARKET_CLOSED`
- 거래일 판정 불가: `FAILED`
- 실행 중: `RUNNING`
- 재시도 대기 또는 수행 중: `RETRYING`
- 전체 실행 불가 오류: `FAILED`
- 최초 게시 경계 완료: `PUBLISHED_INITIAL`, 이번 단계의 정상 거래일 terminal 상태
- 최종 리비전 공개 완료: `PUBLISHED_FINAL`, 후속 이슈에서 사용
- 종목 목록 자체를 가져오지 못한 생성 지연: `DELAYED`, 후속 종목 목록 수집 이슈에서 사용

### `batch_stock_run`

- 처리 전: `PENDING`
- 처리 중: `RUNNING`
- 처리 성공: `SUCCEEDED`
- 재시도 가능 실패: `RETRYABLE`
- 재시도 소진 또는 복구 불가 실패: `FAILED_PERMANENT`

### `daily_stock_processing_status`

- 처리 시작 또는 재시도 대기: `DATA_PREPARING`
- 재시도 소진 또는 복구 불가 데이터 갱신 실패: `DATA_UPDATE_FAILED`
- placeholder 분석 callable의 복구 불가 실패: `ANALYSIS_FAILED`
- `SIGNAL_FOUND`, `NO_SIGNAL`, `INSUFFICIENT_DATA`, `NO_TRADING_TODAY`는 실제 수집·분석 이슈에서 연결한다.

## 제외 범위

- KRX 종목 목록 실제 수집
- FinanceDataReader 의존성 도입과 실제 호출
- 실제 KRX 휴장일 데이터 소스 확정
- 분석 대상 200개 선정
- 일봉 가격 수집
- 시장 지수 수집
- MACD, Stoch MACD, 이동평균 계산
- 골든크로스 신호 판정
- 실제 리포트 리비전 내용 생성과 최종 리비전 게시
- 업종 분석 생성
- AI 시장 요약 생성
- 서버 Flyway 마이그레이션 변경
- DB 테이블, 컬럼, 인덱스, 제약 추가
- Dockerfile, docker-compose, 운영 배포 파일 작성
- APScheduler 같은 worker 내부 long-running scheduler 도입

## 검증 계획

- CLI import와 실행 계약을 단위 테스트로 검증한다.
- Asia/Seoul 기준 `report_date` 결정 테스트를 추가한다.
- fake calendar가 비거래일을 반환하면 정상 종료되고 `SKIPPED_MARKET_CLOSED`가 기록되는지 검증한다.
- fake calendar가 거래일 판정 불가를 반환하면 `FAILED`가 기록되고 non-zero exit code가 반환되는지 검증한다.
- advisory lock 획득 실패 시 중복 실행으로 보고 정상 종료하는지 검증한다.
- 같은 거래일 실행이 `batch_job_run(report_date)` unique 제약과 충돌하지 않고 기존 row를 갱신하는지 검증한다.
- fake `TargetStockProvider`가 제공한 종목 목록만 처리 대상이 되는지 검증한다.
- 종목 처리 callable이 입력 순서대로 호출되는지 검증한다.
- timeout wrapper가 30초 초과 callable을 `StockFetchTimeout`으로 분류하는지 검증한다.
- 실제 종목 실행 오케스트레이터가 timeout wrapper를 통과해 `StockFetchTimeout`을 받는 통합 경로를 검증한다.
- 종목별 timeout 발생 시 `RETRYABLE`, `attempt_count` 증가, `next_retry_at = now + 10분`이 기록되는지 검증한다.
- 종목 처리 시작 또는 재시도 예약 시 `daily_stock_processing_status`가 `DATA_PREPARING`으로 갱신되는지 검증한다.
- 재시도 소진 또는 복구 불가 실패 시 `daily_stock_processing_status`가 `DATA_UPDATE_FAILED` 또는 `ANALYSIS_FAILED`로 갱신되는지 검증한다.
- 성공 종목 발생 후 연속 timeout 카운터가 0으로 리셋되는지 검증한다.
- 일반 예외가 연속 timeout 카운터에 포함되지 않는지 검증한다.
- timeout 5개 연속 발생 시 이후 종목 처리가 중단되고 미호출 종목이 `attempt_count` 증가 없이 `RETRYABLE`, `next_retry_at = now + 10분`으로 예약되는지 검증한다.
- 초기 1회 실패 뒤 최대 3회 재시도까지만 수행하고 총 4회 이후 `FAILED_PERMANENT`가 되는지 검증한다.
- 프로세스 재시작 시 `PENDING`과 재시도 가능 시간이 지난 `RETRYABLE`만 다시 처리 대상이 되는지 검증한다.
- 종목 단위 실패가 이전 성공 종목의 커밋을 되돌리지 않는지 검증한다.
- 앞 종목이 `SUCCEEDED`로 커밋된 뒤 뒤 종목이 `FAILED_PERMANENT` 또는 `RETRYABLE`이 되어도 앞 종목의 `batch_stock_run.status = 'SUCCEEDED'`가 유지되는지 검증한다.
- PostgreSQL에서 실제 `pg_try_advisory_lock` 기반 중복 실행 차단을 검증한다.
- PostgreSQL에서 재시도 대기 중 같은 connection이 advisory lock을 유지하는지 검증한다.
- Spring Flyway가 생성한 실제 스키마에서 `batch_job_run`, `batch_stock_run`, `daily_stock_processing_status` insert/update가 복합 FK와 check constraint를 위반하지 않는지 검증한다.
- 정상 거래일 성공 경로가 주입된 최초 게시 경계를 호출하고, 게시 경계 성공 후 `PUBLISHED_INITIAL`로 종료되는지 검증한다.

## 위험 요소

- 실제 KRX 휴장일 판정 소스를 이번 단계에서 확정하지 않기 때문에, 후속 수집 단계에서 공급자 장애와 휴장일을 구분하는 규칙을 반드시 확정해야 한다.
- `UNKNOWN`을 `FAILED`로 처리하므로 캘린더 소스 장애가 있으면 당일 배치가 실패한다. 이는 공급자 장애를 휴장으로 오판하는 것보다 낫다는 판단이다.
- 19:00 실행은 `supercronic` 책임이므로, worker 코드와 스케줄 파일만으로는 Dockerfile과 운영 배포 구성이 완성되지 않는다.
- `batch_job_run.report_date`가 unique이므로 재시도나 수동 재실행을 새 row 생성 모델로 구현하면 안 된다.
- `batch_stock_run`도 `(batch_job_run_id, stock_id)`가 unique이므로 종목 재시도는 같은 row 갱신으로 구현해야 한다.
- `batch_stock_run`의 `attempt_count` 최대값은 DB 제약으로 강제되지 않으므로 worker 테스트가 off-by-one 오류를 잡아야 한다.
- 공급자 장애로 미호출 종목을 `RETRYABLE`로 예약할 때 `attempt_count`를 증가시키면 실제 시도 횟수 의미가 깨진다.
- 이번 단계는 성공 업무 상태를 만들지 않으므로, placeholder 성공을 `SIGNAL_FOUND`나 `NO_SIGNAL`로 저장하면 안 된다.
- 연속 timeout 카운터는 영속 저장하지 않으므로 프로세스 재시작 후에는 새 실행 루프 기준으로 다시 계산된다.
- 같은 프로세스가 재시도 대기 동안 advisory lock을 유지하므로 최장 실행 시간이 30분 이상이 될 수 있다.
- `ThreadPoolExecutor` 기반 timeout은 내부 블로킹 호출을 강제로 중단하지 못할 수 있어, 실제 FinanceDataReader 연동 후 thread 누수나 장기 블로킹 여부를 별도 검증해야 한다.
- `ThreadPoolExecutor` 기반 timeout은 timeout 이후 worker 상태 전이 기준으로만 실패를 확정한다. 이미 실행 중인 내부 thread가 계속 실행될 수 있으므로, "종목별 순차 처리"는 상태 전이와 오케스트레이터 호출 순서 기준으로 정의한다. 실제 외부 공급자 호출 자체가 절대 겹치면 안 되는 요구가 생기면 thread 방식 대신 process 격리나 공급자별 native timeout으로 변경해야 한다.
- timeout wrapper 단위 테스트만으로는 배치 오케스트레이터가 실제 timeout wrapper 경로를 사용하는지 보장하지 못한다. 연속 timeout, 재시도 예약, 재시도 소진 테스트 중 최소 하나는 fake exception 직접 발생이 아니라 timeout wrapper 통합 경로를 통해 검증해야 한다.
- SQLAlchemy Core 상수 문자열이 Flyway check constraint와 다르면 런타임 DB 오류가 발생한다.
- 복합 FK가 있는 테이블은 `id`와 `report_date`를 항상 일관되게 기록해야 한다.
- SQLite 기반 테스트는 PostgreSQL advisory lock, Flyway check constraint, 복합 FK 동작을 완전히 재현하지 못한다. 원격 이슈 완료 판정 전 PostgreSQL/Flyway 기반 통합 검증을 별도로 수행해야 한다.

## 구현 완료 기준

- worker에 one-shot CLI 실행 계약이 존재한다.
- `report_date`는 Asia/Seoul 기준으로 결정된다.
- 비거래일은 실패가 아니라 `SKIPPED_MARKET_CLOSED` 정상 종료로 처리된다.
- 거래일 판정 불가는 휴장으로 처리하지 않고 `FAILED`와 non-zero exit code로 처리된다.
- 19:00 Asia/Seoul 실행을 위한 `supercronic` 스케줄 파일이 존재한다.
- 같은 거래일 동시 실행은 advisory lock으로 하나만 진행된다.
- 테스트용 `TargetStockProvider`를 통해 실제 FDR 수집 없이 종목 실행 흐름을 검증할 수 있다.
- 종목 처리는 순차 처리된다.
- 종목별 외부 공급자 조회 경계에 30초 timeout 정책이 적용된다.
- 5개 종목 연속 timeout 시 현재 회차가 중단된다.
- 실패 또는 공급자 장애로 미뤄진 종목은 10분 간격으로 최대 3회 재시도된다.
- 재시도는 초기 처리 1회와 별도로 계산되어 종목당 최대 총 4회까지만 시도된다.
- 공급자 장애로 아직 호출하지 않은 종목은 `attempt_count` 증가 없이 `RETRYABLE`로 예약된다.
- `daily_stock_processing_status`는 이번 단계에서 `DATA_PREPARING`, `DATA_UPDATE_FAILED`, `ANALYSIS_FAILED` 범위로 갱신된다.
- 정상 거래일 성공 경로는 `PUBLISHED_INITIAL`로 종료된다.
- Python worker는 Flyway가 생성한 기존 테이블만 사용한다.
- worker README에 실행 명령, 필요한 환경 변수, 19:00 Asia/Seoul 스케줄링 책임, 재시도와 중복 실행 정책이 기록된다.
- timeout, 연속 timeout 중단, 재시도 예약, 재시도 소진 정책은 테스트로 검증된다.
- 종목 단위 실패가 이전 성공 종목의 커밋을 되돌리지 않는지 테스트로 검증된다.
- PostgreSQL advisory lock 기반 중복 실행 차단은 실제 PostgreSQL 경계에서 검증된다.
- Flyway가 생성한 실제 스키마 위에서 worker repository의 상태 전이가 check constraint와 복합 FK를 만족하는지 검증된다.

## 현재 구현 검토 후 보완 필요 사항

2026-07-08 현재 구현 검토에서 원격 이슈 `#3`의 완료 기준 대비 다음 보완이 필요하다고 판단했다.

1. timeout 순차성 해석을 명확히 한다.
   - 현재 계획의 기본 timeout 방식은 `ThreadPoolExecutor(max_workers=1)`와 `future.result(timeout=30)`이다.
   - 이 방식은 timeout 이후 실행 중인 thread를 강제 종료하지 못할 수 있다.
   - 따라서 이번 단계의 순차 처리 완료 기준은 "배치 오케스트레이터가 한 종목의 상태 전이를 확정한 뒤 다음 종목 상태 전이를 시작한다"로 해석한다.
   - 실제 외부 공급자 호출이 물리적으로 겹치면 안 되는 요구는 이번 단계의 `ThreadPoolExecutor` 선택과 충돌하므로, 별도 후속 결정 없이는 완료 기준으로 삼지 않는다.

2. timeout 통합 테스트를 보강한다.
   - timeout wrapper 단위 테스트와 fake `StockFetchTimeout` 직접 발생 테스트만으로는 충분하지 않다.
   - 종목 실행 오케스트레이터가 실제 `TimeoutRunner`를 통해 느린 callable을 `StockFetchTimeout`으로 분류하고 `RETRYABLE` 또는 `FAILED_PERMANENT` 상태 전이를 수행하는 경로를 검증한다.

3. 성공 커밋 보존 테스트를 추가한다.
   - 앞 종목 성공 후 뒤 종목이 재시도 가능 실패 또는 최종 실패가 되는 시나리오를 추가한다.
   - 검증 대상은 앞 종목의 `batch_stock_run.status = 'SUCCEEDED'`와 뒤 종목의 실패 상태가 같은 배치 안에서 함께 유지되는지다.

4. PostgreSQL/Flyway 통합 검증을 추가한다.
   - advisory lock 중복 실행 차단은 `NoopBatchLock`이 아니라 실제 `pg_try_advisory_lock`으로 검증한다.
   - repository는 SQLite `metadata.create_all()`이 아니라 Spring Flyway가 만든 실제 테이블에서 검증한다.
   - 특히 `batch_stock_run(batch_job_run_id, report_date)`와 `daily_stock_processing_status(last_batch_job_run_id, report_date)`의 복합 FK, 각 status check constraint를 확인한다.
