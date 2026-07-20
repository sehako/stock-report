# ExecPlan: 코스피 코스닥 지수 일봉 적재 배치 구현

이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다. 이 문서는 `docs/issues/04-batch-market-index-daily-price-loading.md`의 구현 계획이며, 저장소를 처음 보는 사람도 이 파일만 읽고 작업을 이어갈 수 있도록 필요한 맥락과 결정을 포함한다.

## 목적과 큰 그림

이 계획은 Python 배치가 코스피와 코스닥 지수의 일봉 가격 데이터를 수집해 `market_index_price` 테이블에 저장하게 만드는 실행 계획이다. 구현 전에는 백엔드 API가 `market_index_price`를 읽을 수 있어도 이 테이블을 자동으로 채우는 배치 작업이 없다. 구현 후 사용자는 `app/batch`에서 기본 배치를 실행해 종목 universe, tracked 종목 일봉, 시장 지수 일봉을 차례로 갱신할 수 있고, 배치를 두 번 이상 반복 실행해도 `market_index_price.index_code`, `market_index_price.trade_date` 조합의 중복 row가 생기지 않는지 데이터베이스에서 확인할 수 있다.

이 계획에서 "지수"는 코스피와 코스닥처럼 시장 전체의 움직임을 대표하는 숫자다. "일봉"은 하루 단위의 시가, 고가, 저가, 종가, 거래량, 등락률 데이터다. "upsert"는 같은 고유 키의 row가 없으면 새로 넣고, 이미 있으면 값을 갱신하는 저장 방식이다. 이 이슈의 고유 키는 `index_code`와 `trade_date`다.

이 이슈는 지수 일봉 적재만 다룬다. 종목 메타데이터 갱신, 종목 일봉 가격 수집, 특정 지수나 기간을 지정하는 재수집 옵션, Spring Boot 조회 API 구현은 이미 다른 이슈의 범위이거나 후속 이슈의 범위이므로 이 계획에 섞지 않는다.

## 진행 상황

- [x] (2026-07-20) 이슈 본문, MVP 설계 문서, 배치 아키텍처 문서, ExecPlan 지침을 확인했다.
- [x] (2026-07-20) 현재 Python 배치 구조와 이슈 03의 `stock_daily_price` 구현, 테스트, DB 저장소 패턴을 조사했다.
- [x] (2026-07-20) `market_index_price` 스키마와 백엔드 `marketindex` 조회 코드를 확인해 저장 컬럼과 내부 지수 코드 계약을 확정했다.
- [x] (2026-07-20) FDR 공식 문서에서 국내 지수 심볼 `KS11`, `KQ11`을 확인했다.
- [x] (2026-07-20) 구현 위치, 데이터 흐름, 검증 방법을 현재 저장소 상태 기준으로 계획했다.
- [ ] 실패하는 테스트 작성
- [ ] 최소 구현
- [ ] 리팩터링
- [ ] 전체 테스트 및 빌드 검증
- [ ] 관련 문서 갱신
- [ ] 결과와 회고 작성
- [ ] ExecPlan 최종 상태 확인

## 예상 밖의 발견

- 관찰: 현재 `app/batch/src/batch/main.py`는 이미 이슈 03 구현을 반영해 `stock_universe` 성공 뒤 `stock_daily_price`를 실행한다.
  증거: `main()`은 `StockUniverseRunner.run()`을 호출하고 digest 불일치 시 예외를 던진 뒤 `StockDailyPriceRunner.run()`을 호출한다.
  계획에 미친 영향: 이슈 04 구현은 기본 실행 흐름의 세 번째 단계로 `market_index_daily_price` runner를 추가하는 조합 변경이 필요하다. 기존 두 작업의 내부 로직은 수정하지 않는다.

- 관찰: `market_index_price`는 내부 기본키가 있지만 배치 저장 기준은 `index_code`, `trade_date`다.
  증거: `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`은 `uk_market_index_price_index_trade_date UNIQUE (index_code, trade_date)`와 `chk_market_index_price_index_code CHECK (index_code IN ('KOSPI', 'KOSDAQ'))`를 정의한다.
  계획에 미친 영향: 지수 저장소는 stock id 같은 별도 참조키를 조회하지 않고, 내부 지수 코드 문자열과 거래일만으로 마지막 적재일 조회와 upsert를 수행한다.

- 관찰: 백엔드 지수 최신 수치 API는 `market_index_price.change_rate`를 FinanceDataReader의 `Change` 원값으로 보고 API에서 100을 곱한다.
  증거: `docs/plans/backend/issue-06-backend-market-index-summary-api.md`와 `MarketIndexService` 테스트 계획은 `changeRatePercent = change_rate * 100` 계약을 설명한다.
  계획에 미친 영향: 배치는 지수 `Change` 값을 직접 퍼센트로 변환하지 않고 원값 그대로 `change_rate`에 저장한다. 값이 없거나 변환할 수 없으면 DB 컬럼이 nullable이므로 `NULL` 저장을 허용한다.

- 관찰: FDR 공식 문서는 국내 지수 심볼로 `KS11`과 `KQ11`을 제시하지만, 2026년 2월에 해당 지수 조회에서 `LOGOUT` 오류가 보고된 공개 이슈도 있다.
  증거: FinanceDataReader README와 Quick Start는 `KS11`을 코스피 지수, `KQ11`을 코스닥 지수로 설명한다. GitHub issue #267은 `fdr.DataReader('KS11')`, `fdr.DataReader('KQ11')` 호출 오류 사례를 보고한다.
  계획에 미친 영향: 내부 매핑은 `KOSPI -> KS11`, `KOSDAQ -> KQ11`로 두되, 실제 네트워크 검증은 수동 통합 검증으로 분리한다. 한 지수 호출 실패가 다른 지수 수집을 중단하지 않도록 runner에서 지수 단위 실패로 기록한다.

## 결정 기록

- 결정: 새 작업 패키지는 `app/batch/src/jobs/market_index_daily_price`로 만든다.
  이유: `docs/architecture/batch.md`는 거래량 상위 종목 선정, 종목 일봉 수집, 지수 일봉 수집을 서로 다른 작업 단위로 관리하라고 설명한다. 지수 일봉은 저장 대상과 입력 집합이 종목 일봉과 다르므로 별도 job이 맞다.
  검토한 대안: 기존 `stock_daily_price` 패키지에 지수 로직을 추가하는 방법이 있지만, 작업 목적이 섞이고 저장소 인터페이스가 불필요하게 넓어진다.
  영향: 새 패키지는 기존 배치 계층 구조인 `application`, `domain`, `infrastructure/client`, `infrastructure/persistence`를 그대로 따른다.

- 결정: 내부 지수 코드와 FDR 심볼 매핑은 도메인 또는 application에서 고정 목록으로 관리하고, MVP에서는 `KOSPI -> KS11`, `KOSDAQ -> KQ11`만 지원한다.
  이유: 이슈와 DB 체크 제약은 내부 지수 코드를 `KOSPI`, `KOSDAQ`으로 제한한다. FDR 공식 문서가 두 국내 지수 심볼을 `KS11`, `KQ11`로 안내한다.
  검토한 대안: 지수 목록을 설정 파일이나 DB 테이블로 분리할 수 있지만, MVP의 지원 지수가 두 개로 고정되어 있고 지정 지수 옵션은 이슈 05 범위다.
  영향: `MarketIndexTarget` 모델과 지원 대상 목록은 `app/batch/src/jobs/market_index_daily_price/domain/model.py`에 둔다. `FinanceDataReader` client는 내부 코드 문자열만 받지 않고 `MarketIndexTarget`을 받아 `target.fdr_symbol`로 외부 조회를 수행한다. 새 지수 추가는 후속 이슈에서 매핑과 DB 체크 제약, API 계약을 함께 변경해야 한다.

- 결정: 최초 적재는 `FinanceDataReader.DataReader(symbol, "1900-01-01")`로 요청하고, 이미 적재된 지수는 `MAX(trade_date) + 1일`부터 요청한다.
  이유: 이슈는 최초 적재 시 조회 가능한 최초 일봉부터 최신 일봉까지 수집하고, 이후 실행부터 마지막 적재일 이후 일봉만 수집하라고 요구한다. 별도 최초 거래일 컬럼이 없으므로 충분히 이른 시작일로 FDR이 반환 가능한 범위를 요청한다.
  검토한 대안: 각 지수의 공식 최초 산출일을 코드에 넣는 방법이 있지만, 현재 저장소에는 그 날짜를 검증하는 자료가 없고 운영상 FDR이 반환 가능한 범위를 기준으로 삼는 편이 단순하다.
  영향: 주말과 휴장일 보정은 하지 않는다. 시작일 이후 새 row가 없으면 실패가 아니라 스킵으로 기록한다.

- 결정: 가격 저장은 `ON CONFLICT (index_code, trade_date) DO UPDATE`를 사용한다.
  이유: 같은 배치를 반복 실행해도 중복 row가 없어야 하고, FDR 원천 데이터가 보정될 수 있으므로 충돌 시 기존 row 값을 최신 원천 데이터 기준으로 갱신하는 편이 일관적이다.
  검토한 대안: `DO NOTHING`은 중복 방지는 가능하지만 원천 데이터 정정 반영을 막는다.
  영향: 반복 실행의 최종 DB 상태는 지수와 거래일별 row 하나로 유지된다.

- 결정: DB 저장 트랜잭션은 지수 단위로 묶는다.
  이유: 이슈는 지수별 성공, 스킵, 실패 결과를 로그로 남기라고 요구한다. 한 지수 저장 실패가 다른 지수 저장 결과를 되돌릴 필요는 없다.
  검토한 대안: 코스피와 코스닥 전체를 하나의 트랜잭션으로 묶을 수 있지만, 한 지수의 일시 오류가 다른 지수의 정상 적재까지 막는다.
  영향: `KOSPI` 저장이 성공하고 `KOSDAQ` 저장이 실패하면 `KOSPI` 결과는 commit되고 `KOSDAQ`은 실패로 기록된 뒤 배치 결과에 남는다.

- 결정: FDR 결과가 비어 있으면 해당 지수는 스킵으로 기록하고, FDR 결과 row는 있었지만 필수값 오류로 저장 가능한 row가 0개가 되면 해당 지수는 정규화 실패로 기록한다.
  이유: 이슈 03의 종목 일봉 적재에서 이미 같은 정규화 정책을 적용했다. 시작일 이후 거래일이 없어서 원천 결과가 비어 있는 상황은 정상적인 증분 실행에서 생길 수 있으므로 실패가 아니다. 반면 원천 row가 있었는데 `Open`, `High`, `Low`, `Close`, `Volume`, 거래일 중 필수값이 모두 깨져 저장할 수 없는 상황은 원천 데이터 형식이나 정규화 규칙의 문제이므로 실패로 봐야 한다.
  검토한 대안: 저장 가능한 row가 0개인 모든 상황을 스킵으로 처리할 수 있지만, 그러면 실제 데이터 형식 변경을 정상 실행으로 숨길 위험이 있다.
  영향: runner는 빈 FDR 결과를 `skipped_count`에 더하고, 정규화 예외는 실패 지수 목록에 기록한 뒤 다음 지수를 계속 처리한다.

- 결정: `KOSPI`, `KOSDAQ` 두 지수가 모두 실패해도 기본 배치 프로세스는 예외로 중단하지 않고, `market_index_daily_price` job 결과의 실패로만 기록한다.
  이유: 지수 일봉 적재는 기본 배치의 세 번째 독립 수집 작업이다. `stock_universe` digest 실패처럼 후속 작업의 입력 집합을 신뢰할 수 없게 만드는 오류와 달리, 지수 수집 실패는 실패한 지수 코드와 원인을 로그와 결과 DTO에 남기면 재실행 판단이 가능하다.
  검토한 대안: 두 지수가 모두 실패하면 `MarketIndexDailyPriceRunner.run()`이 예외를 던져 전체 배치를 실패 종료하게 할 수 있다. 그러나 이 방식은 종목 일봉 적재까지 끝난 기본 배치 실행을 전체 실패로 보이게 만들어, 독립 수집 작업의 결과를 구분하기 어렵다.
  영향: 결과 DTO에는 별도 `status` 필드를 추가하지 않는다. 두 지수가 모두 실패한 상태는 `failed_count == total_index_count`로 판단하고, 완료 로그에는 실패 지수 코드 목록을 함께 남긴다.

## 맥락과 방향 안내

저장소 루트는 `/Users/sehako/workspace/stock-report`이다. Python 배치 코드는 `app/batch` 아래에 있으며 `python -m batch.main`으로 실행한다. 배치 의존성은 `app/batch/pyproject.toml`에서 관리하고, 현재 `finance-datareader`, `pandas`, `psycopg[binary]`, `pytest`가 이미 들어 있다. 이 이슈를 위해 새 의존성을 추가하지 않는 방향이 기본 계획이다.

현재 기본 배치 진입점인 `app/batch/src/batch/main.py`는 설정과 로깅을 준비한 뒤 `StockUniverseRunner`와 `StockDailyPriceRunner`를 순서대로 실행한다. 이슈 04 구현 후에는 같은 파일에서 세 번째로 `MarketIndexDailyPriceRunner`를 실행한다. `stock_universe` digest가 실패하면 지금처럼 후속 가격 적재를 실행하지 않는다. `stock_daily_price`에서 일부 종목이 실패하더라도 runner 자체는 결과 객체를 반환하므로, 지수 일봉 적재는 그 뒤에 실행하는 방향으로 계획한다.

`market_index_price` 테이블은 `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`에서 만들어진다. 컬럼은 `index_code`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `change_rate`다. `open_price`, `high_price`, `low_price`, `close_price`, `volume`은 `NOT NULL`이고, `change_rate`는 `NULL`을 허용한다. `index_code`, `trade_date` 조합은 유니크 제약으로 보호된다.

이 계획에서 사용할 FDR 지수 심볼은 `KS11`과 `KQ11`이다. `KS11`은 코스피 지수, `KQ11`은 코스닥 지수다. 배치 내부와 DB에는 이 심볼을 저장하지 않고, 내부 코드 `KOSPI`, `KOSDAQ`만 저장한다. 심볼은 외부 데이터 조회를 위한 매핑 값이다.

## 구현 접근

새 작업 패키지 `jobs.market_index_daily_price`는 이슈 03의 `jobs.stock_daily_price` 구조를 따른다. 도메인 계층에는 내부 지수 코드, FDR 심볼, 지수 일봉 가격 모델, 정규화 결과 모델, 저장소 인터페이스를 둔다. 정규화는 외부 네트워크와 DB 없이 테스트할 수 있는 순수 함수로 만든다. FDR 결과의 날짜 index와 `Open`, `High`, `Low`, `Close`, `Volume`, `Change` 컬럼을 읽어 `MarketIndexDailyPrice` 모델 목록으로 바꾼다.

application runner는 고정된 두 지수 대상을 순회한다. `MarketIndexTarget`은 내부 지수 코드와 FDR 심볼을 함께 가진 도메인 모델이다. 각 지수마다 저장소에서 마지막 적재일을 읽고, FDR client에 `MarketIndexTarget`과 마지막 적재일을 넘긴다. client는 `target.fdr_symbol`로 `FinanceDataReader.DataReader(symbol, start)`를 호출한다. 마지막 적재일이 없으면 `start`는 `"1900-01-01"`이고, 마지막 적재일이 있으면 그 다음 날짜의 ISO 문자열이다.

정규화 함수는 `normalize_market_index_daily_prices(index_code, rows)`처럼 내부 지수 코드를 받고, 반환하는 각 `MarketIndexDailyPrice`에 `index_code`를 채운다. 이 모델은 DB의 `market_index_price` row 하나와 대응하며, 거래일 하나에 대한 시가, 고가, 저가, 종가, 거래량, 등락률을 담는다. 저장소는 `market_index_price`만 다룬다. 마지막 적재일 조회는 `SELECT MAX(trade_date) FROM market_index_price WHERE index_code = %s`로 충분하다. 저장 메서드는 정규화된 `MarketIndexDailyPrice` 목록을 받아 `INSERT INTO market_index_price (...) VALUES (...) ON CONFLICT (index_code, trade_date) DO UPDATE SET ...` 형태로 upsert한다. 저장 중 예외가 발생하면 해당 지수 트랜잭션만 rollback하고 예외를 runner로 올린다. runner는 실패 지수를 결과 DTO와 로그에 남긴 뒤 다음 지수를 계속 처리한다. 실패 DTO에는 최소한 `index_code`와 실패 사유를 포함하고, 완료 로그에는 `failed_indexes=KOSPI,KOSDAQ`처럼 실패 지수 코드 목록을 남긴다.

## 구현 단계

### [ ] 1. 지수 일봉 도메인 모델과 정규화 테스트를 작성한다

- 변경 내용: `MarketIndexTarget`, `MarketIndexDailyPrice`, `MarketIndexDailyPriceCollectionResult` 같은 모델과 FDR row 정규화 규칙을 테스트로 먼저 고정한다. `MarketIndexTarget`과 지원 대상 목록은 도메인 모델에 둔다. `Open`, `High`, `Low`, `Close`, `Volume`, 거래일은 필수값이고 `Change`는 선택값이다. 일부 row의 필수값이 깨지면 해당 row만 제외하고, 같은 거래일이 중복되면 마지막 row 하나를 남긴다. FDR 결과 row는 있었지만 저장 가능한 row가 0개면 정규화 실패 예외를 발생시킨다.
- 예상 변경 파일:
  - `app/batch/tests/jobs/market_index_daily_price/test_market_index_daily_price_service.py`
  - `app/batch/src/jobs/market_index_daily_price/domain/model.py`
  - `app/batch/src/jobs/market_index_daily_price/domain/service.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_market_index_daily_price_service.py`
- 완료 조건:
  - 샘플 DataFrame이 `MarketIndexDailyPrice` 목록으로 변환되고, 결측/중복 처리 결과가 테스트로 확인된다.

### [ ] 2. FDR 지수 client와 심볼 매핑을 추가한다

- 변경 내용: 내부 코드 `KOSPI`, `KOSDAQ`과 FDR 심볼 `KS11`, `KQ11` 매핑을 정의하고, 마지막 적재일 기준 시작일 계산을 구현한다. FDR client는 내부 코드 문자열이 아니라 `MarketIndexTarget`을 받아 `target.fdr_symbol`로 조회한다. 실제 `FinanceDataReader` import는 메서드 안에서 수행해 테스트가 외부 네트워크를 호출하지 않게 한다.
- 예상 변경 파일:
  - `app/batch/tests/jobs/market_index_daily_price/test_finance_data_reader_client.py`
  - `app/batch/src/jobs/market_index_daily_price/infrastructure/client/finance_data_reader_client.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_finance_data_reader_client.py`
- 완료 조건:
  - 최초 적재는 `("KS11", "1900-01-01")` 또는 `("KQ11", "1900-01-01")`로 호출되고, 마지막 적재일이 있으면 다음 날부터 호출되는 것이 fake FDR로 검증된다.

### [ ] 3. runner 흐름과 결과 DTO를 구현한다

- 변경 내용: 두 지수를 순회하며 마지막 적재일 조회, FDR 조회, 정규화, upsert를 조합하는 `MarketIndexDailyPriceRunner`를 추가한다. 각 지수 처리 결과는 성공, 스킵, 실패로 구분하고 로그와 결과 DTO에 남긴다. 실패 결과에는 `index_code`와 사유를 담는다. 한 지수의 실패는 다른 지수 처리를 막지 않는다. 두 지수가 모두 실패해도 `run()`은 예외를 던지지 않고, `failed_count == total_index_count`와 실패 지수 목록을 통해 해당 job 실패를 표현한다.
- 예상 변경 파일:
  - `app/batch/tests/jobs/market_index_daily_price/test_market_index_daily_price_runner.py`
  - `app/batch/src/jobs/market_index_daily_price/application/dto.py`
  - `app/batch/src/jobs/market_index_daily_price/application/market_index_daily_price_runner.py`
  - `app/batch/src/jobs/market_index_daily_price/domain/repository.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_market_index_daily_price_runner.py`
- 완료 조건:
  - fake client와 fake repository로 `KOSPI` 성공, `KOSDAQ` 스킵 또는 실패 시나리오를 검증하고, 결과 객체에 total, success, skipped, failed, saved 건수가 남는다. 두 지수가 모두 실패해도 runner가 예외를 던지지 않고 실패 지수 목록을 결과에 남기는 것을 검증한다.

### [ ] 4. PostgreSQL 저장소를 구현한다

- 변경 내용: `market_index_price`의 지수별 마지막 적재일을 조회하고, 지수 일봉 목록을 `index_code`, `trade_date` 기준으로 upsert하는 psycopg 저장소를 추가한다. commit과 rollback은 지수 단위로 수행한다.
- 예상 변경 파일:
  - `app/batch/tests/jobs/market_index_daily_price/test_market_index_daily_price_repository.py`
  - `app/batch/src/jobs/market_index_daily_price/infrastructure/persistence/market_index_daily_price_repository.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_market_index_daily_price_repository.py`
- 완료 조건:
  - 저장소 테스트가 `MAX(trade_date)` 조회 SQL, `ON CONFLICT (index_code, trade_date) DO UPDATE` upsert SQL, commit과 rollback 동작을 확인한다.

### [ ] 5. 기본 배치 실행에 지수 일봉 적재를 연결하고 문서를 갱신한다

- 변경 내용: `app/batch/src/batch/main.py`에서 기존 `stock_universe`, `stock_daily_price` 다음에 새 지수 runner를 호출한다. `app/batch/README.md`에는 기본 배치가 지수 일봉도 적재한다는 설명과 `market_index_price` 중복 확인 쿼리를 추가한다.
- 예상 변경 파일:
  - `app/batch/tests/test_batch_main.py`
  - `app/batch/src/batch/main.py`
  - `app/batch/README.md`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/test_batch_main.py tests/jobs/market_index_daily_price`
- 완료 조건:
  - 기본 실행 테스트에서 지수 runner가 종목 일봉 runner 뒤에 호출되고, `stock_universe` digest 실패 시 후속 가격 적재가 실행되지 않는 흐름이 유지된다.

### [ ] 6. 전체 검증과 수동 통합 검증을 수행한다

- 변경 내용: 구현 완료 후 전체 배치 테스트를 실행하고, 가능한 환경에서는 실제 PostgreSQL과 FDR 네트워크 호출로 배치를 두 번 실행해 중복 row가 없는지 확인한다.
- 예상 변경 파일:
  - `docs/plans/batch/issue-04-batch-market-index-daily-price-loading.md`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest`
  - `cd app/batch && python -m batch.main`
  - 같은 명령을 한 번 더 실행한 뒤 DB 중복 확인 쿼리 실행
- 완료 조건:
  - 전체 pytest가 통과한다. 수동 검증 환경이 있으면 `market_index_price`의 `index_code`, `trade_date` 중복 건수가 `0`임을 확인하고 이 문서에 결과를 기록한다.

## 테스트 및 검증 계획

자동 테스트는 외부 네트워크와 실제 개발 DB에 의존하지 않는다. `tests/jobs/market_index_daily_price` 아래에 도메인 정규화, FDR client, runner, 저장소 테스트를 둔다. 기존 `stock_daily_price` 테스트와 같은 방식으로 fake DataFrame, fake FDR module, fake repository, fake connection을 사용한다.

최소 자동 테스트 시나리오는 다음과 같다. FDR 일봉 row가 `MarketIndexDailyPrice` 모델로 정규화되어야 한다. `MarketIndexDailyPrice`에는 `index_code`가 포함되어야 한다. `Change`가 없거나 변환할 수 없는 row는 `change_rate = None`으로 정규화되어야 한다. 일부 row만 필수값 정규화에 실패하면 정상 row는 유지되고 실패 row 수가 결과에 남아야 한다. 같은 거래일 중복 row가 있으면 마지막 row가 남고 중복 제거 수가 결과에 남아야 한다. FDR 결과가 비어 있으면 스킵으로 기록되어야 하고, FDR 결과 row가 있었지만 저장 가능한 row가 0개면 실패로 기록되어야 한다. 마지막 적재일이 있으면 다음 날을 시작일로 계산하고, 없으면 `MarketIndexTarget`의 지수 심볼과 `1900-01-01`로 최대 기간 조회를 요청해야 한다. 한 지수 client 예외 또는 저장소 예외가 다른 지수 처리를 막지 않아야 한다. 두 지수가 모두 실패해도 기본 배치 프로세스를 중단하는 예외를 던지지 않고, 결과 DTO와 로그에 `failed_count=2`와 실패 지수 코드 목록을 남겨야 한다. 저장소 upsert SQL은 `ON CONFLICT (index_code, trade_date) DO UPDATE`를 사용해야 한다. 기본 실행은 지수 runner를 기존 가격 적재 흐름 뒤에 호출해야 한다.

전체 자동 검증 명령은 다음과 같다.

    cd /Users/sehako/workspace/stock-report/app/batch
    .venv/bin/python -m pytest

`.venv`가 없다면 다음 순서로 준비한다.

    cd /Users/sehako/workspace/stock-report/app/batch
    python3.14 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"

수동 통합 검증은 `DATABASE_URL`이 설정된 로컬 PostgreSQL과 외부 네트워크 접근이 가능한 환경에서만 수행한다. 배치를 두 번 실행한 뒤 다음 쿼리로 중복 여부를 확인한다.

    SELECT COUNT(*)
    FROM (
        SELECT index_code, trade_date
        FROM market_index_price
        GROUP BY index_code, trade_date
        HAVING COUNT(*) > 1
    ) duplicated;

기대 결과는 `0`이다. 추가로 다음 쿼리로 두 지수 모두 적재되었는지 확인한다.

    SELECT index_code, COUNT(*) AS row_count, MAX(trade_date) AS last_trade_date
    FROM market_index_price
    GROUP BY index_code
    ORDER BY index_code;

기대 결과는 `KOSPI`와 `KOSDAQ` 두 행이 나오고, 각 행의 `row_count`가 0보다 큰 것이다. FDR 지수 조회가 외부 서비스 상태 때문에 실패하면 자동 테스트는 여전히 통과해야 하며, 수동 검증 결과에는 실패 지수 코드와 오류 메시지를 기록한다.

## 수락 기준

구현 완료 여부는 사람이 관찰할 수 있는 동작으로 판단한다. 사용자는 `app/batch`에서 `python -m batch.main`을 실행해 코스피와 코스닥 지수의 일봉 적재를 시작할 수 있어야 한다. 배치는 내부 지수 코드 `KOSPI`, `KOSDAQ`과 FDR 심볼 `KS11`, `KQ11` 매핑을 사용해야 한다. 최초 적재 지수는 `1900-01-01`부터 FDR이 조회 가능한 일봉을 요청해야 한다. 이미 적재된 지수는 `market_index_price`의 `MAX(trade_date)` 다음 날부터만 요청해야 한다. 저장된 row에는 `index_code`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`이 채워져야 하고, `change_rate`는 FDR `Change` 원값이거나 `NULL`이어야 한다.

같은 배치를 반복 실행해도 `index_code`, `trade_date` 기준 중복 row가 생기면 안 된다. 한 지수 수집 실패가 다른 지수 수집을 중단하면 안 되고, 실패 지수 코드와 원인은 로그와 결과 DTO에서 확인할 수 있어야 한다. `KOSPI`, `KOSDAQ` 두 지수가 모두 실패하면 `market_index_daily_price` job 결과는 실패로 해석할 수 있어야 하지만, runner가 예외를 던져 기본 배치 프로세스를 중단하지는 않아야 한다. 종목 메타데이터 갱신, 종목 일봉 가격 수집, 지정 재수집 옵션, Spring Boot 조회 API 구현은 이 이슈에서 새로 확장하지 않아야 한다.

## 위험 및 대응

| 위험 | 영향 | 대응 및 검증 |
| ---- | ---- | ------------ |
| FDR 지수 조회가 외부 서비스 상태에 따라 실패할 수 있음 | 수동 통합 검증에서 `KS11` 또는 `KQ11` 적재가 실패할 수 있음 | 자동 테스트는 fake FDR로 계약을 검증하고, 실제 실패는 지수 단위 실패 로그로 남긴다. 수동 검증 결과에 오류를 기록한다. |
| 지수별 최초 적재량이 많을 수 있음 | 첫 실행 시간이 길어질 수 있음 | 최초 실행은 한 번만 장기 데이터를 적재하고 이후 실행은 마지막 적재일 다음 날부터 조회한다. |
| FDR `Change` 컬럼이 없거나 형식이 바뀔 수 있음 | 등락률 저장이 비거나 정규화 실패가 늘 수 있음 | `Change`는 선택값으로 처리해 가격 row 저장을 유지하고, 필수 컬럼 누락만 row 제외 또는 실패로 본다. |
| 두 지수가 모두 실패했는데 기본 배치가 정상 종료되어 운영자가 실패를 놓칠 수 있음 | 지수 일봉이 적재되지 않은 실행을 성공으로 오해할 수 있음 | 완료 로그와 결과 DTO에 `failed_count`, 실패 지수 코드 목록, 실패 사유를 남긴다. 호출자가 필요하면 `failed_count == total_index_count`로 지수 job 실패를 판단한다. |
| 기본 실행에 새 runner를 연결하면서 기존 종목 적재 흐름이 깨질 수 있음 | 기존 이슈 02, 03 동작 회귀가 생길 수 있음 | `tests/test_batch_main.py`와 전체 `pytest`로 기존 흐름과 새 호출 순서를 함께 검증한다. |

## 미결정 사항

> 구현을 시작하기 위해 추가로 결정할 사항 없음.

## 결과와 회고

아직 구현 전이다. 구현자는 이 계획에 따라 코드를 수정하면서 `진행 상황`, `예상 밖의 발견`, `결정 기록`을 갱신해야 한다. 구현이 끝나면 실제 추가 파일, 테스트 명령, 수동 통합 검증 결과, 계획과 달라진 점을 이 섹션에 기록한다.

### 최종 변경 내용

아직 구현하지 않았다.

### 검증 결과

아직 구현하지 않았으므로 실행한 구현 검증 명령이 없다.

### 계획과 달라진 점

아직 구현하지 않았다.

### 이슈 완료 기준 충족 여부

- [ ] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [ ] 관련 테스트 또는 검증 결과를 기록한다.
- [ ] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [ ] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

### 남은 한계

아직 구현하지 않았다. 계획 단계에서 확인된 운영상 한계는 실제 FDR `KS11`, `KQ11` 조회가 외부 서비스 상태에 의존한다는 점이다.

### 후속 작업

지정 지수와 지정 기간 재수집 옵션은 `docs/issues/05-batch-targeted-reload-options.md`에서 다룬다. 지수 일봉 조회 API는 `docs/issues/07-backend-market-index-price-api.md`에서 다룬다.

### 회고

계획 작성 단계에서는 이슈 03의 종목 일봉 배치 구조가 이미 구현되어 있어 지수 일봉 배치도 같은 계층과 테스트 스타일을 따를 수 있음을 확인했다. 구현자는 새 추상화보다 기존 `stock_daily_price` 패턴을 복제하되, 지수 작업에는 stock id와 tracked 종목 조회가 필요 없다는 차이를 유지해야 한다.

## 완료 확인

- [ ] 이슈의 모든 작업 범위를 구현했다.
- [ ] 이슈의 제외 범위를 침범하지 않았다.
- [ ] 완료 기준을 테스트 또는 실행 결과로 확인했다.
- [ ] 구현 중 주요 결정과 계획 변경을 기록했다.
- [ ] 예상 밖의 발견과 대응을 기록했다.
- [ ] 관련 문서를 갱신했다.
- [ ] 후속 작업이 있다면 별도 이슈로 분리했다.
- [ ] `결과와 회고`에 최종 구현 및 검증 결과를 기록했다.
- [ ] ExecPlan이 최종 코드 상태와 일치한다.

계획 변경 메모:

- 2026-07-20 / Codex: 계획 초안 작성. 이유: `docs/issues/04-batch-market-index-daily-price-loading.md`의 Python 배치 구현을 현재 저장소 구조, 이슈 03 배치 패턴, 실제 `market_index_price` 스키마에 맞춰 자기완결적으로 수행할 수 있게 하기 위해서.
- 2026-07-20 / 사용자, Codex: 계획 검토에서 확인한 보강 사항을 반영. 이유: 저장 가능한 row가 0개인 정규화 실패 처리, 두 지수 모두 실패했을 때의 job 결과 해석, 실패 지수 코드 로깅, `MarketIndexTarget`과 저장 모델의 경계를 구현자가 이 파일만 읽고도 일관되게 적용할 수 있게 하기 위해서.
