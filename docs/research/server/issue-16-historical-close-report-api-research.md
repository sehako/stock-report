# 과거 장 마감 리포트 조회 API 서버 코드베이스 조사

상태: 조사 완료

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 16번 이슈

## 1. 조사 목적

과거 장 마감 리포트 조회 API 구현 전에 현재 서버 코드베이스, 데이터 모델, 기존 최신 리포트 API 패턴, 테스트 기반, 구현 시 결정해야 할 경계를 확인한다.

이번 조사는 서버 코드 구조와 기존 스키마 파악에 한정한다. 애플리케이션 코드는 수정하지 않았다.

## 2. 16번 이슈 요구사항

16번 이슈는 과거 장 마감 리포트 조회 API를 제공하는 것이다.

요구사항은 다음과 같다.

- 서비스 운영 시작일 이후 거래일별 리포트를 조회한다.
- 선택한 거래일의 최종 활성 리비전을 기준으로 리포트 기준 거래일, 분석 범위, 스캐너 통계, AI 요약 상태와 내용을 제공한다.
- 선택한 거래일의 최종 활성 리비전이 참조하는 계산 버전을 내부 조회 기준으로 고정한다.
- 휴장일, 미생성일, 서비스 시작 전 날짜의 처리를 구분할 수 있게 한다.
- 서비스 시작일 이전 날짜는 초기 가격 데이터가 있어도 장 마감 리포트로 반환하지 않는다.

근거: `docs/proposal/stock-report-mvp-issue-breakdown.md` 158-163행.

## 3. 관련 기준 문서

과거 리포트 조회와 직접 관련된 기준은 다음과 같다.

- `docs/proposal/stock-report-mvp-product-architecture-baseline.md`
  - 과거 장 마감 리포트는 서비스 운영 시작일 이후 거래일별로 조회한다.
  - 사용자에게는 거래일별 최종 활성 리비전만 노출한다.
  - 출시 이전 일별 리포트 소급 생성은 MVP 제외 범위다.
  - 공개 API는 `latest` 또는 `tradeDate`를 입력으로 받고, Spring이 해당 거래일의 활성 리비전을 내부에서 해석한다.
- `docs/report-generation-considerations.md`
  - 사용자는 거래일을 선택해 해당 날짜의 장 마감 리포트를 조회할 수 있다.
  - 교체된 이전 리비전은 개발 추적과 복구를 위해 보존하되 일반 화면에는 노출하지 않는다.
  - 초기 적재한 과거 가격에서 재계산한 신호를 당시 실제로 발행된 장 마감 리포트로 취급하지 않는다.
- `CONTEXT.md`
  - **장 마감 리포트**는 KRX 정규시장 종가를 기준으로 생성하며 데이터 검증 뒤 공개되는 일별 리포트다.
  - **시장 AI 요약**은 해당 거래일의 활성 **장 마감 리포트**를 입력으로 생성하는 거래일별 AI 서술이다.
  - **분석 종목**은 거래량 상위 200개 종목이며 KRX 전체를 의미하지 않는다.

## 4. 현재 서버 구조

서버는 Kotlin, Spring Boot, Flyway, JDBC 조회 기반 패턴을 사용한다.

현재 15번 이슈 구현 이후 서버에는 다음 API 계층이 존재한다.

- Controller: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportController.kt`
- Service: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportService.kt`
- Repository: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportRepository.kt`
- DTO: `server/src/main/kotlin/com/stockreport/report/LatestCloseReportDto.kt`
- Time 설정: `server/src/main/kotlin/com/stockreport/config/TimeConfig.kt`

현재 서버 조회 API는 JPA Entity를 만들지 않고 `NamedParameterJdbcTemplate`로 여러 테이블을 조합하는 방식이다. 16번 API도 동일한 읽기 전용 조회 패턴을 따르는 것이 자연스럽다.

## 5. 기존 최신 리포트 API 구현 패턴

15번 API는 `GET /api/reports/latest-close`로 제공된다.

현재 응답 구조는 다음과 같다.

- `status`
- `asOfDate`
- `report`
  - `reportDate`
  - `revisionNo`
  - `revisionType`
  - `calculationVersion`
  - `publishedAt`
  - `analysisUniverse`
  - `marketIndices`
  - `scannerStats`
  - `aiSummary`

`LatestCloseReportService`는 다음 흐름으로 응답을 만든다.

1. `Clock`을 통해 Asia/Seoul 기준 오늘 날짜를 계산한다.
2. 오늘 날짜의 활성 리비전을 조회한다.
3. 오늘 활성 리비전이 없으면 오늘 `batch_job_run.status`로 표시 상태를 결정한다.
4. 필요한 경우 최신 활성 리비전을 fallback으로 선택한다.
5. 선택된 리비전을 DTO로 조립한다.
6. 리비전의 `calculation_version`으로 골든크로스 집계를 고정한다.
7. 리비전의 `report_date`와 `id`로 AI 요약을 조회한다.

16번 API는 fallback 정책이 아니라 사용자가 요청한 `tradeDate` 자체의 상태를 구분해야 한다. 하지만 선택된 리비전을 `LatestCloseReportDto`와 유사한 리포트 DTO로 조립하는 로직은 재사용 후보가 된다.

## 6. 데이터 모델 조사

### 6.1 리포트 리비전

`report_revision`은 과거 리포트 조회의 중심 테이블이다.

주요 컬럼:

- `id`
- `report_date`
- `revision_no`
- `revision_type`
- `is_active`
- `calculation_version`
- `target_stock_count`
- `completed_stock_count`
- `failed_stock_count`
- `insufficient_stock_count`
- `no_trading_stock_count`
- `published_at`

거래일별 활성 리비전은 partial unique index로 1건만 허용된다.

```sql
create unique index ux_report_revision_active_report_date
    on report_revision (report_date)
    where is_active = true;
```

16번 API에서는 요청한 `tradeDate`의 `is_active = true` 행을 사용자에게 노출할 최종 활성 리비전으로 해석할 수 있다. 비활성 리비전은 보존되지만 일반 화면에는 노출하지 않는다.

### 6.2 배치 실행 상태

`batch_job_run`은 거래일별 배치 상태를 담는다.

상태값:

- `RUNNING`
- `PUBLISHED_INITIAL`
- `RETRYING`
- `PUBLISHED_FINAL`
- `FAILED`
- `DELAYED`
- `SKIPPED_MARKET_CLOSED`

16번 API에서 휴장일과 미생성일 구분을 위해 `batch_job_run` 조회가 필요하다.

예상 해석 후보:

- 요청일 활성 리비전 존재: 리포트 존재
- 요청일 활성 리비전 없음 + `SKIPPED_MARKET_CLOSED`: 휴장일
- 요청일 활성 리비전 없음 + `DELAYED` 또는 `FAILED`: 생성 지연 또는 미생성
- 요청일 활성 리비전 없음 + `RUNNING` 또는 `RETRYING`: 아직 생성 중 또는 준비 중
- 요청일 활성 리비전 없음 + 배치 행 없음: 미생성일 또는 서비스 시작 전

다만 16번 요구사항은 휴장일, 미생성일, 서비스 시작 전 날짜를 구분하라고만 명시한다. `RUNNING`, `RETRYING`, `DELAYED`, `FAILED`를 과거 조회 응답에서 어떤 사용자 상태로 노출할지는 계획 단계에서 확정해야 한다.

### 6.3 시장 지수 통계

`market_index_price`는 KOSPI, KOSDAQ 일봉 데이터를 저장한다.

15번 API는 선택된 리비전의 `report_date` 기준 KOSPI, KOSDAQ 행을 조회한다. 16번 API도 선택된 활성 리비전의 `report_date`를 기준으로 동일하게 조회하면 된다.

### 6.4 스캐너 통계

15번 API는 다음 통계를 반환한다.

- `targetStockCount`
- `completedStockCount`
- `failedStockCount`
- `insufficientStockCount`
- `noTradingStockCount`
- `goldenCrossStockCount`

이 중 앞의 다섯 개는 `report_revision`에 저장된 커버리지 집계다. `goldenCrossStockCount`는 `stock_analysis`와 `signal_event`를 조인해 선택 리비전과 계산 버전 기준으로 카운트한다.

16번 API도 선택한 거래일의 활성 리비전이 참조하는 `calculation_version`을 기준으로 같은 방식의 단순 조회성 집계를 사용할 수 있다.

주의할 점:

- Spring은 가격 파생값, 기술지표, 신호, 업종 집계를 새로 계산하지 않는다.
- 상승 종목 수, 하락 종목 수, 평균 등락률 같은 새 시장 통계는 16번 범위에 없다.
- 과거 조회에서도 리비전의 `calculation_version`과 다른 신호를 섞으면 안 된다.

### 6.5 시장 AI 요약

`market_ai_summary`는 거래일별 AI 요약 상태와 내용을 저장한다.

주요 컬럼:

- `report_date`
- `report_revision_id`
- `status`
- `summary_text`
- `input_hash`
- `error_message`

15번 API는 선택 리비전의 `report_date`와 `report_revision_id`를 함께 사용해 AI 요약을 조회한다. 16번 API도 같은 조회 기준을 사용하면 최종 활성 리비전과 AI 요약 입력 리비전의 불일치를 완료 요약처럼 보정하지 않을 수 있다.

AI 요약이 없을 때 15번 API는 `PENDING`, `summaryText = null`을 반환한다. 16번 API에서도 같은 기본값을 사용할지 계획 단계에서 확정해야 한다.

## 7. 서비스 운영 시작일 처리

16번 요구사항의 핵심 차이는 서비스 운영 시작일 이전 날짜를 명확히 구분해야 한다는 점이다.

현재 코드와 설정에는 서비스 운영 시작일을 표현하는 값이 없다.

확인 결과:

- `application.yml`, `application-test.yml`, `application-local.yml`에 서비스 시작일 설정이 없다.
- DB 스키마에 서비스 시작일 또는 운영 설정 테이블이 없다.
- `report_revision`만으로는 "서비스 시작 전"과 "서비스 시작 후이지만 미생성"을 구분할 수 없다.

따라서 구현 계획에서 서비스 운영 시작일의 기준 위치를 결정해야 한다.

선택지 후보:

1. 애플리케이션 설정 프로퍼티로 둔다.
   - 예: `stock-report.service-start-date=2026-07-01`
   - DB 스키마 변경 없이 구현 가능하다.
   - 환경별 설정 누락과 기본값 정책을 정해야 한다.
2. DB 설정 테이블을 추가한다.
   - 운영 데이터와 함께 관리할 수 있다.
   - Flyway 마이그레이션이 필요하므로 이번 이슈 범위와 승인 여부를 따져야 한다.
3. 가장 이른 활성 리비전의 `report_date`를 서비스 시작일처럼 해석한다.
   - 별도 설정이 필요 없다.
   - 요구사항의 "서비스 시작 전"과 "서비스 시작 후 미생성"을 안정적으로 구분할 수 없다.

조사 기준으로는 1번 설정 프로퍼티가 가장 작은 변경으로 보인다. 다만 API 스펙과 운영 설정이므로 계획 단계에서 명시적 승인이 필요하다.

## 8. API 상태 모델 후보

15번 API의 `LatestCloseReportStatus`는 최신 조회 관점의 상태다.

현재 값:

- `PUBLISHED`
- `DELAYED`
- `PREPARING`
- `MARKET_CLOSED`
- `NOT_PUBLISHED`
- `EMPTY`

16번 API는 과거 날짜 조회 관점의 상태가 필요하다.

후보 상태:

- `FOUND`: 요청 거래일의 활성 리비전이 있어 리포트 반환
- `MARKET_CLOSED`: 요청일이 휴장일
- `NOT_CREATED`: 서비스 시작일 이후지만 해당 날짜 리포트가 생성되지 않음
- `BEFORE_SERVICE_START`: 서비스 시작일 이전 날짜

`DELAYED`, `PREPARING`을 과거 조회에서도 별도 노출할지는 계획 단계에서 결정해야 한다. 프론트엔드가 과거 리포트 화면에서 "미생성일"만 표시하면 충분한지, 혹은 운영 중 당일과 가까운 날짜에서 "생성 지연"을 보존해야 하는지에 따라 응답 enum이 달라진다.

## 9. URL과 응답 구조에서 결정해야 할 사항

16번 API의 URL은 아직 확정되어 있지 않다.

후보:

- `GET /api/reports/close/{tradeDate}`
- `GET /api/reports/by-date/{tradeDate}`
- `GET /api/reports/history/{tradeDate}`
- `GET /api/reports?tradeDate=YYYY-MM-DD`

아키텍처 기준은 공개 API가 `latest` 또는 `tradeDate`를 입력으로 받고 Spring이 활성 리비전을 내부에서 해석한다고 말한다. 기존 최신 API가 `GET /api/reports/latest-close`이므로 과거 조회도 같은 `/api/reports` 하위에 두는 것이 자연스럽다.

응답 구조는 15번 DTO를 재사용하거나 공통 DTO로 이름을 바꿀 수 있다.

결정 후보:

- `LatestCloseReportDto`를 범용 `CloseReportDto`로 리네임하고 최신/과거 API가 공유한다.
- 기존 DTO 이름은 유지하고 과거 API 전용 DTO를 만든다.
- 응답의 최상위 `status`와 `asOfDate`는 과거 조회에는 의미가 다르므로 `requestedDate`, `serviceStartDate`, `report` 같은 필드를 별도로 둔다.

기존 API 계약을 깨지 않으려면 15번 응답 필드명은 유지하면서 내부 조립 로직만 공통화하는 방향이 안전하다.

## 10. 기존 테스트 구조

현재 서버 테스트는 다음 세 층으로 구성되어 있다.

- `StockReportApplicationTests`
  - 컨텍스트 로딩
  - Flyway 스키마 생성
  - DB 제약 검증
- `LatestCloseReportApiTests`
  - Testcontainers PostgreSQL
  - MockMvc 기반 API 통합 테스트
  - 실제 Flyway 스키마에 SQL fixture 삽입
  - 최신 조회 상태 정책과 리포트 조립 검증
- `LatestCloseReportRestDocsTests`
  - REST Docs 스니펫 생성
  - 엄격한 `responseFields` 문서화 검증

16번 API도 같은 방식으로 통합 테스트를 추가하는 것이 현재 패턴과 맞다.

추가 테스트 후보:

- 서비스 시작일 이후 요청일에 활성 리비전이 있으면 리포트를 반환한다.
- 같은 거래일에 비활성 리비전과 활성 리비전이 함께 있으면 활성 리비전만 반환한다.
- 요청 리비전의 `calculationVersion`이 응답에 포함되고 골든크로스 카운트 기준으로 사용된다.
- 요청 리비전의 `reportDate` 기준으로 KOSPI, KOSDAQ 지수 요약을 반환한다.
- 요청 리비전 기준 AI 요약이 있으면 상태와 내용을 반환한다.
- 요청 리비전 기준 AI 요약이 없으면 기본 상태를 반환한다.
- 요청일이 `SKIPPED_MARKET_CLOSED`이면 휴장일 상태와 `report = null`을 반환한다.
- 서비스 시작일 이후 배치 행과 활성 리비전이 없으면 미생성 상태와 `report = null`을 반환한다.
- 서비스 시작일 이전 날짜는 초기 가격 데이터나 지수 데이터가 있어도 리포트를 반환하지 않는다.
- REST Docs 스니펫이 대표 성공 응답과 상태별 빈 응답을 문서화한다.

## 11. 구현 시 필요한 조회 흐름 후보

16번 API의 서버 내부 조회 흐름 후보는 다음과 같다.

1. 요청 `tradeDate`를 `LocalDate`로 받는다.
2. 서비스 운영 시작일과 비교한다.
3. 요청일이 서비스 운영 시작일 이전이면 `BEFORE_SERVICE_START`, `report = null`로 반환한다.
4. 요청일의 활성 `report_revision`을 조회한다.
5. 활성 리비전이 있으면 이를 선택 리비전으로 사용한다.
6. 활성 리비전이 없으면 요청일의 `batch_job_run`을 조회해 휴장일과 미생성 상태를 구분한다.
7. 선택 리비전이 없으면 상태와 `report = null`을 반환한다.
8. 선택 리비전의 `calculation_version`을 이후 조회 기준으로 유지한다.
9. 선택 리비전의 `report_date` 기준 KOSPI, KOSDAQ `market_index_price`를 조회한다.
10. 선택 리비전의 `id`와 `calculation_version` 기준으로 골든크로스 종목 수를 집계한다.
11. 선택 리비전의 `report_date`, `id` 기준으로 `market_ai_summary`를 조회한다.
12. DTO로 조립해 반환한다.

## 12. 리스크와 주의사항

- 서비스 운영 시작일 기준이 현재 코드와 DB 어디에도 없다. 16번 구현 전 반드시 저장 위치와 기본값 정책을 확정해야 한다.
- `report_revision`만으로는 휴장일, 미생성일, 서비스 시작 전 날짜를 모두 구분할 수 없다. 최소한 서비스 시작일 설정과 `batch_job_run.status` 해석이 필요하다.
- 과거 조회에서 요청일에 활성 리비전이 없을 때 최신 리포트처럼 fallback 리포트를 반환하면 안 된다. 16번 요구사항은 선택한 거래일의 리포트 존재 여부를 구분하는 것이다.
- 초기 적재 가격, 지표, 신호가 존재하더라도 `report_revision`이 없거나 서비스 시작일 이전이면 장 마감 리포트로 반환하면 안 된다.
- 기존 `LatestCloseReportStatus`와 `LatestCloseReportResponse`는 최신 조회 의미가 강하다. 이름을 그대로 과거 API에 재사용하면 API 의미가 흐려질 수 있다.
- DTO 공통화 또는 이름 변경은 기존 15번 API 계약과 REST Docs 테스트에 영향을 줄 수 있으므로 계획에서 변경 범위를 명확히 해야 한다.
- REST Docs HTML 생성은 15번 계획에서 제외된 상태다. 16번에서도 스니펫까지만 생성할지, API 문서 목차를 시작할지는 별도 결정이 필요하다.

## 13. 계획 단계에서 확정해야 할 사항

다음 항목은 조사만으로 확정하지 않았다.

- API URL과 요청 파라미터 또는 path variable 형식
- 응답 DTO 구조와 상태 enum 이름
- 과거 조회에서 `DELAYED`, `RUNNING`, `RETRYING`, `FAILED`를 별도 상태로 노출할지 여부
- 서비스 운영 시작일을 설정 프로퍼티로 둘지, DB에 저장할지, 다른 기준으로 둘지 여부
- 서비스 운영 시작일 설정의 기본값과 테스트 고정값
- 15번 API DTO와 리포트 조립 로직을 공통화할지 여부
- REST Docs 스니펫 생성 범위
- 16번 API 구현 시 기존 15번 API 응답 계약을 변경해도 되는지 여부

## 14. 결론

16번 API 구현에 필요한 핵심 조회 데이터는 이미 존재한다. 선택한 거래일의 활성 `report_revision`을 기준으로 리포트 본문, KOSPI/KOSDAQ 지수 요약, 스캐너 통계, 시장 AI 요약을 조립하는 흐름은 15번 API와 거의 같다.

가장 큰 미확정 지점은 서비스 운영 시작일이다. 현재 코드와 스키마에는 이 값을 표현하는 곳이 없으므로, 휴장일, 미생성일, 서비스 시작 전 날짜를 구분하려면 구현 계획에서 서비스 시작일의 저장 위치와 상태 매핑을 먼저 확정해야 한다.

구현 시에는 최신 조회 API의 fallback 정책을 과거 조회에 가져오지 않는 것이 중요하다. 과거 조회는 요청한 거래일의 활성 리비전이 없으면 직전 리포트를 대신 반환하지 않고, 해당 날짜의 상태를 명확히 반환해야 한다.
