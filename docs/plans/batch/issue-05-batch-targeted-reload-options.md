# ExecPlan: 시장 데이터 지정 재수집 옵션 구현

이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다. 이 문서는 `docs/issues/05-batch-targeted-reload-options.md`의 구현 계획이며, 저장소를 처음 보는 사람도 이 파일만 읽고 작업을 이어갈 수 있도록 필요한 맥락과 결정을 포함한다.

## 목적과 큰 그림

이 계획은 Python 배치에 특정 종목, 특정 지수, 특정 기간만 다시 수집하는 명령행 옵션을 추가하기 위한 실행 계획이다. 구현 전에는 사용자가 `python -m batch.main`을 실행하면 종목 universe 갱신, tracked 종목 전체 일봉 적재, 코스피/코스닥 지수 전체 증분 적재가 항상 순서대로 실행된다. 특정 기간의 원천 데이터가 정정되었거나 특정 종목 또는 지수 수집만 실패했을 때도 전체 기본 배치를 다시 실행해야 한다.

구현 후 사용자는 `app/batch`에서 `python -m batch.main --stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31`처럼 실행해 삼성전자 종목의 2024년 1월 일봉만 다시 upsert할 수 있다. 사용자는 `python -m batch.main --index-code KOSPI --start-date 2024-01-01 --end-date 2024-01-31`처럼 실행해 코스피 지수의 지정 기간 일봉만 다시 upsert할 수 있다. 옵션을 지정하지 않으면 지금과 같은 기본 실행 흐름을 유지해야 한다.

이 계획에서 "지정 재수집"은 이미 저장된 row가 있으면 같은 고유 키 기준으로 갱신하고, 없으면 새로 넣는 upsert를 지정 입력에 대해서만 수행하는 것을 뜻한다. "기간"은 `YYYY-MM-DD` 형식의 시작일과 종료일을 포함하는 닫힌 범위다. 닫힌 범위란 시작일과 종료일 양쪽 날짜가 모두 수집 대상에 포함된다는 뜻이다. 실제 외부 호출은 `FinanceDataReader.DataReader(symbol, start, end)`처럼 시작일과 종료일 문자열을 넘기는 방식으로 계획한다.

이 이슈는 배치 실행 이력 테이블, 관리자 화면, 실패 관리 화면, Spring Boot 조회 API 변경을 다루지 않는다. 데이터베이스 스키마도 바꾸지 않는다. 기존 `stock_price`의 `(stock_id, trade_date)` 유니크 제약과 `market_index_price`의 `(index_code, trade_date)` 유니크 제약을 그대로 사용한다.

## 진행 상황

- [x] (2026-07-22) 이슈 본문, 참고 MVP 설계 문서, 배치 아키텍처 문서, ExecPlan 지침을 확인했다.
- [x] (2026-07-22) 현재 Python 배치 진입점, 종목 일봉 runner/client/repository, 지수 일봉 runner/client/repository, 관련 테스트를 조사했다.
- [x] (2026-07-22) 기존 배치 계획 문서와 최근 커밋을 확인해 `docs/plans/batch` 아래 한국어 ExecPlan 관례를 확인했다.
- [x] (2026-07-22) 구현 위치, 데이터 흐름, 검증 방법, 미결정 옵션 조합을 현재 저장소 상태 기준으로 계획했다.
- [x] (2026-07-23) 구현 시작 전 미결정 옵션 조합과 지정 단건 실패 정책을 확정했다.
- [x] (2026-07-23) CLI 옵션 파싱과 실행 모드 선택 테스트를 먼저 작성했고, `main(argv)` 미지원 실패를 확인한 뒤 구현했다.
- [x] (2026-07-23) 종목 지정 재수집 runner, repository, FDR client 테스트를 먼저 작성했고, 각 RED 실패를 확인한 뒤 구현했다.
- [x] (2026-07-23) 지수 지정 재수집 runner와 FDR client 테스트를 먼저 작성했고, 각 RED 실패를 확인한 뒤 구현했다.
- [x] (2026-07-23) README에 기본 실행, 종목 지정 재수집, 지수 지정 재수집, 지원하지 않는 조합과 수동 확인 쿼리를 갱신했다.
- [x] (2026-07-23) `cd app/batch && .venv/bin/python -m pytest`로 전체 자동 테스트 66개 통과를 확인했다.
- [x] (2026-07-23) 로컬 PostgreSQL 접속 정보 `postgresql://app:app@localhost:5432/stock_report`와 외부 FDR 접근으로 종목/지수 지정 재수집 수동 통합 검증을 완료했다.
- [x] (2026-07-23) 결과와 회고를 작성했다.
- [x] (2026-07-23) ExecPlan 최종 상태를 확인했다.

## 예상 밖의 발견

- 관찰: 현재 `app/batch/src/batch/main.py`는 명령행 인자를 전혀 읽지 않고, 옵션 없는 기본 실행만 수행한다.
  증거: `main()`은 `load_batch_config()`, `configure_logging()`, `StockUniverseRunner.run()`, `StockDailyPriceRunner.run()`, `MarketIndexDailyPriceRunner.run()`을 순서대로 호출한다.
  영향: 이슈 05 구현은 `main.py`에 인자 파싱과 실행 모드 선택을 추가해야 한다. 다만 `main.py`에는 도메인 규칙, SQL, 외부 API 세부 구현을 넣지 않고 application 계층의 명령 객체 또는 runner로 위임해야 한다.

- 관찰: 종목 일봉 client와 지수 일봉 client는 현재 `end` 값을 받지 않는다.
  증거: `FinanceDataReaderStockPriceClient.fetch_daily_prices(stock_code, last_loaded_date)`와 `FinanceDataReaderMarketIndexPriceClient.fetch_daily_prices(target, last_loaded_date)`는 마지막 적재일로 시작일만 계산하고 `fdr.DataReader(symbol, start)`만 호출한다.
  영향: 지정 기간 재수집을 구현하려면 client 계약을 `start_date`, `end_date`를 표현할 수 있게 확장해야 한다. 기존 기본 실행의 마지막 적재일 기반 증분 적재가 깨지지 않도록 새 command DTO를 통해 기본 실행과 지정 실행을 구분하는 계획이 필요하다.

- 관찰: 종목 가격 저장에는 `stock.id`가 필요하지만 CLI 입력은 `--stock-code` 문자열이다.
  증거: `PsycopgStockDailyPriceRepository.upsert_stock_prices(stock_id, prices)`는 `stock_price.stock_id`에 내부 기본키를 저장한다. 현재 repository의 조회 메서드는 tracked 전체 종목만 반환한다.
  영향: 지정 종목 재수집에는 `stock_code`로 단일 종목을 찾는 repository 메서드가 필요하다. 찾은 종목이 tracked가 아니어도 `stock` 테이블에 존재하면 내부 `stock_id`가 있으므로 저장은 가능하다. `stock` 테이블에 없는 종목코드는 명확한 오류로 처리해야 한다.

- 관찰: 지수 지정 재수집은 DB 조회 없이도 지원 대상 목록에서 `index_code`를 검증할 수 있다.
  증거: `app/batch/src/jobs/market_index_daily_price/domain/model.py`는 `SUPPORTED_MARKET_INDEX_TARGETS`에 `KOSPI -> KS11`, `KOSDAQ -> KQ11`만 정의한다. DB 체크 제약도 `KOSPI`, `KOSDAQ`만 허용한다.
  영향: `--index-code`는 대소문자 정책을 정하고 지원 목록에서 검증해야 한다. 지원하지 않는 값은 외부 FDR 호출 전 명확한 오류로 종료해야 한다.

- 관찰: 참고 설계 문서에는 `python batch.py --start-date 2024-01-01 --end-date 2024-12-31` 예가 있지만, 이슈의 검증 흐름은 `--stock-code`와 기간 조합만 명확하게 제시한다.
  증거: `docs/specs/2026-07-15-stock-market-data-service-design.md`의 지정 실행 예시는 기간 단독 실행을 포함한다. `docs/issues/05-batch-targeted-reload-options.md`의 작업 범위는 종목 코드와 기간 조합, 지수 코드와 기간 조합을 명시하고, 검증 흐름도 `--stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31`이다.
  영향: 기간만 지정했을 때 모든 tracked 종목과 모든 지수를 재수집할지, 아니면 지원하지 않는 조합으로 볼지 구현 전에 확정해야 했다. 2026-07-23 결정으로 이번 이슈에서는 기간 단독 실행을 지원하지 않는 옵션 조합으로 처리한다.

- 관찰: 작업트리에는 최초에 `app/batch/.venv`가 없었고, `python3 -m venv .venv`는 Python 3.9 환경을 만들어 `date | None` 타입 문법에서 테스트 수집 오류가 발생했다.
  증거: `.venv/bin/python -m pytest tests/test_batch_main.py` 실행 시 `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`가 발생했다.
  영향: 프로젝트 요구사항인 Python 3.11 이상에 맞춰 `python3.14 -m venv .venv`로 가상환경을 다시 만들고 테스트를 실행했다.

- 관찰: 이 작업트리의 `app/batch`는 editable install 상태가 아니어서 직접 `python -m batch.main` 실행 시 모듈을 찾지 못했다.
  증거: `DATABASE_URL=... .venv/bin/python -m batch.main --stock-code 005930 ...` 실행 시 `ModuleNotFoundError: No module named 'batch'`가 발생했다.
  영향: 수동 통합 검증 명령에는 `PYTHONPATH=src`를 함께 지정해 현재 소스 트리의 `batch.main`을 실행했다. README의 준비 절차처럼 패키지가 설치된 환경에서는 `python -m batch.main`으로 실행할 수 있다.

## 결정 기록

- 결정: 구현 계획은 `main.py`에 `argparse` 기반 CLI 파싱을 추가하고, 파싱 결과를 application 계층 command DTO로 넘기는 방식을 사용한다.
  근거: `docs/architecture/batch.md`는 `main.py`가 명령행 인자와 환경 설정을 읽고 실행할 runner를 선택하며, 실행 인자는 application 계층에서 사용할 명령 객체 또는 DTO로 변환한다고 설명한다. 현재 코드도 runner가 유스케이스 흐름을 조합하고 repository와 client가 세부 구현을 맡는다.
  검토한 대안: 별도 `TargetedReloadRunner`를 새로 만들면 기본 runner와 정규화/저장 흐름이 중복된다. 기존 runner 내부에 CLI 조건문을 직접 섞으면 `main.py`와 application 경계가 흐려지고 테스트 단위가 커진다.
  영향: `StockDailyPriceRunner.run()`과 `MarketIndexDailyPriceRunner.run()`은 선택 command를 받을 수 있게 확장한다. command가 없으면 현재 기본 실행과 같은 증분 적재를 수행하고, command가 있으면 지정 대상과 기간만 처리한다.

- 결정: 지정 재수집의 기간은 `--start-date`와 `--end-date`를 둘 다 요구한다.
  근거: 이슈는 특정 기간만 재수집하는 옵션을 요구한다. 시작일 또는 종료일 한쪽만 받으면 현재 증분 적재 규칙, 오늘 날짜, FDR 종료일 의미를 섞어야 해서 오류 가능성이 커진다.
  검토한 대안: 시작일만 받으면 종료일을 생략해 최신일까지 가져올 수 있다. 그러나 명확한 재수집 범위를 요구하는 이슈와 맞지 않고, 실수로 긴 기간을 다시 요청할 수 있다.
  영향: `--stock-code` 또는 `--index-code`가 지정된 실행에서는 `--start-date`와 `--end-date`가 모두 있어야 한다. 한쪽만 있거나 날짜 형식이 틀리거나 시작일이 종료일보다 늦으면 명확한 오류를 반환한다.

- 결정: `--start-date` 또는 `--end-date`가 하나라도 지정되면 `--stock-code` 또는 `--index-code` 중 하나가 반드시 함께 지정되어야 한다.
  근거: 옵션 없는 기본 배치는 이미 전체 대상의 마지막 적재일 다음 날부터 최신일까지 증분 수집한다. 기간만 지정해 전체 tracked 종목과 전체 지수를 재수집하게 만들면 실행 시간, 외부 호출 수, 실패 처리, 검증 범위가 이번 이슈보다 커진다.
  검토한 대안: 기간만 지정하면 모든 tracked 종목과 모든 지원 지수의 해당 기간을 재수집하게 할 수 있다. 그러나 그 기능은 대량 재수집 정책과 운영 안전장치가 필요하므로 별도 이슈에서 `--all --start-date --end-date`처럼 의도가 드러나는 옵션으로 다루는 편이 안전하다.
  영향: `python -m batch.main --start-date 2024-01-01 --end-date 2024-01-31`은 CLI 검증 오류로 실패한다. 오류 메시지는 기간 옵션은 `--stock-code` 또는 `--index-code`와 함께 지정해야 한다는 뜻을 담아야 한다.

- 결정: `--stock-code`와 `--index-code`를 동시에 지정하는 조합은 지원하지 않는다.
  근거: 종목 일봉과 지수 일봉은 서로 다른 저장 대상과 입력 모델을 가진다. 한 명령에서 둘을 동시에 처리하면 실패 처리, 결과 요약, 수동 검증 기준이 불필요하게 복잡해진다.
  검토한 대안: 둘을 동시에 허용해 한 번의 명령에서 종목과 지수를 같이 재수집할 수 있다. 하지만 이슈의 검증 흐름은 한 대상 단위 재수집이고, 복구 작업에서도 실패한 대상별로 명령을 나누는 편이 원인 추적이 쉽다.
  영향: 동시에 지정하면 CLI 검증 단계에서 외부 호출 없이 실패한다.

- 결정: `--index-code` 입력은 대소문자를 구분하지 않고 받되, 내부 command와 로그 및 저장 값은 `KOSPI`, `KOSDAQ` 대문자 공식 코드로 정규화한다.
  근거: `kospi`와 `kosdaq`은 CLI 사용자가 자연스럽게 입력할 수 있는 값이며, command 생성 단계에서 대문자로 정규화하면 DB 체크 제약과 로그 식별성은 유지된다.
  검토한 대안: `KOSPI`, `KOSDAQ`만 정확히 허용하면 계약은 단순하지만 사용자가 소문자 입력으로 불필요하게 실패할 수 있다. 반대로 `KS11`, `KQ11` 같은 FDR 심볼 별칭까지 허용하면 CLI 옵션 이름인 `--index-code`의 의미와 DB의 공식 `index_code` 계약이 흐려진다.
  영향: `--index-code KOSPI`, `--index-code kospi`, `--index-code KosDaQ`는 허용하고 각각 `KOSPI`, `KOSDAQ`으로 정규화한다. `--index-code KS11`, `--index-code KQ11`, `--index-code S&P500`, `--index-code UNKNOWN`은 외부 FDR 호출 전에 실패한다.

- 결정: `--stock-code`는 정확히 6자리 숫자 문자열만 CLI에서 허용한다.
  근거: 한국 종목코드는 앞자리 0이 의미 있는 문자열이다. `5930`이나 `005930.KS`를 DB 조회까지 넘기면 사용자가 어떤 식별자를 의도했는지 모호해지고, `stock.stock_code`와 CLI 계약이 흐려진다.
  검토한 대안: 임의 문자열을 받아 DB 조회 또는 FDR 호출 단계에서 실패하게 둘 수 있다. 그러나 형식 오류는 외부 호출이나 DB 조회 전에 명확히 잡는 편이 사용자가 잘못된 입력을 바로 고칠 수 있다.
  영향: `--stock-code 005930`과 `--stock-code 000660` 같은 값만 허용한다. `--stock-code 5930`, `--stock-code 005930.KS`, `--stock-code 삼성전자`, `--stock-code ABCDEF`는 CLI 검증 오류로 실패한다.

- 결정: 지정 종목은 `stock.tracked = true` 여부와 관계없이 `stock` 테이블에 존재하면 재수집 대상으로 허용한다.
  근거: 지정 재수집은 실패 복구와 데이터 보정 목적이다. 과거에 tracked였다가 현재 상위 200개에서 빠진 종목도 이미 `stock`에 남아 있고, 해당 종목의 과거 가격 보정이 필요할 수 있다.
  검토한 대안: tracked 종목만 허용하면 현재 조회 대상만 관리할 수 있어 단순하지만, 기존 저장 데이터 보정 범위가 좁아진다.
  영향: repository에는 `find_stock_by_code(stock_code)` 같은 단일 종목 조회 메서드를 추가한다. 동일 `stock_code`가 여러 market에 존재하는 미래 확장은 이슈 범위 밖이지만, 현재 KRX MVP에서는 `stock_code` 단독 조회 결과가 하나여야 한다는 전제로 구현한다.

- 결정: 6자리 숫자 형식은 맞지만 `stock` 테이블에 없는 종목코드는 CLI 검증 오류가 아니라 runner 실행 오류로 처리한다.
  근거: `005930`처럼 형식이 올바른지는 명령행 파싱 단계에서 판단할 수 있지만, 해당 코드가 현재 DB의 `stock` 테이블에 존재하는지는 repository 조회가 필요하다.
  검토한 대안: CLI command 생성 단계에서 DB까지 조회해 존재 여부를 검증할 수 있다. 그러나 `main.py`가 실행 모드 선택과 인자 변환을 맡고 실제 조회 흐름은 application runner에 위임한다는 배치 아키텍처 원칙과 맞지 않는다.
  영향: `--stock-code 123456 --start-date 2024-01-01 --end-date 2024-01-31`처럼 6자리 숫자 입력은 CLI 검증을 통과한다. 이후 `StockDailyPriceRunner`가 `stock_code = '123456'`을 조회했을 때 결과가 없으면 외부 FDR 호출 전에 명확한 오류로 실패한다.

- 결정: 새 의존성은 추가하지 않는다.
  근거: Python 표준 라이브러리 `argparse`와 `datetime.date.fromisoformat()`으로 CLI 파싱과 날짜 검증을 구현할 수 있다. 기존 프로젝트 의존성에 이미 `finance-datareader`, `pandas`, `psycopg`, `pytest`가 있다.
  검토한 대안: `click`이나 `typer` 같은 CLI 라이브러리를 추가할 수 있지만, 이번 옵션 수와 검증 규칙에는 과하다.
  영향: `app/batch/pyproject.toml`은 변경하지 않는 방향으로 계획한다.

- 결정: 지정 기간 실행에서는 FDR 호출에 `start`와 `end`를 넘긴 뒤, 정규화된 가격 목록을 command 기간으로 한 번 더 필터링한다.
  근거: 이슈는 지정 기간 데이터만 upsert되는지 확인하라고 요구한다. 외부 라이브러리의 종료일 포함 여부나 반환 범위가 바뀌어도 DB 쓰기 전 내부 필터링을 수행하면 요청 기간 밖 row 저장을 막을 수 있다.
  검토한 대안: FDR 호출 인자만 신뢰할 수 있지만, 그러면 외부 라이브러리 동작 변화가 곧바로 DB 저장 범위 변화로 이어진다.
  영향: 지정 실행 테스트는 FDR fake가 기간 밖 row를 포함해도 runner가 기간 안 row만 repository에 넘기는지 검증해야 한다. 기본 증분 실행에는 이 추가 필터를 적용하지 않는다.

- 결정: 지정 단건 재수집에서는 정상 수집이 되지 않으면 모두 실패로 처리하고 프로세스가 비정상 종료되게 한다.
  근거: 지정 재수집은 사용자가 특정 종목 또는 특정 지수 하나의 누락이나 정정을 복구하려고 실행하는 명령이다. 그 하나가 실패했는데 exit code 0으로 끝나면 운영 스크립트나 사용자가 성공으로 오해할 수 있다.
  검토한 대안: 기본 전체 배치처럼 실패를 result DTO와 로그에 누적하고 정상 종료할 수 있다. 그러나 기본 배치는 여러 대상 중 일부 실패를 기록하고 다음 대상을 처리해야 하는 흐름이고, 지정 단건 실행은 요청 대상 하나의 성공 여부가 명령 전체의 성공 여부다.
  영향: 지정 실행에서 CLI 조합 오류, 날짜 형식 오류, 존재하지 않는 종목코드, 지원하지 않는 지수 코드, FDR 호출 실패, 정규화 실패, DB 저장 실패, 저장 가능한 row 0건은 모두 실패다. `main.py`는 지정 실행 result에 실패가 있거나 저장된 row가 없으면 명확한 예외를 발생시켜 비정상 종료하게 한다. 옵션 없는 기본 전체 배치의 기존 실패 누적 방식은 유지한다.

## 맥락과 방향 안내

저장소 루트는 `/Users/sehako/workspace/stock-report`이다. Python 배치 코드는 `app/batch` 아래에 있으며, 실행 진입점은 `app/batch/src/batch/main.py`이다. 개발자는 `cd app/batch` 후 `.venv/bin/python -m batch.main` 또는 가상환경을 활성화한 뒤 `python -m batch.main`으로 배치를 실행한다.

현재 기본 실행은 세 단계다. 첫째, `StockUniverseRunner`가 KRX 종목 목록을 읽고 거래량 상위 200개를 `stock.tracked = true`로 갱신한다. 둘째, `StockDailyPriceRunner`가 `stock.tracked = true` 종목 전체를 조회해 `stock_price`에 일봉을 upsert한다. 셋째, `MarketIndexDailyPriceRunner`가 `KOSPI`, `KOSDAQ` 두 지수의 일봉을 `market_index_price`에 upsert한다. 지정 옵션이 없을 때 이 세 단계와 순서는 바뀌면 안 된다.

종목 일봉 작업은 `app/batch/src/jobs/stock_daily_price`에 있다. `application/stock_daily_price_runner.py`는 저장소에서 tracked 종목과 마지막 적재일을 읽고, client로 FDR 일봉을 가져오고, domain service로 row를 정규화하고, repository로 upsert한다. `infrastructure/client/finance_data_reader_client.py`는 현재 `FinanceDataReader.DataReader(stock_code, start)`를 호출한다. `infrastructure/persistence/stock_daily_price_repository.py`는 `stock`과 `stock_price`를 조인해 tracked 전체 종목을 읽고, `ON CONFLICT (stock_id, trade_date) DO UPDATE`로 저장한다.

지수 일봉 작업은 `app/batch/src/jobs/market_index_daily_price`에 있다. `domain/model.py`는 `SUPPORTED_MARKET_INDEX_TARGETS`에 `KOSPI -> KS11`, `KOSDAQ -> KQ11` 매핑을 둔다. `application/market_index_daily_price_runner.py`는 지원 지수 전체를 순회한다. `infrastructure/client/finance_data_reader_client.py`는 `FinanceDataReader.DataReader(target.fdr_symbol, start)`를 호출한다. `infrastructure/persistence/market_index_daily_price_repository.py`는 `market_index_price`에서 지수별 마지막 적재일을 조회하고, `ON CONFLICT (index_code, trade_date) DO UPDATE`로 저장한다.

테스트는 `app/batch/tests` 아래에 있다. 현재 테스트는 외부 네트워크와 실제 DB에 의존하지 않도록 fake client, fake repository, fake connection, fake `FinanceDataReader` module을 사용한다. 이 이슈의 자동 테스트도 같은 방식을 따라야 한다. 실제 PostgreSQL과 FDR 네트워크 호출은 수동 통합 검증으로 분리한다.

## 구현 접근

구현은 먼저 CLI 입력을 작은 명령 객체로 바꾸는 흐름을 만든다. `main.py`에는 `argparse.ArgumentParser`를 사용해 `--stock-code`, `--index-code`, `--start-date`, `--end-date`를 정의한다. 파싱 결과는 `DefaultBatchCommand`, `ReloadStockDailyPriceCommand`, `ReloadMarketIndexDailyPriceCommand`처럼 application에서 이해할 수 있는 값으로 변환한다. 실제 이름은 기존 DTO 네이밍 규칙인 `ReloadStockDailyPriceCommand` 같은 형태를 따른다. `--stock-code`는 정확히 6자리 숫자 문자열만 허용하고, `--index-code`는 대소문자를 허용하되 command 생성 시점에 `KOSPI` 또는 `KOSDAQ` 대문자 공식 코드로 정규화한다.

`main.py`는 실행 모드만 선택한다. 옵션이 없으면 지금처럼 `stock_universe`, `stock_daily_price`, `market_index_daily_price`를 순서대로 실행한다. `--stock-code`와 기간이 있으면 `stock_universe`는 실행하지 않고 `StockDailyPriceRunner`에 지정 종목 command를 넘겨 종목 일봉만 실행한다. `--index-code`와 기간이 있으면 `MarketIndexDailyPriceRunner`에 지정 지수 command를 넘겨 지수 일봉만 실행한다. 지정 재수집은 이미 존재하는 `stock` row 또는 지원 지수 매핑을 입력으로 삼으므로, universe 갱신을 선행하지 않는다. `--start-date` 또는 `--end-date`가 하나라도 있는데 `--stock-code`와 `--index-code`가 모두 없으면 기간 단독 실행으로 보아 CLI 검증 오류로 실패한다. `--stock-code`와 `--index-code`가 동시에 있으면 CLI 검증 오류로 실패한다.

종목 runner는 command가 없을 때 현재 동작을 유지한다. command가 있으면 repository에서 `stock_code`로 단일 종목을 찾고, 찾은 `stock_id`, `stock_code`, `stock_name`을 사용해 지정 기간 FDR 조회를 수행한다. client는 지정 기간 모드에서 `FinanceDataReader.DataReader(stock_code, start_date.isoformat(), end_date.isoformat())`를 호출한다. 받은 row는 기존 `normalize_stock_daily_prices(stock_id, rows)`로 정규화하고, command 기간 밖 거래일을 제거한 뒤 기존 `upsert_stock_prices(stock_id, prices)`로 저장한다. 저장 대상은 지정 기간 안의 응답 row뿐이며, 기존 DB row 삭제는 하지 않는다.

지수 runner도 command가 없을 때 현재 동작을 유지한다. command가 있으면 `SUPPORTED_MARKET_INDEX_TARGETS`에서 `index_code`를 찾아 단일 `MarketIndexTarget`만 처리한다. client는 지정 기간 모드에서 `FinanceDataReader.DataReader(target.fdr_symbol, start_date.isoformat(), end_date.isoformat())`를 호출한다. 받은 row는 기존 `normalize_market_index_daily_prices(index_code, rows)`로 정규화하고, command 기간 밖 거래일을 제거한 뒤 기존 `upsert_market_index_prices(index_code, prices)`로 저장한다.

오류 처리는 CLI 검증 오류와 runner 실행 오류를 구분한다. 지원하지 않는 옵션 조합, 잘못된 날짜 형식, 시작일이 종료일보다 늦은 경우, 종목코드 형식 오류, 지원하지 않는 지수 코드는 외부 호출이나 DB 조회 전에 명확한 메시지로 실패한다. `argparse` 검증 실패는 `SystemExit`를 발생시킬 수 있으므로 테스트에서는 `pytest.raises(SystemExit)` 또는 파서 함수를 분리해 검증한다. 6자리 숫자 형식은 맞지만 `stock` 테이블에 없는 종목코드는 runner가 repository 조회 후 외부 FDR 호출 전에 실패한다. 지정 단건 실행에서는 FDR 호출 실패, 정규화 실패, DB 저장 실패, 저장 가능한 row 0건도 명령 실패로 처리한다. 옵션 없는 기본 전체 배치는 기존 runner의 실패 누적 방식과 정상 종료 방식을 유지한다.

## 구현 단계

### [x] 1. CLI 옵션 파싱과 검증 테스트를 먼저 작성한다

- 변경 내용: 옵션 없는 실행, 종목 지정 실행, 지수 지정 실행, 잘못된 조합을 검증하는 테스트를 추가한다. `main()`을 직접 호출하기 쉽게 `argv`를 주입할 수 있는 작은 파싱 함수 또는 command 생성 함수를 분리하는 방향을 테스트로 고정한다.
- 예상 변경 파일:
  - `app/batch/tests/test_batch_main.py`
  - `app/batch/src/batch/main.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/test_batch_main.py`
- 완료 조건:
  - 옵션 없는 실행은 기존 세 runner를 같은 순서로 호출한다.
  - `--stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31`은 종목 일봉 runner만 호출한다.
  - `--index-code KOSPI --start-date 2024-01-01 --end-date 2024-01-31`과 `--index-code kospi --start-date 2024-01-01 --end-date 2024-01-31`은 `KOSPI` command로 정규화되어 지수 일봉 runner만 호출한다.
  - `--stock-code`와 `--index-code` 동시 지정, 기간 단독 지정, 날짜 한쪽 누락, 잘못된 날짜 형식, 시작일이 종료일보다 늦은 값은 명확한 오류로 실패한다.
  - `--stock-code 5930`, `--stock-code 005930.KS`, `--stock-code 삼성전자`, `--stock-code ABCDEF`는 DB 조회 전 명확한 오류로 실패한다.

### [x] 2. 종목 지정 재수집 command와 단일 종목 조회를 구현한다

- 변경 내용: `stock_daily_price` application DTO에 지정 종목 재수집 command를 추가하고, repository 인터페이스와 psycopg 구현에 `stock_code`로 단일 종목을 조회하는 메서드를 추가한다. runner는 command가 없으면 기존 tracked 전체 흐름을 유지하고, command가 있으면 단일 종목과 지정 기간만 처리한다.
- 예상 변경 파일:
  - `app/batch/src/jobs/stock_daily_price/application/dto.py`
  - `app/batch/src/jobs/stock_daily_price/application/stock_daily_price_runner.py`
  - `app/batch/src/jobs/stock_daily_price/domain/repository.py`
  - `app/batch/src/jobs/stock_daily_price/infrastructure/persistence/stock_daily_price_repository.py`
  - `app/batch/tests/jobs/stock_daily_price/test_stock_daily_price_runner.py`
  - `app/batch/tests/jobs/stock_daily_price/test_stock_daily_price_repository.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/stock_daily_price/test_stock_daily_price_runner.py tests/jobs/stock_daily_price/test_stock_daily_price_repository.py`
- 완료 조건:
  - fake repository에서 지정 `stock_code`가 조회되고, runner가 해당 종목 하나만 처리한다.
  - 존재하지 않는 종목코드는 외부 FDR 호출 없이 명확한 오류로 실패한다.
  - fake FDR 응답에 지정 기간 밖 거래일이 섞여 있어도 repository에는 지정 기간 안 가격만 전달된다.
  - 지정 실행에서 FDR 응답이 비었거나, 정규화 후 가격이 없거나, 기간 필터 후 가격이 없거나, upsert 결과가 0이면 실패한다.
  - 기존 tracked 전체 실행 테스트가 그대로 통과한다.

### [x] 3. 종목 FDR client에 지정 기간 조회를 추가한다

- 변경 내용: `FinanceDataReaderStockPriceClient`가 기본 증분 실행과 지정 기간 실행을 모두 표현할 수 있게 메서드 인자를 확장한다. 기존 마지막 적재일 기반 호출은 유지하고, 지정 기간 command가 있을 때는 `start_date`와 `end_date`를 ISO 문자열로 넘긴다.
- 예상 변경 파일:
  - `app/batch/src/jobs/stock_daily_price/infrastructure/client/finance_data_reader_client.py`
  - `app/batch/tests/jobs/stock_daily_price/test_finance_data_reader_client.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/stock_daily_price/test_finance_data_reader_client.py`
- 완료 조건:
  - 기존 최초 적재와 마지막 적재일 다음 날짜 호출 테스트가 통과한다.
  - 지정 기간 조회는 fake FDR 호출 목록에서 `("005930", "2024-01-01", "2024-01-31")`처럼 확인된다.

### [x] 4. 지수 지정 재수집 command와 단일 지수 실행을 구현한다

- 변경 내용: `market_index_daily_price` application DTO에 지정 지수 재수집 command를 추가하고, runner가 command가 있을 때 지원 대상 목록에서 단일 지수만 선택하게 한다. 지원하지 않는 `index_code`는 외부 호출 전에 명확한 오류로 처리한다.
- 예상 변경 파일:
  - `app/batch/src/jobs/market_index_daily_price/application/dto.py`
  - `app/batch/src/jobs/market_index_daily_price/application/market_index_daily_price_runner.py`
  - `app/batch/tests/jobs/market_index_daily_price/test_market_index_daily_price_runner.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_market_index_daily_price_runner.py`
- 완료 조건:
  - `KOSPI` 지정 실행은 `KOSDAQ`을 처리하지 않는다.
  - `kospi`, `KosDaQ` 같은 입력은 대문자 공식 코드로 정규화되고, 지원하지 않는 `index_code`는 FDR 호출 없이 실패한다.
  - fake FDR 응답에 지정 기간 밖 거래일이 섞여 있어도 repository에는 지정 기간 안 가격만 전달된다.
  - 지정 실행에서 FDR 응답이 비었거나, 정규화 후 가격이 없거나, 기간 필터 후 가격이 없거나, upsert 결과가 0이면 실패한다.
  - 기존 전체 지수 순회 실행 테스트가 그대로 통과한다.

### [x] 5. 지수 FDR client에 지정 기간 조회를 추가한다

- 변경 내용: `FinanceDataReaderMarketIndexPriceClient`가 기본 증분 실행과 지정 기간 실행을 모두 표현할 수 있게 메서드 인자를 확장한다. 지정 기간 command가 있을 때는 `target.fdr_symbol`, `start_date`, `end_date`를 FDR에 넘긴다.
- 예상 변경 파일:
  - `app/batch/src/jobs/market_index_daily_price/infrastructure/client/finance_data_reader_client.py`
  - `app/batch/tests/jobs/market_index_daily_price/test_market_index_finance_data_reader_client.py`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest tests/jobs/market_index_daily_price/test_market_index_finance_data_reader_client.py`
- 완료 조건:
  - 기존 최초 적재와 마지막 적재일 다음 날짜 호출 테스트가 통과한다.
  - 지정 기간 조회는 fake FDR 호출 목록에서 `("KS11", "2024-01-01", "2024-01-31")`처럼 확인된다.

### [x] 6. README와 수동 검증 절차를 갱신한다

- 변경 내용: `app/batch/README.md`에 옵션 없는 기본 실행과 지정 재수집 실행 예시를 추가한다. 지원하지 않는 조합과 날짜 형식, 수동 중복 확인 쿼리를 함께 적는다.
- 예상 변경 파일:
  - `app/batch/README.md`
- 테스트 또는 검증:
  - 문서 확인
  - `cd app/batch && .venv/bin/python -m pytest`
- 완료 조건:
  - 사용자가 README만 보고 기본 실행, 종목 지정 재수집, 지수 지정 재수집 명령을 구분할 수 있다.
  - 전체 자동 테스트가 통과한다.

### [x] 7. 수동 통합 검증을 수행한다

- 변경 내용: 가능한 환경에서 실제 PostgreSQL과 외부 FDR 네트워크 접근으로 지정 재수집을 실행하고, 중복 row가 없는지 확인한다. 이 단계는 코드 변경이 아니라 검증 기록 갱신이다.
- 예상 변경 파일:
  - `docs/plans/batch/issue-05-batch-targeted-reload-options.md`
- 테스트 또는 검증:
  - `cd app/batch && .venv/bin/python -m pytest`
  - `cd app/batch && python -m batch.main --stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31`
  - `cd app/batch && python -m batch.main --index-code KOSPI --start-date 2024-01-01 --end-date 2024-01-31`
  - DB 중복 확인 쿼리 실행
- 완료 조건:
  - 자동 테스트가 통과한다.
  - 수동 검증 환경이 있으면 지정 기간 실행 후 `stock_price`와 `market_index_price`에 중복 row가 없음을 확인하고 결과를 이 문서에 기록한다.

## 테스트 및 검증 계획

자동 테스트는 외부 네트워크와 실제 개발 DB에 의존하지 않는다. `tests/test_batch_main.py`에서는 fake runner와 monkeypatch로 CLI 실행 모드 선택을 검증한다. 기존 fake runner의 `run()` 메서드는 command 인자를 받을 수 있게 조정해야 한다. 이때 옵션 없는 기본 실행의 호출 순서가 `stock_universe`, `stock_daily_price`, `market_index_daily_price`로 유지되는지 반드시 확인한다.

종목 runner 테스트는 fake repository에 `find_stock_by_code()`를 추가하고, 지정 종목 실행에서 해당 메서드가 호출되는지 확인한다. fake client는 호출 인자를 기록해 지정 기간이 전달되는지 확인한다. fake client가 2023년 12월, 2024년 1월, 2024년 2월 row를 함께 반환하는 테스트를 두고, command 기간이 2024년 1월이면 repository에는 2024년 1월 row만 전달되어야 한다. 저장소 테스트는 `SELECT ... FROM stock WHERE stock_code = %s` 형태의 단일 종목 조회 SQL과 파라미터를 검증한다. 같은 `stock_code`가 없을 때는 외부 호출 없이 명확한 오류로 실패하는 계약을 테스트로 고정한다.

지수 runner 테스트는 `KOSPI` 지정 실행이 `KOSDAQ`을 건너뛰는지 확인한다. 지원하지 않는 지수 코드, 예를 들어 `S&P500` 또는 `UNKNOWN`은 FDR client 호출 없이 실패해야 한다. fake client가 지정 기간 밖 row를 함께 반환해도 repository에는 지정 기간 안 row만 전달되어야 한다. 지수 client 테스트는 기존 시작일 계산 테스트를 유지하면서 지정 기간 호출이 세 번째 인자 `end`를 넘기는지 검증한다.

전체 자동 검증 명령은 다음과 같다.

    cd /Users/sehako/workspace/stock-report/app/batch
    .venv/bin/python -m pytest

`.venv`가 없다면 다음 순서로 준비한다.

    cd /Users/sehako/workspace/stock-report/app/batch
    python3.14 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"

수동 통합 검증은 `DATABASE_URL`이 설정된 로컬 PostgreSQL과 외부 네트워크 접근이 가능한 환경에서만 수행한다. 종목 지정 검증 명령은 다음과 같다.

    cd /Users/sehako/workspace/stock-report/app/batch
    . .venv/bin/activate
    python -m batch.main --stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31

종목 중복 확인 쿼리는 다음과 같다.

    SELECT COUNT(*)
    FROM (
        SELECT stock_id, trade_date
        FROM stock_price
        GROUP BY stock_id, trade_date
        HAVING COUNT(*) > 1
    ) duplicated;

기대 결과는 `0`이다. 지정 종목과 기간만 저장되었는지는 다음 쿼리처럼 확인한다. 이 쿼리는 `005930`의 2024년 1월 row 수를 보여준다.

    SELECT s.stock_code, COUNT(*) AS row_count, MIN(sp.trade_date), MAX(sp.trade_date)
    FROM stock_price sp
    JOIN stock s ON s.id = sp.stock_id
    WHERE s.stock_code = '005930'
      AND sp.trade_date BETWEEN DATE '2024-01-01' AND DATE '2024-01-31'
    GROUP BY s.stock_code;

지수 지정 검증 명령은 다음과 같다.

    python -m batch.main --index-code KOSPI --start-date 2024-01-01 --end-date 2024-01-31

지수 중복 확인 쿼리는 다음과 같다.

    SELECT COUNT(*)
    FROM (
        SELECT index_code, trade_date
        FROM market_index_price
        GROUP BY index_code, trade_date
        HAVING COUNT(*) > 1
    ) duplicated;

기대 결과는 `0`이다.

## 수락 기준

사용자는 옵션 없이 `python -m batch.main`을 실행해 기존 기본 배치 흐름을 그대로 사용할 수 있어야 한다. 이 흐름은 종목 universe 갱신, tracked 종목 일봉 적재, 코스피/코스닥 지수 일봉 적재 순서로 실행되어야 한다.

사용자는 `--stock-code`, `--start-date`, `--end-date`를 함께 지정해 단일 종목의 지정 기간 일봉만 다시 수집할 수 있어야 한다. 지정 종목은 `stock` 테이블에서 내부 `stock_id`를 찾은 뒤 `stock_price`에 `(stock_id, trade_date)` 기준으로 upsert되어야 한다. 같은 명령을 반복 실행해도 중복 row가 생기면 안 된다.

사용자는 `--index-code`, `--start-date`, `--end-date`를 함께 지정해 단일 지수의 지정 기간 일봉만 다시 수집할 수 있어야 한다. 지원 지수 코드는 `KOSPI`, `KOSDAQ`이며 각각 FDR 심볼 `KS11`, `KQ11`로 조회해야 한다. 저장은 `market_index_price`에 `(index_code, trade_date)` 기준으로 upsert되어야 한다.

지원하지 않는 옵션 조합, 잘못된 날짜 형식, 시작일이 종료일보다 늦은 입력, 종목코드 형식 오류, 존재하지 않는 종목코드, 지원하지 않는 지수 코드는 외부 FDR 호출이나 DB 쓰기 전에 명확한 오류로 처리되어야 한다. 지정 단건 실행에서 FDR 응답이 비었거나 저장 가능한 row가 0건이면 명령은 실패해야 한다. 배치 실행 이력 테이블, 관리자 화면, 실패 관리 화면, Spring Boot API, 데이터베이스 스키마는 이 이슈에서 변경하지 않는다.

## 멱등성과 복구

지정 재수집은 삭제를 하지 않는다. 지정 기간에 이미 저장된 가격 row가 있으면 upsert로 최신 FDR 원천 데이터 기준 값을 갱신하고, 없으면 새 row를 넣는다. 따라서 같은 명령을 여러 번 실행해도 최종 DB 상태는 같은 종목 또는 지수와 같은 거래일당 row 하나여야 한다.

FDR 호출이 실패하거나 정규화 가능한 row가 없거나 DB 저장이 실패하면 해당 지정 대상의 실패로 기록한다. 이 경우 사용자는 같은 CLI 명령을 다시 실행해 복구를 시도할 수 있다. 종목 지정 실행에서 `stock` 테이블에 종목이 없으면 가격 row를 저장할 내부 `stock_id`가 없으므로 실패해야 한다. 이 문제는 기본 배치로 universe를 먼저 갱신하거나, 별도 이슈에서 미추적 종목 등록 정책을 정해야 한다.

## 위험 및 대응

| 위험 | 영향 | 대응 및 검증 |
| --- | --- | --- |
| `FinanceDataReader.DataReader(symbol, start, end)`의 종료일 포함 여부가 외부 라이브러리 동작에 따라 다를 수 있음 | 지정 기간 마지막 날짜가 누락될 수 있음 | DB 쓰기 전 command 기간 밖 row를 제거해 추가 날짜 저장은 막는다. 종료일 row가 외부 라이브러리에서 누락되는지는 수동 검증에서 저장된 `MIN(trade_date)`, `MAX(trade_date)`로 확인한다. |
| 참고 설계 문서에는 기간 단독 실행 예시가 있지만 이번 이슈 범위는 단일 종목 또는 단일 지수 재수집임 | 구현 후 사용자가 전체 기간 재수집을 기대할 수 있음 | 2026-07-23 결정에 따라 기간 단독 실행은 지원하지 않는 옵션 조합으로 처리한다. README에 기간 옵션은 `--stock-code` 또는 `--index-code`와 함께 사용해야 한다고 명시한다. |
| 지정 종목이 `stock` 테이블에 없을 수 있음 | `stock_price.stock_id`를 채울 수 없어 저장할 수 없음 | 단일 종목 조회 실패를 명확한 오류로 처리한다. README에 기본 universe 실행 후 지정 재수집을 수행하라고 안내한다. |
| 기존 runner 메서드 시그니처 변경이 테스트 fake와 기본 실행을 깨뜨릴 수 있음 | 옵션 없는 기본 배치 회귀가 생길 수 있음 | `tests/test_batch_main.py`와 기존 runner 테스트를 함께 갱신해 기본 실행과 지정 실행을 모두 검증한다. |
| 지정 단건 실행에서 저장 가능한 row가 0건일 수 있음 | 운영자가 재수집이 성공했다고 오해할 수 있음 | 지정 단건 실행에서는 FDR 응답 empty, 정규화 후 0건, 기간 필터 후 0건, upsert 결과 0건을 모두 실패로 처리한다. |

## 미결정 사항

현재 구현 시작을 막는 미결정 사항은 없다. 2026-07-23에 기간 단독 실행은 지원하지 않고, `--index-code`는 대소문자를 허용하되 내부 대문자 공식 코드로 정규화하며, 지정 단건 재수집은 정상 수집이 안 되면 실패로 처리하기로 결정했다.

## 결과와 회고

2026-07-23 구현 결과, Python 배치 진입점 `app/batch/src/batch/main.py`는 `--stock-code`, `--index-code`, `--start-date`, `--end-date`를 파싱하고 옵션 없는 기본 실행과 지정 종목 또는 지정 지수 재수집 실행을 구분한다. 옵션 없는 기본 실행은 종목 universe 갱신, tracked 종목 일봉 적재, 코스피/코스닥 지수 일봉 적재 순서를 유지한다. 지정 종목 실행은 `ReloadStockDailyPriceCommand`를 `StockDailyPriceRunner`에 전달하고, 지정 지수 실행은 `ReloadMarketIndexDailyPriceCommand`를 `MarketIndexDailyPriceRunner`에 전달한다.

종목 지정 재수집은 `stock_code`로 `stock` row를 조회하고, FDR에 `start_date`와 `end_date`를 넘긴 뒤 정규화된 가격 중 요청 기간 안의 row만 `stock_price`에 upsert한다. 지수 지정 재수집은 `KOSPI`, `KOSDAQ` 지원 목록에서 단일 지수를 찾고, FDR 심볼 `KS11`, `KQ11`로 지정 기간을 조회한 뒤 요청 기간 안의 row만 `market_index_price`에 upsert한다. 지정 단건 실행에서 대상이 없거나, FDR 응답이 비었거나, 정규화 또는 기간 필터 후 저장 가능한 row가 없거나, upsert 결과가 0이면 예외로 실패한다.

자동 검증은 `cd app/batch && .venv/bin/python -m pytest`로 수행했고 66개 테스트가 모두 통과했다. TDD 순서로 `tests/test_batch_main.py`, `tests/jobs/stock_daily_price/test_stock_daily_price_runner.py`, `tests/jobs/stock_daily_price/test_stock_daily_price_repository.py`, `tests/jobs/stock_daily_price/test_finance_data_reader_client.py`, `tests/jobs/market_index_daily_price/test_market_index_daily_price_runner.py`, `tests/jobs/market_index_daily_price/test_market_index_finance_data_reader_client.py`에 실패 테스트를 먼저 추가해 실패를 확인한 뒤 구현했다. `main.py`는 지정 실행 runner가 실패 결과를 반환하거나 저장 row 0건을 반환할 때도 비정상 종료하도록 확인한다.

수동 통합 검증도 완료했다. 이 작업트리에서는 패키지를 editable install하지 않았기 때문에 `PYTHONPATH=src`를 붙여 실행했다. 종목 지정 검증 명령은 `cd app/batch && PYTHONPATH=src DATABASE_URL=postgresql://app:app@localhost:5432/stock_report LOG_LEVEL=INFO .venv/bin/python -m batch.main --stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31`이고, 결과는 `stock daily price targeted reload completed: stock_code=005930 saved=22 excluded=0 duplicated=0`이었다. 지수 지정 검증 명령은 `cd app/batch && PYTHONPATH=src DATABASE_URL=postgresql://app:app@localhost:5432/stock_report LOG_LEVEL=INFO .venv/bin/python -m batch.main --index-code KOSPI --start-date 2024-01-01 --end-date 2024-01-31`이고, 결과는 `market index daily price targeted reload completed: index_code=KOSPI saved=22 excluded=0 duplicated=0`이었다.

수동 DB 확인 결과는 `stock_price_duplicate_count=0`, `stock_price_005930_2024_01=[('005930', 22, datetime.date(2024, 1, 2), datetime.date(2024, 1, 31))]`, `market_index_price_duplicate_count=0`, `market_index_price_KOSPI_2024_01=[('KOSPI', 22, datetime.date(2024, 1, 2), datetime.date(2024, 1, 31))]`이었다. 2024년 1월 1일은 거래일이 아니므로 실제 저장 범위의 최소 거래일은 2024년 1월 2일이었다. 초기 계획과 달라진 구현 방향은 없다.

## 계획 변경 메모

2026-07-23 변경: 구현 전 `grill-me` 검토에서 확정한 여섯 가지 정책을 반영했다. 기간 단독 실행 금지, `--stock-code`와 `--index-code` 동시 지정 금지, `--index-code` 대소문자 허용 후 대문자 정규화, 지정 단건 실패 시 비정상 종료, `--stock-code` 6자리 숫자 형식 검증, 존재하지 않는 종목코드의 runner 실행 오류 처리를 결정 기록과 구현 단계에 반영했다. 변경 이유는 구현자가 옵션 조합과 실패 semantics를 추측하지 않게 하기 위해서다.

2026-07-23 변경: 구현 완료 후 진행 상황, 구현 단계 체크박스, 예상 밖의 발견, 결과와 회고를 실제 코드와 검증 결과에 맞게 갱신했다. 당시 수동 통합 검증은 환경 의존 작업이어서 미완료로 남겼다.

2026-07-23 변경: 사용자의 추가 요청에 따라 로컬 PostgreSQL과 외부 FDR을 사용하는 수동 통합 검증을 수행하고 결과를 진행 상황, 예상 밖의 발견, 결과와 회고에 반영했다. 종목과 지수 지정 재수집 모두 22건 저장됐고, `stock_price`와 `market_index_price` 중복 row 수는 0건이었다.
