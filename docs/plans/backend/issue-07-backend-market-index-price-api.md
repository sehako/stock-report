# 지수 기간별 일봉 차트 API 구현

이 ExecPlan은 살아 있는 문서다. 작업이 진행되는 동안 `진행 상황`, `예상 밖의 발견`, `결정 기록`, `결과와 회고` 섹션을 최신 상태로 유지해야 한다.

이 문서는 저장소 루트의 `PLANS.md`를 따른다. 이 계획을 수정할 때는 `PLANS.md`의 요구사항과 지침을 함께 확인한다. 이 문서는 `docs/issues/07-backend-market-index-price-api.md`의 구현 계획이며, 저장소를 처음 보는 사람도 이 파일만 읽고 작업을 이어갈 수 있도록 필요한 맥락과 결정을 포함한다.

## 목적과 큰 그림

이 변경의 목적은 Spring Boot 백엔드가 저장된 코스피 또는 코스닥 지수 일봉 데이터를 기간별 차트 데이터로 조회할 수 있게 만드는 것이다. 구현 전에는 `market_index_price` 테이블에 코스피와 코스닥 일봉이 저장되어 있어도 외부 사용자가 특정 지수의 1개월, 3개월, 1년 범위 일봉 목록을 HTTP API로 가져올 방법이 없다.

구현 후 사용자는 백엔드 서버를 실행하고 `GET /api/market-indexes/KOSPI/prices?period=3M`처럼 요청해 지정 기간의 일봉 목록을 거래일 오름차순으로 받을 수 있다. 기간은 서버의 오늘 날짜가 아니라 해당 지수에 저장된 최신 거래일을 기준으로 계산한다. 예를 들어 `KOSPI`의 최신 저장 거래일이 `2026-07-22`이면 `period=3M`의 시작일은 `2026-04-22`이고, 응답에는 `startDate`와 `endDate`가 함께 들어간다. 여기서 "일봉"은 하루 단위의 시가, 고가, 저가, 종가, 거래량, 등락률 데이터를 뜻한다. "거래일 오름차순"은 오래된 거래일이 먼저 나오고 최신 거래일이 마지막에 나오는 순서다. "내부 지수 코드"는 이 서비스가 API와 데이터베이스에서 사용하는 문자열 코드이며, 이번 이슈에서는 `KOSPI`와 `KOSDAQ`만 허용한다.

## 진행 상황

- [x] (2026-07-23 00:00KST) `docs/issues/07-backend-market-index-price-api.md`, `docs/specs/2026-07-15-stock-market-data-service-design.md`, `docs/architecture/backend.md`, `PLANS.md`, `EXECPLAN_TEMPLATE.md`를 확인했다.
- [x] (2026-07-23 00:00KST) 기존 `marketindex` 도메인 코드, controller, service, repository, 응답 타입, 테스트를 조사했다.
- [x] (2026-07-23 00:00KST) 구현 방향을 기존 `MarketIndexController`, `MarketIndexService`, `MarketIndexPriceRepository` 확장으로 정했다.
- [x] (2026-07-23 00:00KST) 구현 전 계획 초안을 작성했다.
- [x] (2026-07-23 00:00KST) 계획 자체 검토에서 응답 형태와 날짜 기준 주입 방식을 명확히 고정했다.
- [x] (2026-07-24 00:00KST) grill 검토 결과를 반영해 기간 기준을 서버 현재 날짜에서 저장된 최신 거래일로 변경하고, 응답 메타데이터와 repository 메서드 책임을 재정의했다.
- [x] (2026-07-24 00:00KST) 실패하는 테스트를 작성했다. `MarketIndexDailyPrice`, 기간 조회 repository 메서드, `MarketIndexService.getMarketIndexPrices`가 없어 `compileTestKotlin`이 실패하는 것을 확인했다.
- [x] (2026-07-24 00:00KST) 최소 구현을 완료했다. `MarketIndexDailyPrice`, `MarketIndexPricePeriod`, 기간별 응답 타입, service 유스케이스, JDBC 조회, controller endpoint를 추가했다.
- [x] (2026-07-24 00:00KST) 리팩터링을 완료했다. 기존 최신 수치 API 타입은 유지하고, 차트 일봉 타입을 분리해 기존 응답과 조회 흐름에 불필요한 변경이 없도록 정리했다.
- [x] (2026-07-24 00:00KST) 전체 테스트 및 빌드 검증을 완료했다. `app/backend`에서 `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test -q`가 통과했다.
- [x] (2026-07-24 00:00KST) 결과와 회고를 작성했다.

## 예상 밖의 발견

- 관찰: 기존 `MarketIndexPrice` 도메인 타입은 최신 수치 API에 필요한 `closePrice`와 `storedChangeRate`만 담고 있어 차트 API 응답에 필요한 시가, 고가, 저가, 거래량을 표현할 수 없다.
  증거: `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPrice.kt`의 필드는 `indexCode`, `tradeDate`, `closePrice`, `storedChangeRate`뿐이다.

- 관찰: 기존 repository 인터페이스는 최신 두 거래일 조회만 제공한다.
  증거: `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPriceRepository.kt`에는 `fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice>`만 있다.

- 관찰: 현재 controller에는 전역 예외 응답 규칙이나 공통 오류 DTO가 없다.
  증거: `app/backend/src/main/kotlin/com/stockreport/marketindex/presentation/MarketIndexController.kt`는 `GET /api/market-indexes`만 제공하고, 저장소 전체에서 별도 `ControllerAdvice` 또는 공통 오류 응답 타입이 발견되지 않았다.

- 관찰: 현재 `MarketIndexControllerTest`는 `@MockBean`으로 service를 mocking하지 않고, `@TestConfiguration`에서 실제 `MarketIndexService`와 fake repository를 주입한다.
  증거: `app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt`는 `@WebMvcTest(MarketIndexController::class)`와 `@Import(MarketIndexControllerTest.TestConfig::class)`를 사용한다.

- 관찰: `market_index_price.volume` 컬럼은 `BIGINT NOT NULL`이다.
  증거: `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`의 `market_index_price` 정의에 `volume BIGINT NOT NULL`이 있다.

## 결정 기록

- 결정: 이번 이슈는 기존 `com.stockreport.marketindex` 도메인 안에서 `MarketIndexController`, `MarketIndexService`, `MarketIndexPriceRepository`, `MarketIndexPriceRepositoryImpl`을 확장해 구현한다.
  근거: 이슈 06에서 이미 지수 최신 수치 API를 같은 도메인 구조로 구현했다. 동일한 리소스인 `/api/market-indexes` 아래에 차트 API를 추가하는 작업이므로 새 도메인이나 별도 controller를 만들 필요가 없다.
  검토한 대안: `MarketIndexPriceService`를 별도로 만들 수 있지만, 현재 유스케이스가 두 개뿐이고 repository도 같은 테이블을 읽으므로 클래스 분리가 실질 복잡도를 줄이지 않는다.
  날짜/작성자: 2026-07-23 / Codex

- 결정: `period`는 `1M`, `3M`, `1Y`만 허용하는 작은 enum 또는 값 객체로 파싱하고, 지원하지 않는 값이나 누락된 값은 HTTP 400으로 처리한다.
  근거: 이슈가 지원 기간을 명시하고 있으며, 문자열을 service 곳곳에서 직접 비교하면 잘못된 값 처리와 시작일 계산 규칙이 흩어진다. 작은 타입 하나로 허용값과 시작일 계산을 모으면 테스트하기 쉽다. `period`가 없으면 기간을 계산할 수 없으므로 클라이언트 요청 오류인 400으로 보는 것이 맞다.
  검토한 대안: controller에서 문자열을 직접 분기할 수 있지만, 이후 종목 차트 API에서도 같은 기간 규칙을 사용할 가능성이 있어 중복이 생길 수 있다.
  날짜/작성자: 2026-07-23 / Codex

- 결정: `indexCode`는 `MarketIndexCode`의 명시 파싱 메서드로 변환하고, `KOSPI` 또는 `KOSDAQ`이 아니면 HTTP 404로 처리한다.
  근거: `MarketIndexCode.valueOf`를 그대로 쓰면 잘못된 값에서 `IllegalArgumentException`이 발생하고 Spring 기본 오류로 흘러갈 수 있다. 존재하지 않는 지수 코드는 이슈 요구사항대로 404여야 하므로 명시적인 예외 변환이 필요하다.
  검토한 대안: DB 조회 결과가 없으면 404로 볼 수도 있지만, `KOSPI`에 데이터가 아직 없는 경우는 빈 목록이어야 하므로 지수 코드 유효성과 데이터 존재 여부를 분리해야 한다.
  날짜/작성자: 2026-07-23 / Codex

- 결정: 차트 응답은 최상위 객체에 `indexCode`, `period`, `startDate`, `endDate`, `items`를 포함하고, 각 항목은 `tradeDate`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `changeRatePercent`를 포함한다. 항목에는 `indexCode`를 반복하지 않는다.
  근거: 기존 최신 수치 API가 최상위 `items` 객체 구조를 사용한다. 차트도 같은 스타일을 유지하면 프론트엔드가 API 응답을 일관되게 다룰 수 있다. 기간 기준을 저장된 최신 거래일로 삼으면 프론트엔드가 실제 계산 범위를 알아야 하므로 `startDate`와 `endDate`가 필요하다. 한 응답은 단일 지수에 대한 목록이므로 항목마다 `indexCode`를 반복할 필요는 없다. `changeRatePercent`는 설계 문서에서 DB의 `change_rate` 원값에 100을 곱해 API에 반환한다고 정의되어 있다.
  검토한 대안: 배열 자체를 최상위 응답으로 반환할 수 있지만, 이후 기간 메타데이터나 지수 코드를 추가하기 어렵다.
  날짜/작성자: 2026-07-23 / Codex

- 결정: 기간 시작일은 서버 현재 날짜가 아니라 해당 지수의 저장된 최신 거래일을 기준으로 계산한다. `1M`, `3M`, `1Y`는 최신 저장 거래일에서 각각 `minusMonths(1)`, `minusMonths(3)`, `minusYears(1)`을 적용한다.
  근거: 이 서비스는 장 마감 후 저장된 일봉을 조회한다. 서버 날짜를 기준으로 삼으면 휴장일, 배치 지연, 배치 실패 상황에서 사용자가 기대하는 "저장된 데이터 기준 최근 기간"과 응답 범위가 어긋날 수 있다. 저장된 최신 거래일을 기준으로 삼으면 응답의 `endDate`와 실제 최신 item이 같은 의미를 갖는다.
  검토한 대안: `Clock`을 주입해 서버 현재 날짜를 고정할 수 있지만, 데이터 적재 상태와 관계없는 날짜 기준이므로 차트 API 의미에 덜 맞다. 이 결정으로 `Clock` bean과 service 생성자 주입은 추가하지 않는다.
  날짜/작성자: 2026-07-24 / Codex

- 결정: 유효한 지수 코드지만 저장된 row가 하나도 없으면 HTTP 200과 `startDate: null`, `endDate: null`, `items: []`를 반환한다.
  근거: 이슈는 데이터가 없는 경우 빈 목록을 요구한다. `KOSPI` 또는 `KOSDAQ`이라는 지수 자체는 유효하므로 row 부재를 404로 처리하면 존재하지 않는 지수 코드와 구분할 수 없다.
  검토한 대안: 최신 거래일이 없으므로 404 또는 204로 처리할 수도 있지만, 목록 조회 API에서는 빈 목록이 가장 일관적이다.
  날짜/작성자: 2026-07-24 / Codex

- 결정: repository에는 최신 저장 거래일 조회 메서드와 기간 범위 조회 메서드를 분리해서 추가한다. 정상 요청에서 service는 repository를 두 번 호출한다.
  근거: 기간 계산은 domain/application 규칙이고 repository는 DB 조회 책임만 가져야 한다. SQL 한 번으로 최신 거래일과 기간 조회를 처리하면 `period=1M|3M|1Y` 의미나 월/년 계산 규칙이 SQL에 들어가 책임 경계가 흐려진다. 지수는 `KOSPI`, `KOSDAQ` 두 개뿐이고 조회량도 일봉 차트 범위라서 DB 호출 1회를 줄이는 이득보다 명확성이 중요하다.
  검토한 대안: subquery와 interval을 사용해 SQL 한 번으로 처리할 수 있지만, Kotlin `LocalDate.minusMonths`와 PostgreSQL interval의 월말 처리 차이까지 검증해야 해 불필요하게 복잡하다.
  날짜/작성자: 2026-07-24 / Codex

- 결정: 가격 필드와 `changeRatePercent`는 기존 최신 수치 API와 동일하게 소수점 네 자리 `RoundingMode.HALF_UP`으로 정규화하고, `volume`은 `Long`으로 반환한다.
  근거: 기존 `MarketIndexService`는 `closePrice`, `changeValue`, `changeRatePercent`에 `setScale(4, RoundingMode.HALF_UP)`을 적용한다. 차트 응답도 같은 API 숫자 규칙을 따라야 한다. DB의 `volume`은 `BIGINT NOT NULL`이므로 Kotlin `Long`이 맞다.
  검토한 대안: DB에서 받은 scale을 그대로 반환하거나 `volume`을 `Int`로 둘 수 있지만, 응답 일관성과 오버플로 안전성 면에서 부적절하다.
  날짜/작성자: 2026-07-24 / Codex

- 결정: 이번 이슈에서는 오류 응답 JSON body를 고정하지 않고 HTTP 상태 코드만 고정한다.
  근거: 저장소에 공통 오류 DTO나 전역 `ControllerAdvice`가 없다. 이 API만 독자적인 오류 body를 만들면 이후 공통 오류 정책 도입 때 다시 바꿀 가능성이 높다.
  검토한 대안: `ErrorResponse` 같은 새 공통 응답을 만들 수 있지만, 이번 이슈 범위를 벗어난다.
  날짜/작성자: 2026-07-24 / Codex

## 결과와 회고

구현을 완료했다. `GET /api/market-indexes/{indexCode}/prices?period=1M|3M|1Y` endpoint가 추가되었고, 응답은 저장된 최신 거래일을 `endDate`로 삼아 기간 시작일을 계산한 뒤 해당 범위의 일봉을 거래일 오름차순으로 반환한다. 유효한 지수지만 저장된 row가 없으면 `startDate: null`, `endDate: null`, `items: []`를 반환하고, 존재하지 않는 지수 코드는 404, 지원하지 않는 기간이나 누락된 `period`는 400으로 처리한다.

변경 파일은 `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexDailyPrice.kt`, `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPricePeriod.kt`, `app/backend/src/main/kotlin/com/stockreport/marketindex/application/response/MarketIndexPriceResponse.kt`, 기존 `MarketIndexCode`, `MarketIndexPriceRepository`, `MarketIndexService`, `MarketIndexPriceRepositoryImpl`, `MarketIndexController`, 그리고 관련 테스트 파일이다. 계획과 달라진 기능 방향은 없었다. 기존 최신 수치 API의 `MarketIndexPrice` 타입은 그대로 두고 차트 API용 `MarketIndexDailyPrice`를 별도로 추가해 기존 조회 흐름의 변경 범위를 줄였다.

검증은 `app/backend`에서 수행했다. 먼저 실패 테스트 작성 후 `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test --tests com.stockreport.marketindex.application.MarketIndexServiceTest --tests com.stockreport.marketindex.presentation.MarketIndexControllerTest -q`를 실행했고, 새 production 타입과 메서드가 없어 `compileTestKotlin`이 실패하는 RED를 확인했다. 구현 후 같은 명령이 통과했고, `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test --tests com.stockreport.marketindex.infrastructure.persistence.MarketIndexPriceRepositoryImplTest -q`도 통과했다. 마지막으로 `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test -q` 전체 백엔드 테스트가 통과했다. 테스트 실행 중 JVM class data sharing 관련 경고가 한 줄 출력되었지만 테스트 실패나 빌드 실패는 없었다.

## 맥락과 방향 안내

저장소 루트는 `/Users/sehako/workspace/stock-report-feature-07-backend-market-index-price-api`이다. 백엔드 애플리케이션은 `app/backend` 아래에 있고 Kotlin, Spring Boot, Gradle을 사용한다. 실행 진입점은 `app/backend/src/main/kotlin/com/stockreport/StockReportBackendApplication.kt`이다.

백엔드 패키지는 `docs/architecture/backend.md`의 도메인 중심 구조를 따른다. `presentation` 계층은 HTTP 요청과 응답을 처리한다. `application` 계층은 유스케이스와 비즈니스 흐름을 처리한다. `domain` 계층은 핵심 타입과 repository 인터페이스를 둔다. `infrastructure` 계층은 JDBC 같은 외부 기술로 domain repository 인터페이스를 구현한다. 의존성 방향은 `presentation -> application -> domain`과 `infrastructure -> domain`이다. application 계층은 JDBC 구현체가 아니라 domain repository 인터페이스에 의존해야 한다.

시장 지수 일봉은 `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`의 `market_index_price` 테이블에 저장된다. 이 테이블은 `index_code`, `trade_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `change_rate`를 가진다. `index_code`는 `KOSPI` 또는 `KOSDAQ`만 저장할 수 있고, `index_code`와 `trade_date` 조합은 유니크 제약으로 중복 저장을 막는다. `change_rate`는 FinanceDataReader의 `Change` 원값이며, API에서는 100을 곱한 `changeRatePercent`로 반환한다. `change_rate` 컬럼은 `NULL`을 허용하므로 응답에서도 `changeRatePercent`는 `null`일 수 있다.

이미 구현된 지수 최신 수치 API는 `GET /api/market-indexes`이다. `app/backend/src/main/kotlin/com/stockreport/marketindex/presentation/MarketIndexController.kt`가 HTTP 요청을 받고, `app/backend/src/main/kotlin/com/stockreport/marketindex/application/MarketIndexService.kt`가 유스케이스를 처리하며, `app/backend/src/main/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImpl.kt`가 `JdbcTemplate`으로 `market_index_price`를 조회한다. 기존 repository 메서드 `findLatestTwoByIndexCode`는 최신 수치 계산을 위해 특정 지수의 최신 두 거래일만 최신순으로 읽는다.

기존 테스트는 같은 구조를 따른다. `app/backend/src/test/kotlin/com/stockreport/marketindex/application/MarketIndexServiceTest.kt`는 fake repository로 service 계산을 검증한다. `app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt`는 `@WebMvcTest`와 `MockMvc`로 HTTP 응답을 검증한다. `app/backend/src/test/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImplTest.kt`는 Testcontainers PostgreSQL과 Flyway로 실제 SQL 조회를 검증한다. Testcontainers는 테스트 중 PostgreSQL 컨테이너를 띄우는 도구라서 Docker 또는 호환 런타임이 실행 중이어야 한다.

## 작업 계획

먼저 테스트로 API 계약과 오류 조건을 고정한다. service 테스트에는 `KOSPI`와 `period=3M` 요청에서 저장된 최신 거래일을 `endDate`로 삼고, 그 3개월 전을 `startDate`로 계산한 뒤 해당 범위의 일봉이 거래일 오름차순으로 반환되는 시나리오를 추가한다. 또한 데이터가 없는 유효 지수는 `startDate: null`, `endDate: null`, 빈 `items`를 반환하는지, `change_rate`가 `null`이면 `changeRatePercent`가 `null`인지 확인한다. controller 테스트에는 `GET /api/market-indexes/KOSPI/prices?period=3M`의 HTTP 200 응답과 `startDate`, `endDate`, `items` JSON 구조를 검증한다. 존재하지 않는 지수 코드의 404 응답, 지원하지 않는 기간 값의 400 응답, `period` 누락의 400 응답도 상태 코드로 검증한다. repository 테스트에는 최신 거래일 조회와 시작일/종료일 범위 조회를 각각 검증한다.

그다음 domain 타입을 확장한다. `MarketIndexCode`에는 문자열을 받아 정확히 `KOSPI` 또는 `KOSDAQ`이면 enum을 반환하고, 아니면 `null`을 반환하는 명시 파싱 함수를 추가한다. 소문자 `kospi`, 대소문자 혼합 값, 외부 심볼 `KS11`, `KQ11`은 허용하지 않는다. `period` 값은 `MarketIndexPricePeriod` 같은 새 enum 또는 값 객체로 만든다. Kotlin enum 상수명은 숫자로 시작할 수 없으므로 `ONE_MONTH("1M")`, `THREE_MONTHS("3M")`, `ONE_YEAR("1Y")`처럼 API 문자열 값을 별도 프로퍼티로 둔다. 파싱과 응답은 enum `name`이 아니라 API 문자열 값인 `1M`, `3M`, `1Y`를 사용한다. 이 타입은 기준일에서 각각 1개월 전, 3개월 전, 1년 전 날짜를 계산한다. "기준일"은 repository에서 조회한 해당 지수의 최신 저장 거래일이다. `LocalDate.minusMonths`와 `minusYears`의 기본 동작을 그대로 사용하고, 별도 월초 또는 월말 보정 규칙은 만들지 않는다. `Clock` 주입이나 `Clock` bean은 추가하지 않는다.

차트 일봉 응답에는 기존 `MarketIndexPrice` 타입을 억지로 재사용하지 않는다. 기존 타입은 최신 수치 API에 필요한 일부 필드만 담고 있으므로, 이번 구현에서는 `MarketIndexDailyPrice` 같은 새 domain 타입을 추가하거나 `MarketIndexPrice`를 전체 OHLCV 필드까지 확장한다. 기존 최신 수치 API와 테스트의 영향이 작도록 새 타입을 추가하는 편이 더 보수적이다. 새 타입은 `indexCode`, `tradeDate`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `storedChangeRate`를 담는다.

repository 인터페이스에는 두 메서드를 추가한다. 첫 번째는 `findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate?`처럼 해당 지수의 최신 저장 거래일을 반환한다. 해당 지수 row가 없으면 `null`을 반환한다. 두 번째는 `findDailyPricesByIndexCodeAndTradeDateBetween(indexCode: MarketIndexCode, startDate: LocalDate, endDate: LocalDate): List<MarketIndexDailyPrice>`처럼 시작일과 종료일을 모두 받아 범위 일봉을 조회한다. JDBC 구현은 `market_index_price`에서 `index_code = ?`, `trade_date >= ?`, `trade_date <= ?`로 필터링하고 `ORDER BY trade_date ASC`로 정렬한다. 이슈가 데이터가 없는 경우 빈 목록을 요구하므로, 유효한 지수 코드지만 해당 기간에 row가 없으면 예외를 던지지 않고 빈 리스트를 반환한다.

service에는 `getMarketIndexPrices(indexCode: String, period: String)` 메서드를 추가한다. 기존 controller가 얇은 구조를 유지하고 있으므로, controller는 경로 변수와 query parameter 문자열을 service에 전달하고 service가 유효성 검사와 조회 흐름을 담당한다. 잘못된 지수 코드는 404를 나타내는 예외로 변환하고, 잘못된 기간은 400을 나타내는 예외로 변환한다. 저장소에 공통 오류 응답 규칙이 없으므로 이번 이슈에서는 `ResponseStatusException`을 사용해 상태 코드만 명확히 맞춘다. 오류 응답 body는 테스트나 문서에서 고정하지 않는다. service는 먼저 최신 저장 거래일을 조회한다. 최신 거래일이 없으면 repository 범위 조회를 호출하지 않고 `startDate = null`, `endDate = null`, `items = emptyList()` 응답을 반환한다. 최신 거래일이 있으면 이를 `endDate`로 두고 period로 `startDate`를 계산한 다음, `startDate`와 `endDate`를 모두 repository에 넘겨 일봉 목록을 조회한다.

마지막으로 controller에 `@GetMapping("/api/market-indexes/{indexCode}/prices")`를 추가한다. 응답 타입은 `MarketIndexPriceResponse` 항목과 `MarketIndexPricesResponse` 최상위 객체로 둔다. 최상위 객체는 `indexCode`, `period`, `startDate`, `endDate`, `items`를 반드시 포함한다. 이 중 이슈에서 직접 요구한 핵심은 `items`의 거래일 오름차순 일봉 목록이고, `startDate`와 `endDate`는 저장된 최신 거래일 기준 기간 계산 결과를 클라이언트가 확인하기 위한 메타데이터다. controller에는 날짜 계산, SQL, 금액 변환 로직을 넣지 않는다.

## 마일스톤

첫 번째 마일스톤은 API 계약과 실패 조건을 테스트로 고정하는 것이다. 이 마일스톤이 끝나면 `MarketIndexServiceTest`, `MarketIndexControllerTest`, `MarketIndexPriceRepositoryImplTest`에 새 차트 API 시나리오가 들어간다. 구현 전에는 새 타입이나 메서드가 없어 컴파일 또는 테스트가 실패할 수 있다. 이 실패는 구현해야 할 동작이 테스트에 표현되었다는 신호다.

두 번째 마일스톤은 domain과 application 계층을 확장하는 것이다. 이 마일스톤이 끝나면 `KOSPI`, `KOSDAQ`, `1M`, `3M`, `1Y` 파싱 규칙이 코드에 존재하고, service는 유효한 요청에 대해 최신 저장 거래일을 조회한 뒤 `startDate`와 `endDate`를 계산하고 repository 결과를 API 응답으로 변환한다. 데이터가 없는 경우 `startDate`와 `endDate`가 `null`인 빈 `items`를 반환하고, 잘못된 지수와 기간은 각각 404와 400으로 구분된다.

세 번째 마일스톤은 JDBC 조회와 HTTP endpoint를 연결하는 것이다. 이 마일스톤이 끝나면 `GET /api/market-indexes/{indexCode}/prices?period=...`가 실제 controller에서 동작한다. repository는 `market_index_price`에서 지정 지수와 기간 조건에 맞는 row를 거래일 오름차순으로 읽는다. MockMvc controller 테스트와 Testcontainers repository 테스트가 모두 통과해야 한다.

네 번째 마일스톤은 전체 검증과 계획 갱신이다. 이 마일스톤이 끝나면 `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test -q`가 통과하고, 실행 환경에 Docker가 없어 일부 Testcontainers 테스트를 실행하지 못했다면 그 사실과 대체 검증 결과를 `결과와 회고`에 기록한다. 구현 중 계획과 달라진 점은 `결정 기록` 또는 `예상 밖의 발견`에 남긴다.

## 구체적인 단계

작업 디렉터리는 저장소 루트 `/Users/sehako/workspace/stock-report-feature-07-backend-market-index-price-api`이다. 백엔드 명령은 `app/backend`에서 실행한다.

### [x] 1. API 계약을 테스트로 고정한다

`app/backend/src/test/kotlin/com/stockreport/marketindex/application/MarketIndexServiceTest.kt`에 기간별 일봉 조회 service 테스트를 추가한다. `KOSPI`와 `period=3M` 요청에서 fake repository의 최신 저장 거래일이 `2026-07-22`이면 `endDate`가 `2026-07-22`, `startDate`가 `2026-04-22`가 되고, 이 범위의 일봉 목록이 거래일 오름차순으로 응답되는지 확인한다. 테스트 데이터에는 `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `storedChangeRate`를 포함한다. `storedChangeRate`가 `0.0123`이면 응답의 `changeRatePercent`가 `1.2300`이 되는지도 확인한다. `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `changeRatePercent`는 소수점 네 자리 `RoundingMode.HALF_UP`으로 정규화하고, `volume`은 `Long` 그대로 응답하는지 확인한다. 유효한 지수 코드지만 저장된 row가 없으면 `startDate`, `endDate`가 `null`이고 `items`가 빈 리스트인지도 확인한다.

`app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt`에는 기존 방식처럼 `@WebMvcTest`에 실제 `MarketIndexService`와 fake repository를 주입하는 테스트를 유지한다. 첫째, `GET /api/market-indexes/KOSPI/prices?period=3M`이 HTTP 200과 JSON `indexCode`, `period`, `startDate`, `endDate`, `items` 배열을 반환하는지 확인한다. 둘째, 유효한 지수 코드지만 저장된 데이터가 없는 `GET /api/market-indexes/KOSDAQ/prices?period=3M`은 HTTP 200과 JSON `startDate: null`, `endDate: null`, `items: []`를 반환하는지 확인한다. 셋째, `GET /api/market-indexes/INVALID/prices?period=3M`은 HTTP 404를 반환한다. 넷째, `GET /api/market-indexes/KOSPI/prices?period=2Y`는 HTTP 400을 반환한다. 다섯째, `GET /api/market-indexes/KOSPI/prices`처럼 `period`가 누락되면 HTTP 400을 반환한다. 오류 응답 body는 검증하지 않는다.

`app/backend/src/test/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImplTest.kt`에는 최신 거래일 조회와 기간 조회 SQL 테스트를 추가한다. 최신 거래일 조회 테스트는 `KOSPI`와 `KOSDAQ` 데이터를 섞어 넣고 `findLatestTradeDateByIndexCode(KOSPI)`가 `KOSPI`의 최대 `trade_date`만 반환하는지, 해당 지수 row가 없으면 `null`을 반환하는지 확인한다. 기간 조회 테스트는 여러 거래일과 다른 지수의 데이터를 섞어 넣고, `KOSPI`, `startDate`, `endDate` 조건으로 조회했을 때 시작일 이전 row, 종료일 이후 row, `KOSDAQ` row가 제외되며 결과가 거래일 오름차순인지 확인한다. 이 테스트는 `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, nullable `storedChangeRate` 매핑도 확인한다.

검증 명령은 다음과 같다.

    cd app/backend
    GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test --tests com.stockreport.marketindex.application.MarketIndexServiceTest --tests com.stockreport.marketindex.presentation.MarketIndexControllerTest -q

이 단계의 완료 조건은 테스트가 새 요구사항을 표현하고, 구현 전에는 실패 이유가 명확하게 드러나는 것이다.

### [x] 2. domain과 response 타입을 추가한다

`app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexCode.kt`에 안전한 파싱 함수를 추가한다. 예시는 `fun from(value: String): MarketIndexCode?`이다. 입력은 이슈에 명시된 내부 코드만 지원하므로 소문자나 외부 심볼 `KS11`, `KQ11`은 허용하지 않는다.

새 파일 `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPricePeriod.kt`를 만든다. 이 타입은 `1M`, `3M`, `1Y` 문자열을 허용하고, 기준일을 받아 시작일을 계산한다. enum으로 만들 경우 상수명은 `ONE_MONTH`, `THREE_MONTHS`, `ONE_YEAR`처럼 Kotlin 문법에 맞게 짓고, 각 상수는 API 문자열 값 `1M`, `3M`, `1Y`를 별도 프로퍼티로 가진다. 응답의 `period`는 enum `name`이 아니라 이 API 문자열 값을 사용한다. 기준일이 `2026-07-22`이면 `1M`은 `2026-06-22`, `3M`은 `2026-04-22`, `1Y`는 `2025-07-22`을 시작일로 본다. `LocalDate.minusMonths`와 `minusYears` 기본 동작을 그대로 사용한다. 일봉 조회는 `trade_date >= startDate AND trade_date <= endDate` 조건을 사용한다.

새 domain 타입 `MarketIndexDailyPrice`를 만든다. 위치는 `app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexDailyPrice.kt`이다. 이 타입은 차트 응답에 필요한 전체 일봉 필드를 담고, DB의 `change_rate` 원값은 `storedChangeRate` 이름으로 둔다. `volume`은 DB 컬럼 타입이 `BIGINT`이므로 Kotlin `Long`으로 둔다.

새 response 파일은 기존 `application/response` 패키지에 둔다. 예시는 `app/backend/src/main/kotlin/com/stockreport/marketindex/application/response/MarketIndexPriceResponse.kt`이다. 최상위 타입은 `MarketIndexPricesResponse`, 항목 타입은 `MarketIndexPriceResponse`로 둔다. 최상위 필드는 `indexCode`, `period`, `startDate`, `endDate`, `items`를 사용한다. `startDate`와 `endDate`는 저장된 데이터가 없을 때 `null`이 될 수 있으므로 nullable `LocalDate?`로 둔다. 항목 필드는 `tradeDate`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `changeRatePercent`를 사용한다. 항목에는 `indexCode`를 반복하지 않는다.

이 단계의 완료 조건은 service와 controller가 사용할 타입이 존재하고, 기존 최신 수치 API 응답 타입과 이름 충돌이 나지 않는 것이다.

### [x] 3. service 유스케이스와 오류 처리를 구현한다

`app/backend/src/main/kotlin/com/stockreport/marketindex/application/MarketIndexService.kt`에 기간별 가격 조회 메서드를 추가한다. 메서드는 경로 변수 `indexCode`와 query parameter `period`를 받아 안전하게 파싱한다. `indexCode`가 `KOSPI` 또는 `KOSDAQ`이 아니면 `ResponseStatusException(HttpStatus.NOT_FOUND, ...)`을 던진다. `period`가 `1M`, `3M`, `1Y`가 아니면 `ResponseStatusException(HttpStatus.BAD_REQUEST, ...)`을 던진다.

service는 먼저 repository에서 해당 지수의 최신 저장 거래일을 조회한다. 최신 저장 거래일이 없으면 `startDate = null`, `endDate = null`, `items = emptyList()`인 응답을 반환한다. 최신 저장 거래일이 있으면 그 날짜를 `endDate`로 두고 period 타입으로 `startDate`를 계산한다. 그다음 `startDate`와 `endDate`를 모두 repository에 전달해 범위 일봉 목록을 조회하고, 반환된 일봉 목록을 response 타입으로 변환한다. `openPrice`, `highPrice`, `lowPrice`, `closePrice`는 기존 최신 수치 API와 동일하게 소수점 네 자리 `RoundingMode.HALF_UP`으로 정규화한다. `storedChangeRate`는 `100`을 곱하고 소수점 네 자리로 반올림해 `changeRatePercent`에 넣는다. `storedChangeRate`가 `null`이면 `changeRatePercent`도 `null`이다. repository가 빈 리스트를 반환하면 최상위 응답의 `items`는 빈 리스트다.

이 단계의 완료 조건은 service 테스트가 통과하고, 잘못된 지수와 잘못된 기간이 서로 다른 HTTP 상태로 변환될 수 있는 것이다.

### [x] 4. repository 기간 조회를 구현한다

`app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPriceRepository.kt`에 최신 거래일 조회 메서드와 기간 범위 조회 메서드를 추가한다. 기존 최신 두 거래일 조회 메서드는 최신 수치 API에서 계속 쓰이므로 제거하거나 의미를 바꾸지 않는다.

`app/backend/src/main/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImpl.kt`에 JDBC 조회를 추가한다. SQL의 의도는 다음과 같다.

    SELECT MAX(trade_date)
    FROM market_index_price
    WHERE index_code = ?

    SELECT index_code, trade_date, open_price, high_price, low_price, close_price, volume, change_rate
    FROM market_index_price
    WHERE index_code = ?
      AND trade_date >= ?
      AND trade_date <= ?
    ORDER BY trade_date ASC

이 쿼리는 기존 유니크 제약 `uk_market_index_price_index_trade_date`가 만드는 `(index_code, trade_date)` 인덱스를 활용할 수 있다. 별도 마이그레이션은 필요하지 않다.

검증 명령은 다음과 같다. 이 테스트는 Testcontainers를 사용하므로 Docker 또는 호환 컨테이너 런타임이 필요하다.

    cd app/backend
    GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test --tests com.stockreport.marketindex.infrastructure.persistence.MarketIndexPriceRepositoryImplTest -q

이 단계의 완료 조건은 repository 테스트가 최신 거래일 조회, 요청 지수 필터, 시작일 필터, 종료일 필터, 거래일 오름차순 정렬, OHLCV 매핑, nullable 등락률 매핑을 모두 확인하는 것이다.

### [x] 5. controller endpoint를 연결한다

`app/backend/src/main/kotlin/com/stockreport/marketindex/presentation/MarketIndexController.kt`에 `@GetMapping("/api/market-indexes/{indexCode}/prices")` 메서드를 추가한다. 메서드는 `@PathVariable indexCode: String`과 `@RequestParam period: String`을 받고 `MarketIndexService`의 기간별 가격 조회 메서드를 호출한다. controller에는 SQL, 날짜 계산, BigDecimal 변환을 넣지 않는다.

응답 예시는 다음과 같다.

    {
      "indexCode": "KOSPI",
      "period": "3M",
      "startDate": "2026-04-22",
      "endDate": "2026-07-22",
      "items": [
        {
          "tradeDate": "2026-04-22",
          "openPrice": 2680.0000,
          "highPrice": 2700.0000,
          "lowPrice": 2670.0000,
          "closePrice": 2690.0000,
          "volume": 500000000,
          "changeRatePercent": 0.1200
        }
      ]
    }

저장된 row가 하나도 없는 유효 지수의 응답 예시는 다음과 같다.

    {
      "indexCode": "KOSDAQ",
      "period": "3M",
      "startDate": null,
      "endDate": null,
      "items": []
    }

이 단계의 완료 조건은 MockMvc controller 테스트에서 정상 요청은 HTTP 200, 유효하지만 데이터가 없는 지수도 HTTP 200과 빈 `items`, 존재하지 않는 지수는 404, 지원하지 않는 기간과 누락된 기간은 400으로 관찰되는 것이다.

### [x] 6. 전체 검증과 ExecPlan 갱신을 수행한다

전체 백엔드 테스트를 실행한다.

    cd app/backend
    GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test -q

성공하면 `BUILD SUCCESSFUL`이 출력된다. Docker가 실행되지 않아 Testcontainers 테스트가 실패하면 Docker 또는 Orbstack 같은 컨테이너 런타임을 시작한 뒤 같은 명령을 다시 실행한다. 그래도 실행할 수 없다면 service와 controller 테스트처럼 Docker가 필요 없는 테스트를 별도로 실행하고, repository 통합 테스트를 실행하지 못한 이유를 `결과와 회고`에 기록한다.

이 단계의 완료 조건은 관련 테스트 결과와 남은 위험이 이 ExecPlan의 `결과와 회고`에 기록되고, 구현 단계 체크박스가 실제 상태와 맞게 갱신되는 것이다.

## 검증과 수락 기준

구현이 완료되면 사용자는 백엔드 서버를 실행한 뒤 `GET /api/market-indexes/KOSPI/prices?period=3M`를 호출할 수 있다. 저장된 `KOSPI` 일봉이 있으면 응답은 HTTP 200이고, `endDate`에는 저장된 최신 거래일이 들어간다. `startDate`에는 `endDate`에서 3개월을 뺀 날짜가 들어간다. `items`에는 `startDate <= tradeDate <= endDate` 범위의 일봉만 들어 있으며, `tradeDate`가 오래된 날짜부터 최신 날짜 순서로 정렬되어 있다.

유효한 지수 코드지만 저장된 row가 하나도 없으면 HTTP 200과 `startDate: null`, `endDate: null`, 빈 `items` 배열을 반환한다. 예를 들어 `KOSDAQ`에 row가 없으면 응답의 `items`는 `[]`이다. 이는 존재하지 않는 지수 코드와 다르다. 존재하지 않는 지수 코드인 `INVALID`는 HTTP 404로 처리한다. 지원하지 않는 기간 값인 `2Y`와 누락된 `period`는 HTTP 400으로 처리한다. 오류 응답 body는 이번 이슈에서 고정하지 않는다.

자동 검증 수락 기준은 다음과 같다. `cd app/backend && GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew test -q`를 실행하면 모든 백엔드 테스트가 통과해야 한다. 최소한 `MarketIndexServiceTest`는 저장된 최신 거래일 기준 기간 계산, `startDate`와 `endDate`, 응답 변환, 빈 데이터 응답을 검증하고, `MarketIndexControllerTest`는 HTTP 상태 코드와 JSON 구조를 검증하며, `MarketIndexPriceRepositoryImplTest`는 실제 PostgreSQL SQL 조회의 최신 거래일 조회, 필터, 정렬, 매핑을 검증해야 한다.

기존 최신 수치 API도 깨지면 안 된다. `GET /api/market-indexes` controller 테스트와 기존 service 테스트가 계속 통과해야 한다. 기존 `findLatestTwoByIndexCode` 메서드의 반환 순서는 최신 거래일이 먼저인 상태를 유지해야 한다.

## 멱등성과 복구

이번 구현은 읽기 전용 API를 추가하는 작업이다. 기존 DB 스키마를 바꾸지 않으므로 새 Flyway 마이그레이션이나 데이터 삭제 작업은 필요하지 않다. 테스트는 Testcontainers PostgreSQL에 Flyway 마이그레이션을 적용해 실행하므로 여러 번 실행해도 로컬 개발 DB 데이터를 변경하지 않는다.

작업 중 실패하면 먼저 `git diff`로 본인이 수정한 파일만 확인한다. 사용자가 만든 다른 변경은 되돌리지 않는다. Kotlin 컴파일 오류가 나면 새 response 타입 이름이 기존 `MarketIndexSummaryResponse`와 충돌하지 않는지, repository 인터페이스 구현체가 새 메서드를 모두 구현했는지 확인한다. controller 테스트의 HTTP 상태가 예상과 다르면 `ResponseStatusException`의 `HttpStatus`가 404와 400으로 정확히 매핑되는지 확인한다.

Testcontainers 테스트가 Docker 환경 문제로 실패할 수 있다. 이 경우 오류에는 대체로 Docker 환경을 찾을 수 없다는 메시지가 포함된다. Docker 또는 Orbstack을 시작한 뒤 같은 Gradle 명령을 다시 실행한다. 실행 환경에서 컨테이너 런타임을 사용할 수 없다면 repository 통합 테스트를 완료하지 못한 사실을 숨기지 말고 최종 결과에 기록한다.

## 위험 및 미결정 사항

특별히 구현 전에 사용자 결정이 필요한 미결정 사항은 없다. 계획은 이슈와 기존 설계 문서를 기준으로 `KOSPI`, `KOSDAQ`, `1M`, `3M`, `1Y`만 지원하도록 범위를 고정한다.

주요 위험은 날짜 기준과 테스트 안정성이다. `LocalDate.now()` 또는 `Clock`을 사용하면 테스트 실행일과 서버 날짜에 따라 시작일과 기대 결과가 바뀔 수 있다. 이 계획은 서버 시간이 아니라 저장된 최신 거래일을 기준으로 삼아 이를 완화한다. 또 다른 위험은 기존 최신 수치 API의 `MarketIndexPrice` 타입을 전체 일봉 타입으로 확장하면서 기존 테스트가 불필요하게 흔들리는 것이다. 이 계획은 새 `MarketIndexDailyPrice` 타입을 추가해 기존 최신 수치 API의 조회 모델을 유지한다.

## 산출물과 메모

계획 작성 시점에 조사한 핵심 파일은 다음과 같다.

    docs/issues/07-backend-market-index-price-api.md
    docs/specs/2026-07-15-stock-market-data-service-design.md
    docs/architecture/backend.md
    app/backend/src/main/kotlin/com/stockreport/marketindex/presentation/MarketIndexController.kt
    app/backend/src/main/kotlin/com/stockreport/marketindex/application/MarketIndexService.kt
    app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexCode.kt
    app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPrice.kt
    app/backend/src/main/kotlin/com/stockreport/marketindex/domain/MarketIndexPriceRepository.kt
    app/backend/src/main/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImpl.kt
    app/backend/src/test/kotlin/com/stockreport/marketindex/application/MarketIndexServiceTest.kt
    app/backend/src/test/kotlin/com/stockreport/marketindex/presentation/MarketIndexControllerTest.kt
    app/backend/src/test/kotlin/com/stockreport/marketindex/infrastructure/persistence/MarketIndexPriceRepositoryImplTest.kt
    app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql

`market_index_price` 테이블 정의의 핵심은 다음과 같다.

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

예상 성공 테스트 출력은 다음과 같은 형태다. 실제 테스트 수는 구현된 테스트 수에 따라 달라질 수 있다.

    BUILD SUCCESSFUL

## 인터페이스와 의존성

새 외부 의존성은 추가하지 않는다. 기존 백엔드는 이미 `spring-boot-starter-web`, `spring-boot-starter-jdbc`, Flyway, PostgreSQL driver, Spring Boot test, Testcontainers를 사용한다.

새 HTTP endpoint는 `GET /api/market-indexes/{indexCode}/prices?period=1M|3M|1Y`이다. `indexCode`는 정확히 `KOSPI`와 `KOSDAQ`만 허용한다. `kospi`, `Kospi`, `KS11`, `KQ11` 같은 값은 허용하지 않는다. `period`는 필수 query parameter이고 정확히 `1M`, `3M`, `1Y`만 허용한다. 성공 응답 타입은 `com.stockreport.marketindex.application.response.MarketIndexPricesResponse`로 만들고, 항목 타입은 `MarketIndexPriceResponse`로 만든다. JSON 최상위 필드는 `indexCode`, `period`, `startDate`, `endDate`, `items`를 사용한다. `items` 항목 필드는 `tradeDate`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `changeRatePercent`를 사용한다.

새 domain 타입 후보는 `com.stockreport.marketindex.domain.MarketIndexPricePeriod`와 `com.stockreport.marketindex.domain.MarketIndexDailyPrice`이다. `MarketIndexPricePeriod`는 허용 기간 문자열과 시작일 계산을 담당한다. Kotlin enum으로 구현한다면 `ONE_MONTH("1M")`, `THREE_MONTHS("3M")`, `ONE_YEAR("1Y")`처럼 API 문자열 값을 별도로 가진다. `MarketIndexDailyPrice`는 DB에서 조회한 전체 일봉 한 건을 application 계층으로 전달한다.

기존 repository 인터페이스 `com.stockreport.marketindex.domain.MarketIndexPriceRepository`에는 `findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate?`와 `findDailyPricesByIndexCodeAndTradeDateBetween(indexCode: MarketIndexCode, startDate: LocalDate, endDate: LocalDate): List<MarketIndexDailyPrice>`를 추가한다. 기존 `findLatestTwoByIndexCode`는 최신 수치 API에서 계속 사용하므로 삭제하거나 동작을 바꾸지 않는다. JDBC 구현체 `com.stockreport.marketindex.infrastructure.persistence.MarketIndexPriceRepositoryImpl`은 `JdbcTemplate`으로 `market_index_price`를 조회한다.

기존 service `com.stockreport.marketindex.application.MarketIndexService`에는 기간별 일봉 조회 public 메서드를 추가한다. 기존 `getMarketIndexSummaries`는 유지한다. 기존 controller `com.stockreport.marketindex.presentation.MarketIndexController`에는 새 `@GetMapping` 메서드를 추가한다.

계획 변경 메모:

- 2026-07-23 / Codex: 계획 초안 작성. 이유: `docs/issues/07-backend-market-index-price-api.md` 구현 전에 기존 `marketindex` 도메인 구조와 테스트 관례에 맞는 자기완결적 실행 계획을 마련하기 위해서.
- 2026-07-24 / Codex: grill 검토 결과를 반영해 기간 기준을 서버 현재 날짜에서 저장된 최신 거래일로 변경하고, `startDate`와 `endDate` 응답 메타데이터, repository 최신 거래일 조회와 범위 조회 분리, `period` 누락 400, 오류 body 비고정, 숫자 scale 규칙, `volume`의 `Long` 타입을 계획에 반영했다. 이유: 구현자가 계획만 읽고도 API 계약과 책임 경계를 모호하게 해석하지 않도록 하기 위해서.
