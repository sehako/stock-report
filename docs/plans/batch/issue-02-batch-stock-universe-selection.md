# 거래량 상위 200개 종목 선정 배치 구현

이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다.

## 목적과 큰 그림

이 계획은 `docs/issues/02-batch-stock-universe-selection.md` 이슈를 구현하기 위한 실행 계획이다. 구현이 끝나면 Python 배치를 실행해 `FinanceDataReader.StockListing("KRX")`에서 받은 KRX 종목 목록 중 거래량 기준 상위 200개 종목을 `stock` 테이블의 현재 조회 대상으로 표시할 수 있다. 사용자는 배치 실행 뒤 데이터베이스에서 `tracked = true`인 종목이 정확히 200개이며, 이 종목들이 최신 KRX 목록의 거래량 상위 200개와 일치한다는 것을 확인할 수 있다.

이 이슈는 종목 일봉 가격 수집, 지수 일봉 가격 수집, 지정 재수집 옵션, Spring Boot 조회 API를 구현하지 않는다. 이 이슈의 결과물은 이후 종목 일봉 수집 배치와 백엔드 종목 목록 API가 사용할 조회 대상 종목 집합을 준비하는 것이다.

## 진행 상황

- [x] (2026-07-17 14:25+0900) 이슈 본문, 실행 계획 작성 지침, 설계 문서, 아키텍처 문서를 확인했다.
- [x] (2026-07-17 14:25+0900) 저장소 구조를 조사해 현재 `app` 디렉터리와 Python 배치 코드가 아직 없음을 확인했다.
- [x] (2026-07-17 14:25+0900) 구현 위치와 검증 방법을 현재 저장소 상태 기준으로 계획했다.
- [x] (2026-07-17 15:20+0900) 계획 검토에서 배치 디렉터리 구조, PostgreSQL 전제, 데이터 정규화, 테스트 전략, 실행 환경을 확정하고 계획에 반영했다.
- [x] (2026-07-17 15:45+0900) 로컬 PostgreSQL `stock_report` 데이터베이스의 실제 3개 테이블 컬럼, 제약, 인덱스를 확인하고 실제 스키마 기준으로 계획을 갱신했다.
- [x] (2026-07-17 17:22+0900) Python 배치 프로젝트 골격과 테스트를 먼저 추가하고, 미구현 모듈 import 실패로 RED 상태를 확인했다.
- [x] (2026-07-17 17:30+0900) 거래량 상위 200개 선정, FDR 클라이언트, runner, PostgreSQL 저장소 구현을 추가하고 자동 테스트 GREEN 상태를 확인했다.
- [x] (2026-07-17 17:37+0900) 실제 `FinanceDataReader.StockListing("KRX")` 응답 2,872행에서 200개 선정이 동작함을 확인했다.
- [x] (2026-07-17 17:39+0900) 로컬 PostgreSQL 컨테이너의 `stock`, `stock_price`, `market_index_price` 스키마를 확인했다.
- [x] (2026-07-17 17:43+0900) 로컬 전용 `.env`에 `DATABASE_URL`을 설정하고 실제 배치를 실행해 DB 반영과 멱등성을 확인했다.
- [x] (2026-07-17 17:44+0900) 결과와 회고를 작성하고 ExecPlan 최종 상태를 확인했다.
- [x] (2026-07-17 21:18+0900) `KOSDAQ GLOBAL`을 `KOSDAQ`으로 정규화하도록 수정하고, 실제 배치와 DB 반영을 다시 확인했다.

## 예상 밖의 발견

- 관찰: 현재 저장소에는 `docs` 중심의 문서만 있고, `app/backend`, `app/frontend`, Python 배치 코드 디렉터리는 아직 없다.
  증거: 저장소 루트에서 `rg --files docs app`을 실행했을 때 `rg: app: No such file or directory (os error 2)`가 출력되었고, `find . -maxdepth 3 -type f` 결과에도 `app` 하위 파일이 없었다.
  영향: 이 이슈 구현은 기존 Python 배치 관례를 확장하는 작업이 아니라, 저장소 안에 새 Python 배치 골격을 도입하는 작업이 된다. 단, 이 계획은 이슈 02 범위를 넘지 않도록 종목 선정과 `stock` 테이블 갱신에 필요한 최소 구조만 다룬다.

- 관찰: `stock` 테이블을 만드는 이슈는 `docs/issues/01-market-data-schema.md`로 분리되어 있다.
  증거: 해당 이슈의 작업 범위는 `stock`, `stock_price`, `market_index_price` 테이블 생성과 중복 방지 제약 적용이고, 제외 범위는 Python 배치 구현이다.
  영향: 이슈 02 구현 전 또는 구현 중 이슈 01 산출물이 존재하는지 확인해야 한다. 이 계획은 다른 워크트리에서 백엔드 마이그레이션이 완료되어 로컬 PostgreSQL `localhost:5432`에 초기 테이블 3개가 존재하는 상태를 전제로 한다. 현재 워크트리에 스키마 파일이 없더라도 실제 DB 테이블과 제약을 확인할 수 있으면 DB 저장소 구현과 수동 통합 검증을 진행한다. DB 접속 정보나 테이블 정의를 확인할 수 없을 때만 DB 통합 검증을 보류한다.

- 관찰: `docs/architecture/batch.md`는 이슈 02 적용 예시로 `app/batch/src/jobs/stock_universe` 작업 패키지 구조를 명시한다.
  증거: `docs/architecture/batch.md`의 이슈 02 적용 예시는 `application`, `domain`, `infrastructure` 계층 아래 `stock_universe_runner.py`, `service.py`, `stock_universe_repository.py`, `finance_data_reader_client.py`를 둔다.
  영향: 초기 계획의 `app/batch/src/stock_universe` 단일 패키지 구조는 아키텍처 문서와 맞지 않으므로, 구현 계획과 예상 변경 파일을 `app/batch/src/jobs/stock_universe` 구조로 바꾼다. 실행 진입점은 `app/batch/src/batch/main.py`에 두고 `python -m batch.main`으로 실행한다.

- 관찰: 로컬 PostgreSQL `stock_report` 데이터베이스의 실제 `stock` 테이블에는 `last_loaded_date` 컬럼이 없고, 중복 방지 제약은 `stock_code` 단독이 아니라 `(market, stock_code)`이다. `stock_price`도 설계 문서의 `stock_code` 직접 참조가 아니라 `stock_id` 외래 키로 `stock(id)`를 참조한다.
  증거: `docker exec local-postgres psql -U app -d stock_report`로 `information_schema.columns`, `information_schema.table_constraints`, `pg_constraint`를 조회했다. 실제 `stock` 컬럼은 `id`, `market`, `stock_code`, `stock_name`, `tracked`이고, 제약은 `stock_pkey`와 `uk_stock_market_stock_code`이다. 실제 `stock_price` 컬럼은 `stock_id`를 포함하고, `fk_stock_price_stock` 외래 키와 `uk_stock_price_stock_trade_date` 유니크 제약이 있다.
  영향: 이슈 02 저장소 구현은 `ON CONFLICT (market, stock_code) DO UPDATE`를 사용해야 한다. 이슈 02 계획에서 `last_loaded_date`를 삽입하거나 보존하라는 지시는 제거한다. `stock_price` 구조 차이는 이 이슈의 직접 구현 범위는 아니지만, 후속 종목 일봉 배치에서는 `stock_code`가 아니라 `stock.id`를 조회해 `stock_price.stock_id`에 저장해야 한다.

- 관찰: `app/batch`에서 기본 `python3`는 Python 3.9.6이지만, 배치 프로젝트는 `pyproject.toml`에서 Python 3.11 이상을 요구한다.
  증거: `python3 --version`은 `Python 3.9.6`을 출력했고, `/opt/homebrew/bin/python3.14`가 존재했다. Python 3.9 기반 `.venv`에서 `pip install -e ".[dev]"`는 `requires a different Python: 3.9.6 not in '>=3.11'`로 실패했다.
  영향: 로컬 검증은 Python 3.14 기반 `.venv`를 다시 생성해 진행했다. `app/batch/README.md`의 가상환경 생성 명령도 `python3.14 -m venv .venv`로 작성했다.

- 관찰: 오래된 pip 21.2.4는 `finance-datareader`의 하위 의존성을 과도하게 역추적해 설치가 오래 걸리거나 실패했다.
  증거: Python 3.9 기반 `.venv`에서 `pip install '.[dev]'` 실행 중 `plotly`, `lxml`, `beautifulsoup4`, `soupsieve` 여러 버전을 계속 내려받으며 수렴하지 않았다. Python 3.14 기반 `.venv`에서 `python -m pip install --upgrade pip setuptools` 후 `pip install -e ".[dev]"`는 성공했다.
  영향: README 설치 절차에 pip와 setuptools 업그레이드 단계를 추가했다. `pyproject.toml`에는 직접 필요한 의존성만 남겼다.

- 관찰: 실제 FDR 호출은 샌드박스 네트워크 제한에서는 실패하지만, 네트워크 권한으로 실행하면 현재 KRX 목록을 읽고 선정 로직이 정상 동작한다.
  증거: 제한 환경에서는 `data.krx.co.kr` 이름 해석 실패가 발생했다. 권한을 부여해 실행한 검증 명령은 `2872 200 ['Code', 'ISU_CD', 'Name', 'Market', 'Dept', 'Close', 'ChangeCode', 'Changes', 'ChagesRatio', 'Open'] StockUniverseStock(market='KOSDAQ', stock_code='067290', stock_name='JW신약', volume=41313262)`를 출력했다.
  영향: 자동 테스트는 계속 외부 네트워크에 의존하지 않는다. 실제 FDR 호출은 수동 또는 승인된 네트워크 환경에서 검증한다.

- 관찰: 호스트에서 로컬 PostgreSQL에 접속하려면 비밀번호가 필요하지만 현재 셸에는 `DATABASE_URL`이 없다.
  증거: `printenv DATABASE_URL`은 값을 출력하지 않았고, `DATABASE_URL=postgresql://app@localhost:5432/stock_report`로 읽기 쿼리를 실행하면 `fe_sendauth: no password supplied`가 발생했다. 컨테이너 내부 `docker exec local-postgres psql -U app -d stock_report` 스키마 조회는 성공했다.
  영향: 실제 배치의 DB 쓰기 검증은 민감정보를 추측하지 않기 위해 수행하지 않았다. `DATABASE_URL`이 제공되면 `python -m batch.main`으로 최종 수동 검증을 수행할 수 있다.

- 관찰: 사용자에게서 로컬 개발 DB 접속 정보를 제공받아 실제 DB 쓰기 검증을 완료했다.
  증거: `app/batch/.env`를 Git 무시 대상으로 두고 로컬 전용 `DATABASE_URL`을 설정한 뒤 `python -m batch.main`을 실행했다. 초기 실행 로그는 `source=2872 valid=2715 selected=200 untracked=0 digest_matched=True`를 출력했다. 이후 `KOSDAQ GLOBAL` 정규화 수정 후 재실행 로그는 `source=2872 valid=2765 selected=200 untracked=4 digest_matched=True`를 출력했다. 실행 후 읽기 쿼리는 `tracked_true_count= 200`, `duplicated_market_stock_code_count= 0`을 출력했다.
  영향: 이슈 02의 핵심 수락 기준인 실제 DB의 tracked 200개 반영, 반복 실행 시 중복 없음, digest 일치가 로컬 환경에서 확인되었다. 접속 문자열 값 자체는 민감정보이므로 문서에 기록하지 않는다.

- 관찰: `FinanceDataReader.StockListing("KRX")`의 거래량 상위 200개에는 `KOSDAQ GLOBAL`로 표시되는 코스닥 글로벌 세그먼트 종목이 포함될 수 있다.
  증거: 실제 FDR 데이터를 조회해 거래량 상위 200개 시장 값을 세어 보니 `{'KOSDAQ': 110, 'KOSPI': 86, 'KOSDAQ GLOBAL': 4}`가 출력되었다. 수정 후 실제 선정된 코스닥 글로벌 종목 `403870`, `240810`, `036930`, `086520`은 DB에서 모두 `market='KOSDAQ'`, `tracked=true`로 저장되었다.
  영향: `KOSDAQ GLOBAL`은 이슈의 KRX 거래량 상위 200개 취지에 맞게 제외하지 않고 `KOSDAQ`으로 정규화한다. `KONEX`처럼 MVP 지원 범위 밖인 시장은 계속 제외한다.

## 결정 기록

- 결정: 이 ExecPlan은 `EXECPLAN_TEMPLATE.md`와 `PLANS.md`의 살아 있는 문서 형식을 따르고, `docs/templates/prompt/create-exec-plan.md`의 조사 항목을 내용에 반영한다.
  근거: 저장소 루트의 `PLANS.md`는 모든 ExecPlan이 자기완결적이어야 하며 진행 상황, 예상 밖의 발견, 결정 기록, 결과와 회고를 유지해야 한다고 요구한다. `docs/templates/prompt/create-exec-plan.md`는 이슈, 참고 문서, 실제 코드베이스 조사 결과를 바탕으로 구현 접근과 검증 방법을 작성하라고 지시한다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 배치 구현은 `app/batch` 아래에 Python 코드로 둔다.
  근거: `AGENTS.md`는 `app`을 애플리케이션 코드 디렉터리로 설명하고, 설계 문서는 시스템을 Python 배치, Spring Boot 백엔드, React 프론트엔드로 분리한다고 설명한다. 현재 `app` 디렉터리가 없으므로 `app/batch`를 새로 만들면 `app/backend`, `app/frontend`와 병렬인 애플리케이션 하위 영역으로 배치 코드를 배치할 수 있다. 작업 패키지는 `docs/architecture/batch.md`의 이슈 02 적용 예시에 맞춰 `app/batch/src/jobs/stock_universe` 아래에 둔다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 거래량 상위 200개 선정은 `FinanceDataReader.StockListing("KRX")` 결과의 거래량 컬럼을 숫자로 변환한 뒤 내림차순 정렬해 상위 200개를 선택하는 방식으로 계획한다.
  근거: 이슈 02가 `FinanceDataReader.StockListing("KRX")` 사용과 거래량 기준 상위 200개 선정을 명시한다. 설계 문서도 KRX 제공 목록을 그대로 사용하고 ETF, ETN, 우선주 등 비보통주를 별도로 제외하지 않는다고 설명한다. 거래량이 같은 경우에는 결과가 실행마다 흔들리지 않도록 종목코드 오름차순을 두 번째 정렬 기준으로 사용한다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: `tracked` 갱신은 한 번의 배치 실행 안에서 현재 상위 200개는 `true`, 이전에 저장되었지만 이번 상위 200개에 없는 종목은 `false`가 되도록 트랜잭션으로 처리한다.
  근거: 같은 실행 중 일부 종목만 갱신된 상태로 남으면 백엔드 API가 잘못된 조회 대상 집합을 읽을 수 있다. 트랜잭션은 여러 SQL 변경을 하나의 단위로 묶어 모두 성공하거나 모두 취소되게 하는 데이터베이스 기능이다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: DB는 PostgreSQL로 확정하고, 접속 정보는 `DATABASE_URL` 환경 변수 하나로 받으며, Python 드라이버는 `psycopg[binary]`를 사용한다.
  근거: 사용자는 다른 워크트리에서 백엔드 마이그레이션이 완료되어 로컬 PostgreSQL `localhost:5432`에 초기 테이블 3개가 있는 상태라고 확인했다. 실제 DB의 `stock` 중복 방지 제약은 `(market, stock_code)`이므로 upsert는 `ON CONFLICT (market, stock_code) DO UPDATE`로 구현한다. `DATABASE_URL`은 로컬과 CI/CD에서 같은 방식으로 접속 정보를 주입하기 쉽고, 실제 비밀번호를 코드나 문서에 쓰지 않는 원칙을 지킬 수 있다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: Python 배치 의존성은 `app/batch/pyproject.toml`로 관리하고, 설치와 실행은 `app/batch/.venv` 가상환경에서만 수행한다.
  근거: 사용자는 전역 Python 환경에 의존성이 설치되는 것을 원하지 않는다. `pyproject.toml`은 의존성 목록과 테스트 설정을 프로젝트 파일로 관리하고, `.venv`는 실제 설치 위치를 프로젝트 하위 로컬 가상환경으로 제한한다. 같은 원칙을 `docs/architecture/batch.md`에도 반영한다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: 자동 테스트는 외부 네트워크와 개발용 DB에 의존하지 않는 mock 또는 fake 중심으로 작성하고, 실제 `FinanceDataReader` 호출과 로컬 PostgreSQL 반영은 수동 통합 검증으로 확인한다.
  근거: `FinanceDataReader` 호출은 외부 네트워크와 원천 데이터 상태에 의존하므로 자동 테스트에 넣으면 재현성이 떨어진다. 개발용 `localhost:5432` DB는 상태가 오염될 수 있어 CI/CD 자동 테스트의 기반으로 적합하지 않다. 나중에 CI/CD를 붙일 때 PostgreSQL 통합 테스트는 격리된 테스트 DB 또는 Testcontainers 같은 일회용 테스트 DB가 준비되면 추가한다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: `market`은 DB 문자열 값으로 `KOSPI`, `KOSDAQ`만 저장하고, 애플리케이션에서는 enum으로 취급한다. `FinanceDataReader`가 `KOSDAQ GLOBAL`로 표시하는 종목은 코스닥 글로벌 세그먼트이므로 `KOSDAQ`으로 정규화한다. `KONEX` 등 코스피와 코스닥 밖의 시장 값은 이번 MVP 지원 범위 밖이므로 제외하고 로그에 남긴다.
  근거: 사용자는 `market`을 애플리케이션 기준 enum, DB 기준 문자열 `KOSPI`, `KOSDAQ`으로 사용하기로 했다고 확인했다. `KOSDAQ GLOBAL`은 코스닥 안의 세그먼트이므로 제외하면 이슈의 KRX 거래량 상위 200개 선정 취지와 어긋난다. 이 제한은 ETF, ETN, 우선주 같은 종목 유형을 제외하는 것이 아니라 MVP 지원 시장을 코스피와 코스닥으로 제한하는 것이다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: 거래량 결측값이나 숫자로 변환할 수 없는 값은 0으로 정규화해 하위로 밀고, 종목코드 또는 종목명이 비어 있는 행은 제외한다. 유효 행이 200개 미만이면 배치를 실패 처리한다.
  근거: 외부 데이터 일부가 이상하더라도 나머지 유효 행으로 상위 200개를 채우는 편이 운영 친화적이다. 다만 유효 행이 200개 미만이면 이슈의 완료 기준인 정확한 200개 조회 대상 갱신을 만족할 수 없으므로 실패로 다룬다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: 같은 `stock_code`가 중복으로 들어오면 비정상 입력 방어 케이스로 보고 경고 로그를 남긴 뒤 거래량이 가장 큰 행 하나만 사용한다.
  근거: `FinanceDataReader.StockListing("KRX")`의 정상 KRX 목록에서 같은 현재 종목코드가 중복될 가능성은 낮다. 그래도 selector 단계에서 중복을 결정적으로 하나로 줄이면 같은 입력에서 항상 같은 상위 200개가 나오고, 이후 `(market, stock_code)` 기준 upsert 결과도 구현 세부에 의존하지 않는다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

- 결정: 이슈 02는 실제 로컬 DB 스키마를 기준으로 `stock.last_loaded_date`를 다루지 않고, `stock` upsert 충돌 기준을 `(market, stock_code)`로 사용한다.
  근거: 실제 `stock` 테이블에는 `last_loaded_date` 컬럼이 없고, `uk_stock_market_stock_code` 유니크 제약만 있다. 계획서가 설계 문서의 초기 모델만 따라 `last_loaded_date`나 `ON CONFLICT (stock_code)`를 지시하면 실제 DB에서 SQL이 실패하거나 없는 컬럼을 참조하게 된다.
  날짜/작성자: 2026-07-17 / 사용자, Codex

## 결과와 회고

구현이 완료되었다. `app/batch` 아래에 Python 배치 프로젝트를 추가했고, 옵션 없는 기본 실행 진입점 `batch.main`을 만들었다. 배치는 `FinanceDataReader.StockListing("KRX")`로 KRX 목록을 조회하고, `Code`, `Name`, `Market`, `Volume` 값을 정규화해 KOSPI와 KOSDAQ 종목 중 거래량 상위 200개를 선택한다. `KOSDAQ GLOBAL`은 코스닥 글로벌 세그먼트이므로 `KOSDAQ`으로 정규화한다. 종목코드 또는 종목명이 비어 있거나 `NaN`인 행은 제외하고, 거래량 결측 또는 변환 불가 값은 0으로 처리한다. ETF, ETN, 우선주처럼 보이는 이름은 제외하지 않는다. 같은 `stock_code`가 중복되면 거래량이 가장 큰 행 하나만 사용한다.

실제 변경 파일은 `app/batch/pyproject.toml`, `app/batch/README.md`, `app/batch/.gitignore`, `app/batch/src/batch/main.py`, `app/batch/src/shared`, `app/batch/src/jobs/stock_universe`, `app/batch/tests/jobs/stock_universe`이다. 저장소 구현은 `ON CONFLICT (market, stock_code) DO UPDATE`로 upsert하고, 현재 선정 목록에 없는 기존 tracked 종목을 `tracked = false`로 바꾼다. 자동 테스트는 도메인 선정 규칙, runner 흐름, 저장소 SQL 의도와 롤백을 검증한다.

실행한 검증 명령과 결과는 다음과 같다.

    cd /Users/sehako/workspace/stock-report-batch/app/batch
    /opt/homebrew/bin/python3.14 -m venv --clear .venv
    .venv/bin/python -m pip install --upgrade pip setuptools
    .venv/bin/python -m pip install -e ".[dev]"
    .venv/bin/python -m pytest

    결과: 13 passed in 0.02s

    .venv/bin/python -c "from jobs.stock_universe.infrastructure.client.finance_data_reader_client import FinanceDataReaderKrxListingClient; from jobs.stock_universe.domain.service import select_top_volume_stocks; rows=FinanceDataReaderKrxListingClient().fetch_krx_listing(); result=select_top_volume_stocks(rows); print(len(rows), len(result.stocks), rows.columns.tolist()[:10], result.stocks[0])"

    결과: 2872 200 ['Code', 'ISU_CD', 'Name', 'Market', 'Dept', 'Close', 'ChangeCode', 'Changes', 'ChagesRatio', 'Open'] StockUniverseStock(market='KOSDAQ', stock_code='067290', stock_name='JW신약', volume=41313262)

    docker exec local-postgres psql -U app -d stock_report -P pager=off -c "select table_name, column_name, data_type from information_schema.columns where table_schema='public' and table_name in ('stock','stock_price','market_index_price') order by table_name, ordinal_position;"

    결과: stock은 id, market, stock_code, stock_name, tracked 컬럼을 가지고, stock_price와 market_index_price도 존재한다.

사용자가 제공한 로컬 개발 DB 접속 정보로 `app/batch/.env`를 만들고, 이 파일을 `.gitignore`에 포함해 Git 추적 대상에서 제외했다. 실제 값은 민감정보이므로 이 문서에는 쓰지 않는다. `.env`를 로드한 뒤 실제 배치를 두 번 실행했고, 두 번 모두 digest가 일치했다.

    cd /Users/sehako/workspace/stock-report-batch/app/batch
    set -a; . ./.env; set +a; .venv/bin/python -m batch.main

    결과: source=2872 valid=2765 selected=200 untracked=4 digest_matched=True

    set -a; . ./.env; set +a; .venv/bin/python -c "import os, psycopg; conn=psycopg.connect(os.environ['DATABASE_URL']); print('tracked_true_count=', conn.execute('select count(*) from stock where tracked = true').fetchone()[0]); print('duplicated_market_stock_code_count=', conn.execute('select count(*) from (select market, stock_code from stock group by market, stock_code having count(*) > 1) duplicated').fetchone()[0]); conn.close()"

    결과: tracked_true_count= 200
    결과: duplicated_market_stock_code_count= 0

    KOSDAQ GLOBAL로 표시된 종목이 KOSDAQ으로 저장되었는지 확인한 결과: [('KOSDAQ', '036930', '주성엔지니어링', True), ('KOSDAQ', '086520', '에코프로', True), ('KOSDAQ', '240810', '원익IPS', True), ('KOSDAQ', '403870', 'HPSP', True)]

## 맥락과 방향 안내

저장소 루트는 `/Users/sehako/workspace/stock-report-batch`이다. 현재 확인한 관련 파일은 다음과 같다.

`docs/issues/02-batch-stock-universe-selection.md`는 이 계획의 대상 이슈다. 이슈는 Python 배치에서 KRX 종목 목록을 조회하고 거래량 상위 200개 종목을 `stock` 테이블에 저장하며, 현재 조회 대상 여부를 뜻하는 `tracked` 값을 갱신하라고 요구한다.

`docs/specs/2026-07-15-stock-market-data-service-design.md`는 전체 MVP 설계 문서다. 이 문서는 시스템을 Python 배치, Spring Boot 백엔드, React 프론트엔드로 나누며, Python 배치가 `FinanceDataReader`를 사용해 장 마감 후 데이터를 수집한다고 설명한다. 이 이슈에서 필요한 부분은 기본 배치의 1번부터 5번까지다. 즉 KRX 전체 종목 목록 조회, 거래량 상위 200개 선정, `stock` 테이블 upsert, 현재 상위 200개 `tracked = true`, 제외된 기존 종목 `tracked = false` 처리다. 여기서 upsert는 같은 종목코드가 이미 있으면 갱신하고 없으면 새로 삽입하는 저장 방식이다.

`docs/issues/01-market-data-schema.md`는 `stock` 테이블을 포함한 데이터베이스 스키마 이슈다. 이슈 02는 `stock` 테이블이 있다고 가정하고 데이터를 갱신한다. 실제 로컬 PostgreSQL `stock_report` 데이터베이스 기준 `stock` 테이블의 이 이슈 관련 컬럼은 `id`, `market`, `stock_code`, `stock_name`, `tracked`이다. `id`는 데이터베이스가 각 행을 구분하기 위해 자동으로 증가시키는 숫자 기본 키이고, 이 이슈의 upsert 입력값으로 직접 넣지 않는다. 실제 DB에는 `last_loaded_date` 컬럼이 없으므로 이 이슈에서는 해당 값을 삽입하거나 갱신하지 않는다. `stock`의 중복 방지 제약은 `(market, stock_code)` 조합이다. 이 계획은 다른 워크트리에서 백엔드 마이그레이션이 완료되어 로컬 PostgreSQL에 초기 테이블이 있는 상태를 전제로 한다. 현재 워크트리에 스키마 파일이 없더라도 실제 DB에서 테이블과 제약을 확인할 수 있으면 구현과 수동 통합 검증을 진행한다.

`docs/architecture/backend.md`는 Spring Boot 백엔드 패키지 구조를 설명한다. 이 이슈는 Spring Boot 조회 API를 제외하므로 백엔드 패키지를 수정하지 않는다. 다만 `stock` 테이블은 이후 Spring Boot API가 읽을 데이터 계약이므로 컬럼 의미를 바꾸면 안 된다.

`docs/architecture/batch.md`는 Python 배치 작업의 계층 구조와 실행 진입점 원칙을 설명한다. 이 이슈의 작업 패키지는 이 문서의 이슈 02 적용 예시를 따라 `app/batch/src/jobs/stock_universe` 아래에 둔다. 배치 전체 실행 진입점은 `app/batch/src/batch/main.py`에 두고, `app/batch`에서 가상환경을 활성화한 뒤 `python -m batch.main`으로 실행한다.

현재 저장소에는 `app` 디렉터리가 없다. 따라서 이 이슈의 구현자는 `app/batch` 새 Python 배치 영역을 만들되, 종목 선정 배치에 필요한 최소 파일만 추가해야 한다. 종목 일봉 수집, 지수 일봉 수집, 지정 재수집 CLI 옵션은 후속 이슈의 범위다.

## 작업 계획

먼저 이슈 01 산출물의 존재 여부를 확인한다. 구현자가 저장소 루트에서 파일 목록을 조사해 데이터베이스 마이그레이션 파일, Spring Boot 설정, 또는 SQL 스키마 파일이 추가되어 있는지 확인한다. 현재 워크트리에 스키마 파일이 없더라도 다른 워크트리의 백엔드 마이그레이션으로 로컬 PostgreSQL `localhost:5432`에 `stock`, `stock_price`, `market_index_price` 초기 테이블이 만들어져 있다는 전제를 확인한다. `DATABASE_URL`을 통해 실제 DB에 접속해 `stock` 테이블과 `(market, stock_code)` 기준 중복 방지 제약을 확인할 수 있으면 DB 저장소 구현과 수동 통합 검증을 진행한다. 접속 정보나 테이블 정의를 확인할 수 없을 때만 DB 통합 검증을 보류한다.

그다음 `app/batch` 아래에 Python 배치 구조를 만든다. 의존성은 `app/batch/pyproject.toml`에 기록하고, 설치와 실행은 `app/batch/.venv` 가상환경에서 수행한다. 최소 구조는 설정을 읽는 `shared.config`, PostgreSQL 연결을 만드는 `shared.database`, `FinanceDataReader.StockListing("KRX")`를 호출하는 클라이언트 모듈, 거래량 상위 200개를 고르는 도메인 서비스, `stock` 테이블을 갱신하는 저장소 구현, 기본 배치를 실행하는 진입점 모듈로 나눈다. 도메인 로직은 외부 네트워크나 데이터베이스 없이 테스트 가능해야 한다. 저장소 모듈은 `DATABASE_URL` 환경 변수에서 데이터베이스 연결 문자열을 읽어야 하며, 비밀번호나 토큰 같은 민감정보를 코드에 직접 쓰지 않는다.

거래량 상위 200개 선정 로직은 KRX 목록의 종목코드, 종목명, 시장 구분, 거래량 값을 정규화한다. 정규화는 외부 데이터의 컬럼 이름이나 값 형식을 내부에서 쓰기 쉬운 형태로 바꾸는 작업이다. 구현자는 실제 `FinanceDataReader.StockListing("KRX")`가 반환하는 컬럼을 확인해야 한다. 거래량 컬럼은 숫자 비교가 가능하도록 변환하고, 결측값이나 숫자로 바꿀 수 없는 값은 0으로 처리해 하위로 밀리도록 처리한다. 종목코드 또는 종목명이 비어 있는 행은 제외하고, 제외된 행 수와 사유를 로그에 남긴다. `market`은 DB 저장 기준으로 `KOSPI`, `KOSDAQ`만 유효한 값으로 인정하되, FDR의 `KOSDAQ GLOBAL`은 `KOSDAQ`으로 정규화한다. `KONEX` 등 코스피와 코스닥 밖의 시장은 MVP 지원 범위 밖이므로 제외한다. 이 시장 제한은 종목 유형 필터가 아니므로, ETF, ETN, 우선주처럼 보이는 이름은 제외하지 않는다.

선정 정렬은 거래량 내림차순, 종목코드 오름차순으로 한다. 거래량이 같은 종목이 있을 때 종목코드 오름차순을 두 번째 기준으로 쓰면 같은 입력에서 항상 같은 200개가 나온다. `FinanceDataReader.StockListing("KRX")`의 정상 결과에서 같은 `stock_code`가 중복될 가능성은 낮지만, 중복이 발견되면 경고 로그를 남기고 거래량이 가장 큰 행 하나만 사용한다. 유효 행이 200개 미만이면 `tracked = true` 200개라는 수락 기준을 만족할 수 없으므로 배치를 실패 처리한다.

DB 갱신 로직은 하나의 트랜잭션 안에서 처리한다. 먼저 상위 200개 종목을 `stock` 테이블에 upsert한다. upsert는 실제 DB의 유니크 제약인 `(market, stock_code)`를 기준으로 하고, `stock_name`과 `tracked`를 갱신한다. `market`과 `stock_code`는 충돌 대상을 찾는 키로 사용한다. 실제 `stock` 테이블에는 `last_loaded_date`가 없으므로 이 이슈에서 해당 컬럼을 읽거나 쓰지 않는다. 그다음 현재 상위 200개 종목의 `tracked`를 `true`로 만들고, `stock` 테이블에 이미 있지만 현재 상위 200개 목록에 없는 종목의 `tracked`를 `false`로 만든다.

배치 진입점은 옵션 없는 기본 실행만 제공한다. 실행하면 KRX 목록 조회, 상위 200개 선정, DB 갱신, 결과 로그 출력 순서로 동작한다. 로그에는 실행 시작 시각, FDR 원본 행 수, 유효 행 수, 제외된 행 수와 사유별 개수, 중복 `stock_code` 제거 건수, 최종 선정 종목 수, upsert 대상 수, 실제로 `tracked = true`에서 `false`로 변경된 기존 종목 수를 남긴다. 또한 선정한 200개 종목코드 집합의 digest와 DB에서 다시 읽은 `tracked = true` 종목코드 집합의 digest를 남기고 두 값이 일치하는지 기록한다. digest는 종목코드 목록을 정렬해 하나의 문자열로 만든 뒤 SHA-256 같은 해시 함수로 만든 짧은 요약값이다. 두 digest가 같고 `tracked = true` 수가 200이면 이번 실행에서 계산한 200개가 DB에 반영되었다고 판단할 수 있다. 한 번 실패한 뒤 다시 실행해도 같은 상위 200개 기준으로 같은 최종 상태가 되어야 한다.

## 마일스톤

첫 번째 마일스톤은 선행 스키마와 배치 골격을 확인하는 것이다. 이 마일스톤이 끝나면 구현자는 `stock` 테이블을 사용할 수 있는지 알고, `app/batch` 아래에 어떤 파일을 만들지 확정한다. 검증은 저장소 루트에서 파일 목록과 스키마 파일을 확인하고, `DATABASE_URL`로 로컬 PostgreSQL에 접속해 `stock` 테이블과 `(market, stock_code)` 기준 중복 방지 제약을 확인하는 것으로 한다. 현재 워크트리에 스키마 파일이 없더라도 로컬 DB 테이블이 확인되면 저장소 구현과 수동 통합 검증을 진행한다.

두 번째 마일스톤은 거래량 상위 200개 선정 로직을 외부 의존성 없이 테스트 가능하게 만드는 것이다. 이 마일스톤이 끝나면 샘플 KRX 목록 DataFrame 또는 같은 구조의 테스트 데이터로 거래량 내림차순과 종목코드 오름차순 기준의 상위 200개가 선택되고, ETF나 우선주처럼 보이는 이름도 제거되지 않는다는 테스트가 통과해야 한다. 여기서 DataFrame은 행과 열로 된 표 형식 데이터를 다루는 Python 객체이며, `FinanceDataReader.StockListing("KRX")`가 반환하는 형태다. 테스트는 거래량 비정상 값 0 처리, 필수값 누락 행 제외, `KONEX` 제외, 중복 `stock_code` 방어 처리도 확인한다.

세 번째 마일스톤은 PostgreSQL의 `stock` 테이블 갱신을 구현하는 것이다. 이 마일스톤이 끝나면 `psycopg[binary]`를 사용한 저장소 구현이 `ON CONFLICT (market, stock_code) DO UPDATE`로 상위 200개 종목을 upsert하고, 이전 실행에서 `tracked = true`였으나 이번 상위 200개에 없는 종목을 `tracked = false`로 바꾼다. 자동 테스트는 fake 저장소나 fake 연결을 사용해 호출 흐름과 SQL 실행 의도를 검증한다. 실제 로컬 PostgreSQL 반영은 네 번째 마일스톤의 수동 통합 검증에서 확인한다.

네 번째 마일스톤은 기본 배치 실행과 최종 검증이다. 이 마일스톤이 끝나면 사용자는 `app/batch`에서 `.venv`를 활성화하고 `python -m batch.main`을 실행해 실제 FDR 조회와 로컬 PostgreSQL 반영을 확인할 수 있어야 한다. 데이터베이스 조회로 `tracked = true` 종목 수가 200인지 확인하고, 로그의 선정 코드 digest와 DB tracked 코드 digest가 일치하는지 확인한다. 이 단계에서 종목 일봉 가격과 지수 일봉 가격은 수집되지 않아야 한다.

## 구체적인 단계

작업 디렉터리:

    /Users/sehako/workspace/stock-report-batch

1. 선행 스키마와 현재 구조를 확인한다.

    실행 명령:

        find . -maxdepth 5 -type f | sort
        rg -n "CREATE TABLE.*stock|stock_code|tracked|market_index_price|stock_price" .

    기대 결과는 `stock` 테이블 정의나 마이그레이션 파일을 찾는 것이다. 현재 워크트리에서 찾지 못하더라도, 다른 워크트리의 백엔드 마이그레이션으로 로컬 PostgreSQL에 테이블이 만들어져 있다는 전제를 `DATABASE_URL` 접속으로 확인한다. `psql`이 설치되어 있다면 배치 골격 생성 전에도 다음처럼 확인할 수 있다.

        psql "$DATABASE_URL" -c "select table_name from information_schema.tables where table_schema = 'public' and table_name in ('stock', 'stock_price', 'market_index_price') order by table_name;"

    `psql`이 없다면 2단계에서 `.venv`와 의존성을 설치한 뒤 구현한 Python DB 연결 코드나 다음 Python 명령으로 같은 정보를 확인한다.

        cd /Users/sehako/workspace/stock-report-batch/app/batch
        . .venv/bin/activate
        python -c "import os, psycopg; conn = psycopg.connect(os.environ['DATABASE_URL']); cur = conn.execute(\"select table_name from information_schema.tables where table_schema = 'public' and table_name in ('stock', 'stock_price', 'market_index_price') order by table_name\"); print([row[0] for row in cur])"

    기대 출력은 세 테이블 이름이 모두 포함된 목록이다. `DATABASE_URL`이 없거나 테이블을 확인할 수 없으면 수동 DB 통합 검증은 보류하되, 도메인 로직과 fake 기반 자동 테스트는 진행한다.

2. Python 배치 골격을 만든다.

    예상 변경 파일:

        app/batch/README.md
        app/batch/pyproject.toml
        app/batch/src/batch/__init__.py
        app/batch/src/batch/main.py
        app/batch/src/jobs/stock_universe/__init__.py
        app/batch/src/jobs/stock_universe/application/__init__.py
        app/batch/src/jobs/stock_universe/application/dto.py
        app/batch/src/jobs/stock_universe/application/stock_universe_runner.py
        app/batch/src/jobs/stock_universe/domain/__init__.py
        app/batch/src/jobs/stock_universe/domain/model.py
        app/batch/src/jobs/stock_universe/domain/repository.py
        app/batch/src/jobs/stock_universe/domain/service.py
        app/batch/src/jobs/stock_universe/infrastructure/__init__.py
        app/batch/src/jobs/stock_universe/infrastructure/client/__init__.py
        app/batch/src/jobs/stock_universe/infrastructure/client/finance_data_reader_client.py
        app/batch/src/jobs/stock_universe/infrastructure/persistence/__init__.py
        app/batch/src/jobs/stock_universe/infrastructure/persistence/stock_universe_repository.py
        app/batch/src/shared/__init__.py
        app/batch/src/shared/config/__init__.py
        app/batch/src/shared/database/__init__.py
        app/batch/src/shared/logging/__init__.py
        app/batch/tests/jobs/stock_universe/test_service.py
        app/batch/tests/jobs/stock_universe/test_stock_universe_runner.py

    `pyproject.toml`에는 최소 의존성으로 `FinanceDataReader`, `pandas`, `psycopg[binary]`, 테스트 도구인 `pytest`를 명시한다. 새 의존성은 이 이슈 구현에 필요한 것만 추가한다. `.venv`는 생성하되 커밋하지 않는다.

    가상환경 생성과 설치 명령:

        cd /Users/sehako/workspace/stock-report-batch/app/batch
        python3.14 -m venv .venv
        . .venv/bin/activate
        python -m pip install --upgrade pip setuptools
        python -m pip install -e ".[dev]"

3. 거래량 상위 200개 선정 로직을 구현한다.

    `app/batch/src/jobs/stock_universe/domain/service.py`에는 외부 API나 DB를 직접 호출하지 않는 순수 함수를 둔다. 이 함수는 KRX 목록 데이터를 입력받아 내부 종목 레코드 목록을 반환한다. 반환 레코드는 최소한 종목코드, 종목명, 시장 구분, 거래량을 포함한다. 거래량은 숫자로 비교한다. 정렬은 거래량 내림차순, 종목코드 오름차순이다. `market`은 DB 저장 기준으로 `KOSPI`, `KOSDAQ`만 허용하고, `KOSDAQ GLOBAL`은 `KOSDAQ`으로 정규화한다. 종목 유형 필터는 넣지 않는다.

    검증 명령 예시:

        cd /Users/sehako/workspace/stock-report-batch/app/batch
        . .venv/bin/activate
        pytest

    기대 결과는 상위 200개 선정 테스트가 통과하는 것이다.

4. `FinanceDataReader` 클라이언트와 기본 배치 흐름을 구현한다.

    `app/batch/src/jobs/stock_universe/infrastructure/client/finance_data_reader_client.py`는 `FinanceDataReader.StockListing("KRX")` 호출만 감싼다. `app/batch/src/jobs/stock_universe/application/stock_universe_runner.py`는 기본 실행에서 클라이언트를 호출하고, domain service로 상위 200개를 고른 뒤 repository에 저장을 요청한다. `app/batch/src/batch/main.py`는 설정과 로깅을 준비하고 runner를 호출한다.

    네트워크 의존성이 있는 실제 FDR 호출은 단위 테스트에서 직접 호출하지 않는다. 테스트에서는 가짜 DataFrame을 주입해 selector와 batch 흐름을 확인한다.

5. `stock` 테이블 저장소를 구현한다.

    `app/batch/src/jobs/stock_universe/infrastructure/persistence/stock_universe_repository.py`는 `DATABASE_URL`로 PostgreSQL 연결을 열고 트랜잭션 안에서 upsert와 `tracked` 갱신을 수행한다. upsert는 실제 DB의 `uk_stock_market_stock_code` 제약에 맞춰 `ON CONFLICT (market, stock_code) DO UPDATE`를 사용한다. 삽입 값은 `market`, `stock_code`, `stock_name`, `tracked`이고, `id`는 데이터베이스가 자동으로 만든다. 실제 DB에는 `last_loaded_date` 컬럼이 없으므로 읽거나 쓰지 않는다. 제외 종목 로그의 `tracked = false` 변경 수는 실제로 `true`에서 `false`로 바뀐 행 수만 센다.

    저장소의 완료 조건은 같은 종목코드로 배치를 반복 실행해도 `stock` 행이 중복되지 않고, `tracked` 상태가 현재 상위 200개 목록과 일치하는 것이다.

6. 최종 검증을 수행한다.

    자동 테스트:

        cd /Users/sehako/workspace/stock-report-batch/app/batch
        . .venv/bin/activate
        pytest

    수동 DB 검증 예시:

        cd /Users/sehako/workspace/stock-report-batch/app/batch
        . .venv/bin/activate
        python -m batch.main

        SELECT COUNT(*) FROM stock WHERE tracked = true;
        SELECT stock_code, stock_name, market, tracked FROM stock WHERE tracked = true ORDER BY stock_code LIMIT 10;

    기대 결과는 첫 번째 쿼리의 값이 200인 것이다. 배치 로그에는 선정 top 200 종목코드 집합 digest와 DB tracked 종목코드 집합 digest가 함께 출력되고 두 값이 일치해야 한다.

## 검증과 수락 기준

수락 기준은 다음과 같다.

- 사용자는 옵션 없는 기본 Python 배치를 실행할 수 있다.
- 배치는 `FinanceDataReader.StockListing("KRX")`로 KRX 종목 목록을 조회한다.
- 배치는 거래량 기준 상위 200개 종목을 선정한다.
- 배치는 선정된 종목을 `stock` 테이블에 upsert한다.
- 배치 실행 후 현재 상위 200개 종목은 `tracked = true`이다.
- 배치 실행 후 이전에 저장되었지만 현재 상위 200개에서 제외된 종목은 `tracked = false`이다.
- ETF, ETN, 우선주 등 비보통주를 이름이나 시장 구분으로 제외하지 않는다.
- 같은 입력으로 배치를 반복 실행해도 `stock` 행이 중복되지 않는다.
- 종목 일봉 가격, 지수 일봉 가격, 지정 재수집 옵션, Spring Boot 조회 API는 이 이슈에서 새로 동작하지 않는다.
- 배치 로그에서 선정 top 200 종목코드 집합 digest와 DB tracked 종목코드 집합 digest가 일치한다.

자동 테스트는 최소한 다음을 검증해야 한다.

- 201개 이상의 샘플 종목에서 거래량 상위 200개만 선택된다.
- 거래량이 문자열로 들어와도 숫자 기준으로 정렬된다.
- 거래량 동률이면 종목코드 오름차순으로 정렬된다.
- 거래량 결측값이나 숫자 변환 불가 값은 0으로 처리된다.
- 종목코드 또는 종목명이 비어 있는 행은 제외된다.
- `KOSDAQ GLOBAL`은 `KOSDAQ`으로 정규화되고, `KONEX` 등 코스피와 코스닥 밖의 시장은 제외된다.
- 같은 `stock_code`가 중복되면 거래량이 가장 큰 행 하나만 사용된다.
- 비보통주로 보이는 이름의 종목도 거래량이 높으면 결과에 포함된다.
- 이전 tracked 종목과 현재 상위 200개 종목이 다를 때 제외 종목을 `tracked = false`로 만드는 저장소 로직이 검증된다. 자동 테스트는 fake 저장소나 fake 연결로 검증하고, 실제 PostgreSQL 검증은 수동 절차로 남긴다.

## 멱등성과 복구

이 배치는 멱등적이어야 한다. 멱등적이라는 말은 같은 입력과 같은 DB 상태에서 여러 번 실행해도 최종 결과가 동일해야 한다는 뜻이다. 실제 DB의 `(market, stock_code)` 유니크 제약을 기준으로 upsert하므로 같은 시장의 같은 종목이 반복 삽입되지 않아야 한다. `tracked` 값은 매 실행마다 현재 상위 200개 목록을 기준으로 다시 계산하므로, 이전 실행의 잔여 상태에 의존하지 않아야 한다.

DB 갱신 중 오류가 발생하면 PostgreSQL 트랜잭션이 롤백되어야 한다. 롤백은 트랜잭션 안의 변경을 모두 취소하는 데이터베이스 동작이다. 일부 종목만 `tracked = true`가 된 상태로 남으면 안 된다. 실패 후 원인을 수정하고 같은 배치를 다시 실행하면 정상 최종 상태로 복구할 수 있어야 한다.

파괴적인 데이터 삭제는 이 이슈에서 필요하지 않다. 상위 200개에서 제외된 종목도 삭제하지 않고 `tracked = false`로 남긴다. 이 동작은 설계 문서의 `tracked` 의미와 일치한다.

## 산출물과 메모

이 계획 작성 시 확인한 핵심 증거는 다음과 같다.

    rg --files docs app
    rg: app: No such file or directory (os error 2)
    docs/issues/02-batch-stock-universe-selection.md
    docs/issues/01-market-data-schema.md
    docs/specs/2026-07-15-stock-market-data-service-design.md
    docs/templates/exec-plan.md
    docs/templates/prompt/create-exec-plan.md
    docs/architecture/batch.md

    docker exec local-postgres psql -U app -d stock_report -P pager=off -c "select table_name, column_name, data_type, is_nullable, column_default from information_schema.columns where table_schema='public' and table_name in ('stock','stock_price','market_index_price') order by table_name, ordinal_position;"
    결과 요약: stock은 id, market, stock_code, stock_name, tracked 컬럼을 가진다. stock_price는 stock_id 외래 키를 가진다. market_index_price는 index_code와 trade_date 유니크 제약을 가진다.

    docker exec local-postgres psql -U app -d stock_report -P pager=off -c "select conrelid::regclass as table_name, conname, pg_get_constraintdef(oid) as definition from pg_constraint where conrelid in ('stock'::regclass, 'stock_price'::regclass, 'market_index_price'::regclass) order by conrelid::regclass::text, conname;"
    결과 요약: stock의 유니크 제약은 UNIQUE (market, stock_code)이고, stock에는 last_loaded_date 컬럼이 없다.

    git log --oneline -5
    ede209f docs(agents): 이슈 작업 지침 수정
    7ceda58 docs(template): 실행 계획 템플릿 추가
    1108e2a docs(issue): 시장 데이터 구현 이슈 정리
    c7f2c37 docs(spec): 주식 시장 데이터 서비스 설계 추가
    861cd67 docs(architecture): 아키텍처와 실행 계획 문서 추가

## 인터페이스와 의존성

새 Python 배치는 `FinanceDataReader.StockListing("KRX")`에 의존한다. `FinanceDataReader`는 금융 데이터를 가져오는 Python 라이브러리이며, 이 이슈에서는 KRX 종목 목록 조회에만 사용한다.

배치는 PostgreSQL에 연결해야 한다. PostgreSQL은 행과 열로 된 테이블에 데이터를 저장하는 관계형 데이터베이스다. 이 계획은 다른 워크트리에서 백엔드 마이그레이션이 완료되어 로컬 PostgreSQL `localhost:5432`의 `stock_report` 데이터베이스에 `stock`, `stock_price`, `market_index_price` 테이블이 이미 있는 상태를 전제로 한다. Python 드라이버는 `psycopg[binary]`를 사용하고, `stock` upsert는 실제 DB 제약에 맞춰 `ON CONFLICT (market, stock_code) DO UPDATE` 문법을 사용한다.

환경 변수는 데이터베이스 접속 정보를 전달하는 기본 방식으로 사용한다. 이 이슈에서는 `DATABASE_URL` 하나를 사용한다. 값의 형식은 `postgresql://user:password@localhost:5432/dbname` 같은 PostgreSQL 접속 URL이다. 접속 문자열, 비밀번호, 토큰은 코드나 문서에 실제 값으로 기록하지 않는다.

Python 의존성은 `app/batch/pyproject.toml`에 기록한다. 의존성을 설치할 때는 `app/batch/.venv` 가상환경을 만들고 활성화한 뒤 설치한다. 이 방식은 사용자의 전역 Python 환경을 바꾸지 않는다. `.venv`는 로컬 산출물이므로 Git에 커밋하지 않는다.

외부로 노출되는 HTTP API는 이 이슈에서 추가하지 않는다. `stock` 테이블의 데이터 계약은 이후 Spring Boot 조회 API가 사용하므로, 이 이슈는 실제 DB에 존재하는 `id`, `market`, `stock_code`, `stock_name`, `tracked`의 의미를 바꾸지 않는다. 설계 문서에 언급된 `last_loaded_date`는 현재 실제 DB에 없으므로 이 이슈에서 다루지 않는다.

계획 변경 메모:

- 2026-07-17 / Codex: 초기 ExecPlan 작성. 이유: `docs/issues/02-batch-stock-universe-selection.md`를 구현하기 전에 실제 저장소 구조, 선행 스키마 의존성, 구현 순서, 검증 방법을 자기완결적으로 정리하기 위해서.
- 2026-07-17 / 사용자, Codex: 계획 검토에서 확정한 사항을 반영. 이유: 배치 아키텍처 문서의 `jobs/stock_universe` 구조와 맞추고, 로컬 PostgreSQL 전제, `pyproject.toml`과 `.venv` 사용, `DATABASE_URL`, `psycopg[binary]`, 데이터 정규화 규칙, mock/fake 자동 테스트와 실제 FDR plus PostgreSQL 수동 검증 전략을 구현 전에 명확히 하기 위해서.
- 2026-07-17 / 사용자, Codex: 로컬 PostgreSQL `stock_report`의 실제 스키마를 기준으로 계획을 갱신. 이유: 실제 `stock` 테이블에는 `last_loaded_date`가 없고 유니크 제약이 `(market, stock_code)`이므로, 구현 계획의 upsert SQL과 컬럼 계약을 실제 데이터베이스와 일치시키기 위해서.
- 2026-07-17 / Codex: 이슈 02 구현 완료 결과를 반영. 이유: TDD로 추가한 자동 테스트, Python 3.14 기반 설치 절차, 실제 FDR 응답 확인, 로컬 PostgreSQL 스키마 확인, `DATABASE_URL` 부재로 보류한 실제 DB 쓰기 검증 상태를 다음 작업자가 ExecPlan만 보고 재현할 수 있게 하기 위해서.
- 2026-07-17 / 사용자, Codex: 로컬 개발 DB 접속 정보를 사용해 실제 DB 쓰기 검증 결과를 반영. 이유: 보류되었던 `python -m batch.main` 실행, tracked 200개 확인, 반복 실행 멱등성 확인이 완료되었기 때문이다. 접속 문자열은 민감정보라 문서에는 기록하지 않고 Git에서 제외되는 `app/batch/.env`에만 둔다.
- 2026-07-17 / 사용자, Codex: `KOSDAQ GLOBAL`을 `KOSDAQ`으로 정규화하도록 계획과 구현 결과를 갱신. 이유: 코스닥 글로벌은 코스닥 세그먼트이므로 제외하면 이슈의 KRX 거래량 상위 200개 선정 취지와 어긋나기 때문이다.
