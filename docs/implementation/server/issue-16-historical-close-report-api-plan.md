# 과거 장 마감 리포트 조회 API 구현 계획

상태: 계획

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 16번 이슈

원격 이슈: https://github.com/sehako/stock-report/issues/10

기준 조사 문서: `docs/research/server/issue-16-historical-close-report-api-research.md`

관련 ADR: `docs/adr/0006-use-trade-date-and-active-revision-for-historical-close-report.md`

## 1. 목적

사용자가 선택한 거래일의 장 마감 리포트를 조회할 수 있는 서버 API를 제공한다.

이 API는 서비스 운영 시작일 이후의 거래일에 대해서만 실제 발행된 활성 리비전을 반환한다. 선택한 거래일의 최종 활성 리비전을 기준으로 리포트 기준 거래일, 분석 범위, 계산 버전, KOSPI·KOSDAQ 지수 요약, 분석 종목 기준 스캐너 통계, 시장 AI 요약 상태와 내용을 함께 제공한다.

서비스 시작 전 날짜, 휴장일, 서비스 시작 이후이지만 리포트가 공개되지 않은 날짜는 서로 다른 표시 상태로 구분한다. 서비스 시작일 이전 날짜는 초기 가격 데이터나 기술지표 데이터가 있어도 장 마감 리포트로 반환하지 않는다.

## 2. 기준 문서

- `docs/proposal/stock-report-mvp-product-architecture-baseline.md`
- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/research/server/issue-16-historical-close-report-api-research.md`
- `docs/implementation/server/issue-15-latest-close-report-api-plan.md`
- `docs/adr/0006-use-trade-date-and-active-revision-for-historical-close-report.md`
- `docs/report-generation-considerations.md`
- `CONTEXT.md`

## 3. 결정 사항

- API 경로는 `GET /api/reports/close?tradeDate=YYYY-MM-DD`로 둔다.
- `tradeDate`는 쿼리 파라미터로 받고, `yyyy-MM-dd` 형식의 KST 기준 거래일 후보 날짜로 해석한다.
- 정상 파싱 가능한 날짜이지만 리포트가 없는 경우에도 HTTP 200과 상태 응답을 반환한다.
- `tradeDate`가 누락된 경우는 Spring MVC 기본 요청 파라미터 검증 오류에 따라 HTTP 400으로 처리한다.
- 날짜 형식이 잘못된 경우는 Spring MVC 기본 바인딩 오류에 따라 HTTP 400으로 처리한다.
- 서비스 운영 시작일은 필수 Spring 설정 프로퍼티로 둔다.
- 프로퍼티 이름은 `stock-report.service-start-date`로 둔다.
- 서비스 운영 시작일의 운영 기준값은 `2026-07-01`로 둔다.
- 서비스 운영 시작일은 `LocalDate`로 바인딩한다.
- 서비스 운영 시작일 설정이 누락되면 애플리케이션이 기동하지 않아야 한다.
- 테스트에서는 명시적인 고정값을 사용한다.
- 요청일이 서비스 운영 시작일보다 이전이면 `BEFORE_SERVICE_START`, `report = null`을 반환한다.
- 서비스 운영 시작일 당일은 시작 전이 아니며, 활성 리비전 또는 배치 상태에 따라 판정한다.
- 모든 응답에는 `serviceStartDate`를 포함해 프론트엔드가 조회 가능 시작일을 안내할 수 있게 한다.
- 요청일이 서비스 운영 시작일 이상이고 활성 리비전이 있으면 `PUBLISHED`와 해당 리비전 기반 리포트를 반환한다.
- 요청일에 활성 리비전이 있으면 같은 날짜의 배치 상태가 `FAILED`, `DELAYED`, `RETRYING` 등이어도 `PUBLISHED`를 우선한다.
- 요청일에 활성 리비전이 없고 `batch_job_run.status = 'SKIPPED_MARKET_CLOSED'`이면 `MARKET_CLOSED`, `report = null`을 반환한다.
- 요청일에 활성 리비전이 없고 그 외 배치 상태가 있거나 배치 행이 없으면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 현재 스키마에서 `batch_job_run`은 거래일별 현재 배치 상태 1건만 표현하므로, 휴장 판정은 해당 `report_date`의 단일 상태값만 사용한다.
- 과거 조회 API에서는 `RUNNING`, `RETRYING`, `DELAYED`, `FAILED` 같은 내부 배치 진행 상태를 사용자 공개 상태로 세분화하지 않는다.
- 과거 조회 API에는 `reason`, `batchStatus`, `internalStatus` 같은 내부 원인 필드를 추가하지 않는다.
- 과거 조회 API는 최신 조회 API와 달리 직전 활성 리포트 fallback을 반환하지 않는다.
- 사용자에게 노출할 리비전은 `report_revision.is_active = true`인 리비전 1건으로 한정한다.
- 비활성 리비전은 개발 추적과 복구를 위해 보존되지만 이 API에서는 반환하지 않는다.
- 선택된 활성 리비전의 `calculation_version`을 이후 신호 집계의 내부 조회 기준으로 고정한다.
- Spring API는 금융 지표, 신호, 업종 통계를 새로 계산하지 않고 저장된 데이터만 조회한다.
- 시장 지수 데이터가 일부 누락되어도 활성 리비전이 있으면 `PUBLISHED`를 유지하고 조회된 지수만 `marketIndices`에 포함한다.
- 골든크로스 집계는 저장된 신호 조회 결과의 단순 카운트로 보고, 데이터 부재와 실제 0건을 API 상태로 구분하지 않는다.
- 시장 AI 요약은 거래일별 1건으로 조회하되, 현재 활성 리비전과 기준이 맞을 때만 완료 요약으로 취급한다.
- `market_ai_summary`가 없거나 `market_ai_summary.report_revision_id != activeRevision.id`이면 `aiSummary.status = 'PENDING'`, `summaryText = null`로 반환한다.
- `market_ai_summary.report_revision_id = activeRevision.id`이면 저장된 AI 상태 enum과 요약 내용을 그대로 반환한다.
- 기존 최신 조회 API의 경로, 응답 필드, fallback 정책은 변경하지 않는다.
- 기존 DTO 파일명은 변경하지 않고 과거 조회 응답 DTO와 enum만 의미가 드러나게 추가한다.
- REST Docs 스니펫은 `PUBLISHED`, `MARKET_CLOSED`, `BEFORE_SERVICE_START`, `NOT_PUBLISHED` 대표 응답으로 생성한다.
- REST Docs HTML 조립, 목차 구성, 배포 문서는 이번 범위에서 제외한다.

## 4. 승인된 변경 범위

이번 계획에서 승인된 변경은 다음으로 한정한다.

- 필수 설정 프로퍼티 `stock-report.service-start-date` 추가
- 신규 공개 API `GET /api/reports/close?tradeDate=YYYY-MM-DD` 추가
- 과거 조회 전용 표시 상태 enum 추가
  - `PUBLISHED`
  - `MARKET_CLOSED`
  - `NOT_PUBLISHED`
  - `BEFORE_SERVICE_START`
- 과거 조회 전용 응답 DTO 추가
- 기존 최신 조회 API와 공유 가능한 리포트 본문 조립 로직 정리
- 과거 조회 API 통합 테스트 추가
- 과거 조회 API REST Docs 스니펫 생성 테스트 추가

서비스 운영 시작일은 API의 공개 동작을 결정하는 운영 설정이다. 구현 시 운영/로컬/테스트 설정 파일 중 필요한 위치에 명시 값을 추가하되, 설정 누락을 조용히 기본값으로 대체하지 않는다.

## 5. 응답 모델

응답 DTO는 다음 구조를 기준으로 한다.

```json
{
  "status": "PUBLISHED",
  "tradeDate": "2026-07-08",
  "serviceStartDate": "2026-07-01",
  "report": {
    "reportDate": "2026-07-08",
    "revisionNo": 2,
    "revisionType": "FINAL",
    "calculationVersion": "stoch-macd-v1",
    "publishedAt": "2026-07-08T19:15:00+09:00",
    "analysisUniverse": {
      "market": "KRX",
      "selectionRule": "종가 1,000원 이상 종목 중 거래량 상위 200개",
      "targetStockCount": 200
    },
    "marketIndices": [
      {
        "indexCode": "KOSPI",
        "tradeDate": "2026-07-08",
        "openPrice": 0,
        "highPrice": 0,
        "lowPrice": 0,
        "closePrice": 0,
        "volume": 0,
        "changeRate": 0
      }
    ],
    "scannerStats": {
      "targetStockCount": 200,
      "completedStockCount": 190,
      "failedStockCount": 3,
      "insufficientStockCount": 5,
      "noTradingStockCount": 2,
      "goldenCrossStockCount": 12
    },
    "aiSummary": {
      "status": "COMPLETED",
      "summaryText": "..."
    }
  }
}
```

리포트가 없는 상태의 응답은 다음 구조를 기준으로 한다.

```json
{
  "status": "BEFORE_SERVICE_START",
  "tradeDate": "2026-06-28",
  "serviceStartDate": "2026-07-01",
  "report": null
}
```

상태별 의미는 다음과 같다.

- `PUBLISHED`: 요청일의 활성 리비전이 있어 리포트를 반환한다.
- `MARKET_CLOSED`: 요청일이 휴장일로 처리되어 리포트가 없다.
- `NOT_PUBLISHED`: 서비스 시작일 이후 날짜이지만 사용자에게 제공할 활성 리비전이 없다.
- `BEFORE_SERVICE_START`: 요청일이 서비스 운영 시작일 이전이라 리포트를 반환하지 않는다.

`serviceStartDate`는 모든 상태에서 포함한다. 프론트엔드는 `BEFORE_SERVICE_START` 응답을 받으면 이 값을 기준으로 조회 가능 시작일을 안내할 수 있다.

## 6. 조회 흐름

1. Controller가 query parameter `tradeDate`를 `LocalDate`로 바인딩한다.
2. Service가 설정 프로퍼티에서 서비스 운영 시작일을 읽는다.
3. `tradeDate < serviceStartDate`이면 `BEFORE_SERVICE_START`, `report = null`로 응답한다.
4. `report_revision`에서 `report_date = tradeDate and is_active = true` 리비전을 조회한다.
5. 활성 리비전이 있으면 `PUBLISHED` 상태로 선택한다.
6. 활성 리비전이 없으면 `batch_job_run`의 요청일 상태를 조회한다.
7. 배치 상태가 `SKIPPED_MARKET_CLOSED`이면 `MARKET_CLOSED`로 매핑한다.
8. 배치 상태가 `RUNNING`, `RETRYING`, `DELAYED`, `FAILED`, 기타 값, 또는 배치 행 없음이면 `NOT_PUBLISHED`로 매핑한다.
9. 선택된 리비전이 없으면 `report = null`로 응답한다.
10. 선택된 리비전이 있으면 기존 최신 리포트 API와 동일한 리포트 본문 조립 로직을 재사용한다.
11. 선택 리비전의 `calculation_version`으로 골든크로스 종목 수를 집계한다.
12. 선택 리비전의 `report_date` 기준 KOSPI, KOSDAQ `market_index_price`를 조회한다.
13. 선택 리비전의 `report_date` 기준 `market_ai_summary`를 조회한다.
14. 조회된 AI 요약의 `report_revision_id`가 선택 리비전의 `id`와 같으면 저장된 AI 상태와 내용을 반환한다.
15. AI 요약이 없거나 `report_revision_id`가 다르면 `PENDING`, `summaryText = null`을 반환한다.
16. DTO로 조립해 반환한다.

## 7. 수정할 파일

### `server/src/main/resources/application.yml`

- `stock-report.service-start-date` 설정을 추가한다.
- 운영 기준값은 `2026-07-01`을 사용한다.
- 설정 누락을 숨기는 기본값을 코드에 두지 않는다.

### `server/src/main/resources/application-test.yml`

- 테스트에서 사용할 `stock-report.service-start-date` 값을 추가한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportController.kt`

- 기존 `GET /api/reports/latest-close`는 유지한다.
- `GET /api/reports/close?tradeDate=YYYY-MM-DD` 엔드포인트를 추가한다.
- Controller는 날짜 query parameter를 Service에 전달하고 DTO를 반환한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportService.kt`

- 기존 최신 조회 정책은 변경하지 않는다.
- 리포트 DTO 조립 로직을 과거 조회 API에서도 재사용할 수 있게 private 함수 또는 별도 컴포넌트로 분리한다.
- 최신 조회의 fallback 정책과 과거 조회의 no fallback 정책이 섞이지 않도록 메서드를 분리한다.
- 서비스 운영 시작일 설정을 주입받아 과거 조회 상태 판정에 사용한다.
- AI 요약은 거래일별로 조회한 뒤 선택 리비전과 기준이 일치하는지 검증한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportRepository.kt`

- 기존 `findActiveRevisionByReportDate`, `findBatchStatusByReportDate`, `findMarketIndices`, `countGoldenCrossStocks` 조회를 재사용한다.
- AI 요약 조회는 거래일 기준 조회를 기본으로 하고, Service에서 선택 리비전과의 일치 여부를 판단할 수 있게 `report_revision_id`를 포함해 반환한다.
- 필요하면 메서드 이름을 최신 전용 의미가 아닌 리포트 조회 공통 의미로 정리한다.
- 새 테이블 조회나 금융 계산 쿼리는 추가하지 않는다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportDto.kt`

- 과거 조회 응답 DTO를 추가한다.
- 과거 조회 전용 상태 enum을 추가한다.
- 과거 조회 응답에는 요청일 `tradeDate`와 조회 가능 시작일 `serviceStartDate`를 포함한다.
- 기존 최신 조회 응답 DTO는 호환성을 유지한다.
- 공통 리포트 본문 DTO는 기존 이름을 변경하지 않고 공유할 수 있다.

### `server/src/test/kotlin/com/stockreport/report/LatestCloseReportApiTests.kt`

- 과거 조회 API 통합 테스트를 추가한다.
- 기존 최신 조회 API 테스트 의미를 축소하지 않는다.

### `server/src/test/kotlin/com/stockreport/report/LatestCloseReportRestDocsTests.kt`

- 과거 조회 API REST Docs 스니펫 생성 테스트를 추가한다.
- 기존 최신 조회 API 스니펫 생성 테스트는 유지한다.

## 8. 변경 금지 범위

- Flyway 마이그레이션 추가 또는 기존 DB 스키마 변경
- Python worker 코드 변경
- 프론트엔드 코드 변경
- 최신 조회 API의 응답 계약 변경
- 최신 조회 API의 fallback 정책 변경
- 과거 조회 API에서 직전 활성 리포트 fallback 반환
- 비활성 리비전 사용자 노출
- 서비스 시작일 이전 리포트 소급 생성 또는 노출
- 서비스 운영 시작일을 가장 이른 활성 리비전 날짜로 대체
- 금융 지표, 신호, 업종 통계 계산 로직 추가
- AI 요약 생성 또는 재시도 로직 구현
- `market_ai_summary`를 리비전별 사용자 기능으로 변경
- 인증, 권한, CORS 정책 추가
- 신규 외부 의존성 추가
- Asciidoctor 플러그인, HTML 문서 생성 태스크, `index.adoc` 추가

## 9. 테스트 범위

다음 통합 테스트를 추가한다.

- 서비스 시작일 이전 날짜를 요청하면 `BEFORE_SERVICE_START`, `report = null`을 반환한다.
- 서비스 시작일 이전 날짜에 활성 리비전이 있어도 `BEFORE_SERVICE_START`, `report = null`을 반환한다.
- 요청일 활성 리비전이 있으면 `PUBLISHED`와 요청일 리포트를 반환한다.
- 요청일에 여러 리비전이 있고 최종 리비전만 활성 상태이면 활성 리비전만 반환한다.
- 요청일 활성 리비전의 `calculationVersion`이 응답에 포함된다.
- KOSPI, KOSDAQ 지수 요약이 요청일 활성 리비전의 `reportDate` 기준으로 반환된다.
- 스캐너 통계가 요청일 활성 리비전의 커버리지 집계와 해당 계산 버전의 골든크로스 종목 수를 반환한다.
- AI 요약이 있고 활성 리비전과 기준이 같으면 상태와 내용을 반환한다.
- AI 요약이 없으면 `PENDING`과 `summaryText = null`을 반환한다.
- AI 요약이 같은 거래일의 비활성 리비전을 참조하면 `PENDING`과 `summaryText = null`을 반환한다.
- 요청일 활성 리비전이 없고 `SKIPPED_MARKET_CLOSED`이면 `MARKET_CLOSED`, `report = null`을 반환한다.
- 요청일 활성 리비전이 없고 `RUNNING`이면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 요청일 활성 리비전이 없고 `RETRYING`이면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 요청일 활성 리비전이 없고 `DELAYED`이면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 요청일 활성 리비전이 없고 `FAILED`이면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 요청일 활성 리비전이 없고 배치 행도 없으면 `NOT_PUBLISHED`, `report = null`을 반환한다.
- 과거 조회 API는 직전 활성 리포트를 fallback으로 반환하지 않는다.
- `tradeDate`가 누락된 요청은 HTTP 400으로 처리된다.
- 잘못된 날짜 형식이면 HTTP 400을 반환한다.
- 서비스 운영 시작일 설정이 누락되면 애플리케이션 기동이 실패한다.
- `PUBLISHED` 상태 응답에서 REST Docs 스니펫이 생성된다.
- `MARKET_CLOSED` 상태 응답에서 REST Docs 스니펫이 생성된다.
- `BEFORE_SERVICE_START` 상태 응답에서 REST Docs 스니펫이 생성된다.
- `NOT_PUBLISHED` 상태 응답에서 REST Docs 스니펫이 생성된다.
- REST Docs 응답 필드 문서화가 실제 JSON 응답과 일치한다.
- 문서화되지 않은 응답 필드가 있으면 REST Docs 테스트가 실패한다.

검증 명령:

```bash
cd server
./gradlew test
```

테스트 실행 후 다음 경로에 스니펫이 생성되어야 한다.

```text
server/build/generated-snippets/reports/close/published
server/build/generated-snippets/reports/close/market-closed
server/build/generated-snippets/reports/close/before-service-start
server/build/generated-snippets/reports/close/not-published
```

## 10. 구현 완료 조건

- [x] `GET /api/reports/close?tradeDate=YYYY-MM-DD`가 HTTP 200 JSON 응답을 반환한다.
- [x] 모든 정상 응답은 `tradeDate`와 `serviceStartDate`를 포함한다.
- [x] `tradeDate`가 누락된 요청은 HTTP 400으로 처리된다.
- [x] 잘못된 날짜 형식 요청은 HTTP 400으로 처리된다.
- [x] 서비스 시작일 이전 날짜는 리포트 데이터 존재 여부와 무관하게 `BEFORE_SERVICE_START`, `report = null`로 응답한다.
- [x] 서비스 시작일 이후 요청일의 활성 리비전이 있으면 해당 리비전 기준 리포트 본문을 반환한다.
- [x] 과거 조회 API는 직전 활성 리포트 fallback을 반환하지 않는다.
- [x] 휴장일, 공개 전, 서비스 시작 전 상태를 프론트엔드가 구분할 수 있다.
- [x] 내부 배치 진행 상태는 과거 조회 API의 공개 상태로 세분화되지 않는다.
- [x] 선택 리비전의 `calculationVersion`으로 골든크로스 집계를 고정한다.
- [x] 시장 AI 요약은 거래일별 1건으로 조회하되, 선택 리비전과 기준이 맞을 때만 완료 요약으로 반환한다.
- [x] Spring API는 저장된 분석 결과를 조회만 하며 금융 계산을 수행하지 않는다.
- [x] 신규 통합 테스트가 통과한다.
- [x] 신규 REST Docs 테스트가 통과한다.
- [x] 기존 최신 조회 API 테스트가 통과한다.

## 11. 리스크와 확인 사항

- 서비스 운영 시작일 값은 `2026-07-01`로 확정되었으므로, 구현과 배포 설정에서 동일한 값을 사용해야 한다.
- `stock-report.service-start-date`는 운영 설정이므로 배포 환경에서도 값이 누락되지 않게 관리해야 한다.
- `NOT_PUBLISHED`는 배치 실행 중, 재시도 중, 생성 지연, 실패, 배치 미실행을 하나의 과거 조회 상태로 묶는다. 이는 과거 조회에서 내부 배치 상태를 공개 API 계약으로 노출하지 않기 위한 의도적 결정이다.
- REST Docs HTML 문서 구조는 아직 확정하지 않는다. 서버 API가 더 쌓인 뒤 Asciidoctor 플러그인, 문서 목차, 공통 응답 형식, 배포 위치를 별도 계획으로 정한다.
