# 최신 장 마감 리포트 조회 API 서버 코드베이스 조사

상태: 조사 완료

대상 이슈: `docs/proposal/stock-report-mvp-issue-breakdown.md`의 15번 이슈

## 1. 조사 목적

최신 장 마감 리포트 조회 API 구현 전에 현재 서버 코드베이스, 데이터 모델, 테스트 기반, 구현 시 결정해야 할 경계를 확인한다.

이번 조사는 서버 코드 구조와 기존 스키마 파악에 한정한다. 애플리케이션 코드는 수정하지 않았다.

## 2. 15번 이슈 요구사항

15번 이슈는 최신 장 마감 리포트 조회 API를 제공하는 것이다.

요구사항은 다음과 같다.

- 기본 조회는 최신 활성 리비전을 반환한다.
- 리포트 기준 거래일과 분석 범위를 함께 제공한다.
- 리포트가 참조하는 계산 버전을 내부 조회 기준으로 고정한다.
- 시장 개요에서 사용할 KOSPI, KOSDAQ 지수 통계와 분석 종목 기준 스캐너 통계를 함께 제공한다.
- 시장 전체 AI 요약 상태와 내용을 함께 제공한다.
- 당일 장 마감 리포트가 아직 공개되지 않은 경우 사용자에게 표시할 상태를 구분할 수 있게 한다.
- 당일 장 마감 리포트가 생성 지연 상태이면 직전 활성 리포트와 생성 지연 상태를 함께 제공한다.

근거: `docs/proposal/stock-report-mvp-issue-breakdown.md` 149-156행.

## 3. 현재 서버 구조

서버는 Kotlin, Spring Boot, JPA, Flyway 기반이다.

- 패키지 루트: `com.stockreport`
- 현재 애플리케이션 코드는 Spring Boot 진입점만 존재한다.
- Controller, Service, Repository, Entity, DTO 패키지는 아직 없다.
- Flyway 마이그레이션은 `V1__initial_schema.sql` 한 개가 존재한다.
- 테스트는 Testcontainers PostgreSQL 기반의 컨텍스트 로딩과 DB 제약 검증 중심이다.

확인 파일:

- `server/src/main/kotlin/com/stockreport/StockReportApplication.kt`
- `server/src/main/resources/db/migration/V1__initial_schema.sql`
- `server/src/test/kotlin/com/stockreport/StockReportApplicationTests.kt`

## 4. 빌드와 의존성 상태

현재 주요 의존성은 다음과 같다.

- `spring-boot-starter`
- `spring-boot-starter-data-jpa`
- `spring-boot-starter-flyway`
- PostgreSQL 드라이버
- Testcontainers PostgreSQL

근거: `server/build.gradle.kts` 25-39행.

주의할 점:

- 조회 HTTP API 구현에 필요한 `spring-boot-starter-web` 또는 동등한 웹 의존성이 현재 없다.
- API 구현 계획에는 웹 의존성 추가 여부가 명시되어야 한다.
- 외부 의존성 추가는 프로젝트 지침상 사용자 승인 대상이다.

## 5. 데이터 모델 조사

### 5.1 리포트 리비전

`report_revision`은 최신 활성 리비전 조회의 중심 테이블이다.

주요 컬럼:

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

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 13-40행.

15번 API에서는 `is_active = true`인 리비전 중 `report_date`가 가장 큰 행을 최신 활성 리비전으로 해석할 수 있다. 이 리비전의 `calculation_version`을 이후 지표, 신호 조회 기준으로 고정해야 한다.

### 5.2 배치 실행 상태

`batch_job_run`은 거래일별 배치 공개 상태를 담는다.

상태값:

- `RUNNING`
- `PUBLISHED_INITIAL`
- `RETRYING`
- `PUBLISHED_FINAL`
- `FAILED`
- `DELAYED`
- `SKIPPED_MARKET_CLOSED`

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 42-67행.

15번 API의 표시 상태는 이 테이블과 활성 리비전 존재 여부를 함께 해석해야 한다.

예상 해석:

- 당일 활성 리비전 존재: 공개 완료
- 당일 활성 리비전 없음 + 당일 `DELAYED`: 생성 지연, 직전 활성 리포트 반환
- 당일 활성 리비전 없음 + 당일 `RUNNING` 또는 `RETRYING`: 공개 전 또는 생성 중
- 당일 `SKIPPED_MARKET_CLOSED`: 휴장일, 직전 활성 리포트 반환 가능
- 당일 배치 행 없음: 공개 전 또는 아직 배치 미실행
- 당일 활성 리비전 없음 + 당일 `FAILED`: 생성 지연, 직전 활성 리포트 반환

정확한 응답 상태 enum은 계획 단계에서 확정해야 한다.

`FAILED` 해석은 특히 주의해야 한다. 기준 아키텍처는 종목 목록 자체를 가져오지 못한 경우 당일 분석 대상을 정할 수 없으므로 전체 리포트를 생성 지연 상태로 두고 직전 리포트를 유지한다고 정한다. 반면 개별 종목 실패는 장 마감 리포트 전체 공개를 막지 않고 종목 상태로 격리해야 한다. 따라서 15번 API에서 `batch_job_run.status = 'FAILED'`는 사용자에게 별도 장애 상태로 노출하지 않고 생성 지연과 동일하게 매핑한다. 내부 배치 상태값은 운영 추적을 위해 `FAILED`로 유지한다.

### 5.3 시장 지수 통계

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

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 107-121행.

15번 API의 시장 개요 지수 통계는 최신 활성 리비전의 `report_date` 기준으로 KOSPI, KOSDAQ 행을 조회하면 된다. 지수 차트 시계열은 17번 이슈의 별도 API 범위이므로 15번에서는 요약 통계만 포함하는 것이 자연스럽다.

### 5.4 분석 종목 기준 스캐너 통계

스캐너 통계 후보 데이터는 `report_revision`, `stock_analysis`, `signal_event`, `daily_price`에 나뉘어 있다.

이미 저장된 집계:

- `target_stock_count`
- `completed_stock_count`
- `failed_stock_count`
- `insufficient_stock_count`
- `no_trading_stock_count`

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 20-24행.

리비전별 종목 상태와 스냅샷:

- `analysis_status`
- `selection_rank`
- `selection_volume`
- `current_price`
- `last_trade_date`
- `market_cap`
- `trade_value`

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 141-181행.

15번 API에서 제공할 수 있는 스캐너 통계:

- 분석 대상 종목 수
- 판정 완료 종목 수
- 실패 종목 수
- 데이터 부족 종목 수
- 당일 거래 없음 종목 수
- 골든크로스 발생 종목 수

주의할 점:

- 상승 종목 수, 하락 종목 수, 평균 등락률 같은 통계는 `stock_analysis`에 직접 저장되어 있지 않다.
- `stock_analysis.stock_id`, `stock_analysis.last_trade_date`, `daily_price.change_rate`를 조인하면 상승 종목 수, 하락 종목 수, 평균 등락률을 조회 시점에 산출할 수는 있다.
- 그러나 기준 아키텍처는 모든 가격 파생값, 기술지표, 신호, 순위와 업종 집계를 Python 결정론적 코드가 계산하고 Spring은 조회만 한다고 정한다.
- 따라서 15번 API에서는 Spring이 `daily_price`를 조인해 새로운 스캐너 통계를 산출하지 않는 것이 안전하다.
- 15번 API의 스캐너 통계는 이미 저장된 `report_revision` 커버리지 집계와 `stock_analysis.signal_event_id` 기반 단순 카운트처럼 리비전 결과를 설명하는 조회성 집계로 제한하는 것이 기준서와 가장 잘 맞는다.
- 상승 종목 수, 하락 종목 수, 평균 등락률이 시장 개요에 꼭 필요하다면 Python worker가 저장한 값을 조회하거나 별도 저장 구조를 먼저 승인해야 한다.

### 5.5 AI 시장 요약

`market_ai_summary`는 거래일별 AI 요약을 저장한다.

주요 컬럼:

- `report_date`
- `report_revision_id`
- `status`
- `summary_text`
- `input_hash`
- `error_message`

상태값:

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `DELAYED`

근거: `server/src/main/resources/db/migration/V1__initial_schema.sql` 208-222행.

15번 API에서는 최신 활성 리비전의 `report_date`와 `report_revision_id`로 AI 요약을 조회하는 것이 리비전 기준을 가장 명확하게 유지한다. 다만 현재 unique key는 `report_date` 단위라 같은 거래일의 최종 리비전 교체 후 AI 요약이 어떤 리비전을 참조하는지는 worker의 갱신 정책과 함께 확인해야 한다.

기준 아키텍처는 AI 요약을 거래일별 1건으로 유지하되 입력으로 사용한 리비전을 참조한다고 정한다. 따라서 최종 리비전이 기존 최초 리비전을 대체할 때 worker는 같은 `report_date`의 `market_ai_summary`를 새 활성 리비전 기준으로 갱신해야 한다. 이때 `report_revision_id`와 `input_hash`는 새 입력 기준으로 갱신하고, 기존 `summary_text`가 새 리비전 입력 기준이 아니면 비운 뒤 `PENDING` 또는 `RUNNING`으로 전환해 재생성한다. API는 거래일별 AI 요약 1건을 조회하되 최신 활성 리비전과 참조 리비전이 어긋난 요약을 최신 리포트의 완료 요약처럼 보정하지 않는다.

## 6. 기존 테스트 구조

현재 테스트는 다음을 검증한다.

- PostgreSQL Testcontainers로 Spring 컨텍스트가 로딩되는지 확인한다.
- Flyway가 초기 테이블을 생성하는지 확인한다.
- 주요 unique key, foreign key, check constraint가 동작하는지 확인한다.

근거: `server/src/test/kotlin/com/stockreport/StockReportApplicationTests.kt` 19-84행.

API 구현 시 추가가 필요한 테스트:

- 최신 활성 리비전이 반환되는지 검증하는 통합 테스트
- 당일 생성 지연 시 직전 활성 리포트와 지연 상태가 함께 반환되는지 검증하는 테스트
- 당일 활성 리비전이 없고 배치가 진행 중일 때 표시 상태가 구분되는지 검증하는 테스트
- AI 요약 상태가 응답에 포함되는지 검증하는 테스트
- KOSPI, KOSDAQ 지수 통계가 리포트 기준 거래일로 조회되는지 검증하는 테스트

현재 MockMvc 또는 WebTestClient 기반 테스트 의존성은 웹 스타터 추가 방식에 따라 결정해야 한다.

## 7. 구현 시 필요한 조회 흐름 후보

15번 API의 서버 내부 조회 흐름 후보는 다음과 같다.

1. 서버 기준 오늘 날짜를 Asia/Seoul 기준으로 계산한다.
2. 오늘 날짜의 `batch_job_run`을 조회해 당일 공개 상태 후보를 확인한다.
3. 오늘 날짜의 활성 `report_revision`이 있으면 이를 기준 리비전으로 선택한다.
4. 오늘 활성 리비전이 없고 당일 상태가 `DELAYED` 또는 `FAILED`이면 최신 활성 리비전 중 가장 최근 거래일을 fallback 리비전으로 선택한다.
5. 오늘 활성 리비전이 없고 당일 상태가 공개 전, 진행 중, 휴장일이면 상태와 fallback 리비전 반환 여부를 응답 정책에 따라 결정한다.
6. 선택된 리비전의 `report_date`, `revision_no`, `calculation_version`, 커버리지 집계를 응답에 포함한다.
7. 선택된 리비전의 `report_date` 기준으로 KOSPI, KOSDAQ `market_index_price`를 조회한다.
8. 선택된 리비전의 `id` 기준으로 `stock_analysis` 상태별 집계와 신호 수를 조회한다.
9. 선택된 리비전의 `report_date`와 `id` 기준으로 `market_ai_summary`를 조회한다.

## 8. 계획 단계에서 확정해야 할 사항

다음 항목은 조사만으로 확정하지 않았다.

- API URL과 응답 DTO 구조
- 공개 상태 enum 이름과 매핑 규칙
- 당일 휴장일 또는 배치 미실행 상태에서 직전 활성 리포트를 반환할지 여부
- 분석 범위 문구를 서버에서 고정 문자열로 내려줄지, 구조화된 조건으로 내려줄지 여부
- `spring-boot-starter-web` 추가 승인 여부
- JPA Entity/Repository 방식과 JdbcTemplate 방식 중 어느 패턴으로 첫 API 계층을 만들지 여부

## 9. 리스크와 주의사항

- 현재 서버에는 API 계층 패턴이 없어서 15번 구현이 서버 조회 API의 첫 기준이 된다.
- 웹 의존성이 없어 Controller 구현 전 의존성 추가 계획과 승인이 필요하다.
- `market_ai_summary`는 거래일별 unique 구조라 최종 리비전 교체 후 AI 요약 참조 리비전 갱신 정책이 중요하다.
- `batch_job_run` 상태와 `report_revision.is_active`를 함께 해석해야 하므로 상태 매핑 테스트가 필요하다.
- Spring은 금융 지표를 재계산하지 않는다는 아키텍처 기준을 지켜야 한다. 조회 시 단순 집계와 새 의미의 계산을 구분해야 한다.
- 특히 `daily_price.change_rate`를 Spring에서 조인해 상승 종목 수, 하락 종목 수, 평균 등락률을 계산하면 Python이 집계 책임을 가진다는 기준을 침범할 수 있다. 15번 API는 저장된 리비전 집계와 신호 참조 기반 단순 카운트로 제한하는 것이 안전하다.
- `batch_job_run.status = 'FAILED'`는 기준서의 리포트 공개 상태 축에 직접 대응하는 용어가 아니다. 15번 API에서는 생성 지연으로 매핑하지만, 운영 로그와 내부 상태에서는 원래 `FAILED`를 보존해야 한다.
- AI 요약은 거래일별 1건이지만 입력 리비전을 참조한다. 최종 리비전으로 활성 리비전이 교체된 뒤 worker가 AI 요약 참조를 갱신하지 않으면 최신 리비전과 AI 요약 입력 기준이 어긋날 수 있다.

## 10. 확정된 보완 결정

다음 항목은 검토 과정에서 확정했다.

1. `batch_job_run.status = 'FAILED'`는 15번 최신 리포트 API에서 사용자 표시 상태를 생성 지연으로 매핑하고 직전 활성 리포트를 반환한다. 사용자 화면에는 별도 `FAILED` 공개 상태를 노출하지 않는다.
2. 15번 API의 스캐너 통계는 `target_stock_count`, `completed_stock_count`, `failed_stock_count`, `insufficient_stock_count`, `no_trading_stock_count`, 골든크로스 종목 수로 제한한다. 상승 종목 수, 하락 종목 수, 평균 등락률은 제외한다.
3. 최종 리비전 교체 후 AI 요약은 worker가 같은 거래일의 `market_ai_summary`를 새 활성 리비전 기준으로 갱신하는 계약으로 둔다. API는 리비전 불일치 상태를 임의로 보정하지 않는다.

## 11. 결론

15번 API 구현에 필요한 핵심 테이블은 이미 존재한다. 반면 서버 애플리케이션 레이어는 아직 비어 있으므로 구현 계획에서는 웹 의존성 추가, 패키지 구조, 조회 방식, 응답 상태 모델, 통합 테스트 범위를 먼저 확정해야 한다.

가장 중요한 구현 기준은 최신 활성 리비전을 단순히 최신 적재 데이터로 대체하지 않는 것이다. API는 `report_revision.is_active = true`인 게시 완료 리비전을 기준으로 시장 지수, 스캐너 통계, AI 요약을 같은 기준 거래일과 리비전 안에서 묶어 반환해야 한다.
