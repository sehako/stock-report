# KOSPI/KOSDAQ 지수 시계열 API 구현 계획

상태: 계획

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 17번 이슈

원격 이슈: https://github.com/sehako/stock-report/issues/13

기준 조사 문서: `docs/research/server/issue-17-market-index-timeseries-api-research.md`

## 1. 목적

시장 개요 화면이 KOSPI와 KOSDAQ 일봉 차트를 그릴 수 있도록 저장된 시장 지수 일봉을 날짜 범위로 조회하는 서버 API를 제공한다.

이 API는 장 마감 리포트의 `marketIndices` 단일 거래일 요약과 분리한다. 리포트 조회 API는 선택된 활성 리비전 기준의 시장 요약과 스캐너 통계를 계속 제공하고, 지수 시계열 API는 차트에 필요한 기간 일봉만 제공한다.

Spring은 지수 가격, 등락률, 보조 지표를 계산하지 않는다. `market_index_price`에 저장된 KOSPI, KOSDAQ 일봉을 조회해 반환하며, 휴장일이나 누락 거래일은 보간하지 않는다.

## 2. 기준 문서

- `docs/proposal/stock-report-mvp-product-architecture-baseline.md`
- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/research/server/issue-17-market-index-timeseries-api-research.md`
- `docs/implementation/server/issue-15-latest-close-report-api-plan.md`
- `docs/implementation/server/issue-16-historical-close-report-api-plan.md`
- `CONTEXT.md`

## 3. 그릴링 결과와 결정 사항

질문: 지수 시계열 API를 리포트 API 아래에 둘 것인가, 별도 시장 지수 리소스로 둘 것인가?

권장 답변: 별도 리소스인 `GET /api/market-indices/timeseries`로 둔다. 17번 이슈가 "리포트 조회 API의 스캐너 통계와 지수 차트용 시계열 데이터를 분리"하라고 요구하고, 기준 아키텍처도 KOSPI·KOSDAQ 지수 시계열을 독립 조회 경계로 둔다.

질문: 응답에 KOSPI/KOSDAQ series를 항상 포함할 것인가, 데이터가 있는 지수만 포함할 것인가?

권장 답변: 항상 포함한다. `indices` 배열은 KOSPI, KOSDAQ 순서로 고정하고, 기간 내 데이터가 없는 지수는 `prices = []`로 반환한다. 프론트엔드는 안정적인 응답 모양을 기준으로 차트를 구성할 수 있고, 데이터 부재와 응답 대상 제외를 구분할 수 있다.

질문: 요청 기간에 상한을 둘 것인가?

권장 답변: 이번 MVP에서는 상한을 두지 않는다. 대상이 KOSPI/KOSDAQ 2개 지수의 일봉뿐이라 응답 크기 위험이 제한적이고, 임의 상한을 두면 프론트엔드 기간 선택 정책과 맞물린 추가 API 규칙이 생긴다. 장기 운영 후 실제 요청 패턴을 보고 별도 이슈로 기간 상한 또는 캐싱을 검토한다.

질문: `period=1M`, `period=3M` 같은 프리셋 파라미터를 지금 API에 넣을 것인가?

권장 답변: 넣지 않는다. 17번 이슈는 요청한 기간의 지수 일봉 조회이고, 종목 상세 이슈의 1W·1M·3M·6M·1Y 프리셋과 섞이면 API 책임이 커진다. 이번 API는 `startDate/endDate`만 받고, 프론트엔드가 프리셋을 날짜 범위로 변환해 호출한다.

질문: `indexCode=KOSPI` 같은 지수 필터를 제공할 것인가?

권장 답변: 이번 MVP에서는 제공하지 않는다. 시장 개요 화면은 KOSPI와 KOSDAQ을 함께 보여주는 요구이고, 스키마도 두 지수만 허용한다. 필터를 넣으면 검증해야 할 입력과 문서화 범위가 늘지만 MVP 이득은 작다. 응답은 항상 두 지수 series로 고정한다.

질문: `startDate > endDate`일 때 빈 결과를 반환할 것인가, HTTP 400을 반환할 것인가?

권장 답변: HTTP 400을 반환한다. 날짜 범위가 의미적으로 잘못된 요청이므로 실제 데이터 부재와 구분해야 한다. 기간 내 데이터가 실제로 없는 경우만 HTTP 200과 빈 `prices`로 반환한다.

질문: 이 API가 `serviceStartDate` 이전의 지수 데이터 조회를 막아야 하는가?

권장 답변: 막지 않는다. 서비스 운영 시작일은 발행된 장 마감 리포트의 공개 기준이고, 시장 지수 시계열은 저장된 일봉 차트 데이터이다. 기준서도 초기 가격·시계열 데이터와 발행 리포트를 구분한다. 따라서 이 API는 `startDate/endDate` 범위에 저장된 지수 일봉을 그대로 반환하고, 리포트 발행 가능 여부는 검증하지 않는다.

질문: 응답의 가격 필드와 등락률이 DB에서 `null`이면 어떻게 할 것인가?

권장 답변: 그대로 `null`을 반환한다. 현재 스키마에서 `open_price`, `high_price`, `low_price`, `close_price`, `change_rate`는 nullable이고, Spring은 금융 값을 보정하거나 계산하지 않는 원칙이다. 차트가 필수로 필요한 값의 결측 처리는 프론트엔드 표시 정책 또는 데이터 수집 검증 이슈에서 다룬다.

질문: `volume`이 DB에서 `null`이면 그대로 `null`로 반환할 것인가, `0`으로 바꿀 것인가?

권장 답변: 그대로 `null`을 반환한다. `0`은 실제 거래량 0이라는 의미가 될 수 있어 결측과 섞인다. 가격 필드와 같은 원칙으로 저장된 값을 보정하지 않는다.

질문: REST Docs에서 400 오류 응답까지 문서화할 것인가, 정상 응답만 문서화하고 400은 테스트로만 검증할 것인가?

권장 답변: 정상 응답만 REST Docs로 문서화하고, 400은 통합 테스트로 검증한다. 현재 프로젝트에 공통 오류 응답 포맷이 아직 정의되어 있지 않고, Spring 기본 오류 응답을 문서화하면 나중에 공통 오류 포맷 도입 시 문서 변경이 커진다.

질문: 기존 `LatestCloseReportRepository.findMarketIndices(reportDate)`를 새 `MarketIndexRepository`로 옮겨 공통화할 것인가?

권장 답변: 이번 구현에서는 옮기지 않는다. 공통화하면 기존 리포트 API 코드까지 변경되어 회귀 범위가 커진다. 17번은 새 시계열 API 추가가 목적이므로 기존 단일 거래일 리포트 조회는 그대로 두고, 새 `market` 패키지에 기간 조회 Repository를 추가한다.

질문: 이 결정들을 ADR로 남길 것인가?

권장 답변: 남기지 않는다. 대부분은 17번 API의 공개 스펙과 구현 범위 결정이며, 되돌리기 어렵거나 아키텍처 전반에 영향을 주는 수준은 아니다. 구현 계획 문서와 `CONTEXT.md` 용어 보강으로 충분하다. 나중에 지수 시계열을 리포트 리비전에 묶는 방향으로 바꾸면 그때는 ADR 후보로 검토한다.

확정 계획:

- API 경로는 `GET /api/market-indices/timeseries?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`로 둔다.
- `startDate`와 `endDate`는 모두 필수 query parameter로 둔다.
- 날짜는 `LocalDate`로 바인딩하고 `yyyy-MM-dd` 형식을 사용한다.
- `startDate` 또는 `endDate`가 누락되면 Spring MVC 기본 요청 파라미터 검증 오류에 따라 HTTP 400으로 처리한다.
- 날짜 형식이 잘못되면 Spring MVC 기본 바인딩 오류에 따라 HTTP 400으로 처리한다.
- `startDate > endDate`이면 Service에서 검증해 HTTP 400을 반환한다.
- MVP에서는 `period=1M` 같은 기간 프리셋을 제공하지 않는다.
- MVP에서는 `indexCode` 필터를 제공하지 않고 KOSPI와 KOSDAQ을 함께 반환한다.
- 기간 상한은 이번 구현에서 두지 않는다. 대상 지수가 2개뿐이고 일봉 데이터라 응답 크기 리스크가 제한적이다.
- 응답은 지수별 series 배열로 그룹핑한다.
- 응답에는 요청한 `startDate`, `endDate`를 그대로 포함한다.
- KOSPI와 KOSDAQ은 항상 `indices` 배열에 포함한다.
- 요청 기간 내 특정 지수 데이터가 없으면 해당 지수의 `prices`를 빈 배열로 반환한다.
- 각 지수의 `prices`는 `tradeDate` 오름차순으로 정렬한다.
- 지수 순서는 KOSPI, KOSDAQ 순서로 고정한다.
- 휴장일이나 누락 거래일은 서버에서 생성하지 않는다.
- `market_index_price`에 저장된 값만 반환한다.
- 기존 `LatestCloseReportDto.MarketIndexDto`는 재사용하지 않고 차트 시계열 전용 DTO를 새로 둔다.
- 기존 리포트 API의 URL, 응답 필드, fallback 정책, 상태 enum은 변경하지 않는다.
- 과거 장 마감 리포트 화면에서 사용하는 경우에도 이 API는 리포트 기준일을 검증하지 않는다.
- 과거 장 마감 리포트 화면은 프론트엔드가 `endDate`를 해당 리포트의 `reportDate` 이하로 제한해 호출한다.
- DB 스키마 변경과 외부 의존성 추가는 하지 않는다.
- REST Docs 스니펫은 정상 응답 대표 케이스를 생성하고, 400 오류는 통합 테스트로 검증한다.

## 4. 승인 필요한 API 스펙

구현 전 사용자가 승인해야 하는 공개 API 스펙은 다음과 같다.

```http
GET /api/market-indices/timeseries?startDate=2026-06-01&endDate=2026-07-09
```

정상 응답 예시는 다음 구조를 기준으로 한다.

```json
{
  "startDate": "2026-06-01",
  "endDate": "2026-07-09",
  "indices": [
    {
      "indexCode": "KOSPI",
      "prices": [
        {
          "tradeDate": "2026-07-08",
          "openPrice": 2700.0,
          "highPrice": 2720.0,
          "lowPrice": 2680.0,
          "closePrice": 2710.0,
          "volume": 1000000,
          "changeRate": 0.0123
        }
      ]
    },
    {
      "indexCode": "KOSDAQ",
      "prices": []
    }
  ]
}
```

상태 코드 기준:

- 정상 조회: HTTP 200
- 필수 파라미터 누락: HTTP 400
- 날짜 형식 오류: HTTP 400
- `startDate > endDate`: HTTP 400
- 기간 내 데이터 없음: HTTP 200, KOSPI/KOSDAQ 각각 `prices = []`

## 5. 조회 흐름

1. Controller가 `startDate`, `endDate` query parameter를 `LocalDate`로 바인딩한다.
2. Service가 `startDate <= endDate`인지 검증한다.
3. 검증 실패 시 HTTP 400으로 응답하도록 Spring의 `ResponseStatusException` 또는 동일한 기존 오류 처리 방식으로 예외를 발생시킨다.
4. Repository가 `market_index_price`에서 `index_code in ('KOSPI', 'KOSDAQ')`이고 `trade_date between startDate and endDate`인 행을 조회한다.
5. Repository 조회 결과는 `index_code` 정렬 우선순위와 `trade_date asc`로 정렬한다.
6. Service가 KOSPI, KOSDAQ 기본 series를 만들고 조회된 일봉을 각 series에 배치한다.
7. 조회된 행이 없는 지수도 빈 `prices` 배열로 포함한다.
8. Controller가 DTO를 JSON으로 반환한다.

조회 SQL 기준은 다음과 같다.

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

## 6. 수정할 파일

### `server/src/main/kotlin/com/stockreport/market/MarketIndexController.kt`

- 신규 컨트롤러를 추가한다.
- `@RequestMapping("/api/market-indices")`를 사용한다.
- `GET /timeseries` 엔드포인트를 추가한다.
- `startDate`, `endDate`를 `@RequestParam`과 `@DateTimeFormat(iso = DateTimeFormat.ISO.DATE)`로 받는다.
- Controller는 입력 바인딩과 Service 호출만 담당한다.

### `server/src/main/kotlin/com/stockreport/market/MarketIndexService.kt`

- 신규 서비스를 추가한다.
- `startDate > endDate` 검증을 담당한다.
- Repository 조회 결과를 KOSPI, KOSDAQ series 응답으로 조립한다.
- 조회 결과가 없는 지수도 빈 series로 포함한다.
- 금융 데이터 계산, 보간, 기간 프리셋 해석은 하지 않는다.

### `server/src/main/kotlin/com/stockreport/market/MarketIndexRepository.kt`

- 신규 Repository를 추가한다.
- `NamedParameterJdbcTemplate`를 사용해 `market_index_price` 기간 조회를 수행한다.
- 조회 대상 지수 코드는 Service 또는 Repository 내부 상수로 KOSPI, KOSDAQ에 한정한다.
- JPA Entity는 추가하지 않는다.
- 기존 `LatestCloseReportRepository.findMarketIndices(reportDate)`는 이동하거나 변경하지 않는다.

### `server/src/main/kotlin/com/stockreport/market/MarketIndexDto.kt`

- 신규 DTO 파일을 추가한다.
- `MarketIndexTimeseriesResponse`를 둔다.
- `MarketIndexSeriesDto`를 둔다.
- `MarketIndexPricePointDto`를 둔다.
- DTO 필드는 응답 예시의 camelCase 이름을 따른다.
- 가격 필드, 거래량, 등락률은 DB nullable 여부를 반영해 nullable 타입으로 둔다.

### `server/src/test/kotlin/com/stockreport/market/MarketIndexApiTests.kt`

- 신규 통합 테스트를 추가한다.
- 기존 서버 테스트와 동일하게 `@SpringBootTest`, `@ActiveProfiles("test")`, Testcontainers PostgreSQL, MockMvc 패턴을 사용한다.
- 테스트별로 `market_index_price`를 truncate한다.
- 필요한 fixture는 테스트 내부 helper로 삽입한다.

### `server/src/test/kotlin/com/stockreport/market/MarketIndexRestDocsTests.kt`

- 신규 REST Docs 테스트를 추가한다.
- 정상 응답 대표 케이스 스니펫을 생성한다.
- 응답 필드 설명에는 빈 거래일 보간을 하지 않고 저장된 일봉만 반환한다는 의미를 포함한다.

## 7. 변경 금지 범위

- Flyway 마이그레이션 추가 또는 기존 DB 스키마 변경
- `market_index_price` 컬럼, 제약, 인덱스 변경
- Python worker 코드 변경
- 프론트엔드 코드 변경
- 기존 `GET /api/reports/latest-close` 응답 계약 변경
- 기존 `GET /api/reports/close` 응답 계약 변경
- 기존 리포트 API의 `marketIndices` 의미 변경
- 기존 최신/과거 리포트 API fallback 정책 변경
- 리포트 DTO에 기간 시계열 필드 추가
- 지수 시계열 API에서 리포트 활성 리비전 또는 서비스 운영 시작일 검증 추가
- `period` 파라미터 또는 프리셋 기간 API 추가
- `indexCode` 필터 추가
- 서버의 금융 지표, 등락률, 이동평균, 신호 재계산
- 휴장일 또는 누락 거래일 보간
- AI 요약 생성, 조회, 상태 처리 변경
- 인증, 권한, CORS 정책 추가
- 신규 외부 의존성 추가
- REST Docs HTML 조립, 목차 구성, 배포 문서 추가

## 8. 테스트 범위

다음 통합 테스트를 추가한다.

- 요청 기간의 KOSPI와 KOSDAQ 일봉이 지수별 series로 반환된다.
- KOSPI가 KOSDAQ보다 먼저 반환된다.
- 각 지수의 `prices`가 `tradeDate` 오름차순으로 반환된다.
- 요청 기간 밖의 지수 일봉은 제외된다.
- 요청 기간 내 일부 날짜가 누락되어도 저장된 일봉만 반환하고 누락 날짜를 보간하지 않는다.
- 한쪽 지수 데이터가 없으면 해당 지수는 빈 `prices` 배열로 반환된다.
- 요청 기간 내 양쪽 지수 데이터가 모두 없으면 KOSPI, KOSDAQ 모두 빈 `prices` 배열로 반환된다.
- `startDate`가 누락되면 HTTP 400을 반환한다.
- `endDate`가 누락되면 HTTP 400을 반환한다.
- 날짜 형식이 잘못되면 HTTP 400을 반환한다.
- `startDate > endDate`이면 HTTP 400을 반환한다.

다음 REST Docs 테스트를 추가한다.

- `GET /api/market-indices/timeseries` 정상 응답 스니펫을 생성한다.
- 스니펫 이름은 `market-indices/timeseries/success`로 둔다.
- `startDate`, `endDate`, `indices`, `indices[].indexCode`, `indices[].prices[]` 필드를 문서화한다.

테스트 실행 명령은 다음을 기준으로 한다.

```bash
cd server
./gradlew test
```

## 9. 완료 조건

- [x] `GET /api/market-indices/timeseries?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`가 HTTP 200으로 KOSPI/KOSDAQ 지수별 일봉 series를 반환한다.
- [x] 날짜 범위 밖 데이터가 응답에 포함되지 않는다.
- [x] 지수별 가격 배열은 거래일 오름차순이다.
- [x] 데이터가 없는 지수도 빈 series로 포함된다.
- [x] 필수 파라미터 누락, 날짜 형식 오류, `startDate > endDate`가 HTTP 400으로 검증된다.
- [x] 기존 최신 장 마감 리포트 API 테스트가 계속 통과한다.
- [x] 기존 과거 장 마감 리포트 API 테스트가 계속 통과한다.
- [x] 신규 지수 시계열 API 통합 테스트가 통과한다.
- [x] 신규 REST Docs 스니펫 테스트가 통과한다.
- [x] DB 스키마, worker, client, 기존 리포트 API 계약이 변경되지 않는다.

## 10. 구현 후 리뷰 기준

구현 완료 후 `code-reviewer` 서브에이전트는 다음 기준으로 diff를 검토한다.

- 승인된 API 경로와 응답 구조를 벗어난 변경이 없는가
- 기존 리포트 API의 응답 계약과 fallback 정책이 보존되는가
- DB 스키마, 외부 의존성, worker, client 변경이 없는가
- 서버가 시장 지수 데이터를 계산하거나 보간하지 않는가
- DB의 nullable 가격 필드와 등락률을 임의 기본값으로 대체하지 않는가
- KOSPI/KOSDAQ 순서와 가격 배열 정렬이 테스트로 고정되어 있는가
- 오류 입력에 대한 HTTP 400 테스트가 충분한가
- REST Docs 필드 설명이 실제 응답과 일치하는가

## 11. 남은 리스크

- `market_index_price`는 리포트 리비전과 직접 연결되지 않는다. 과거 리포트 화면에서 사용할 때도 서버는 리포트 기준일을 검증하지 않으며, 프론트엔드가 `endDate`를 해당 리포트 거래일로 제한해야 한다.
- 이번 API는 기간 상한을 두지 않는다. 지수 2개 일봉만 반환하므로 MVP 위험은 낮지만, 장기 운영 후 매우 긴 기간 요청이 많아지면 상한 또는 캐싱 정책을 별도 이슈로 검토할 수 있다.
- 응답 오류 본문 형식은 현재 프로젝트의 공통 오류 포맷이 정의되어 있지 않으므로 Spring 기본 오류 응답을 따른다.

## 12. 사용자 확인이 필요한 사항

구현 착수 전 다음 공개 API 결정을 승인해야 한다.

- API 경로: `GET /api/market-indices/timeseries`
- 필수 파라미터: `startDate`, `endDate`
- 미지원 파라미터: `period`, `indexCode`
- 응답 구조: 지수별 series 그룹
- 데이터 없음 정책: KOSPI/KOSDAQ series를 유지하고 `prices = []`
- 오류 정책: `startDate > endDate`는 HTTP 400
