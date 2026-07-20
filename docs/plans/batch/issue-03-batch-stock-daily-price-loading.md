# tracked 종목 일봉 적재 배치 구현

이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다.

## 목적과 큰 그림

이 계획은 `docs/issues/03-batch-stock-daily-price-loading.md` 이슈를 구현하기 위한 실행 계획이다. 구현이 끝나면 Python 배치를 실행해 `stock.tracked = true`인 종목들의 일봉 가격을 `FinanceDataReader.DataReader`로 수집하고, `stock_price` 테이블에 저장할 수 있다. 사용자는 배치를 두 번 이상 실행한 뒤에도 `stock_price.stock_id`, `stock_price.trade_date` 조합의 중복 row가 생기지 않는지 데이터베이스에서 확인할 수 있다.

일봉은 하루 단위의 시가, 고가, 저가, 종가, 거래량, 등락률 데이터다. 최초 적재 종목은 조회 가능한 가장 이른 일봉부터 최신 일봉까지 저장하고, 이미 적재된 종목은 `stock_price`에 저장된 마지막 거래일 다음 날부터 추가로 조회한다. 한 종목 수집이 실패해도 나머지 종목 수집은 계속 진행해야 하며, 실패한 종목은 로그로 식별할 수 있어야 한다.

이 이슈는 거래량 상위 200개 종목 선정 로직, 지수 일봉 적재, 지정 재수집 옵션, 배치 실패 이력 테이블 저장을 구현하지 않는다. 기본 실행에서는 기존 `stock_universe` 배치가 `tracked` 대상 종목을 준비한 뒤, 이 계획에서 추가할 종목 일봉 배치가 그 대상의 가격을 적재하는 흐름으로 확장한다.

## 진행 상황

- [x] (2026-07-19 17:00+0900) 이슈 본문, 참고 설계 문서, 배치 아키텍처 문서, ExecPlan 지침을 확인했다.
- [x] (2026-07-19 17:00+0900) 현재 Python 배치 구조와 `stock_universe` 구현, 테스트, 설정, DB 연결 방식을 조사했다.
- [x] (2026-07-19 17:00+0900) `stock_price` 스키마와 백엔드 스키마 테스트를 확인해 중복 방지 기준과 컬럼 의미를 확정했다.
- [x] (2026-07-19 17:00+0900) 구현 위치, 데이터 흐름, 검증 방법을 현재 저장소 상태 기준으로 계획했다.
- [x] (2026-07-19 18:20+0900) 계획 검토를 통해 부분 실패 종료 상태, 최초/증분 조회 기준, upsert 정책, 정규화 실패 처리, 트랜잭션 경계를 확정해 이 문서에 반영했다.
- [ ] 실패하는 테스트 작성.
- [ ] 최소 구현.
- [ ] 리팩터링.
- [ ] 전체 테스트 및 수동 검증.
- [ ] 결과와 회고 작성.
- [ ] ExecPlan 최종 상태 확인.

## 예상 밖의 발견

- 관찰: 현재 `app/batch/src/batch/main.py`는 옵션 없는 실행에서 `StockUniverseRunner`만 직접 호출한다.
  증거: `app/batch/src/batch/main.py`는 `FinanceDataReaderKrxListingClient`와 `PsycopgStockUniverseRepository`를 만들어 `StockUniverseRunner.run()`을 실행하고, digest 불일치만 검사한다.
  영향: 이슈 03 구현은 새 `stock_daily_price` 작업 패키지 추가만으로 끝나지 않는다. 옵션 없는 기본 실행이 MVP 기본 배치 흐름을 수행하려면 `stock_universe` 실행 다음에 종목 일봉 적재 runner를 호출하도록 `batch.main`을 좁은 범위에서 확장해야 한다.

- 관찰: 실제 스키마에는 `stock.last_loaded_date`가 없고, 종목 일봉은 `stock_price.stock_id`로 `stock.id`를 참조한다.
  증거: `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`에서 `stock` 컬럼은 `id`, `market`, `stock_code`, `stock_name`, `tracked`이고, `stock_price`는 `stock_id`, `trade_date` 유니크 제약 `uk_stock_price_stock_trade_date`를 가진다.
  영향: 마지막 적재일은 설계 문서대로 `stock_price`에서 종목별 `MAX(trade_date)`를 조회해야 한다. 가격 upsert는 `stock_code`가 아니라 `stock.id`와 `trade_date`를 기준으로 해야 한다.

- 관찰: 기존 Python 배치 테스트는 외부 네트워크와 실제 DB에 의존하지 않는 fake 기반 테스트를 우선한다.
  증거: `app/batch/tests/jobs/stock_universe/test_service.py`, `test_stock_universe_runner.py`, `test_stock_universe_repository.py`는 샘플 row와 fake repository 또는 fake connection으로 도메인 규칙, runner 흐름, SQL 의도를 검증한다.
  영향: 이슈 03 자동 테스트도 `FinanceDataReader` 실제 호출과 개발 DB 쓰기에 의존하지 않게 작성한다. 실제 FDR 호출과 PostgreSQL 반영은 수동 통합 검증으로 분리한다.

- 관찰: `FinanceDataReader` 국내 주식 가격 데이터는 수정가격이며, KRX 장기 조회는 `KRX:{stock_code}` 심볼과 충분히 이른 시작일을 사용할 수 있다.
  증거: `app/batch/pyproject.toml`은 `finance-datareader>=0.9.96`을 요구한다. `FinanceDataReader` Quick Start는 국내 주식 가격 데이터가 수정가격이라고 설명하고, 0.9.92 릴리스 노트는 `KRX:000100`처럼 데이터 소스를 명시하고 긴 기간 조회를 2년 단위로 나눠 병합하는 방식을 설명한다.
  영향: 최초 적재는 시작일 생략이 아니라 `KRX:{stock_code}`와 `1900-01-01`을 사용해 FDR이 반환 가능한 최대 KRX 기간을 요청한다. 수정가격은 과거 값이 재계산될 수 있으므로 가격 저장 충돌 시 기존 row를 원천 데이터 기준으로 갱신하는 `DO UPDATE`가 더 적합하다.

## 결정 기록

- 결정: 새 작업 패키지는 `app/batch/src/jobs/stock_daily_price`로 만든다.
  근거: `docs/architecture/batch.md`는 배치 목적별로 작업 패키지를 분리하라고 지시한다. 이슈 02의 `stock_universe`와 이슈 03의 종목 일봉 적재는 목적, 저장 대상, 실패 처리 단위가 다르므로 별도 작업으로 두는 것이 계층과 책임을 명확하게 유지한다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: tracked 종목 조회 결과는 `id`, `market`, `stock_code`, `stock_name`, `last_loaded_date`를 포함하는 도메인 모델로 다룬다.
  근거: 가격 저장에는 내부 기본키인 `stock.id`가 필요하고, FDR 조회에는 종목코드가 필요하다. 로그에는 사용자가 실패 종목을 식별할 수 있도록 종목코드와 종목명이 필요하다. 마지막 적재일은 `stock_price`의 `MAX(trade_date)`로 계산해 추가 수집 시작일을 정한다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 최초 적재 종목은 `FinanceDataReader.DataReader(f"KRX:{stock_code}", "1900-01-01")`로 조회한다.
  근거: 이슈는 "조회 가능한 최초 일봉부터" 수집하라고 요구한다. 저장소에는 최초 상장일 컬럼이 없고, `FinanceDataReader`는 `KRX:` 접두어로 KRX 데이터 소스를 명시할 수 있다. `1900-01-01`은 실제 상장일을 뜻하지 않고 FDR이 반환 가능한 최대 KRX 기간을 요청하기 위한 충분히 이른 시작일이다. 외부 호출 성공은 보장하지 않으므로 특정 종목에서 예외가 나면 그 종목은 실패로 기록하고 다음 종목 처리를 계속한다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: `change_rate`에는 설계 문서의 정의대로 `FinanceDataReader.DataReader` 결과의 `Change` 원값을 저장하되, `Change`가 없거나 변환할 수 없으면 `NULL`로 저장한다.
  근거: `docs/specs/2026-07-15-stock-market-data-service-design.md`는 `stock_price.change_rate`를 `FinanceDataReader`의 `Change` 원값으로 저장하고 API에서 100을 곱해 퍼센트로 반환한다고 설명한다. 프로토타입 일부는 종가 차이로 등락률을 계산하지만, MVP 데이터 계약은 `Change` 원값 저장이다. 실제 DB 스키마에서 `change_rate`는 nullable이고 가격과 거래량만 `NOT NULL`이므로, `Change` 결측 때문에 정상 가격 row 전체를 버릴 필요는 없다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 한 종목 단위 실패는 runner에서 잡아 실패 결과에 누적하고, 다음 종목 처리를 계속한다. 개별 종목 실패가 하나 이상 있어도 `stock_daily_price` 작업 자체는 성공 종료한다.
  근거: 이슈가 한 종목 수집 실패가 나머지 종목 수집을 중단하지 않게 처리하라고 요구한다. 이 배치는 best-effort 수집 성격이므로 199개 종목이 성공하고 1개 종목이 실패한 상황을 전체 실패로 보지 않는다. 실패 종목의 종목코드와 종목명, 실패 사유, 성공/스킵/실패 건수 요약은 로그와 결과 DTO에 남긴다. 필수 설정 누락, DB 연결 실패, tracked 종목 목록 조회 실패, `stock_universe` 선행 작업 실패처럼 배치 자체를 시작하거나 입력 집합을 준비할 수 없는 오류는 전체 실패로 본다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 기본 실행 연결은 `app/batch/src/batch/main.py`에서 기존 `StockUniverseRunner.run()` 뒤에 새 `StockDailyPriceRunner.run()`을 추가하는 조합 변경으로 한정한다.
  근거: 이슈 03은 거래량 상위 200개 종목 선정 로직을 제외 범위로 둔다. 따라서 `stock_universe` 내부 선정 규칙, 저장 방식, `tracked` 갱신 규칙은 수정하지 않는다. 새 일봉 적재 작업은 DB에 저장된 `stock.tracked = true` 종목을 입력으로 삼고, 기본 실행에서 선행 `stock_universe`가 실패하면 입력 집합이 준비되지 않은 상태이므로 `stock_daily_price`를 실행하지 않는다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 이미 적재된 종목은 해당 종목의 `stock_price.MAX(trade_date) + 1일`을 시작일로 조회하고, 주말과 공휴일 보정은 하지 않는다.
  근거: 마지막 저장 거래일 다음 날짜를 넘기면 이미 저장된 마지막 row를 불필요하게 다시 요청하지 않는다. 그 날짜가 휴장일이면 FDR이 빈 DataFrame을 반환하거나 다음 거래일부터 반환할 수 있으므로 별도 한국거래소 휴장일 달력을 도입하지 않는다. 휴장일 계산은 이슈 범위를 키우며, 빈 결과는 실패가 아니라 스킵으로 기록하면 충분하다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 가격 저장은 `ON CONFLICT (stock_id, trade_date) DO UPDATE`를 사용한다.
  근거: 같은 종목과 거래일 row가 이미 있으면 FDR에서 다시 받은 `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `change_rate`로 갱신한다. FDR 국내 주식 가격 데이터는 수정가격이므로 과거 값이 재계산될 수 있고, FDR의 데이터 소스와 조회 정책도 변경된 이력이 있다. 기본 증분 적재에서는 대부분 신규 거래일만 조회하므로 기존 row 업데이트는 드물지만, 충돌이 발생하면 원천 데이터 기준으로 DB를 최신화하는 편이 일관적이다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: 정규화 단계에서 필수값이 깨진 일부 row는 제외하고 정상 row는 저장한다. 같은 거래일이 중복되면 마지막 row를 우선한다.
  근거: `Open`, `High`, `Low`, `Close`, `Volume`, 거래일은 가격 row 저장에 필요한 필수값이다. 일부 row만 깨졌을 때 전체 종목을 버리면 데이터 공백이 커지므로 정상 row는 저장한다. 저장 가능한 row가 0개라면 해당 종목은 정규화 실패로 본다. FDR 결과 안에서 동일 거래일이 중복되면 DB의 `(stock_id, trade_date)` 단일 row 기준과 맞추기 위해 마지막 row 하나만 남기고, 제외 row 수와 중복 제거 수를 로그 또는 결과 요약에 남긴다.
  날짜/작성자: 2026-07-19 / Codex

- 결정: DB 저장 트랜잭션은 종목 단위로 묶는다.
  근거: 이 계획의 실패 처리 단위는 종목이다. 한 종목의 일봉 목록 저장이 모두 성공하면 commit하고, 저장 중 예외가 발생하면 해당 종목의 이번 저장분은 rollback한다. 이전에 성공한 다른 종목의 저장 결과는 유지하고, 이후 종목 처리는 계속한다.
  날짜/작성자: 2026-07-19 / Codex

## 결과와 회고

아직 구현은 시작하지 않았다. 이 계획은 현재 저장소의 Python 배치 구조, PostgreSQL 스키마, 기존 테스트 관례를 조사해 작성한 구현 전 계획이다.

## 맥락과 방향 안내

저장소 루트는 `/Users/sehako/workspace/stock-report`이다. Python 배치 코드는 `app/batch` 아래에 있으며, 의존성은 `app/batch/pyproject.toml`에서 관리한다. 현재 의존성에는 `finance-datareader`, `pandas`, `psycopg[binary]`, `pytest`가 이미 포함되어 있어 이 이슈를 위해 새 라이브러리를 추가할 필요는 없어 보인다.

`app/batch/src/jobs/stock_universe`는 이슈 02에서 구현된 거래량 상위 200개 종목 선정 작업이다. 이 작업은 `FinanceDataReader.StockListing("KRX")`로 KRX 목록을 조회하고, 거래량 상위 200개를 `stock` 테이블에 upsert하며, 현재 선정되지 않은 기존 종목을 `tracked = false`로 바꾼다. 이슈 03은 이 작업이 만든 `tracked = true` 종목을 읽어 가격을 적재한다.

`app/batch/src/batch/main.py`는 옵션 없는 배치 실행 진입점이다. 진입점은 도메인 규칙, SQL, 외부 API 세부 구현을 직접 담지 않고 runner를 조합해야 한다. 이슈 03 구현 후에는 이 파일이 `StockUniverseRunner.run()`을 실행한 뒤 새 `StockDailyPriceRunner.run()`을 실행해야 한다.

`app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`은 실제 데이터베이스 계약이다. `stock_price`에는 `stock_id`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `change_rate`가 있고, `stock_id`, `trade_date` 조합에 유니크 제약이 있다. 유니크 제약은 같은 종목의 같은 거래일 일봉이 중복 저장되지 않도록 데이터베이스가 강제하는 규칙이다.

`FinanceDataReader.DataReader(symbol, start, end)`는 종목코드로 일봉 데이터를 가져오는 외부 라이브러리 호출이다. 기존 프로토타입 `docs/prototypes/stock-analysis/finance_data_to_csv.py`와 `docs/prototypes/stock-analysis/stoch_macd_golden_cross_scanner.py`는 이 호출로 `Open`, `High`, `Low`, `Close`, `Volume` 컬럼을 읽는다. 설계 문서는 추가로 `Change` 컬럼 원값을 `change_rate`에 저장하라고 정의한다. 최초 적재에서는 `symbol`에 `KRX:{stock_code}`를 넘기고, `start`에 `1900-01-01`을 넘겨 FDR이 반환 가능한 최대 KRX 기간을 요청한다. `Change`가 없거나 변환할 수 없어도 가격 row는 저장하고 `change_rate`만 `NULL`로 둔다.

## 작업 계획

먼저 `app/batch/src/jobs/stock_daily_price` 아래에 작업 패키지를 만든다. 구조는 `application`, `domain`, `infrastructure/client`, `infrastructure/persistence` 계층으로 나눈다. 도메인 계층에는 tracked 종목과 일봉 가격을 표현하는 모델, FDR row를 가격 모델로 정규화하는 순수 로직, 저장소 인터페이스를 둔다. 순수 로직은 외부 네트워크나 DB 없이 테스트 가능해야 한다.

저장소 인터페이스는 두 책임을 가진다. 첫째, `stock`과 `stock_price`를 조인해 `tracked = true` 종목별 마지막 적재일을 조회한다. 이 조회는 `stock.id`, `stock.market`, `stock.stock_code`, `stock.stock_name`, `MAX(stock_price.trade_date)`를 반환해야 한다. 둘째, 한 종목의 가격 목록을 `stock_price`에 upsert한다. upsert는 `ON CONFLICT (stock_id, trade_date) DO UPDATE`를 사용해 같은 종목과 거래일이 이미 있으면 가격 값을 갱신하고, 없으면 새로 넣는다.

FDR client는 종목코드와 시작일을 받아 `FinanceDataReader.DataReader`를 호출한다. 마지막 적재일이 없는 최초 적재에서는 `FinanceDataReader.DataReader(f"KRX:{stock_code}", "1900-01-01")`로 조회 가능한 최대 KRX 기간을 요청한다. 마지막 적재일이 있는 종목은 마지막 적재일 다음 날을 시작일로 계산하고, 주말과 공휴일 보정은 하지 않는다. 시작일이 오늘 이후가 되거나 FDR이 빈 DataFrame을 반환하면 해당 종목은 실패가 아니라 스킵으로 기록한다.

runner는 tracked 종목 목록을 읽고 종목별로 수집, 정규화, 저장을 반복한다. 각 종목 처리 결과는 성공, 스킵, 실패 중 하나로 기록한다. 성공은 하나 이상의 일봉 row가 upsert된 경우다. 스킵은 새로 수집할 row가 없는 경우다. 실패는 FDR 호출, 저장 가능한 row가 0개인 정규화 실패, DB 저장 중 예외가 발생한 경우다. 실패는 로그에 남기고 다음 종목으로 진행하며, 개별 종목 실패가 있어도 `stock_daily_price` 작업은 성공 종료한다. 필수 설정 누락, DB 연결 실패, tracked 종목 목록 조회 실패처럼 작업 자체를 시작하거나 입력 집합을 읽을 수 없는 오류는 전체 실패로 본다.

기본 실행 진입점은 기존 `stock_universe` 실행 후 새 `stock_daily_price` 실행을 이어서 호출하도록 바꾼다. 이 변경은 옵션 없는 기본 실행 흐름만 다룬다. `stock_universe` 내부 선정 규칙, 저장 방식, `tracked` 갱신 규칙은 수정하지 않는다. `stock_universe`가 실패하면 입력 집합이 준비되지 않은 상태이므로 `stock_daily_price`를 실행하지 않고 전체 배치를 실패 종료한다. `--stock-code`, `--start-date`, `--end-date` 같은 지정 재수집 옵션은 `docs/issues/05-batch-targeted-reload-options.md`의 범위이므로 이 계획에 섞지 않는다.

## 마일스톤

첫 번째 마일스톤은 실패하는 테스트로 기대 동작을 고정하는 것이다. 이 마일스톤이 끝나면 `app/batch/tests/jobs/stock_daily_price` 아래에 도메인 정규화 테스트, runner 흐름 테스트, 저장소 SQL 의도 테스트가 생긴다. 아직 구현 전이므로 테스트는 import 실패 또는 미구현 오류로 실패할 수 있다. 검증 명령은 `cd app/batch` 후 `.venv/bin/python -m pytest tests/jobs/stock_daily_price`이고, 기대 결과는 새 모듈이 아직 없어 실패하는 것이다.

두 번째 마일스톤은 종목 일봉 도메인 모델과 정규화 로직을 구현하는 것이다. 이 마일스톤이 끝나면 샘플 DataFrame 또는 row 목록에서 거래일, 시가, 고가, 저가, 종가, 거래량, `Change` 원값이 `StockDailyPrice` 모델로 변환된다. 거래일은 Python `date`, 가격과 등락률은 `Decimal`, 거래량은 `int`로 다룬다. 필수 가격 값이나 거래일이 없는 row는 저장하지 않고 제외 사유를 결과에 남긴다. `Change`가 없거나 변환할 수 없으면 `change_rate`를 `None`으로 둔다. 같은 거래일이 중복되면 마지막 row를 우선해 하나만 남기고 중복 제거 수를 결과에 남긴다. 저장 가능한 row가 0개인 종목은 정규화 실패로 판단한다. 이 마일스톤의 검증은 도메인 테스트 통과다.

세 번째 마일스톤은 FDR client와 runner 흐름을 구현하는 것이다. 이 마일스톤이 끝나면 fake client와 fake repository로 runner를 실행했을 때 tracked 종목 세 개 중 하나는 성공, 하나는 빈 데이터로 스킵, 하나는 예외로 실패하는 시나리오가 검증된다. 실패한 종목이 있어도 나머지 종목이 처리되고 결과 요약에 성공, 스킵, 실패 수와 종목코드가 남아야 한다.

네 번째 마일스톤은 PostgreSQL 저장소 구현과 기본 실행 연결이다. 이 마일스톤이 끝나면 저장소는 tracked 종목과 마지막 적재일을 조회하고, 가격 row를 `stock_price`에 upsert하는 SQL을 실행한다. upsert는 `ON CONFLICT (stock_id, trade_date) DO UPDATE`로 기존 row를 FDR 원천 데이터 기준으로 갱신한다. DB 트랜잭션은 종목 단위로 묶어 한 종목 저장이 모두 성공하면 commit하고, 저장 중 예외가 발생하면 그 종목의 이번 저장분만 rollback한다. `batch.main`은 기존 `stock_universe` 다음에 `stock_daily_price`를 호출하되 `stock_universe` 내부 로직은 수정하지 않는다. 자동 테스트는 fake connection으로 SQL의 핵심 구문, 파라미터, commit과 rollback 동작을 검증한다.

다섯 번째 마일스톤은 최종 자동 테스트와 수동 통합 검증이다. 이 마일스톤이 끝나면 `cd app/batch && .venv/bin/python -m pytest`가 통과한다. `DATABASE_URL`이 설정된 로컬 PostgreSQL과 네트워크 접근이 가능한 환경에서는 `python -m batch.main`을 두 번 실행하고, DB 조회로 `stock_price`에 `(stock_id, trade_date)` 중복이 없음을 확인한다.

## 구체적인 단계

작업 디렉터리:

    /Users/sehako/workspace/stock-report

1. 실패하는 테스트를 먼저 추가한다. 예상 변경 파일은 `app/batch/tests/jobs/stock_daily_price/test_service.py`, `app/batch/tests/jobs/stock_daily_price/test_stock_daily_price_runner.py`, `app/batch/tests/jobs/stock_daily_price/test_stock_daily_price_repository.py`이다. 테스트는 외부 네트워크와 실제 DB 없이 동작해야 한다.

2. 도메인 모델과 정규화 로직을 추가한다. 예상 변경 파일은 `app/batch/src/jobs/stock_daily_price/domain/model.py`, `app/batch/src/jobs/stock_daily_price/domain/service.py`, `app/batch/src/jobs/stock_daily_price/domain/repository.py`이다. 모델은 `TrackedStock`, `StockDailyPrice`, `StockDailyPriceCollectionResult` 같은 이름을 사용한다. 정규화 함수는 FDR 결과의 `Open`, `High`, `Low`, `Close`, `Volume`, `Change` 컬럼과 날짜 index를 읽어 저장 가능한 가격 목록을 만든다. `Open`, `High`, `Low`, `Close`, `Volume`, 거래일은 필수값으로 보고, `Change`는 선택값으로 처리한다. 일부 row만 깨졌으면 정상 row는 저장 대상으로 남기고 제외 row 수와 사유를 결과에 남긴다. 같은 거래일이 중복되면 마지막 row 하나만 남긴다.

3. FDR client를 추가한다. 예상 변경 파일은 `app/batch/src/jobs/stock_daily_price/infrastructure/client/finance_data_reader_client.py`이다. client는 실제 `FinanceDataReader` import를 메서드 안에서 수행해 테스트에서 외부 라이브러리를 직접 호출하지 않게 한다. 마지막 적재일이 있으면 그 다음 날부터 조회하고, 마지막 적재일이 없으면 `f"KRX:{stock_code}"`와 `"1900-01-01"`로 전체 KRX 기간 조회를 요청한다.

4. application runner를 추가한다. 예상 변경 파일은 `app/batch/src/jobs/stock_daily_price/application/dto.py`, `app/batch/src/jobs/stock_daily_price/application/stock_daily_price_runner.py`이다. runner는 저장소에서 tracked 종목을 조회하고, 종목별 시작일을 계산하고, client에서 일봉을 가져오고, service로 정규화한 뒤 저장소에 upsert를 요청한다. 각 종목별 성공, 스킵, 실패 로그를 남긴다.

5. PostgreSQL 저장소를 추가한다. 예상 변경 파일은 `app/batch/src/jobs/stock_daily_price/infrastructure/persistence/stock_daily_price_repository.py`이다. tracked 종목 조회 SQL은 `stock`을 기준으로 `LEFT JOIN stock_price`를 사용해 가격이 없는 종목도 가져와야 한다. 가격 저장 SQL은 `INSERT INTO stock_price (...) VALUES (...) ON CONFLICT (stock_id, trade_date) DO UPDATE SET ...` 형태로 작성한다.

6. 기본 실행을 연결하고 README를 갱신한다. 예상 변경 파일은 `app/batch/src/batch/main.py`, `app/batch/README.md`이다. README는 이제 기본 배치가 종목 universe 갱신 뒤 tracked 종목 일봉을 적재한다는 점과 수동 검증 쿼리를 한글로 설명한다. `main.py` 변경은 기존 `StockUniverseRunner.run()` 뒤에 새 runner를 조합하는 데 한정하고, 선행 `stock_universe`가 실패하면 일봉 적재 runner를 실행하지 않는다.

7. 자동 테스트를 실행한다.

    cd /Users/sehako/workspace/stock-report/app/batch
    .venv/bin/python -m pytest

    기대 결과는 모든 배치 테스트가 통과하는 것이다. `.venv`가 없다면 `python3.14 -m venv .venv`, `. .venv/bin/activate`, `python -m pip install -e ".[dev]"` 순서로 준비한다.

8. 가능한 경우 수동 통합 검증을 실행한다.

    cd /Users/sehako/workspace/stock-report/app/batch
    . .venv/bin/activate
    python -m batch.main
    python -m batch.main

    DB 중복 확인 쿼리는 다음과 같다.

    SELECT COUNT(*)
    FROM (
        SELECT stock_id, trade_date
        FROM stock_price
        GROUP BY stock_id, trade_date
        HAVING COUNT(*) > 1
    ) duplicated;

    기대 결과는 `0`이다. 추가로 `SELECT COUNT(*) FROM stock_price;` 값이 첫 실행 이후에는 늘 수 있지만, 같은 원천 데이터 상태에서 두 번째 실행으로 중복 row가 생기면 안 된다.

## 검증과 수락 기준

수락 기준은 다음과 같다.

- 사용자는 `app/batch`에서 `python -m batch.main`을 실행해 tracked 종목의 일봉 적재를 시작할 수 있다.
- 배치는 `stock.tracked = true` 종목을 조회하고, 각 종목의 마지막 적재일을 `stock_price.MAX(trade_date)`로 계산한다.
- 최초 적재 종목은 `KRX:{stock_code}`와 `1900-01-01` 시작일로 FDR이 조회 가능한 최대 KRX 일봉을 요청하고, 저장 가능한 row를 `stock_price`에 저장한다.
- 이미 적재된 종목은 마지막 적재일 다음 날 이후 일봉만 조회하며, 주말과 공휴일 보정은 하지 않는다.
- 저장된 row에는 `stock_id`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`이 채워진다. `change_rate`는 FDR의 `Change` 원값이며, `Change`가 없거나 변환할 수 없으면 `NULL`로 저장한다.
- 같은 배치를 반복 실행해도 `stock_id`, `trade_date` 기준 중복 row가 생기지 않는다.
- 한 종목 수집 실패가 다른 종목 수집을 중단하지 않고, 실패 종목의 종목코드와 종목명이 로그에 남는다. 개별 종목 실패가 있어도 `stock_daily_price` 작업은 성공 종료한다.
- 필수 설정 누락, DB 연결 실패, tracked 종목 목록 조회 실패, 선행 `stock_universe` 실패처럼 작업 자체를 시작하거나 입력 집합을 준비할 수 없는 오류는 전체 배치 실패로 처리한다.
- 기본 실행 연결은 `main.py`에서 기존 `stock_universe` runner 뒤에 새 일봉 적재 runner를 호출하는 조합 변경으로 한정한다. 거래량 상위 200개 종목 선정 내부 로직, 지수 일봉 적재, 지정 재수집 옵션, 배치 실패 이력 테이블 저장은 새로 구현되지 않는다.

자동 테스트는 최소한 다음을 검증해야 한다.

- FDR 일봉 row가 `StockDailyPrice` 모델로 정규화된다.
- `Change`가 없거나 변환할 수 없는 row는 `change_rate = None`으로 정규화된다.
- 일부 row만 필수값 정규화에 실패하면 정상 row는 유지되고 실패 row 수가 결과에 남는다.
- 같은 거래일 중복 row가 있으면 마지막 row가 남고 중복 제거 수가 결과에 남는다.
- 마지막 적재일이 있으면 다음 날을 시작일로 계산하고, 없으면 `KRX:{stock_code}`와 `1900-01-01`로 최대 KRX 기간 조회를 요청한다.
- 빈 FDR 결과는 스킵으로 기록된다.
- 한 종목 client 예외 또는 저장소 예외가 다음 종목 처리를 막지 않고, 개별 종목 실패만으로 runner 결과가 전체 실패가 되지 않는다.
- 저장소 조회 SQL이 tracked 종목과 마지막 적재일을 함께 읽는다.
- 저장소 upsert SQL이 `ON CONFLICT (stock_id, trade_date) DO UPDATE`를 사용한다.
- 저장소 저장은 종목 단위 commit과 rollback을 수행한다.
- 기본 실행은 `stock_universe` 실패 시 `stock_daily_price`를 호출하지 않는다.
- 기존 `stock_universe` 테스트가 계속 통과한다.

## 멱등성과 복구

가격 저장은 데이터베이스 유니크 제약 `uk_stock_price_stock_trade_date`와 `ON CONFLICT (stock_id, trade_date) DO UPDATE` upsert를 사용하므로 같은 종목과 거래일을 여러 번 저장해도 최종 row는 하나여야 한다. 충돌이 발생하면 기존 row는 FDR 원천 데이터 기준으로 갱신된다. 실행 중 특정 종목이 실패하면 그 종목의 이번 저장분은 rollback되고, 이미 성공한 다른 종목의 저장 결과는 유지된다. 실패한 종목은 다음 전체 실행에서 다시 시도된다.

이 계획은 데이터 삭제, 강제 초기화, 강제 푸시를 요구하지 않는다. 수동 통합 검증에서 로컬 DB 데이터가 많아져도 중복 확인 쿼리로 안전하게 상태를 확인한다. 테스트용으로 데이터를 지워야 하는 상황이 생기면 이 ExecPlan을 구현하는 사람은 먼저 사용자에게 명시적으로 확인받아야 한다.

## 산출물과 메모

계획 작성 시 확인한 핵심 파일은 다음과 같다.

    docs/issues/03-batch-stock-daily-price-loading.md
    docs/specs/2026-07-15-stock-market-data-service-design.md
    docs/architecture/batch.md
    docs/plans/batch/issue-02-batch-stock-universe-selection.md
    app/batch/src/batch/main.py
    app/batch/src/jobs/stock_universe/domain/service.py
    app/batch/src/jobs/stock_universe/application/stock_universe_runner.py
    app/batch/src/jobs/stock_universe/infrastructure/persistence/stock_universe_repository.py
    app/batch/tests/jobs/stock_universe/test_service.py
    app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql
    app/backend/src/test/kotlin/com/stockreport/marketdata/MarketDataSchemaTest.kt

FDR 조회 정책을 확인한 참고 문서는 다음과 같다.

    https://github.com/FinanceData/FinanceDataReader/wiki/Quick-Start
    https://github.com/FinanceData/FinanceDataReader/wiki/Release-Note-0.9.92
    https://github.com/FinanceData/FinanceDataReader/wiki/Release-Note-0.9.110

현재 저장소에서 확인한 `stock_price` 생성 SQL의 핵심은 다음과 같다.

    CREATE TABLE stock_price (
        id BIGSERIAL PRIMARY KEY,
        stock_id BIGINT NOT NULL,
        trade_date DATE NOT NULL,
        open_price NUMERIC(19, 4) NOT NULL,
        high_price NUMERIC(19, 4) NOT NULL,
        low_price NUMERIC(19, 4) NOT NULL,
        close_price NUMERIC(19, 4) NOT NULL,
        volume BIGINT NOT NULL,
        change_rate NUMERIC(10, 4),
        CONSTRAINT fk_stock_price_stock FOREIGN KEY (stock_id) REFERENCES stock (id),
        CONSTRAINT uk_stock_price_stock_trade_date UNIQUE (stock_id, trade_date)
    );

## 인터페이스와 의존성

새로 추가할 주요 Python 인터페이스는 다음과 같다.

`jobs.stock_daily_price.domain.repository.StockDailyPriceRepository`는 tracked 종목 조회와 가격 upsert를 정의한다. 구현체는 `jobs.stock_daily_price.infrastructure.persistence.stock_daily_price_repository.PsycopgStockDailyPriceRepository`로 둔다.

`jobs.stock_daily_price.infrastructure.client.finance_data_reader_client.FinanceDataReaderStockPriceClient`는 FDR 일봉 조회를 감싼다. 외부 네트워크 호출은 이 class 밖으로 퍼뜨리지 않는다.

`jobs.stock_daily_price.application.stock_daily_price_runner.StockDailyPriceRunner`는 작업의 유스케이스를 조합한다. 이 runner는 한 종목 실패를 잡아 로그와 결과 DTO에 반영하고 다음 종목으로 진행한다.

기존 의존성 `finance-datareader`, `pandas`, `psycopg[binary]`, `pytest`를 그대로 사용한다. 새 의존성을 추가하지 않는 방향이 기본 계획이다. 구현 중 기존 의존성만으로 날짜 index 변환이나 Decimal 변환을 안정적으로 처리하기 어렵다는 증거가 나오면, 새 의존성 추가 여부를 `결정 기록`에 남기고 사용자에게 영향 범위를 보고한다.

계획 변경 메모:

- 2026-07-19 / Codex: 계획 초안 작성. 이유: `docs/issues/03-batch-stock-daily-price-loading.md`의 Python 배치 구현을 현재 저장소 구조와 실제 DB 스키마에 맞춰 자기완결적으로 수행할 수 있게 하기 위해서.
- 2026-07-19 / Codex: 계획 검토 결과를 반영했다. 이유: 부분 실패 종료 상태, `stock_universe` 연결 범위, 최초/증분 FDR 조회 방식, `DO UPDATE` upsert, `Change` nullable 처리, row 정규화 실패 처리, 중복 거래일 처리, 종목 단위 트랜잭션 경계를 구현자가 추가 판단 없이 따를 수 있게 하기 위해서.
