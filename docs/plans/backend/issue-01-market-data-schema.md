# ExecPlan: 시장 데이터 RDB 스키마 구성

> 이 ExecPlan은 이슈의 조사부터 구현 완료까지 지속적으로 갱신하는 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 항상 현재 상태와 일치하도록 유지해야 한다.
>
> 계획과 실제 구현이 달라진 경우 기존 계획을 조용히 덮어쓰지 않는다. 계획 본문은 현재 실행 방향에 맞게 갱신하되, 변경된 이유와 영향은 `결정 기록` 또는 `예상 밖의 발견`에 남긴다.
>
> 이 문서는 이슈의 요구사항을 대체하지 않는다. 요구사항이나 완료 기준이 변경되면 GitHub 이슈를 먼저 갱신한 뒤 이 ExecPlan에 반영한다.

## 이슈 정보

- Issue: #01
- 상태: 구현 완료
- 작성일: `2026-07-16`
- 최종 갱신일: `2026-07-17`
- 관련 문서:
  - `docs/issues/01-market-data-schema.md`
  - `docs/specs/2026-07-15-stock-market-data-service-design.md`
  - `docs/architecture/backend.md`
  - `docs/templates/prompt/create-exec-plan.md`
  - `docs/templates/exec-plan.md`

## 목표

이 이슈의 목표는 주식 시장 데이터 조회 서비스 MVP에서 Python 배치와 Spring Boot 조회 API가 함께 사용할 수 있는 PostgreSQL 저장 구조를 만드는 것이다. 구현이 끝나면 저장소에는 Flyway 마이그레이션으로 관리되는 종목 메타데이터, 종목 일봉, 시장 지수 일봉 테이블 생성 정의가 존재해야 하며, 같은 종목 또는 같은 지수의 같은 거래일 데이터가 중복 저장되지 않아야 한다.

- 구현하거나 변경할 대상: `stock`, `stock_price`, `market_index_price` 테이블과 중복 방지 제약, 주요 조회 조건을 위한 인덱스.
- 사용자가 확인할 수 있는 최종 동작: 스키마 생성 검증을 실행했을 때 세 테이블과 유니크 제약이 생성되고, 동일한 종목의 동일 거래일 또는 동일한 `index_code`/`trade_date` 조합을 두 번 저장할 수 없음을 확인할 수 있다.
- 이슈 완료 기준과의 관계: Python 배치 구현, Spring Boot 조회 API 구현, React 화면 구현, 배치 실행 이력 테이블은 만들지 않고, 이슈 본문에 있는 DB 스키마 범위만 완료한다.

## 코드베이스 조사

구현 전에 저장소의 실제 파일과 문서를 확인했다. 구현 시작 시점에는 `app/backend` 디렉터리와 Spring Boot 프로젝트 파일이 없고, 문서와 프로토타입만 존재했다. 이번 구현에서 최초 백엔드 프로젝트와 최초 DB 마이그레이션 구조를 함께 추가했다.

### 관련 코드

- `docs/issues/01-market-data-schema.md`: 이번 이슈의 작업 범위, 제외 범위, 검증 흐름을 정의한다.
- `docs/specs/2026-07-15-stock-market-data-service-design.md`: MVP 데이터 모델을 정의한다. `stock`, `stock_price`, `market_index_price` 세 테이블과 각 컬럼의 의미, `stock_code`/`trade_date`, `index_code`/`trade_date` 유니크 제약을 명시한다. 이 ExecPlan에서는 이후 미국장 확장 가능성과 JPA 단순성을 고려해 `stock.id`를 종목 내부 식별자로 두고, `stock_price`는 `stock_id`/`trade_date` 유니크 제약으로 같은 의미의 중복 방지를 구현한다.
- `docs/architecture/backend.md`: Spring Boot 백엔드의 도메인 중심 계층 구조와 의존성 방향을 정의한다. 다만 이번 이슈는 DB 스키마 생성이 중심이므로 controller, service, repository 구현은 제외한다.
- `docs/prototypes/stock-analysis/finance_data_to_csv.py`: 기존 데이터 수집 프로토타입이다. `FinanceDataReader`로 KRX 종목 목록과 종목 일봉 데이터를 가져오며, CSV 기반 저장 방식을 사용한다. 이번 이슈에서는 이 파일을 수정하지 않는다.
- `app/backend`: 이번 구현에서 최소 Kotlin + Spring Boot Gradle 프로젝트로 생성했다. Flyway 마이그레이션 파일과 스키마 검증 테스트를 포함한다.
- `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`: 시장 데이터 세 테이블과 제약, 인덱스를 생성한다.
- `app/backend/src/main/resources/application.yml`: Spring Boot 실행 시 datasource와 Flyway 활성화 설정을 환경 변수 기반으로 제공하며, 환경 변수가 없으면 로컬 개발 DB 기본값을 사용한다.
- `app/backend/src/test/kotlin/com/stockreport/marketdata/MarketDataSchemaTest.kt`: Testcontainers PostgreSQL에 Flyway 마이그레이션을 적용한 뒤 테이블, 유니크 제약, 체크 제약, tracked 종목 조회 인덱스를 검증한다.
- 관련 테스트 또는 검증 코드: `./gradlew test`, `./gradlew build`로 실행한다.

### 기존 규칙과 제약

- 패키지 또는 모듈 구조: 백엔드는 `app/backend` 아래 Kotlin + Spring Boot로 구성한다.
- 계층 간 의존성 방향: `docs/architecture/backend.md`는 `presentation → application → domain`, `infrastructure → domain` 방향을 요구한다. 이번 이슈는 DB 스키마만 다루므로 계층 간 호출 코드는 만들지 않는다.
- 데이터베이스 및 마이그레이션 방식: 대상 DB는 PostgreSQL로 확정한다. 마이그레이션 도구는 Flyway로 확정하며, 마이그레이션 파일은 Spring Boot 백엔드의 `app/backend/src/main/resources/db/migration` 아래에 둔다.
- 트랜잭션 관리 방식: 이번 이슈에서는 애플리케이션 트랜잭션을 구현하지 않는다. 이후 배치 또는 API 이슈에서 application 계층 트랜잭션을 다룬다.
- 테스트 작성 방식: JUnit 5 기반 Kotlin 테스트를 사용한다. Orbstack Docker 환경을 전제로 Testcontainers PostgreSQL을 사용해 실제 PostgreSQL 엔진에 Flyway SQL과 제약 동작을 검증한다. H2 fallback은 두지 않고, Docker/Testcontainers 환경 문제가 있으면 검증 실패로 다룬다.
- 설정 및 환경 변수 관리 방식: Spring Boot 실행용 `app/backend/src/main/resources/application.yml`은 PostgreSQL datasource와 Flyway 설정을 제공한다. DB URL, 사용자명, 비밀번호는 환경 변수로 주입할 수 있고, 환경 변수가 없으면 로컬 개발 DB 기본값을 사용한다. 운영 민감정보는 코드나 문서에 직접 작성하지 않는다.
- 외부 의존성 연동 방식: 데이터 수집은 Python 배치와 `FinanceDataReader`가 담당하지만, 이번 이슈에서는 외부 API 연동을 구현하지 않는다.

### 현재 동작

현재 이슈와 직접 연결된 실행 가능한 백엔드 동작은 Flyway 마이그레이션 기반 스키마 생성 검증이다.

1. `app/backend`에는 최소 Spring Boot 프로젝트와 Gradle wrapper가 존재한다.
2. `V1__create_market_data_tables.sql`은 `stock`, `stock_price`, `market_index_price`를 생성한다.
3. `application.yml`은 환경 변수 기반 datasource, 로컬 개발 기본값, Flyway 활성화 설정을 제공한다.
4. `MarketDataSchemaTest`는 Testcontainers PostgreSQL에 마이그레이션을 적용한 뒤 테이블 존재, 중복 저장 실패, 허용되지 않은 시장/지수 코드 저장 실패, tracked 조회 인덱스 존재를 검증한다.

### 영향 범위

- 직접 변경되는 영역: `app/backend`의 Gradle 프로젝트 구조, DB 마이그레이션, 관련 스키마 검증 테스트.
- 간접적으로 영향받을 수 있는 영역: 이후 Python 배치의 upsert 구현, Spring Boot 조회 API의 엔티티 및 repository 구현, 프론트엔드가 소비할 API 응답의 데이터 기반.
- 호환성을 확인해야 하는 영역: `docs/specs/2026-07-15-stock-market-data-service-design.md`의 데이터 모델, `docs/issues/02-batch-stock-universe-selection.md` 이후 배치 이슈, `docs/issues/06-backend-market-index-summary-api.md` 이후 API 이슈.
- 변경하지 않아야 하는 영역: `docs/prototypes/stock-analysis`의 CSV 프로토타입, React 화면, Spring Boot 조회 API, Python 배치 로직, 배치 실행 이력 테이블.

## 변경 범위

- [x] `stock` 테이블 생성 정의를 추가한다.
- [x] `stock_price` 테이블 생성 정의를 추가한다.
- [x] `market_index_price` 테이블 생성 정의를 추가한다.
- [x] `stock_price`에 `stock_id`, `trade_date` 조합 유니크 제약을 적용한다.
- [x] `market_index_price`에 `index_code`, `trade_date` 조합 유니크 제약을 적용한다.
- [x] 배치 upsert와 API 조회에 필요한 인덱스를 검토하고 최소 인덱스를 적용한다.
- [x] 세 테이블과 제약이 정상 생성되는지 자동 또는 실행 가능한 검증을 추가한다.
- [x] Spring Boot 실행용 `application.yml`을 추가하고 datasource 및 Flyway 설정을 환경 변수 기반으로 구성하되 로컬 개발 기본값을 둔다.

## 제외 범위

- Python 배치 구현은 제외한다.
- Spring Boot 조회 API 구현은 제외한다.
- React 화면 구현은 제외한다.
- 배치 실행 이력 테이블은 MVP 범위에서 제외한다.
- 종목 또는 지수 데이터의 실제 적재 로직은 제외한다.
- JPA 엔티티와 repository는 스키마 검증에 꼭 필요하지 않다면 이번 이슈에 포함하지 않는다.

## 구현 접근

- 적용할 구조: `app/backend`가 없다면 Kotlin + Spring Boot 프로젝트의 최소 구조를 만든 뒤, Flyway 마이그레이션 파일과 검증 테스트를 추가한다. 이미 백엔드 프로젝트가 생긴 상태에서 이 계획을 실행한다면 기존 빌드 도구는 따르되 DB 마이그레이션은 Flyway를 사용한다.
- 주요 데이터 흐름: 이후 Python 배치는 종목 목록을 `stock`에 저장하고, 종목 일봉을 `stock_price`에 저장하며, 코스피/코스닥 지수 일봉을 `market_index_price`에 저장한다. 종목 일봉 적재 시 배치는 `market`과 `stock_code`로 `stock.id`를 확인한 뒤 `stock_price.stock_id` 기준으로 upsert한다. 이후 Spring Boot API는 이 세 테이블을 읽기 전용으로 조회한다.
- 계층 또는 모듈별 책임: 이번 이슈는 DB 구조만 만든다. application, domain, presentation 계층의 비즈니스 흐름은 만들지 않는다.
- 외부 의존성 처리: `FinanceDataReader`나 외부 시장 데이터 API 호출은 구현하지 않는다.
- 실패 및 예외 처리: 동일 거래일 데이터 중복은 DB 유니크 제약으로 차단한다. 배치의 실패 처리와 upsert 정책은 후속 이슈에서 구현한다.
- 멱등성 또는 중복 처리: 배치가 같은 데이터를 다시 적재해도 중복 row가 생기지 않도록 DB 수준 유니크 제약을 먼저 둔다. 종목 메타데이터는 `UNIQUE (market, stock_code)`, 종목 일봉은 `UNIQUE (stock_id, trade_date)`, 지수 일봉은 `UNIQUE (index_code, trade_date)`를 사용한다.
- 동시성 처리: 같은 종목 또는 지수의 같은 거래일 데이터를 동시에 저장하려는 경우 DB 유니크 제약이 최종 방어선이 된다. 애플리케이션 재시도 정책은 이번 범위가 아니다.
- 기존 구현과의 일관성: 문서상 데이터 모델과 백엔드 아키텍처를 따른다. 아직 백엔드 코드가 없으므로 새 구조는 문서의 `app/backend` 기준을 벗어나지 않게 만든다.
- 선택 이유: 스키마를 먼저 확정해야 이후 배치와 API 이슈가 같은 데이터 계약을 기준으로 독립적으로 진행될 수 있다. `stock.id`를 내부 식별자로 사용하면 JPA 엔티티는 단일 기본키를 사용할 수 있고, `UNIQUE (market, stock_code)`는 코스피/코스닥을 넘어 미국장 등 다른 시장으로 확장할 여지를 남긴다.

### 확정 스키마 요약

`stock` 테이블은 종목 메타데이터와 현재 MVP 조회 대상 여부를 저장한다. `id`는 내부 기본키이고, 외부 데이터와 API에서 사용하는 식별자는 `market`, `stock_code` 조합이다.

- `id BIGSERIAL PRIMARY KEY`
- `market VARCHAR(20) NOT NULL`
- `stock_code VARCHAR(20) NOT NULL`
- `stock_name VARCHAR(255) NOT NULL`
- `tracked BOOLEAN NOT NULL DEFAULT false`
- `UNIQUE (market, stock_code)`
- `CHECK (market IN ('KOSPI', 'KOSDAQ'))`

`stock_price` 테이블은 종목 일봉을 저장한다. 같은 종목의 같은 거래일 데이터는 하나만 허용한다.

- `id BIGSERIAL PRIMARY KEY`
- `stock_id BIGINT NOT NULL REFERENCES stock(id)`
- `trade_date DATE NOT NULL`
- `open_price NUMERIC(19,4) NOT NULL`
- `high_price NUMERIC(19,4) NOT NULL`
- `low_price NUMERIC(19,4) NOT NULL`
- `close_price NUMERIC(19,4) NOT NULL`
- `volume BIGINT NOT NULL`
- `change_rate NUMERIC(10,4)`
- `UNIQUE (stock_id, trade_date)`

`market_index_price` 테이블은 코스피와 코스닥 지수 일봉을 저장한다. 같은 지수의 같은 거래일 데이터는 하나만 허용한다.

- `id BIGSERIAL PRIMARY KEY`
- `index_code VARCHAR(20) NOT NULL`
- `trade_date DATE NOT NULL`
- `open_price NUMERIC(19,4) NOT NULL`
- `high_price NUMERIC(19,4) NOT NULL`
- `low_price NUMERIC(19,4) NOT NULL`
- `close_price NUMERIC(19,4) NOT NULL`
- `volume BIGINT NOT NULL`
- `change_rate NUMERIC(10,4)`
- `UNIQUE (index_code, trade_date)`
- `CHECK (index_code IN ('KOSPI', 'KOSDAQ'))`

초기 인덱스는 유니크 제약으로 생성되는 복합 인덱스를 우선 활용한다. 종목 목록 조회를 위해 `stock(tracked, market)` 인덱스를 추가할 수 있다. `stock_price(stock_id, trade_date)`와 `market_index_price(index_code, trade_date)`는 유니크 제약 인덱스가 기간별 가격 조회와 중복 방지에 함께 사용된다.

## 구현 단계

### 1. 백엔드 프로젝트와 DB 도구 상태 확인

- 변경 내용: 구현 시작 시점의 `app/backend` 존재 여부와 빌드 도구를 확인한다. 백엔드 프로젝트가 여전히 없다면 이번 이슈에서 최소 Spring Boot 프로젝트를 함께 생성할지, 별도 선행 이슈로 분리할지 결정한다. DB는 PostgreSQL, 마이그레이션 도구는 Flyway로 고정한다.
- 예상 변경 파일:
  - `app/backend`
  - `app/backend/build.gradle.kts` 또는 기존 빌드 설정 파일
  - `app/backend/src/main/resources`

- 테스트 또는 검증:
  - `find app/backend -maxdepth 3 -type f | sort`
  - `find app/backend -maxdepth 2 -type f -name '*gradle*' -o -name 'pom.xml' | sort`

- 완료 조건:
  - Flyway 마이그레이션 파일을 `app/backend/src/main/resources/db/migration`에 둘 수 있는 프로젝트 구조가 있다.
  - PostgreSQL 기반 스키마 검증을 실행할 방법이 정해져 있다.

### 2. 시장 데이터 테이블 생성 정의 추가

- 변경 내용: 세 테이블 생성 정의를 추가한다. `stock`은 `id BIGSERIAL PRIMARY KEY`를 내부 기본키로 사용하고, `market`, `stock_code` 조합에 유니크 제약을 둔다. `stock.market`은 MVP에서 `KOSPI`, `KOSDAQ`만 허용한다. `stock.last_loaded_date`는 만들지 않고, 마지막 적재일은 이후 배치/API에서 `stock_price`의 `MAX(trade_date)`로 계산한다. `stock_price`는 `stock_id`와 거래일을 기준으로 종목 일봉을 저장한다. `market_index_price`는 `KOSPI`, `KOSDAQ` 같은 내부 지수 코드와 거래일을 기준으로 지수 일봉을 저장한다.
- 예상 변경 파일:
  - `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`

- 테스트 또는 검증:
  - `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`
  - Flyway 마이그레이션이 Testcontainers PostgreSQL 테스트 DB에 적용되는지 테스트로 확인한다.

- 완료 조건:
  - `stock`, `stock_price`, `market_index_price` 세 테이블이 생성된다.
  - 각 가격 테이블은 날짜별 시가, 고가, 저가, 종가, 거래량, 등락률을 저장할 수 있다.
  - 가격 계열 컬럼은 `NUMERIC(19,4)`, 등락률은 `NUMERIC(10,4)`, 거래량은 `BIGINT`로 생성된다.

### 3. 유니크 제약과 조회 인덱스 적용

- 변경 내용: `stock(market, stock_code)`, `stock_price(stock_id, trade_date)`, `market_index_price(index_code, trade_date)`에 유니크 제약을 추가한다. `stock.market`과 `market_index_price.index_code`에는 `KOSPI`, `KOSDAQ`만 허용하는 `CHECK` 제약을 둔다. 이후 API 조회 패턴을 고려해 `tracked` 종목 조회와 기간별 가격 조회에 필요한 최소 인덱스를 적용한다. `stock_id, trade_date`와 `index_code, trade_date` 유니크 제약은 각각 기간별 가격 조회에도 활용되므로, `stock_id` 또는 `index_code` 단독 인덱스는 초기에는 추가하지 않는다.
- 예상 변경 파일:
  - `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`

- 테스트 또는 검증:
  - 동일한 `market`, `stock_code` 조합을 두 번 넣는 검증에서 두 번째 저장이 실패하는지 확인한다.
  - 동일한 `stock_id`, `trade_date` 조합을 두 번 넣는 검증에서 두 번째 저장이 실패하는지 확인한다.
  - 동일한 `index_code`, `trade_date` 조합을 두 번 넣는 검증에서 두 번째 저장이 실패하는지 확인한다.
  - `stock.market` 또는 `market_index_price.index_code`에 허용되지 않은 값을 넣으면 실패하는지 확인한다.

- 완료 조건:
  - DB가 중복 일봉 저장을 막는다.
  - 시장 구분과 지수 코드에 허용되지 않은 값이 저장되지 않는다.
  - 기간별 가격 조회와 tracked 종목 조회를 위한 최소 인덱스가 존재한다.

### 4. Testcontainers 기반 스키마 검증 테스트 추가

- 변경 내용: 세 테이블과 주요 제약이 생성되는지 확인하는 테스트를 추가한다. Testcontainers PostgreSQL 테스트 DB에 마이그레이션을 적용하고 메타데이터 또는 실제 insert 시나리오로 검증한다. H2는 사용하지 않는다.
- 예상 변경 파일:
  - `app/backend/build.gradle.kts`
  - `app/backend/src/test/kotlin/.../MarketDataSchemaTest.kt`

- 테스트 또는 검증:
  - `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`

- 완료 조건:
  - Testcontainers가 `postgres:16-alpine` 컨테이너를 기동한다.
  - Flyway가 실제 PostgreSQL 테스트 DB에 마이그레이션을 적용한다.
  - 테스트가 세 테이블 존재를 확인한다.
  - 테스트가 `stock`, `stock_price`, `market_index_price`의 유니크 제약과 체크 제약 동작을 확인한다.

### 5. 백엔드 실행 설정 파일 추가

- 변경 내용: Spring Boot 애플리케이션이 실제 PostgreSQL에 연결하고 Flyway 마이그레이션을 실행할 수 있도록 `application.yml`을 추가한다. 공통 설정 파일에는 환경 변수 placeholder와 로컬 개발 기본값을 두고, 운영 DB 접속 정보는 작성하지 않는다.
- 예상 변경 파일:
  - `app/backend/src/main/resources/application.yml`

- 포함할 설정:
  - `spring.datasource.url`: `${SPRING_DATASOURCE_URL:jdbc:postgresql://localhost:5432/stock_report}`
  - `spring.datasource.username`: `${SPRING_DATASOURCE_USERNAME:stock_report}`
  - `spring.datasource.password`: `${SPRING_DATASOURCE_PASSWORD:stock_report}`
  - `spring.flyway.enabled`: `true`

- 테스트 또는 검증:
  - 환경 변수가 없어도 Spring Boot 애플리케이션이 로컬 개발 DB 기본값으로 datasource를 구성할 수 있는지 확인한다.
  - 환경 변수를 제공한 상태에서는 기본값보다 환경 변수 값이 우선되는지 확인한다.
  - 실제 PostgreSQL 인스턴스가 준비된 환경에서는 애플리케이션 시작 시 Flyway 마이그레이션이 적용되는지 확인한다.
  - 자동 스키마 검증은 Testcontainers PostgreSQL 기반 테스트로 수행한다.

- 완료 조건:
  - `application.yml`에 DB 연결과 Flyway 실행에 필요한 최소 설정이 존재한다.
  - 운영 민감정보가 파일에 직접 작성되지 않는다.
  - 환경 변수 없이 실행했을 때 로컬 개발 DB 기본값을 사용한다.

## 테스트 및 검증 계획

### 자동 테스트

- [x] 단위 테스트: 해당 없음. 이번 이슈는 애플리케이션 로직보다 DB 스키마가 중심이다.
- [x] 통합 테스트: Testcontainers PostgreSQL 테스트 DB에 Flyway 스키마를 생성하고 세 테이블 존재, 유니크 제약 동작, 체크 제약 동작, 인덱스 존재를 검증했다.
- [x] 회귀 테스트: 기존 백엔드 기능은 없으며, 새로 생성한 백엔드 프로젝트의 전체 테스트를 실행했다.

### 빌드 및 정적 검증

- [x] `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`
- [x] 백엔드 프로젝트가 생성된 경우 `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon build`
- [x] Flyway 마이그레이션이 테스트 실행 중 적용되는지 확인한다.

### 수동 검증

- [x] 테스트 DB에 접속해 `stock`, `stock_price`, `market_index_price` 테이블이 존재하는지 확인한다.
- [x] `stock`에 같은 `market`, `stock_code` 조합을 두 번 insert했을 때 중복 제약 오류가 발생하는지 확인한다.
- [x] `stock_price`에 같은 `stock_id`, `trade_date` 조합을 두 번 insert했을 때 중복 제약 오류가 발생하는지 확인한다.
- [x] `market_index_price`에 같은 `index_code`, `trade_date` 조합을 두 번 insert했을 때 중복 제약 오류가 발생하는지 확인한다.
- [x] `stock.market`과 `market_index_price.index_code`에 `KOSPI`, `KOSDAQ` 외 값을 insert했을 때 체크 제약 오류가 발생하는지 확인한다.

### 핵심 검증 시나리오

#### 정상 흐름

- 입력 또는 조건: 스키마 마이그레이션 또는 스키마 생성 검증을 실행한다.
- 기대 결과: 세 테이블과 주요 컬럼, 인덱스, 유니크 제약이 생성된다.

#### 중복 또는 재실행

- 입력 또는 조건: 같은 종목과 거래일의 종목 일봉, 같은 지수코드와 거래일의 지수 일봉을 각각 두 번 저장한다. 종목은 `stock_id`로 식별하며, `stock_id`는 `stock`의 `market`, `stock_code` 유니크 조합으로 결정된다.
- 기대 결과: 첫 번째 저장은 성공하고 두 번째 저장은 DB 유니크 제약으로 실패한다.

#### 기존 기능 회귀

- 확인 대상: 현재 저장소에는 실행 가능한 백엔드 기능이 없으므로 회귀 대상이 없다.
- 기대 결과: 백엔드 프로젝트가 생성된 뒤에는 전체 테스트가 통과해야 한다.

## 위험 및 대응

| 위험 | 영향 | 대응 및 검증 |
| --- | --- | --- |
| 구현 시작 시 `app/backend`가 없어 스키마만 추가할 위치가 불명확했음 | 프로젝트 생성까지 포함되어 범위가 커질 수 있음 | 최소 Spring Boot 프로젝트와 Flyway 마이그레이션 구조만 생성하고, 스키마 외 API/JPA 구현은 제외했다. |
| Spring Boot가 마이그레이션 실행 주체가 됨 | Python 배치를 백엔드보다 먼저 실행하면 테이블이 없을 수 있음 | 배치 실행 전 백엔드 마이그레이션 적용을 운영 절차로 명시하고, 배치 이슈에서 DB 준비 상태 확인을 다룬다. |
| Spring Boot 실행용 `application.yml`이 없음 | 마이그레이션 파일과 테스트는 있어도 애플리케이션 실행 시 datasource 설정이 없어 DB 연결 또는 Flyway 실행이 실패할 수 있음 | `application.yml`을 추가하고, DB 접속 정보는 환경 변수 placeholder와 로컬 개발 기본값으로 관리한다. |
| Testcontainers가 Docker API 버전을 낮게 협상함 | Orbstack Docker 서버가 최소 API version 요구사항을 만족하지 못한다고 판단해 테스트 초기화가 실패할 수 있음 | 테스트 JVM에 `api.version=1.40` system property를 설정해 검증한다. |
| `stock_price`가 `stock_id`를 사용함 | Python 배치는 가격 upsert 전에 `market`, `stock_code`로 `stock.id`를 확인해야 함 | 배치 이슈에서 tracked 종목 조회 시 `id`, `market`, `stock_code`를 함께 읽도록 계획한다. 지정 재수집은 기본 market을 `KOSPI`/`KOSDAQ` 중 어떻게 받을지 후속 이슈에서 다룬다. |
| 인덱스를 과도하게 추가함 | 쓰기 성능 저하와 불필요한 유지 비용이 생길 수 있음 | MVP 조회 조건에 필요한 최소 인덱스만 추가하고, 성능 최적화 인덱스는 실제 쿼리 구현 후 후속 이슈로 분리한다. |
| JPA 엔티티를 함께 구현해 범위가 확장됨 | API 또는 배치 이슈의 책임을 침범할 수 있음 | 스키마 검증에 필요한 최소 테스트 외 엔티티, repository, service 구현은 하지 않는다. |

## 미결정 사항

> 구현을 시작하기 위해 추가로 결정할 사항 없음.

이번 계획의 핵심 DB 결정은 `결정 기록`에 반영했다. 이후 구현 중 실제 Spring Boot 프로젝트 구조나 테스트 환경 제약으로 접근이 달라지면 이 섹션을 다시 열고, 변경 이유를 `결정 기록` 또는 `예상 밖의 발견`에 남긴다.

## 진행 상황

날짜와 함께 실제 진행 상태를 기록한다. 완료한 항목은 체크하고, 현재 작업 위치를 확인할 수 있도록 유지한다.

- [x] 이슈와 참고 문서 확인
- [x] 관련 코드베이스 조사
- [x] 영향 범위 확인
- [x] 초기 구현 접근 수립
- [x] 미결정 사항 해소
- [x] 실패하는 테스트 작성
- [x] 최소 구현
- [x] 리팩터링
- [x] 전체 테스트 및 빌드 검증
- [x] 관련 문서 갱신
- [x] 결과와 회고 작성
- [x] ExecPlan 최종 상태 확인

### 진행 기록

- `2026-07-16`: `docs/issues/01-market-data-schema.md`, MVP 설계 문서, 백엔드 아키텍처 문서, 템플릿 문서를 확인하고 초기 ExecPlan을 작성했다.
- `2026-07-16`: 저장소에 `app/backend` 디렉터리와 빌드 파일이 아직 없음을 확인했다. 이 제약을 구현 단계와 위험에 반영했다.
- `2026-07-16`: grill 세션에서 PostgreSQL, Spring Boot 리소스 경로의 Flyway, `id` 기반 가격 테이블, `stock.id`와 `UNIQUE (market, stock_code)`, `stock_id` 기반 종목 일봉, 숫자 타입, `last_loaded_date` 제거, `tracked` 유지 결정을 확정하고 ExecPlan에 반영했다.
- `2026-07-17`: `docs/templates/prompts/execute-exec-plan.md` 경로가 존재하지 않음을 확인하고, 승인된 ExecPlan 본문과 현재 저장소 문서를 기준으로 실행했다.
- `2026-07-17`: 최소 Kotlin + Spring Boot Gradle 프로젝트와 Gradle wrapper를 `app/backend`에 생성했다.
- `2026-07-17`: 마이그레이션 SQL 없이 스키마 테스트를 먼저 실행해 테이블 미존재 실패를 확인했다.
- `2026-07-17`: `V1__create_market_data_tables.sql`을 추가해 세 테이블, 유니크 제약, 체크 제약, tracked 조회 인덱스를 생성했다.
- `2026-07-17`: `./gradlew clean test build`를 실행해 테스트와 빌드가 통과함을 확인했다.
- `2026-07-17`: Spring Boot 실행용 `application.yml`이 없어 실제 PostgreSQL datasource와 Flyway 실행 설정을 후속 보완 항목으로 추가한 뒤 구현했다.
- `2026-07-17`: Orbstack Docker 환경을 전제로 스키마 검증을 H2 PostgreSQL 호환 모드가 아니라 Testcontainers PostgreSQL 기반으로 전환하는 후속 보완 항목을 반영한 뒤 구현했다.
- `2026-07-17`: `MarketDataSchemaTest`를 먼저 Testcontainers PostgreSQL 기반으로 바꾼 뒤 Testcontainers 의존성 부재로 `compileTestKotlin`이 실패하는 RED를 확인했다.
- `2026-07-17`: H2 테스트 의존성을 제거하고 Testcontainers 의존성을 추가했으며, `application.yml`에 환경 변수 기반 datasource와 Flyway 설정을 추가했다.
- `2026-07-17`: `application.yml`의 datasource 설정에 환경 변수가 없을 때 사용할 로컬 개발 기본값을 추가했다.
- `2026-07-17`: Testcontainers가 Orbstack Docker API 버전을 낮게 협상하는 문제를 확인하고, 테스트 JVM에 `api.version=1.40`을 설정했다.
- `2026-07-17`: `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test --rerun-tasks`와 `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon build`가 통과함을 확인했다.

## 예상 밖의 발견

### `2026-07-16` — 백엔드 프로젝트 부재

- 발견: 문서상 프로젝트 구조에는 `app/backend`가 있지만 실제 저장소에는 `app/backend` 디렉터리, Gradle/Maven 설정, Spring Boot 코드가 없다.
- 근거: `find app/backend -maxdepth 4 -type f` 실행 시 `find: app/backend: No such file or directory`가 출력되었다.
- 계획에 미친 영향: 스키마 파일만 추가하는 계획으로는 구현 위치를 특정할 수 없다. 구현 시작 시 백엔드 프로젝트 생성 여부와 PostgreSQL/Flyway 검증 환경을 먼저 확인해야 한다.
- 대응: 구현 단계 1에 백엔드 프로젝트와 DB 도구 상태 확인을 추가했다. 이후 grill 세션에서 PostgreSQL과 Flyway를 확정하고 `결정 기록`에 남겼다.

### `2026-07-17` — 요청한 실행 템플릿 경로 부재

- 발견: 요청에 포함된 `docs/templates/prompts/execute-exec-plan.md` 파일이 저장소에 없다.
- 근거: `sed -n '1,240p' docs/templates/prompts/execute-exec-plan.md` 실행 시 `No such file or directory`가 출력되었고, `rg --files docs/templates docs | rg 'execute-exec-plan|exec-plan|create-exec-plan'`에서는 `docs/templates/exec-plan.md`, `docs/templates/prompt/create-exec-plan.md`만 확인되었다.
- 계획에 미친 영향: 별도 실행 템플릿을 읽을 수 없었으므로 승인된 ExecPlan 자체의 진행 규칙과 TDD 지침에 따라 진행했다.
- 대응: 실제 코드와 문서를 확인하고, ExecPlan의 진행 상황과 결과 섹션을 구현 상태에 맞게 갱신했다.

### `2026-07-17` — Testcontainers 검증 환경 재검토

- 발견: 개발 환경에 Orbstack이 있으므로 Testcontainers PostgreSQL을 사용할 수 있는 방향으로 스키마 검증 전략을 재검토했다.
- 근거: 사용자가 Orbstack 사용 가능성을 명시했고, 이번 스키마 테스트는 PostgreSQL 방언 차이가 중요하므로 H2 호환 모드보다 실제 PostgreSQL 엔진 검증이 적합하다.
- 계획에 미친 영향: H2 PostgreSQL 호환 모드 검증은 후속 방향에서 제외하고, Testcontainers PostgreSQL 기반 검증을 수락 기준으로 변경한다.
- 대응: `build.gradle.kts`에서 H2 테스트 의존성을 제거하고 Testcontainers 의존성을 추가했다. `MarketDataSchemaTest`는 `postgres:16-alpine` 컨테이너의 JDBC 정보로 Flyway 마이그레이션을 실행하도록 전환했다.

### `2026-07-17` — 백엔드 실행 설정 파일 부재

- 발견: `app/backend/src/main/resources` 아래에 Spring Boot 실행용 `application.yml`이 없다.
- 근거: 리소스 디렉터리에는 `db/migration/V1__create_market_data_tables.sql`만 존재하며, `application.yml`, `application.yaml`, `application.properties` 파일은 확인되지 않았다.
- 계획에 미친 영향: 스키마 마이그레이션과 검증 테스트는 완료되었지만, 실제 애플리케이션 실행 시 PostgreSQL datasource와 Flyway 실행 설정을 별도로 추가해야 한다.
- 대응: `application.yml`을 추가해 datasource URL, 사용자명, 비밀번호를 환경 변수 placeholder로 주입하고, 환경 변수가 없을 때는 로컬 개발 기본값을 사용하도록 했다. Flyway를 활성화했으며 운영 민감정보는 파일에 직접 작성하지 않았다.

### `2026-07-17` — Orbstack Docker API version 협상 문제

- 발견: Testcontainers가 Orbstack Docker 서버에 API version `1.32`로 접근해 초기화에 실패했다.
- 근거: Testcontainers 리포트에 `client version 1.32 is too old. Minimum supported API version is 1.40` 오류가 기록되었고, `docker version`은 Orbstack 서버의 최소 API version이 `1.40`임을 보여주었다.
- 계획에 미친 영향: Testcontainers PostgreSQL 전환 자체는 유지하되, 테스트 JVM에 Docker API version을 명시해야 한다.
- 대응: `tasks.withType<Test>`에 `systemProperty("api.version", "1.40")`을 추가했다.

## 결정 기록

### `2026-07-16` — 이슈 #01은 스키마 범위로 제한

- 결정: 이번 계획은 `stock`, `stock_price`, `market_index_price` 테이블과 제약, 인덱스, 스키마 검증까지만 포함한다.
- 이유: 이슈의 제외 범위가 Python 배치, Spring Boot 조회 API, React 화면, 배치 실행 이력 테이블을 명시적으로 제외한다.
- 검토한 대안: 스키마와 함께 JPA 엔티티, repository, API 조회 틀을 만드는 방안을 검토할 수 있으나, 이는 후속 API 이슈 범위를 침범한다.
- 영향: 이후 이 계획을 실행하는 작업자는 DB 스키마 검증에 꼭 필요한 테스트 외 애플리케이션 계층 구현을 추가하지 않는다.

### `2026-07-16` — DB 중복 방지는 애플리케이션보다 DB 제약을 우선

- 결정: 종목 일봉과 지수 일봉의 중복 방지는 DB 유니크 제약을 필수 수락 기준으로 둔다. 종목 일봉은 `UNIQUE (stock_id, trade_date)`, 지수 일봉은 `UNIQUE (index_code, trade_date)`를 사용한다.
- 이유: 배치는 재실행과 지정 재수집을 지원해야 하며, 애플리케이션 로직만으로 중복을 막으면 동시 실행이나 장애 재시도에서 데이터 정합성이 깨질 수 있다.
- 검토한 대안: 배치에서 저장 전 조회로 중복을 피하는 방식은 이후 구현할 수 있지만, DB 제약 없이 단독으로 사용하면 최종 방어선이 없다.
- 영향: 스키마 검증은 단순 테이블 존재 확인뿐 아니라 중복 insert 실패까지 확인해야 한다.

### `2026-07-16` — PostgreSQL과 Flyway 사용

- 결정: 대상 RDB는 PostgreSQL로 확정하고, DB 마이그레이션은 Spring Boot 백엔드의 `app/backend/src/main/resources/db/migration` 경로에 둔 Flyway SQL 파일로 관리한다.
- 이유: PostgreSQL은 `ON CONFLICT` 기반 upsert가 명확해 이후 Python 배치와 잘 맞고, Spring Boot와 Flyway 연동이 단순하다. MVP에서는 별도 공통 DB 마이그레이션 프로젝트보다 백엔드 애플리케이션 시작 또는 테스트 시 자동 적용되는 방식이 운영과 개발 편의성이 높다.
- 검토한 대안: MySQL은 운영 환경이 이미 MySQL로 고정된 경우가 아니라면 이점이 적다. 루트 공통 `db/migration` 경로는 Python 배치와 Spring API의 공동 DB 계약을 더 명확하게 표현하지만, 별도 실행 책임이 개발자 또는 CI에 남아 MVP 편의성이 낮다. Liquibase는 변경 이력과 rollback 관리가 강하지만 현재 테이블 3개를 만드는 범위에는 과하다.
- 영향: Python 배치는 마이그레이션 실행 주체가 아니며, 배치 실행 전 백엔드 마이그레이션이 선행되어야 한다.

### `2026-07-16` — 종목과 가격 테이블은 내부 ID를 사용

- 결정: `stock`, `stock_price`, `market_index_price`에는 `id BIGSERIAL PRIMARY KEY`를 둔다. `stock`은 `UNIQUE (market, stock_code)`로 외부 종목 식별자의 중복을 막고, `stock_price`는 `stock_id`로 `stock.id`를 참조하며 `UNIQUE (stock_id, trade_date)`를 둔다.
- 이유: JPA 엔티티는 단일 기본키를 사용할 수 있어 단순하고, `UNIQUE (market, stock_code)`는 코스피/코스닥을 넘어 미국장 같은 다른 시장 확장 여지를 남긴다. 가격 테이블에서 `stock_id`를 쓰면 동일 ticker가 다른 시장에 존재할 때도 중복 기준이 명확하다.
- 검토한 대안: `stock.stock_code`를 기본키로 두면 현재 KRX MVP에는 단순하지만, 미국장 등으로 확장할 때 코드 단독 유일성을 보장하기 어렵다. `stock_price.stock_code`가 `stock.stock_code`를 직접 참조하는 방식은 배치가 단순하지만 시장 확장성이 약하다.
- 영향: Python 배치는 가격 적재 전 `market`, `stock_code`로 `stock.id`를 확인해야 한다. 기존 이슈 문서의 `stock_code`, `trade_date` 중복 방지 표현은 논리적으로는 유지되지만, 실제 DB 제약은 `stock_id`, `trade_date`로 구현된다.

### `2026-07-16` — 시장 구분과 지수 코드는 문자열 CHECK 제약 사용

- 결정: `stock.market`은 `KOSPI`, `KOSDAQ`만 허용하는 `VARCHAR(20)`과 `CHECK` 제약을 사용한다. `market_index_price.index_code`도 `KOSPI`, `KOSDAQ`만 허용하는 `VARCHAR(20)`과 `CHECK` 제약을 사용한다.
- 이유: 이번 MVP의 사용자가 필터링할 시장 구분은 `KRX`가 아니라 코스피/코스닥이다. PostgreSQL enum보다 문자열과 `CHECK` 제약이 이후 값 추가 마이그레이션을 다루기 쉽다.
- 검토한 대안: `KRX`를 `market`에 저장하고 코스피/코스닥을 별도 컬럼으로 두는 방식은 MVP 화면 필터와 맞지 않는다. `country`, `exchange`, `market_segment`를 지금부터 분리하는 방식은 현재 범위에 비해 과하다.
- 영향: `FinanceDataReader.StockListing("KRX")`의 `KRX`는 배치 입력 범위로만 사용하고 DB의 `stock.market`에는 `KOSPI` 또는 `KOSDAQ`을 저장한다.

### `2026-07-16` — 가격 숫자 타입 확정

- 결정: 시가, 고가, 저가, 종가 같은 가격 계열은 `NUMERIC(19,4)`, 등락률은 `NUMERIC(10,4)`, 거래량은 `BIGINT`를 사용한다.
- 이유: 지수 값과 등락률은 소수점이 필요하고, FDR/Pandas에서 원 단위 종목 가격도 소수점 형태로 들어올 수 있다. `NUMERIC`은 시장 데이터에서 부동소수점 오차를 피한다.
- 검토한 대안: 종목 가격만 `BIGINT`로 두고 지수 값만 `NUMERIC(19,4)`로 나누는 방식은 저장 공간은 아낄 수 있지만 배치 매핑과 API 변환에서 타입이 갈라진다.
- 영향: 종목 가격과 지수 가격은 같은 타입으로 저장되며, API와 차트 데이터 변환에서 일관된 숫자 처리가 가능하다.

### `2026-07-16` — `stock.last_loaded_date` 제거와 `tracked` 유지

- 결정: `stock.last_loaded_date`는 만들지 않는다. 마지막 적재일은 `stock_price`에서 `MAX(trade_date)`로 계산한다. `stock.tracked BOOLEAN NOT NULL DEFAULT false`는 유지한다.
- 이유: `last_loaded_date`를 별도로 저장하면 가격 적재 실패나 특정 기간 재수집 뒤 실제 가격 데이터와 불일치할 수 있다. 반면 `tracked`는 현재 거래량 상위 200개 조회 대상 여부를 빠르게 표현하는 MVP 핵심 상태다.
- 검토한 대안: `last_loaded_date`를 유지하면 마지막 적재일 조회는 빠르지만, 데이터 정합성 책임이 배치 코드에 더 강하게 묶인다. `tracked`를 별도 선정 테이블로 분리하는 방식은 랭킹 이력까지 다룰 수 있으나 MVP 범위를 넘는다.
- 영향: 이후 배치 이슈는 마지막 적재일 계산 시 `stock_price`를 조회해야 한다. 종목 목록 API는 `tracked = true`를 기준으로 MVP 조회 대상을 필터링한다.

### `2026-07-17` — 로컬 자동 테스트는 Testcontainers PostgreSQL 사용

- 결정: 로컬 자동 테스트는 Testcontainers PostgreSQL로 Flyway 마이그레이션과 핵심 제약 동작을 검증한다.
- 이유: 대상 DB가 PostgreSQL로 확정되어 있고, 스키마 마이그레이션은 DB 방언 차이의 영향을 직접 받는다. Orbstack Docker 환경이 있으므로 실제 PostgreSQL 컨테이너를 사용하는 편이 H2 호환 모드보다 정확하다.
- 검토한 대안: H2 PostgreSQL 호환 모드는 빠르고 단순하지만 PostgreSQL 엔진 고유 동작을 보장하지 않는다. 로컬 PostgreSQL 직접 연결은 개발자별 DB 상태에 의존하므로 테스트 독립성이 낮다.
- 영향: `MarketDataSchemaTest`는 Docker/Testcontainers 실행 환경에 의존한다. Docker가 unavailable이면 테스트 실패로 보고하고, H2 fallback은 두지 않는다.

### `2026-07-17` — Docker API version 명시

- 결정: Gradle Test task에 `systemProperty("api.version", "1.40")`을 설정한다.
- 이유: Orbstack Docker 서버의 최소 API version이 `1.40`인데 Testcontainers가 기본 협상에서 `1.32`를 사용해 초기화에 실패했다.
- 검토한 대안: 사용자 홈의 `~/.testcontainers.properties`를 수정할 수 있지만 저장소 외부 사용자 설정을 변경하는 방식이라 재현성이 낮다. Testcontainers 버전 상향은 추가 검토가 필요하므로 이번 범위에서는 최소 system property로 해결한다.
- 영향: 테스트 JVM은 Docker API version `1.40`으로 Orbstack Docker 서버와 통신한다.

## 결과와 회고

### 최종 변경 내용

- `app/backend`에 최소 Kotlin + Spring Boot Gradle 프로젝트와 Gradle wrapper를 추가했다.
- `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`에 `stock`, `stock_price`, `market_index_price` 테이블 생성 정의를 추가했다.
- `stock(market, stock_code)`, `stock_price(stock_id, trade_date)`, `market_index_price(index_code, trade_date)` 유니크 제약을 추가했다.
- `stock.market`, `market_index_price.index_code`에 `KOSPI`, `KOSDAQ` 체크 제약을 추가했다.
- `stock(tracked, market)` 조회 인덱스를 추가했다.
- `MarketDataSchemaTest`를 Testcontainers PostgreSQL 기반으로 전환해 실제 PostgreSQL 엔진에서 테이블 생성, 중복 저장 실패, 체크 제약 실패, 인덱스 생성을 검증했다.
- `app/backend/src/main/resources/application.yml`에 환경 변수 기반 datasource, 로컬 개발 기본값, Flyway 활성화 설정을 추가했다.

### 검증 결과

- RED: 마이그레이션 SQL 추가 전 `./gradlew test` 실행 시 테이블 미존재로 실패함을 확인했다.
- RED: `idx_stock_tracked_market` 인덱스 정의를 제거한 상태에서 인덱스 테스트가 실패함을 확인했다.
- RED: `MarketDataSchemaTest`를 Testcontainers PostgreSQL 기반으로 먼저 바꾼 뒤 Testcontainers 의존성 부재로 `compileTestKotlin`이 실패함을 확인했다.
- GREEN: `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test --rerun-tasks` 실행 결과 `BUILD SUCCESSFUL`을 확인했다.
- GREEN: `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon build` 실행 결과 `BUILD SUCCESSFUL`을 확인했다.

### 계획과 달라진 점

- 초기 구현 중에는 H2 PostgreSQL 호환 모드로 자동 검증했지만, Orbstack Docker 환경을 사용할 수 있음을 확인해 Testcontainers PostgreSQL 검증으로 전환했다.
- Testcontainers가 Orbstack Docker API version을 낮게 협상해 테스트 JVM에 `api.version=1.40`을 명시했다.

### 이슈 완료 기준 충족 여부

- [x] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [x] 관련 테스트 또는 검증 결과를 기록한다.
- [x] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [x] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

### 남은 한계

- Testcontainers 검증은 Docker 실행 환경에 의존한다.
- API, JPA 엔티티, repository, Python 배치 적재 로직은 이 이슈 범위에서 제외되어 아직 없다.

### 후속 작업

- `docs/issues/02-batch-stock-universe-selection.md` 이후 배치 이슈에서 `stock` 테이블 upsert 정책을 구현한다.
- `docs/issues/03-batch-stock-daily-price-loading.md`와 `docs/issues/04-batch-market-index-daily-price-loading.md`에서 가격 테이블 upsert와 재실행 멱등성을 구현한다.
- `docs/issues/06-backend-market-index-summary-api.md` 이후 API 이슈에서 조회 쿼리와 추가 인덱스 필요성을 실제 쿼리 기준으로 다시 검토한다.

### 회고

이번 구현으로 스키마 계약과 자동 검증의 기준점이 생겼다. 스키마 검증은 PostgreSQL 엔진 고유 동작의 영향을 받으므로, H2 호환 모드 대신 Testcontainers PostgreSQL로 같은 Flyway 마이그레이션을 확인하도록 조정한 것이 적절했다.

## 완료 확인

- [x] 이슈의 모든 작업 범위를 구현했다.
- [x] 이슈의 제외 범위를 침범하지 않았다.
- [x] 완료 기준을 테스트 또는 실행 결과로 확인했다.
- [x] 구현 중 주요 결정과 계획 변경을 기록했다.
- [x] 예상 밖의 발견과 대응을 기록했다.
- [x] 관련 문서를 갱신했다.
- [x] 후속 작업이 있다면 별도 이슈로 분리했다.
- [x] `결과와 회고`에 최종 구현 및 검증 결과를 기록했다.
- [x] ExecPlan이 최종 코드 상태와 일치한다.
