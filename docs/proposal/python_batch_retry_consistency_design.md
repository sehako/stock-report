# Python 배치 재시도 정합성 설계

## 1. 목적

이 문서는 Stock Reports Lab의 Python 배치가 작업 실패 이후 동일 작업을 재시도해도 중복 데이터와 부분 공개 문제 없이 장 마감 리포트를 생성하기 위한 설계를 정의한다.

Python 배치는 FinanceDataReader 기반 데이터 수집, 기술지표 계산, 신호 판정, 시장·업종 집계 및 리포트 결과 적재를 담당한다. Spring은 조회 API와 사용자 기능을 담당하며, 데이터베이스 스키마 변경은 Spring Flyway만 수행한다.

## 2. 기본 기술 스택

- 런타임: Python 3.12
- 패키지 관리: uv
- 데이터 수집: FinanceDataReader
- 데이터 처리: pandas, numpy
- DB 접근: psycopg 3, SQLAlchemy Core
- 설정: pydantic-settings
- 테스트: pytest
- 스케줄링: 컨테이너 내부 cron 또는 supercronic
- 데이터베이스: PostgreSQL

기존 `stock/`의 Python 코드는 FinanceDataReader, pandas, pandas_ta_classic 기반 프로토타입으로 참고한다. 운영 배치에서는 CSV append 저장 방식을 사용하지 않고 PostgreSQL upsert와 리비전 모델로 전환한다.

## 3. 정합성 원칙

### 3.1 중복 데이터 방지

동일 작업을 여러 번 실행해도 같은 의미의 데이터가 여러 행으로 생성되지 않도록 모든 주요 데이터에 고유키를 둔다.

| 데이터 | 권장 고유키 | 재시도 동작 |
|---|---|---|
| 원본 일봉 | `(stock_code, trade_date)` | `ON CONFLICT DO UPDATE` |
| 기술지표 | `(stock_code, trade_date, calculation_version)` | `ON CONFLICT DO UPDATE` |
| 신호 | `(stock_code, signal_type, signal_date, calculation_version)` | `ON CONFLICT DO NOTHING` 또는 `DO UPDATE` |
| 종목 처리 상태 | `(report_date, stock_code)` | `ON CONFLICT DO UPDATE` |
| 배치 종목 실행 | `(run_id, stock_code)` | `ON CONFLICT DO UPDATE` |

원본 일봉은 동일 날짜 재수집 시 새 행을 만들지 않고 갱신한다. 신호는 같은 계산 버전에서 동일 신호가 반복 저장되지 않도록 한다.

### 3.2 종목 단위 트랜잭션

전체 200개 종목을 하나의 트랜잭션으로 처리하지 않는다. 한 종목을 독립 단위로 처리하고 커밋한다.

```text
종목 1건 처리 시작
  ├─ FDR 일봉 조회
  ├─ 원본 일봉 upsert
  ├─ 기술지표 계산 및 upsert
  ├─ 신호 판정 및 upsert
  ├─ 종목 처리 상태 갱신
  └─ commit
```

종목 처리 중 실패하면 해당 종목 트랜잭션만 rollback하고, `batch_stock_run`에 실패 상태와 재시도 정보를 기록한다. 다른 종목 처리는 계속 진행한다.

### 3.3 리비전 공개 원자성

사용자에게 노출되는 리포트는 거래일별 활성 리비전 하나만 허용한다.

리비전 공개는 다음 작업을 하나의 트랜잭션으로 처리한다.

```text
리비전 공개 시작
  ├─ 새 report_revision 생성 또는 draft 리비전 확정
  ├─ 종목 분석 결과 연결
  ├─ 시장·업종 집계 결과 연결
  ├─ 기존 active 리비전 비활성화
  ├─ 새 리비전 active 처리
  └─ commit
```

중간 단계에서 실패하면 새 리비전은 활성화하지 않는다. Spring API는 항상 최종 활성 리비전만 조회한다.

### 3.4 중복 실행 방지

컨테이너 내부 cron 또는 supercronic은 실행 시각만 관리한다. 같은 거래일 배치가 동시에 실행되는 것을 막기 위해 Python 배치는 시작 시 PostgreSQL advisory lock을 획득한다.

```text
배치 시작
  ├─ 거래일 기준 advisory lock 획득 시도
  ├─ 실패하면 이미 실행 중으로 보고 정상 종료
  └─ 성공하면 배치 진행
```

락은 거래일을 기준으로 잡아 같은 날짜의 중복 배치를 차단한다. 수동 재실행도 같은 경로를 사용한다.

## 4. 실행 상태 모델

Spring Batch의 JobRepository에 해당하는 실행 메타데이터를 Python 배치용 테이블로 관리한다.

### 4.1 batch_job_run

거래일별 배치 실행 단위를 기록한다.

| 컬럼 | 의미 |
|---|---|
| `run_id` | 배치 실행 식별자 |
| `report_date` | 대상 거래일 |
| `status` | `RUNNING`, `PUBLISHED_INITIAL`, `RETRYING`, `PUBLISHED_FINAL`, `FAILED`, `SKIPPED_MARKET_CLOSED` |
| `started_at` | 시작 시각 |
| `finished_at` | 종료 시각 |
| `last_error` | 전체 실행 오류 |

### 4.2 batch_stock_run

종목별 처리와 재시도 상태를 기록한다.

| 컬럼 | 의미 |
|---|---|
| `run_id` | 배치 실행 식별자 |
| `report_date` | 대상 거래일 |
| `stock_code` | 종목 코드 |
| `status` | `PENDING`, `RUNNING`, `SUCCEEDED`, `RETRYABLE`, `FAILED_PERMANENT` |
| `attempt_count` | 시도 횟수 |
| `next_retry_at` | 다음 재시도 가능 시각 |
| `last_error` | 마지막 오류 |
| `started_at` | 종목 처리 시작 시각 |
| `finished_at` | 종목 처리 종료 시각 |

재실행 시 Python 배치는 `PENDING` 또는 `RETRYABLE` 상태인 종목만 다시 처리한다.

## 5. 재시도 흐름

```text
19:00 배치 시작
  ├─ advisory lock 획득
  ├─ KRX 거래일 확인
  ├─ batch_job_run 생성
  ├─ 분석 대상 200개 선정
  ├─ batch_stock_run 초기화
  ├─ 종목별 순차 처리
  ├─ 성공 종목 기준 최초 리비전 공개
  ├─ 실패 종목만 최대 3회 재시도
  ├─ 변경분이 있으면 최종 리비전 공개
  ├─ AI 시장 요약 비동기 생성
  └─ advisory lock 해제
```

프로세스가 중간에 종료되면 다음 실행에서 실행 상태 테이블을 읽어 미완료 종목과 재시도 가능 종목을 복구한다.

## 6. 실패 처리 규칙

| 실패 상황 | 처리 |
|---|---|
| 한 종목 FDR 조회 실패 | 해당 종목 `RETRYABLE`, 다른 종목 계속 처리 |
| 한 종목 지표 계산 실패 | 해당 종목 `FAILED_PERMANENT` 또는 `RETRYABLE`, 오류 저장 |
| 5개 종목 연속 타임아웃 | 공급자 장애로 보고 현재 회차 중단 |
| 종목 목록 조회 실패 | 당일 리포트 생성 지연, 직전 활성 리포트 유지 |
| 최초 리비전 공개 실패 | 새 리비전 비활성 상태 유지, 직전 활성 리포트 유지 |
| 최종 리비전 공개 실패 | 최초 리비전 유지, 최종 리비전은 재시도 대상 |
| AI 요약 실패 | 금융 데이터 리비전과 독립적으로 AI 상태만 갱신 |

## 7. 테스트 기준

다음 검증을 자동화한다.

- 같은 종목 가격 데이터를 두 번 upsert해도 `(stock_code, trade_date)` 행이 하나만 유지된다.
- 같은 계산 버전의 신호를 두 번 저장해도 중복 신호가 생기지 않는다.
- 종목 처리 중 예외가 발생하면 해당 종목만 실패 상태가 되고 다른 종목 처리는 계속된다.
- 중간 종료 후 재실행 시 `PENDING`, `RETRYABLE` 종목만 다시 처리된다.
- 같은 거래일 배치를 동시에 시작하면 하나만 advisory lock을 획득한다.
- 리비전 공개 중 실패하면 기존 active 리비전이 유지된다.
- 리비전 공개 성공 후 거래일별 active 리비전은 하나만 존재한다.

## 8. 남은 설계 과제

- 실제 Flyway 마이그레이션에서 테이블명, 컬럼명, enum 값, unique index를 확정해야 한다.
- Python worker가 사용할 DB 계정 권한을 금융 원천 및 분석 결과 테이블로 제한해야 한다.
- 기존 `pandas_ta_classic` 계산 결과와 운영용 직접 구현 결과가 일치하는지 골든 데이터셋으로 검증해야 한다.
- cron과 supercronic 중 최종 스케줄러를 선택하고 컨테이너 로그 수집 방식을 결정해야 한다.
