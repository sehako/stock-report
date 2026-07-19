# ExecPlan: 지수 최신 수치 조회 API 구현


이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다. 이 문서는 `docs/issues/06-backend-market-index-summary-api.md`의 구현 계획이며, 저장소를 처음 보는 사람도 이 파일만 읽고 작업을 이어갈 수 있도록 필요한 맥락과 결정을 포함한다.

## 목적과 큰 그림


이 변경의 목적은 Spring Boot 백엔드가 저장된 시장 지수 일봉 데이터에서 코스피와 코스닥의 최신 수치를 HTTP API로 제공하게 만드는 것이다. 구현 전에는 `market_index_price` 테이블에 데이터가 있어도 외부 사용자가 서버를 통해 최신 지수 값을 조회할 방법이 없다. 구현 후 사용자는 백엔드 서버를 실행하고 `GET /api/market-indexes`를 호출해 `KOSPI`와 `KOSDAQ` 각각의 최신 거래일, 최신 종가, 전일 대비 값, 등락률을 확인할 수 있다.

이 계획에서 "지수"는 코스피와 코스닥처럼 시장 전체의 움직임을 대표하는 숫자를 뜻한다. "일봉"은 하루 단위의 시가, 고가, 저가, 종가, 거래량, 등락률 데이터를 뜻한다. "전일 대비 값"은 최신 종가에서 같은 지수의 저장된 직전 거래일 종가를 뺀 값이다. "등락률 퍼센트"는 `market_index_price.change_rate`에 저장된 FinanceDataReader의 `Change` 원값에 100을 곱한 값이다. 예를 들어 DB의 `change_rate`가 `0.0123`이면 API의 `changeRatePercent`는 `1.2300`이다. 직전 거래일 데이터가 없으면 전일 대비 값은 계산할 수 없으므로 `null`로 응답한다.

## 진행 상황


- [x] (2026-07-17 00:00KST) `PLANS.md`, `EXECPLAN_TEMPLATE.md`, 대상 이슈, 백엔드 아키텍처 문서, 기존 스키마 계획, 현재 백엔드 코드를 조사했다.
- [x] (2026-07-17 00:00KST) API 응답 계약, 계층 구조, 조회 방식, 결측 데이터 처리 방식을 계획에 확정했다.
- [x] (2026-07-17 00:00KST) 구현 전 계획 검토에서 응답 필드와 등락률 계산 기준의 모호함을 확인하고 API 계약을 수정했다.
- [ ] `spring-boot-starter-web` 의존성을 추가하고 HTTP API 실행 기반을 만든다.
- [ ] `marketindex` 도메인 패키지에 controller, service, repository 인터페이스, JDBC repository 구현체, 응답 타입을 추가한다.
- [ ] 저장된 최신 row와 직전 row를 기준으로 최신 종가, 전일 대비 값, 등락률 퍼센트를 만든다.
- [ ] 데이터가 없는 지수는 HTTP 200 응답 안에서 `status: "EMPTY"`와 `null` 숫자 필드로 표현한다.
- [ ] 관련 service 테스트와 JDBC repository 또는 controller 통합 테스트를 추가한다.
- [ ] `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`로 전체 백엔드 테스트를 통과시킨다.
- [ ] 구현 결과와 검증 결과를 이 문서의 `결과와 회고`에 기록한다.

## 예상 밖의 발견


- 관찰: 현재 `app/backend`에는 `spring-boot-starter-jdbc`와 Flyway 기반 스키마 검증만 있고, HTTP controller를 실행하는 Web 의존성은 없다.
  증거: `app/backend/build.gradle.kts`에는 `implementation("org.springframework.boot:spring-boot-starter")`, `implementation("org.springframework.boot:spring-boot-starter-jdbc")`가 있지만 `spring-boot-starter-web`은 없다.

- 관찰: `market_index_price` 테이블은 최신 종가와 등락률을 저장하지만 전일 대비 값을 저장하지 않는다.
  증거: `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`의 `market_index_price` 컬럼은 `index_code`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `change_rate`이다.

- 관찰: `market_index_price.change_rate`는 nullable이므로 정상 배치에서는 값이 채워질 것으로 기대하더라도 API는 `null`을 방어해야 한다.
  증거: `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`의 `change_rate NUMERIC(10, 4)` 정의에는 `NOT NULL`이 없다.

## 결정 기록


- 결정: HTTP endpoint 구현을 위해 `app/backend/build.gradle.kts`에 `implementation("org.springframework.boot:spring-boot-starter-web")`를 추가한다.
  근거: 현재 백엔드에는 HTTP 요청을 처리하는 Spring MVC 의존성이 없고, 이 이슈의 핵심 산출물은 `GET /api/market-indexes` 엔드포인트다. 기존 Spring Boot와 Gradle 구조를 유지하면서 필요한 최소 의존성만 추가한다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 새 패키지는 `com.stockreport.marketindex`로 만들고, 하위 구조는 `presentation`, `application`, `application.response`, `domain`, `infrastructure.persistence`를 사용한다.
  근거: `docs/architecture/backend.md`는 도메인별 패키지와 `presentation → application → domain`, `infrastructure → domain` 의존성 방향을 요구한다. `market_index_price` 조회는 지수 도메인에 해당하므로 `marketindex`라는 단일 도메인 패키지에 모은다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: persistence 구현은 JPA가 아니라 JDBC로 작성한다.
  근거: 현재 프로젝트는 `spring-boot-starter-jdbc`를 이미 사용하고 JPA 의존성이 없다. 단순 읽기 쿼리 하나를 위해 JPA를 추가하면 새 의존성과 엔티티 매핑 범위가 커진다. JDBC repository는 기존 의존성만으로 구현할 수 있고 조회 SQL도 명확하다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 응답은 항상 `KOSPI`, `KOSDAQ` 두 항목을 같은 순서로 반환한다. 데이터가 없으면 해당 항목의 `status`를 `EMPTY`로 두고 날짜와 숫자 필드는 `null`로 반환한다.
  근거: 이슈는 데이터가 아직 적재되지 않은 지수를 명확한 빈 상태 또는 결측 상태로 응답하라고 요구한다. 항목 자체를 생략하면 클라이언트가 지수 코드 목록을 따로 알아야 하므로, 고정 두 항목과 상태 필드가 더 명확하다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: API 응답에는 `changeRate`를 두지 않고 `changeRatePercent`만 둔다. `changeRatePercent`는 최신 row의 `market_index_price.change_rate`에 100을 곱해 만든다.
  근거: FinanceDataReader의 `Change` 값은 비율 원값으로 저장된다. 프론트엔드가 별도 계산 없이 화면에 백분율 수치를 표시할 수 있게 하되, 필드명에 `Percent`를 포함해 단위를 명확히 한다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 전일 대비 값은 최신 거래일 row와 같은 지수의 저장된 직전 거래일 row의 종가 차이로 계산한다. 중간 거래일 누락 여부는 이번 API에서 검증하지 않는다.
  근거: 테이블에는 전일 대비 값이 없으므로 직전 row의 종가가 필요하다. 백엔드는 거래소 휴장일이나 누락일 캘린더를 갖고 있지 않으므로, 저장된 row 중 최신 row 바로 이전 row를 직전 기준으로 삼는다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: `AVAILABLE`은 응답 숫자 값이 모두 채워진 상태, `PARTIAL`은 최신 row는 있지만 일부 응답 값이 `null`인 상태, `EMPTY`는 해당 지수 row가 없는 상태로 정의한다.
  근거: 직전 row가 없으면 `changeValue`를 계산할 수 없고, 최신 row의 `change_rate`가 `null`이면 `changeRatePercent`를 만들 수 없다. 두 경우 모두 항목 자체는 존재하지만 API 계약의 일부 값이 비어 있으므로 `PARTIAL`로 통합한다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: 응답에서 `displayName`과 `volume`은 제외한다.
  근거: 표시명은 향후 다국어 처리를 고려해 프론트엔드가 `indexCode`를 기준으로 변환하는 편이 낫다. 거래량은 `market_index_price`에 저장되어 있지만 이슈 06의 범위인 최신 수치, 전일 대비 값, 등락률에는 포함되지 않는다.
  날짜/작성자: 2026-07-17 / Codex

- 결정: JDBC repository 구현체 이름은 `MarketIndexPriceRepositoryImpl`로 한다.
  근거: `docs/architecture/backend.md`는 repository 구현체 이름을 `{Domain}RepositoryImpl` 형식으로 제시한다. 일반 JDBC는 Spring Data JPA처럼 인터페이스만으로 자동 구현되지 않으므로 구현 클래스는 직접 작성한다.
  날짜/작성자: 2026-07-17 / Codex

## 결과와 회고


아직 구현은 시작하지 않았다. 계획 작성 단계에서 확인한 핵심 위험은 HTTP Web 의존성이 아직 없다는 점과 전일 대비 값을 저장하는 컬럼이 없다는 점이다. 이 계획은 두 위험을 각각 `spring-boot-starter-web` 추가와 저장된 직전 거래일 종가 기반 `changeValue` 계산으로 해결하도록 정했다. 구현 전 계획 검토에서 등락률은 재계산하지 않고 최신 row의 `change_rate`를 백분율 값으로 변환해 `changeRatePercent`로 응답하기로 수정했다.

## 맥락과 방향 안내


저장소 루트는 `/Users/sehako/workspace/stock-report-backend`이다. 백엔드 애플리케이션은 `app/backend` 아래에 있고 Kotlin, Spring Boot, Gradle을 사용한다. 현재 실행 진입점은 `app/backend/src/main/kotlin/com/stockreport/StockReportBackendApplication.kt`의 `main` 함수다.

시장 데이터 테이블은 Flyway 마이그레이션 파일 `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`에서 만든다. 이 파일은 `market_index_price` 테이블을 생성하며, `index_code`는 `KOSPI` 또는 `KOSDAQ`만 허용한다. `trade_date`는 거래일, `close_price`는 종가, `change_rate`는 등락률이다. `index_code`와 `trade_date` 조합에는 유니크 제약이 있어 같은 지수의 같은 거래일 일봉이 중복 저장되지 않는다.

기존 자동 검증은 `app/backend/src/test/kotlin/com/stockreport/marketdata/MarketDataSchemaTest.kt`에 있다. 이 테스트는 Testcontainers PostgreSQL에 Flyway 마이그레이션을 적용해 테이블과 제약을 확인한다. Testcontainers는 테스트 중 실제 PostgreSQL 컨테이너를 띄우는 도구다. 이 계획의 새 테스트도 같은 방식을 사용하면 실제 PostgreSQL SQL 동작을 확인할 수 있다.

백엔드 아키텍처 문서 `docs/architecture/backend.md`는 도메인 중심 계층 구조를 요구한다. `presentation` 계층은 HTTP 요청과 응답을 처리한다. `application` 계층은 유스케이스와 비즈니스 흐름을 처리한다. `domain` 계층은 핵심 타입과 repository 인터페이스를 둔다. `infrastructure` 계층은 JDBC 같은 외부 기술로 domain repository 인터페이스를 구현한다.

## 작업 계획


먼저 `app/backend/build.gradle.kts`에 `spring-boot-starter-web`을 추가한다. 이 의존성은 Spring Boot에서 HTTP controller를 실행하고 JSON 응답을 만들기 위해 필요하다. 기존 JDBC, Flyway, PostgreSQL 의존성은 그대로 둔다.

그다음 `app/backend/src/main/kotlin/com/stockreport/marketindex` 아래에 지수 최신 수치 조회 도메인을 만든다. `domain/MarketIndexCode.kt`는 `KOSPI`, `KOSDAQ` 두 코드를 enum으로 표현한다. 화면 표시명은 API 응답에 포함하지 않고 프론트엔드가 `indexCode`를 기준으로 변환한다. `domain/MarketIndexPrice.kt`는 repository가 DB에서 읽은 일봉 한 건을 담는 내부 타입이다. 이 타입에는 `tradeDate`, `closePrice`, `storedChangeRate`가 들어가며, 여기서 `storedChangeRate`는 DB의 `change_rate` 원값을 담는 내부 필드다. API 응답 필드명은 `changeRate`가 아니라 `changeRatePercent`다. `domain/MarketIndexSummary.kt`는 service가 계산한 최신 수치 결과를 담는 내부 타입이다. `domain/MarketIndexPriceRepository.kt`는 지수별 최신 일봉 최대 두 건을 읽는 인터페이스다.

`infrastructure/persistence/MarketIndexPriceRepositoryImpl.kt`는 `JdbcTemplate`을 사용해 `market_index_price`를 조회한다. 지수 하나에 대해 `index_code`로 필터링하고 `trade_date DESC`로 정렬한 뒤 최대 두 행을 읽는다. 첫 번째 행은 최신 거래일이고 두 번째 행은 저장된 직전 거래일이다. 쿼리는 유니크 제약에서 만들어지는 `index_code, trade_date` 인덱스를 활용할 수 있다.

`application/MarketIndexService.kt`는 `KOSPI`, `KOSDAQ` 순서로 repository를 호출한다. row가 없으면 `EMPTY` 상태를 만든다. row가 하나만 있으면 최신 종가와 거래일은 반환하고, 최신 row의 `change_rate`가 있으면 `changeRatePercent`를 만든다. 이때 직전 row가 없어 `changeValue`는 `null`이므로 `PARTIAL` 상태를 만든다. row가 두 개 있으면 최신 종가에서 직전 종가를 빼 `changeValue`를 만든다. `changeRatePercent`는 직전 종가로 재계산하지 않고 최신 row의 `change_rate * 100`으로 만든다. 최신 row의 `change_rate`가 `null`이면 `changeRatePercent`는 `null`이다. `changeValue`와 `changeRatePercent`가 모두 값으로 채워진 경우에만 `AVAILABLE` 상태를 만든다. `BigDecimal` 계산은 소수점 네 자리로 반올림한다.

`application/response/MarketIndexSummaryResponse.kt`는 HTTP JSON으로 나갈 응답 타입이다. 최상위 응답은 배열 대신 객체를 사용해 이후 메타데이터를 추가하기 쉽게 한다. 구체적인 JSON 모양은 다음과 같다.

    {
      "items": [
        {
          "indexCode": "KOSPI",
          "status": "AVAILABLE",
          "tradeDate": "2026-07-16",
          "closePrice": 2705.4000,
          "changeValue": 5.4000,
          "changeRatePercent": 1.2300
        },
        {
          "indexCode": "KOSDAQ",
          "status": "EMPTY",
          "tradeDate": null,
          "closePrice": null,
          "changeValue": null,
          "changeRatePercent": null
        }
      ]
    }

`status`는 문자열 enum으로 `AVAILABLE`, `PARTIAL`, `EMPTY`를 사용한다. `AVAILABLE`은 최신 row와 직전 row가 있고 최신 row의 `change_rate`도 있어 최신 종가, 전일 대비 값, 등락률 퍼센트를 모두 응답할 수 있는 상태다. `PARTIAL`은 최신 row는 있지만 `changeValue` 또는 `changeRatePercent` 중 일부가 `null`인 상태다. 대표적으로 직전 row가 없거나 최신 row의 `change_rate`가 `null`인 경우다. `EMPTY`는 해당 지수의 row가 하나도 없는 상태다.

`presentation/MarketIndexController.kt`는 `@RestController`로 만들고 `GET /api/market-indexes`를 처리한다. controller는 service를 호출해 응답 객체를 반환할 뿐 계산 로직을 갖지 않는다. 데이터가 전혀 없어도 요청 자체는 성공한 것이므로 HTTP 200을 반환한다. DB 연결 실패처럼 서버가 요청을 처리할 수 없는 예외는 Spring Boot 기본 예외 처리로 HTTP 500이 되게 두고, 이 이슈에서 별도 전역 예외 응답 형식은 만들지 않는다. 아직 저장소에 공통 예외 응답 규칙이 없기 때문이다.

테스트는 구현보다 먼저 기대 동작을 고정한다. `app/backend/src/test/kotlin/com/stockreport/marketindex/application/MarketIndexServiceTest.kt`는 fake repository를 사용해 데이터 있음, 한 건만 있음, 데이터 없음을 검증한다. `app/backend/src/test/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImplTest.kt`는 Testcontainers PostgreSQL과 Flyway를 사용해 최신 두 거래일을 올바른 순서로 읽는지 검증한다. `app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt`는 가능하면 `@SpringBootTest(webEnvironment = RANDOM_PORT)` 또는 `@AutoConfigureMockMvc`로 실제 HTTP `GET /api/market-indexes`가 JSON을 반환하는지 확인한다. Spring Boot Web 의존성이 추가된 뒤 MockMvc를 쓰려면 `spring-boot-starter-test`에 포함된 테스트 도구를 사용한다.

## 마일스톤


첫 번째 마일스톤은 HTTP 실행 기반과 API 계약을 고정하는 것이다. 이 마일스톤이 끝나면 `spring-boot-starter-web` 의존성이 추가되고, `MarketIndexController`가 반환할 응답 타입 이름과 JSON 필드가 코드에 존재한다. 이 단계의 검증은 `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`를 실행했을 때 기존 스키마 테스트가 계속 통과하고, 새 controller 테스트가 아직 구현 전이라면 실패하는 것이다. 실패는 구현해야 할 동작이 테스트로 표현되었다는 증거다.

두 번째 마일스톤은 service 계산 로직과 repository 조회 로직을 구현하는 것이다. 이 마일스톤이 끝나면 service는 저장된 최신 두 거래일 데이터와 최신 row의 `change_rate`로 `AVAILABLE` 응답을 만들고, 최신 row는 있지만 `changeValue` 또는 `changeRatePercent`가 비면 `PARTIAL`, 한 건도 없으면 `EMPTY`를 만든다. repository는 `market_index_price`에서 지수별 최신 두 row를 읽는다. 검증은 service 테스트와 JDBC repository 테스트를 실행해 계산과 SQL 조회가 모두 통과하는 것이다.

세 번째 마일스톤은 HTTP endpoint를 실제로 통합 검증하는 것이다. 이 마일스톤이 끝나면 테스트 데이터가 들어간 PostgreSQL 테스트 DB를 기준으로 `GET /api/market-indexes`가 HTTP 200과 JSON 객체를 반환한다. 사용자는 서버를 실행한 뒤 같은 경로를 호출해 코스피와 코스닥 두 항목을 볼 수 있다. 이 단계에서 전체 백엔드 테스트가 통과해야 한다.

네 번째 마일스톤은 계획과 결과를 정리하는 것이다. 이 마일스톤이 끝나면 이 문서의 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고`가 실제 구현과 검증 결과에 맞게 갱신되어 있어야 한다. 이슈 범위를 넘어선 차트 API, 종목 API, Python 배치 구현은 여전히 제외되어야 한다.

## 구체적인 단계


작업 디렉터리는 저장소 루트 `/Users/sehako/workspace/stock-report-backend`이다. 백엔드 명령은 `app/backend`에서 실행한다.

1. 현재 상태를 확인한다.

    git status --short
    find app/backend/src/main/kotlin app/backend/src/test/kotlin -type f | sort

   성공 기준은 작업 전에 사용자가 만든 변경이 있는지 확인하고, 기존 백엔드 파일이 `StockReportBackendApplication.kt`와 `MarketDataSchemaTest.kt` 중심임을 파악하는 것이다.

2. `app/backend/build.gradle.kts`에 Web 의존성을 추가한다.

    implementation("org.springframework.boot:spring-boot-starter-web")

   이 줄은 기존 `implementation("org.springframework.boot:spring-boot-starter-jdbc")` 근처에 둔다. 새 의존성은 HTTP controller와 JSON 응답 직렬화를 위해 필요하다.

3. 실패하는 service 테스트를 먼저 작성한다.

   새 파일은 `app/backend/src/test/kotlin/com/stockreport/marketindex/application/MarketIndexServiceTest.kt`이다. 테스트 클래스와 테스트 메서드에는 `@DisplayName`을 붙이고, 테스트 메서드 이름은 한글로 작성한다. 최소 시나리오는 다음 세 가지다.

   - `KOSPI`와 `KOSDAQ` 모두 최신 두 거래일 데이터가 있고 최신 row의 `change_rate`가 있으면 두 항목 모두 `AVAILABLE`이고 전일 대비 값과 등락률 퍼센트를 만든다.
   - 최신 row가 하나만 있으면 `PARTIAL`이고 `changeValue`가 `null`이며, 최신 row의 `change_rate`가 있으면 `changeRatePercent`는 값이 있다.
   - 최신 row와 직전 row가 모두 있어도 최신 row의 `change_rate`가 `null`이면 `PARTIAL`이고 `changeRatePercent`가 `null`이다.
   - row가 없으면 `EMPTY`이고 날짜와 숫자 필드가 모두 `null`이다.

4. domain과 application 타입을 추가해 service 테스트를 통과시킨다.

   새 파일은 다음과 같다.

   - `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexCode.kt`
   - `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPrice.kt`
   - `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexSummary.kt`
   - `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPriceRepository.kt`
   - `app/backend/src/main/kotlin/com/stockreport/marketindex/application/MarketIndexService.kt`
   - `app/backend/src/main/kotlin/com/stockreport/marketindex/application/response/MarketIndexSummaryResponse.kt`

   `MarketIndexPriceRepository`는 `fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice>` 형태로 만든다. 반환 리스트는 최신 거래일이 먼저 오도록 repository 구현이 보장한다.

5. JDBC repository 테스트를 작성한다.

   새 파일은 `app/backend/src/test/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImplTest.kt`이다. Testcontainers PostgreSQL에 Flyway 마이그레이션을 적용하고, `market_index_price`에 같은 지수의 여러 거래일 데이터를 insert한 뒤 repository가 최신 두 건만 최신순으로 반환하는지 확인한다. 다른 지수의 데이터가 섞여 있어도 요청한 지수만 반환되어야 한다. 조회 결과에는 `close_price`와 `change_rate`가 모두 매핑되어야 한다.

6. JDBC repository 구현을 추가한다.

   새 파일은 `app/backend/src/main/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImpl.kt`이다. SQL은 다음 의도를 가져야 한다.

    SELECT index_code, trade_date, close_price, change_rate
    FROM market_index_price
    WHERE index_code = ?
    ORDER BY trade_date DESC
    LIMIT 2

   실제 Kotlin 코드에서는 `JdbcTemplate`을 사용한다. 이 저장소에는 아직 JDBC repository 패턴이 없으므로, 한 개 파라미터 조회에는 `JdbcTemplate`을 사용해 단순하게 시작한다. `close_price`와 `change_rate`는 `BigDecimal`, `trade_date`는 `LocalDate`로 매핑한다.

7. controller 테스트를 작성한다.

   새 파일은 `app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt`이다. 테스트는 HTTP `GET /api/market-indexes`가 200을 반환하고, JSON에 `items[0].indexCode = "KOSPI"`와 `items[1].indexCode = "KOSDAQ"`가 포함되는지 확인한다. 데이터가 없는 지수는 `status = "EMPTY"`로 응답해야 한다. 테스트 방식은 `@SpringBootTest`와 `@AutoConfigureMockMvc`를 사용한다.

8. controller를 구현한다.

   새 파일은 `app/backend/src/main/kotlin/com/stockreport/marketindex/presentation/MarketIndexController.kt`이다. `@GetMapping("/api/market-indexes")` 메서드는 `MarketIndexService`를 호출하고 `MarketIndexSummariesResponse`를 반환한다. controller에는 계산이나 SQL을 넣지 않는다.

9. 전체 테스트를 실행한다.

    cd app/backend
    GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test

   성공 기준은 Gradle이 `BUILD SUCCESSFUL`을 출력하고 기존 `MarketDataSchemaTest`와 새 `marketindex` 테스트가 모두 통과하는 것이다.

10. 수동 실행이 필요한 경우 서버를 실행하고 endpoint를 호출한다.

    cd app/backend
    SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/stock_report SPRING_DATASOURCE_USERNAME=stock_report SPRING_DATASOURCE_PASSWORD=stock_report GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon bootRun

   다른 터미널에서 다음을 실행한다.

    curl -s http://localhost:8080/api/market-indexes

   로컬 PostgreSQL에 지수 데이터가 없다면 `items` 안의 두 항목이 `EMPTY`로 나온다. 데이터가 있다면 해당 지수는 `AVAILABLE` 또는 `PARTIAL`로 나온다. 이 수동 검증은 로컬 DB 준비가 필요하므로 자동 테스트를 필수 검증으로 삼고, 수동 검증은 가능한 환경에서만 수행한다.

## 검증과 수락 기준


수락 기준은 사람이 관찰할 수 있는 동작으로 판단한다.

- 사용자가 백엔드 서버를 실행하고 `GET /api/market-indexes`를 호출하면 HTTP 200을 받는다.
- 응답 JSON은 최상위 `items` 필드를 가지며, 그 안에 `KOSPI`, `KOSDAQ` 두 항목이 이 순서로 들어 있다.
- 저장된 최신 두 거래일 데이터가 있고 최신 row의 `change_rate`가 있는 지수 항목은 `status: "AVAILABLE"`, 최신 `tradeDate`, 최신 `closePrice`, 계산된 `changeValue`, 계산된 `changeRatePercent`를 포함한다.
- 저장된 최신 row는 있지만 직전 row가 없는 지수 항목은 `status: "PARTIAL"`이고 `tradeDate`와 `closePrice`는 값이 있으며 `changeValue`는 `null`이다. 최신 row의 `change_rate`가 있으면 `changeRatePercent`는 값이 있다.
- 저장된 최신 row는 있지만 최신 row의 `change_rate`가 `null`이면 `status: "PARTIAL"`이고 `changeRatePercent`는 `null`이다.
- 저장된 row가 없는 지수 항목은 `status: "EMPTY"`이고 `tradeDate`, `closePrice`, `changeValue`, `changeRatePercent`가 모두 `null`이다.
- `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test`를 실행하면 `BUILD SUCCESSFUL`이 출력된다.
- 기존 스키마 검증 테스트가 계속 통과해 DB 마이그레이션 동작이 깨지지 않았음을 확인할 수 있다.

## 멱등성과 복구


이 구현은 기존 DB 스키마를 바꾸지 않고 읽기 전용 API를 추가한다. 마이그레이션 파일을 새로 만들 필요가 없으므로 데이터 삭제나 스키마 파괴 작업은 없다. 테스트는 Testcontainers PostgreSQL을 사용해 매번 새 테스트 DB에 Flyway 마이그레이션을 적용하므로 여러 번 실행해도 로컬 개발 DB 데이터에 영향을 주지 않는다.

의존성 추가 후 Gradle 다운로드나 테스트가 실패하면 네트워크 또는 Docker 환경 문제인지 먼저 확인한다. Docker 또는 Orbstack이 실행 중이 아니면 Testcontainers 테스트가 실패할 수 있다. 이 경우 Docker 환경을 시작한 뒤 같은 테스트 명령을 다시 실행한다. 구현 중 파일을 잘못 수정했다면 `git diff`로 변경 내용을 확인하고, 사용자가 만든 변경이 아닌 본인이 방금 만든 변경만 되돌린다. `git reset --hard`나 강제 삭제는 사용자의 명시적 지시 없이 사용하지 않는다.

DB 연결 실패가 HTTP 호출 중 발생하면 이번 이슈에서는 별도 오류 응답 형식을 만들지 않는다. Spring Boot 기본 처리로 HTTP 500이 발생할 수 있다. 공통 오류 응답 형식이 필요해지면 별도 이슈로 분리한다.

## 산출물과 메모


계획 작성 시점의 관련 파일 상태는 다음과 같다.

    app/backend/src/main/kotlin/com/stockreport/StockReportBackendApplication.kt
    app/backend/src/main/resources/application.yml
    app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql
    app/backend/src/test/kotlin/com/stockreport/marketdata/MarketDataSchemaTest.kt

`market_index_price` 테이블 정의의 핵심 부분은 다음과 같다.

    CREATE TABLE market_index_price (
        id BIGSERIAL PRIMARY KEY,
        index_code VARCHAR(20) NOT NULL,
        trade_date DATE NOT NULL,
        open_price NUMERIC(19, 4) NOT NULL,
        high_price NUMERIC(19, 4) NOT NULL,
        low_price NUMERIC(19, 4) NOT NULL,
        close_price NUMERIC(19, 4) NOT NULL,
        volume BIGINT NOT NULL,
        change_rate NUMERIC(10, 4),
        CONSTRAINT uk_market_index_price_index_trade_date UNIQUE (index_code, trade_date),
        CONSTRAINT chk_market_index_price_index_code CHECK (index_code IN ('KOSPI', 'KOSDAQ'))
    );

예상 성공 테스트 출력은 다음과 같은 형태다. 실제 테스트 개수는 구현된 테스트 수에 따라 달라질 수 있다.

    > Task :test
    BUILD SUCCESSFUL

## 인터페이스와 의존성


새 의존성은 `app/backend/build.gradle.kts`의 `dependencies` 블록에 추가하는 `implementation("org.springframework.boot:spring-boot-starter-web")` 하나다.

새 endpoint는 `GET /api/market-indexes`이다. 요청 body와 query parameter는 없다. 성공 응답의 Kotlin 타입은 `MarketIndexSummariesResponse`로 만들고, 내부 항목 타입은 `MarketIndexSummaryResponse`로 만든다. JSON 필드는 `items`, `indexCode`, `status`, `tradeDate`, `closePrice`, `changeValue`, `changeRatePercent`를 사용한다. `displayName`, `changeRate`, `volume`은 응답에 포함하지 않는다.

새 domain 타입은 `MarketIndexCode`, `MarketIndexPrice`, `MarketIndexSummary`, `MarketIndexSummaryStatus`, `MarketIndexPriceRepository`이다. `MarketIndexSummaryStatus` 값은 `AVAILABLE`, `PARTIAL`, `EMPTY`이다.

새 application 서비스는 `com.stockreport.marketindex.application.MarketIndexService`이다. public 메서드는 `fun getSummaries(): MarketIndexSummariesResponse`로 만든다. service는 domain repository 인터페이스에만 의존하고, JDBC 구현체에는 직접 의존하지 않는다.

새 infrastructure 구현체는 `com.stockreport.marketindex.infrastructure.persistence.MarketIndexPriceRepositoryImpl`이다. 이 클래스는 Spring bean으로 등록되어 `MarketIndexPriceRepository`를 구현한다. SQL은 `market_index_price`에서 특정 `index_code`의 최신 두 row만 읽는다.

새 presentation controller는 `com.stockreport.marketindex.presentation.MarketIndexController`이다. 이 클래스는 `MarketIndexService`에 의존하고, HTTP 요청을 service 호출로 연결한다.

계획 변경 메모:

- 2026-07-17 / Codex: 계획 초안 작성. 이유: `docs/issues/06-backend-market-index-summary-api.md`를 구현하기 전에 `PLANS.md` 기준의 자기완결적 실행 계획을 마련하기 위해서.
- 2026-07-17 / Codex: 구현 전 계획 검토 결과를 반영해 API 계약을 수정했다. 이유: `changeRate` 재계산, `displayName` 포함, repository 구현체 이름이 사용자 의도 및 아키텍처 지침과 맞지 않았기 때문이다.
