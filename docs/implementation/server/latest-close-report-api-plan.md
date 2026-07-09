# 최신 장 마감 리포트 조회 API 구현 계획

상태: 계획

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 15번 이슈

원격 이슈: https://github.com/sehako/stock-report/issues/4

기준 조사 문서: `docs/research/server/latest-close-report-api-research.md`

## 1. 목적

사용자 기본 진입 화면에서 사용할 최신 장 마감 리포트 조회 API를 제공한다.

이 API는 게시 완료된 최신 활성 리비전을 기준으로 리포트 기준 거래일, 분석 범위, 계산 버전, 시장 지수 요약, 분석 종목 기준 스캐너 통계, 시장 AI 요약 상태와 내용을 함께 반환한다. 당일 리포트가 아직 공개되지 않았거나 생성 지연 상태인 경우 프론트엔드가 사용자 표시 상태를 구분할 수 있게 한다.

## 2. 기준 문서

- `docs/proposal/stock-report-mvp-issue-breakdown.md`
- `docs/research/server/latest-close-report-api-research.md`
- `docs/implementation/server/backend-scaffold-plan.md`
- `docs/implementation/server/server-data-model-flyway-plan.md`
- `docs/adr/0002-share-database-with-single-schema-owner.md`
- `docs/adr/0003-version-published-report-results.md`
- `CONTEXT.md`

## 3. 결정 사항

- API 경로는 `GET /api/reports/latest-close`로 둔다.
- 서버 기준 오늘은 `Asia/Seoul` 날짜로 계산한다.
- 기본 조회 기준 리비전은 `report_revision.is_active = true`인 행 중 `report_date`가 가장 큰 리비전이다.
- 당일 활성 리비전이 있으면 당일 리비전을 반환하고 표시 상태는 `PUBLISHED`로 둔다.
- 당일 활성 리비전이 없고 당일 `batch_job_run.status = 'DELAYED'`이면 직전 최신 활성 리비전을 fallback 리포트로 반환하고 표시 상태는 `DELAYED`로 둔다.
- 당일 활성 리비전이 없고 당일 `batch_job_run.status = 'FAILED'`이면 직전 최신 활성 리비전을 fallback 리포트로 반환하고 표시 상태는 `DELAYED`로 둔다. 사용자 화면에는 내부 배치 상태 `FAILED`를 별도 공개 상태로 노출하지 않는다.
- 당일 활성 리비전이 없고 당일 `batch_job_run.status = 'RUNNING'` 또는 `RETRYING`이면 직전 최신 활성 리비전을 함께 반환하고 표시 상태는 `PREPARING`으로 둔다.
- 당일 활성 리비전이 없고 당일 `batch_job_run.status = 'SKIPPED_MARKET_CLOSED'`이면 직전 최신 활성 리비전을 함께 반환하고 표시 상태는 `MARKET_CLOSED`로 둔다.
- 당일 활성 리비전이 없고 당일 배치 행이 없으면 직전 최신 활성 리비전을 함께 반환하고 표시 상태는 `NOT_PUBLISHED`로 둔다.
- 활성 리비전이 전혀 없으면 HTTP 200으로 리포트 본문 없이 표시 상태만 반환한다.
- 조회 API는 금융 지표를 새로 계산하지 않는다. 저장된 리비전, 지수, 분석 상태, 신호 참조를 단순 조회 또는 집계한다.
- 스캐너 통계는 `report_revision`의 커버리지 집계와 `stock_analysis`/`signal_event` 기반 골든크로스 종목 수만 포함한다.
- 상승 종목 수, 하락 종목 수, 평균 등락률은 15번 API에서 제외한다. 이 통계가 필요하면 Python worker가 리비전 단위로 저장하는 별도 이슈로 다룬다.
- KOSPI, KOSDAQ 지수 요약은 선택된 리비전의 `report_date`와 `market_index_price.index_code`로 조회한다.
- 시장 AI 요약은 선택된 리비전의 `report_date`와 `report_revision_id`로 조회한다.
- AI 요약이 없으면 `aiSummary.status = 'PENDING'`, `summaryText = null`로 응답한다.
- 최종 리비전 교체 후 AI 요약은 worker가 같은 거래일의 `market_ai_summary`를 새 활성 리비전 기준으로 갱신하는 계약으로 둔다. API는 최신 활성 리비전과 AI 요약 참조 리비전이 어긋난 상태를 임의로 보정하지 않는다.
- Spring REST Docs로 `GET /api/reports/latest-close` 응답 계약 스니펫을 생성한다.
- REST Docs 산출물은 이번 단계에서 `build/generated-snippets` 아래 스니펫까지만 생성한다.
- Asciidoctor 플러그인, `index.adoc`, HTML 문서 생성 태스크는 이번 범위에서 제외한다.
- 대표 REST Docs 스니펫은 `PUBLISHED`와 `EMPTY` 응답으로 생성한다.
- 상태별 정책 전체는 REST Docs 예시를 모두 만들기보다 `status` 필드 설명에 enum 의미를 명시한다.
- 요청 파라미터, path variable, request body는 없는 것으로 문서화한다.

## 4. 승인 필요 사항

구현 전에 다음 변경을 승인해야 한다.

- `server/build.gradle.kts`에 `spring-boot-starter-web` 의존성을 추가한다.
- `server/build.gradle.kts`에 `testImplementation("org.springframework.restdocs:spring-restdocs-mockmvc")` 의존성을 추가한다.

이 변경은 HTTP Controller, MockMvc 기반 테스트, REST Docs 스니펫 생성을 위해 필요하다. 외부 의존성 변경이므로 사용자 승인 없이 구현하지 않는다.

## 5. 응답 모델

응답 DTO는 다음 구조를 기준으로 한다.

```json
{
  "status": "PUBLISHED",
  "asOfDate": "2026-07-09",
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

`status` 값은 API 표시 상태이며 DB 상태값을 그대로 노출하지 않는다.

- `PUBLISHED`: 당일 활성 리비전 공개 완료
- `DELAYED`: 당일 핵심 데이터 문제로 생성 지연, 직전 활성 리포트 반환 가능
- `PREPARING`: 당일 배치 실행 또는 재시도 중, 직전 활성 리포트 반환 가능
- `MARKET_CLOSED`: 당일 휴장, 직전 활성 리포트 반환 가능
- `NOT_PUBLISHED`: 당일 리포트 공개 전 또는 배치 미실행, 직전 활성 리포트 반환 가능
- `EMPTY`: 활성 리포트가 전혀 없음

## 6. 조회 흐름

1. `Clock` 빈을 통해 `Asia/Seoul` 기준 오늘 날짜를 구한다.
2. 오늘 날짜의 활성 `report_revision`을 조회한다.
3. 오늘 활성 리비전이 있으면 선택 리비전으로 사용한다.
4. 오늘 활성 리비전이 없으면 오늘 날짜의 `batch_job_run`을 조회해 표시 상태를 결정한다.
5. 오늘 배치 상태가 `FAILED`이면 사용자 표시 상태는 `DELAYED`로 매핑한다.
6. fallback이 필요한 상태에서는 `is_active = true`인 최신 활성 리비전을 조회한다.
7. 선택 리비전이 없으면 `status = EMPTY`, `report = null`로 응답한다.
8. 선택 리비전의 `calculation_version`을 이후 조회 기준으로 유지한다.
9. 선택 리비전의 `report_date` 기준 KOSPI, KOSDAQ `market_index_price`를 조회한다.
10. 선택 리비전의 `report_revision_id` 기준 `stock_analysis` 상태와 `signal_event_id` 존재 건수를 집계한다.
11. 선택 리비전의 `report_date`, `report_revision_id` 기준 `market_ai_summary`를 조회한다.
12. DTO로 조립해 반환한다.

## 7. 수정할 파일

### `server/build.gradle.kts`

- `spring-boot-starter-web` 의존성을 추가한다.
- `spring-restdocs-mockmvc` 테스트 의존성을 추가한다.
- Asciidoctor 관련 플러그인이나 태스크는 추가하지 않는다.
- 이 변경은 승인 필요 사항이다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportController.kt`

- `GET /api/reports/latest-close` 엔드포인트를 추가한다.
- Controller는 요청 파라미터 없이 Service를 호출하고 DTO를 반환한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportService.kt`

- 최신 장 마감 리포트 선택 정책을 구현한다.
- 당일 배치 상태와 활성 리비전 존재 여부를 조합해 API 표시 상태를 결정한다.
- Repository 조회 결과를 응답 DTO로 조립한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportRepository.kt`

- 조회 전용 JDBC 기반 Repository를 추가한다.
- 현재 서버에는 Entity 패턴이 없고 이 API는 여러 테이블의 읽기 조합이므로 JPA Entity를 새로 만들지 않는다.
- `NamedParameterJdbcTemplate` 또는 `JdbcTemplate`으로 필요한 행과 집계를 조회한다.

### `server/src/main/kotlin/com/stockreport/report/LatestCloseReportDto.kt`

- API 응답 DTO와 내부 표시 상태 enum을 정의한다.
- DB 상태 enum과 API 표시 상태 enum을 분리한다.

### `server/src/main/kotlin/com/stockreport/config/TimeConfig.kt`

- `Clock.system(ZoneId.of("Asia/Seoul"))` 빈을 추가한다.
- 테스트에서 날짜를 고정할 수 있게 한다.

### `server/src/test/kotlin/com/stockreport/report/LatestCloseReportApiTests.kt`

- Testcontainers PostgreSQL과 MockMvc 기반 API 통합 테스트를 추가한다.
- 테스트 fixture는 SQL insert helper로 구성한다.

### `server/src/test/kotlin/com/stockreport/report/LatestCloseReportRestDocsTests.kt`

- REST Docs 스니펫 생성 전용 테스트를 추가한다.
- 기존 정책 검증용 `LatestCloseReportApiTests`와 문서 계약 테스트를 분리한다.
- `MockMvc`에 REST Docs 설정을 적용한다.
- Testcontainers PostgreSQL을 사용해 실제 스키마 기반 fixture를 구성한다.
- `PUBLISHED` 응답 스니펫을 `reports/latest-close/published` 이름으로 생성한다.
- `EMPTY` 응답 스니펫을 `reports/latest-close/empty` 이름으로 생성한다.
- 응답 필드는 현재 구현된 DTO 기준으로 모두 문서화한다.

## 8. 변경 금지 범위

- Flyway 마이그레이션 추가 또는 기존 스키마 변경
- API 경로 외 추가 API 구현
- Python worker 코드 변경
- 프론트엔드 코드 변경
- 금융 지표, 신호, 업종 통계 계산 로직 추가
- AI 요약 생성 또는 재시도 로직 구현
- 인증, 권한, CORS 정책 추가
- DB enum 도입 또는 상태값 스키마 변경
- Asciidoctor 플러그인 추가
- HTML 문서 생성 태스크 추가
- `index.adoc` 또는 API 문서 목차 작성
- `docs/api` 등으로 REST Docs 스니펫을 복사하는 빌드 태스크 추가
- 기존 정책 테스트의 의미 축소

## 9. 테스트 범위

다음 통합 테스트를 추가한다.

- 당일 활성 리비전이 있으면 `PUBLISHED`와 당일 리포트를 반환한다.
- 당일 `DELAYED`이고 당일 활성 리비전이 없으면 `DELAYED`와 직전 활성 리포트를 반환한다.
- 당일 `FAILED`이고 당일 활성 리비전이 없으면 사용자 표시 상태 `DELAYED`와 직전 활성 리포트를 반환한다.
- 당일 `RUNNING` 또는 `RETRYING`이고 당일 활성 리비전이 없으면 `PREPARING`과 직전 활성 리포트를 반환한다.
- 당일 `SKIPPED_MARKET_CLOSED`이면 `MARKET_CLOSED`와 직전 활성 리포트를 반환한다.
- 당일 배치 행이 없고 당일 활성 리비전이 없으면 `NOT_PUBLISHED`와 직전 활성 리포트를 반환한다.
- 활성 리비전이 전혀 없으면 `EMPTY`와 `report = null`을 반환한다.
- 최신 활성 리비전의 `calculationVersion`이 응답에 포함된다.
- KOSPI, KOSDAQ 지수 요약이 선택 리비전의 `reportDate` 기준으로 반환된다.
- 스캐너 통계가 리비전 커버리지 집계와 골든크로스 종목 수를 반환한다.
- AI 요약이 있으면 상태와 내용을 반환한다.
- AI 요약이 없으면 `PENDING`과 `summaryText = null`을 반환한다.
- `PUBLISHED` 상태 응답에서 REST Docs 스니펫이 생성된다.
- `EMPTY` 상태 응답에서 `report = null` 계약이 REST Docs 스니펫으로 생성된다.
- REST Docs 응답 필드 문서화가 실제 JSON 응답과 일치한다.
- 문서화되지 않은 응답 필드가 있으면 REST Docs 테스트가 실패한다.

검증 명령:

```bash
cd server
./gradlew test
```

테스트 실행 후 다음 경로에 스니펫이 생성되어야 한다.

```text
server/build/generated-snippets/reports/latest-close/published
server/build/generated-snippets/reports/latest-close/empty
```

## 10. 구현 완료 조건

- `GET /api/reports/latest-close`가 HTTP 200 JSON 응답을 반환한다.
- 응답은 최신 활성 리비전 또는 정책상 fallback 리비전을 기준으로 일관된 `reportDate`, `calculationVersion`, 지수 통계, 스캐너 통계, AI 요약을 포함한다.
- 당일 미공개, 생성 지연, 준비 중, 휴장, 데이터 없음 상태를 프론트엔드가 구분할 수 있다.
- Spring API는 저장된 분석 결과를 조회만 하며 금융 계산을 수행하지 않는다.
- `GET /api/reports/latest-close`의 `PUBLISHED` 응답 REST Docs 스니펫이 생성된다.
- `GET /api/reports/latest-close`의 `EMPTY` 응답 REST Docs 스니펫이 생성된다.
- REST Docs 응답 필드 문서화가 현재 DTO와 일치한다.
- Asciidoctor HTML 생성 관련 설정은 추가되지 않는다.
- 신규 통합 테스트가 통과한다.
- 신규 REST Docs 테스트가 통과한다.
- 기존 테스트가 통과한다.

## 11. 리스크와 확인 사항

- 웹 의존성 추가가 승인되지 않으면 HTTP API 구현을 진행할 수 없다.
- 현재 `market_ai_summary`는 거래일별 unique 구조이므로 같은 거래일의 최종 리비전 교체 후 worker가 `report_revision_id`를 갱신해야 API가 최신 리비전 기준 AI 요약을 찾을 수 있다.
- 최종 리비전 교체 시 worker는 같은 거래일의 AI 요약을 새 활성 리비전 기준으로 갱신해야 한다. 기존 요약이 새 입력 기준이 아니면 완료 요약으로 재사용하지 않고 재생성 대기 상태로 전환해야 한다.
- 당일 미공개 상태에서도 직전 활성 리포트를 반환하는 정책은 프론트엔드가 기준 거래일을 명확히 표시한다는 전제에 의존한다.
- 스캐너 통계는 MVP 범위에서 새 금융 의미를 만들지 않도록 제한한다. 상승 종목 수, 하락 종목 수, 평균 등락률은 이번 API에 포함하지 않는다.
- REST Docs HTML 문서 구조는 아직 확정하지 않는다. 서버 API가 더 쌓인 뒤 Asciidoctor 플러그인, 문서 목차, 공통 응답 형식, 배포 위치를 별도 계획으로 정한다.
