# KOSPI/KOSDAQ 지수 시계열 API 서버 코드베이스 조사

상태: 조사 완료

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 17번 이슈

## 1. 조사 목적

KOSPI와 KOSDAQ 지수 시계열 API 구현 전에 현재 서버 코드베이스, 데이터 모델, 기존 리포트 API 패턴, 테스트 기반, 구현 시 결정해야 할 경계를 확인한다.

이번 조사는 서버 코드 구조와 기존 스키마 파악에 한정한다. 애플리케이션 코드는 수정하지 않았다.

## 2. 17번 이슈 요구사항

17번 이슈는 KOSPI와 KOSDAQ 지수 시계열 API를 제공하는 것이다.

요구사항은 다음과 같다.

- KOSPI와 KOSDAQ 일봉 시계열을 반환한다.
- 시장 개요의 지수 차트가 요청한 기간에 해당하는 지수 일봉 데이터를 조회할 수 있게 한다.
- 리포트 조회 API의 스캐너 통계와 지수 차트용 시계열 데이터를 분리한다.

근거: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 17번 항목.

## 3. 현재 서버 구조

서버는 Kotlin, Spring Boot, Flyway, JDBC 조회 기반 패턴을 사용한다.

현재 서버에는 15번, 16번 이슈 구현 결과로 다음 API 계층이 있다.

- Controller: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportController.kt`
- Service: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportService.kt`
- Repository: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportRepository.kt`
- DTO: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportDto.kt`
- Time 설정: `server/src/main/kotlin/com/stockreport/config/TimeConfig.kt`

현재 조회 API는 JPA Entity를 만들지 않고 `NamedParameterJdbcTemplate`로 여러 테이블을 직접 조회한다. 17번 API도 읽기 전용 조회 API이므로 같은 패턴을 따르는 것이 자연스럽다.

## 4. 기존 리포트 API와의 관계

현재 리포트 API는 다음 두 개다.

- `GET /api/reports/latest-close`
- `GET /api/reports/close?tradeDate=YYYY-MM-DD`

두 API는 응답 본문 `report.marketIndices`에 KOSPI, KOSDAQ 지수 요약을 포함한다. 이 데이터는 선택된 리포트 리비전의 `reportDate` 기준 단일 거래일 일봉이다.

17번 API는 시장 개요 차트용 기간 시계열을 반환해야 하므로 기존 `report.marketIndices`와 역할이 다르다.

- 기존 리포트 API의 `marketIndices`: 리포트 기준일의 KOSPI/KOSDAQ 지수 요약
- 17번 API의 지수 시계열: 사용자가 요청한 기간의 KOSPI/KOSDAQ 일봉 배열

따라서 17번 구현에서는 기존 리포트 DTO에 기간 시계열을 추가하지 않고 별도 엔드포인트와 DTO를 두는 것이 요구사항과 맞다.

## 5. 데이터 모델 조사

### 5.1 시장 지수 일봉 테이블

`market_index_price`는 KOSPI, KOSDAQ 일봉 데이터를 저장한다.

주요 컬럼:

- `index_code`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `change_rate`
- `created_at`
- `updated_at`

제약:

- `(index_code, trade_date)` unique
- `index_code in ('KOSPI', 'KOSDAQ')`

현재 스키마에는 별도 조회 인덱스가 없다. unique 제약은 PostgreSQL에서 unique index를 생성하므로 `index_code = ? and trade_date between ? and ?` 형태의 기간 조회에 활용될 수 있다.

### 5.2 리포트 리비전과의 관계

`market_index_price`는 `report_revision`을 직접 참조하지 않는다. 리포트 API는 선택 리비전의 `report_date`와 같은 날짜의 지수 행을 조회한다.

17번 API는 차트 기간 데이터가 목적이므로 리비전 ID나 계산 버전을 기준으로 조회할 필요가 없다. 다만 과거 리포트 화면에서 진입하는 시장 개요라면 프론트엔드가 기준 거래일을 알고 있으므로, API는 요청 종료일을 명시적으로 받아 그 날짜까지의 지수 일봉만 반환하는 방식이 안전하다.

### 5.3 데이터 누락 처리

기존 리포트 API는 활성 리비전이 있으면 지수 데이터가 일부 누락되어도 조회된 지수만 `marketIndices`에 포함한다. 17번 API도 저장된 일봉을 조회하는 API로 보고, 요청 기간 내 일부 날짜가 없더라도 보간하거나 빈 거래일을 생성하지 않는 것이 현재 아키텍처와 맞다.

휴장일은 `market_index_price`에 일봉 행이 없을 가능성이 높다. 시계열 API가 달력일 기준 모든 날짜를 채우면 금융 데이터를 새로 해석하는 결과가 되므로 피해야 한다.

## 6. 기존 Repository 조회 패턴

`LatestCloseReportRepository.findMarketIndices(reportDate)`는 다음 조건으로 단일 거래일의 KOSPI/KOSDAQ 지수 데이터를 조회한다.

- `trade_date = :reportDate`
- `index_code in ('KOSPI', 'KOSDAQ')`
- 정렬은 KOSPI, KOSDAQ 순서

17번 API에는 기간 조회 메서드가 필요하다.

조회 후보:

```sql
select
    index_code,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    change_rate
from market_index_price
where index_code in (:indexCodes)
  and trade_date between :startDate and :endDate
order by
    case index_code when 'KOSPI' then 1 when 'KOSDAQ' then 2 else 3 end,
    trade_date asc
```

응답 구조는 두 가지 후보가 있다.

1. 지수별 series 배열로 그룹핑한다.
   - 프론트엔드 차트가 KOSPI/KOSDAQ을 별도 선 또는 별도 패널로 그리기 쉽다.
   - 같은 날짜의 KOSPI/KOSDAQ 행이 모두 존재한다는 가정을 하지 않아도 된다.
2. 평탄한 일봉 배열로 반환한다.
   - DTO가 단순하다.
   - 프론트엔드가 지수별 그룹핑을 다시 해야 한다.

시장 개요 차트 목적을 고려하면 지수별 series 배열이 더 적합해 보인다. 단, API 스펙은 계획 단계에서 확정해야 한다.

## 7. API 입력 모델 후보

17번 요구사항은 "요청한 기간"이라고만 표현하며 URL과 파라미터는 아직 확정되어 있지 않다.

후보 API:

- `GET /api/market-indices?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`
- `GET /api/market-indices/timeseries?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`
- `GET /api/market-indices/timeseries?endDate=YYYY-MM-DD&period=1M`
- `GET /api/reports/market-indices?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`

현재 리포트 API는 `/api/reports` 아래에 있지만, 지수 시계열은 리포트 스캐너 통계와 분리해야 한다. 따라서 `/api/market-indices/timeseries`처럼 리포트와 별도 리소스로 두는 후보가 요구사항과 가장 직접적으로 맞다.

입력 파라미터 후보:

- `startDate`: 조회 시작 거래일 후보 날짜
- `endDate`: 조회 종료 거래일 후보 날짜
- `indexCode`: 선택 지수 필터. MVP 시장 개요가 KOSPI와 KOSDAQ을 함께 보여준다면 생략 가능

주의할 점:

- 날짜 형식 오류는 기존 API처럼 Spring MVC 바인딩 오류로 HTTP 400 처리할 수 있다.
- `startDate > endDate`는 별도 검증이 필요하다.
- 요청 기간 상한을 둘지 결정해야 한다. MVP 요구사항은 기간 제한을 명시하지 않는다.
- `1W`, `1M`, `3M`, `6M`, `1Y` 같은 기간 프리셋은 21번 종목 상세 차트 이슈에는 명시되어 있지만 17번에는 명시되어 있지 않다. 지수 시계열 API에 프리셋을 둘지는 계획 단계에서 확정해야 한다.

## 8. 응답 모델 후보

지수별 series 그룹 응답 후보:

```json
{
  "startDate": "2026-06-01",
  "endDate": "2026-07-09",
  "indices": [
    {
      "indexCode": "KOSPI",
      "prices": [
        {
          "tradeDate": "2026-07-09",
          "openPrice": 2700.0,
          "highPrice": 2720.0,
          "lowPrice": 2680.0,
          "closePrice": 2710.0,
          "volume": 1000000,
          "changeRate": 0.0123
        }
      ]
    }
  ]
}
```

평탄한 응답 후보:

```json
{
  "startDate": "2026-06-01",
  "endDate": "2026-07-09",
  "prices": [
    {
      "indexCode": "KOSPI",
      "tradeDate": "2026-07-09",
      "openPrice": 2700.0,
      "highPrice": 2720.0,
      "lowPrice": 2680.0,
      "closePrice": 2710.0,
      "volume": 1000000,
      "changeRate": 0.0123
    }
  ]
}
```

기존 `MarketIndexDto`는 `indexCode`와 일봉 필드를 모두 포함하므로 평탄한 응답에는 바로 재사용할 수 있다. 지수별 series 응답을 택하면 `MarketIndexSeriesDto`, `MarketIndexPriceDto` 같은 새 DTO를 두는 편이 명확하다.

## 9. 테스트 구조 조사

현재 서버 API 테스트는 다음 패턴을 사용한다.

- `@SpringBootTest`
- `@ActiveProfiles("test")`
- Testcontainers PostgreSQL
- MockMvc
- Flyway 실제 스키마에 SQL fixture 삽입
- `jdbcTemplate.execute("truncate table ... restart identity cascade")`로 테스트별 초기화

관련 테스트 파일:

- `server/src/test/kotlin/com/stockreport/report/LatestCloseReportApiTests.kt`
- `server/src/test/kotlin/com/stockreport/report/LatestCloseReportRestDocsTests.kt`

17번 구현 시 필요한 테스트 후보:

- 요청 기간의 KOSPI와 KOSDAQ 일봉이 날짜 오름차순으로 반환되는지 검증
- 요청 기간 밖의 지수 일봉은 제외되는지 검증
- KOSPI와 KOSDAQ 외 지수는 스키마 제약상 저장 불가하므로 별도 필터 테스트는 불필요
- 한쪽 지수 데이터가 일부 날짜에 없어도 조회된 데이터만 반환하는지 검증
- 기간 내 데이터가 없으면 빈 series 또는 빈 prices를 반환하는지 검증
- `startDate` 누락, `endDate` 누락, 날짜 형식 오류가 HTTP 400인지 검증
- `startDate > endDate`의 응답 정책 검증
- REST Docs 스니펫 생성 테스트 추가

## 10. 구현 시 수정 후보 파일

조사 기준 구현 후보 파일은 다음과 같다.

- `server/src/main/kotlin/com/stockreport/report/LatestCloseReportController.kt`
  - 기존 리포트 컨트롤러에 추가할 수도 있으나 리포트와 분리 요구가 있으므로 새 컨트롤러 후보가 더 명확하다.
- `server/src/main/kotlin/com/stockreport/market/MarketIndexController.kt`
  - 지수 시계열 전용 컨트롤러 후보.
- `server/src/main/kotlin/com/stockreport/market/MarketIndexService.kt`
  - 기간 검증과 응답 조립 담당 후보.
- `server/src/main/kotlin/com/stockreport/market/MarketIndexRepository.kt`
  - `market_index_price` 기간 조회 담당 후보.
- `server/src/main/kotlin/com/stockreport/market/MarketIndexDto.kt`
  - 시계열 응답 DTO 후보.
- `server/src/test/kotlin/com/stockreport/market/MarketIndexApiTests.kt`
  - API 통합 테스트 후보.
- `server/src/test/kotlin/com/stockreport/market/MarketIndexRestDocsTests.kt`
  - REST Docs 스니펫 테스트 후보.

기존 `LatestCloseReportRepository.findMarketIndices(reportDate)`를 공통 지수 Repository로 옮기는 리팩터링도 가능하지만, 구현 범위를 키운다. 17번 계획에서는 기존 리포트 API를 건드리지 않고 새 market 패키지에 지수 시계열 조회를 추가할지, 공통화를 수행할지 결정해야 한다.

## 11. 변경 금지 또는 주의 범위

- DB 스키마 변경은 17번 요구사항만으로는 필요하지 않아 보인다.
- 외부 의존성 추가는 필요하지 않아 보인다.
- Spring API에서 등락률, 이동평균, 신호, 차트용 보조 지표를 새로 계산하지 않는다.
- 휴장일이나 누락 거래일을 서버에서 보간하지 않는다.
- 기존 리포트 API의 `marketIndices` 응답 의미를 기간 시계열로 확장하지 않는다.
- 기존 최신/과거 리포트 API의 fallback 정책과 상태 enum을 변경하지 않는다.

## 12. 계획 단계에서 확정해야 할 사항

다음 항목은 조사만으로 확정하지 않았다.

- API URL
- 입력 파라미터를 `startDate/endDate`로 둘지, `endDate/period`로 둘지 여부
- 지수 코드 필터를 제공할지 여부
- `startDate > endDate`일 때 HTTP 400을 반환할지, 빈 결과를 반환할지 여부
- 기간 상한을 둘지 여부
- 응답을 지수별 series로 그룹핑할지, 평탄한 일봉 배열로 반환할지 여부
- 데이터가 없는 지수를 빈 series로 포함할지, 아예 제외할지 여부
- 기존 report 패키지에 추가할지, market 패키지를 새로 만들지 여부
- REST Docs 스니펫 명칭과 문서화 범위

## 13. 리스크와 주의사항

- 현재 `market_index_price`에는 리포트 리비전 참조가 없으므로, 과거 리포트 기준 화면에서 사용할 때는 클라이언트가 요청 종료일을 해당 리포트 거래일로 제한해야 한다.
- API가 `endDate`를 생략하고 서버의 오늘 날짜를 기본값으로 사용하면 과거 리포트 화면에서 기준일 이후 데이터가 섞일 수 있다. MVP에서는 명시적 기간 입력을 요구하는 편이 더 안전하다.
- 요청 기간이 과도하게 길면 응답 크기가 커질 수 있다. KOSPI/KOSDAQ 2개 지수만 대상이라 리스크는 제한적이지만, 기간 상한 정책은 계획 단계에서 검토해야 한다.
- 지수별로 누락 날짜가 다를 수 있으므로, 같은 인덱스의 배열 안에서 `tradeDate`를 기준으로 차트를 그리도록 응답 의미를 문서화해야 한다.
- 기존 `MarketIndexDto`를 재사용하면 빠르게 구현할 수 있지만 리포트 요약 DTO와 차트 시계열 DTO의 의미가 섞일 수 있다. 전용 DTO를 두는 편이 장기적으로 명확하다.
