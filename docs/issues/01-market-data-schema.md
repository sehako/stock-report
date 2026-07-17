---
name: 기능 구현
about: 새로운 기능 구현 또는 기존 기능 확장을 위한 이슈
title: "[Feature] 시장 데이터 RDB 스키마 구성"
labels: feature
assignees: ""
---

- GitHub Issue: https://github.com/sehako/stock-report/issues/25
- 상태: 완료

## 개요

주식 시장 데이터 조회 서비스 MVP에서 사용할 종목 메타데이터, 종목 일봉, 지수 일봉 저장 구조를 구성한다.

## 작업 범위

- [x] `stock` 테이블을 생성한다.
- [x] `stock_price` 테이블을 생성한다.
- [x] `market_index_price` 테이블을 생성한다.
- [x] `stock_price(stock_id, trade_date)` 조합과 `market_index_price(index_code, trade_date)` 조합에 중복 방지 제약을 적용한다.
- [x] 배치와 API에서 사용할 주요 조회 조건에 맞는 인덱스를 검토하고 적용한다.

## 검증 흐름

- [x] 마이그레이션 또는 스키마 생성 검증을 실행해 세 테이블과 중복 방지 제약이 정상 생성되는지 확인한다.

## 제외 범위

- Python 배치 구현은 제외한다.
- Spring Boot 조회 API 구현은 제외한다.
- React 화면 구현은 제외한다.
- 배치 실행 이력 테이블은 MVP 범위에서 제외한다.

## 완료 기준

- [x] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [x] 관련 테스트 또는 검증 결과를 기록한다.
- [x] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [x] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

## 구현 결과

- `app/backend`에 Kotlin + Spring Boot Gradle 프로젝트와 Flyway 마이그레이션 구조를 추가했다.
- `app/backend/src/main/resources/db/migration/V1__create_market_data_tables.sql`에 `stock`, `stock_price`, `market_index_price` 테이블 생성 정의를 추가했다.
- `stock(market, stock_code)`, `stock_price(stock_id, trade_date)`, `market_index_price(index_code, trade_date)` 유니크 제약을 추가했다.
- `stock.market`, `market_index_price.index_code`에 `KOSPI`, `KOSDAQ` 체크 제약을 추가했다.
- `stock(tracked, market)` 조회 인덱스를 추가했다.
- `app/backend/src/main/resources/application.yml`에 datasource와 Flyway 설정을 환경 변수 기반으로 추가했다.
- `MarketDataSchemaTest`를 Testcontainers PostgreSQL 기반으로 구성해 실제 PostgreSQL 엔진에서 스키마와 제약을 검증했다.

## 검증 결과

- `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon test --rerun-tasks`: `BUILD SUCCESSFUL`
- `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew --no-daemon build`: `BUILD SUCCESSFUL`

## 참고 문서

- `docs/plans/backend/issue-01-market-data-schema.md`
- `docs/specs/2026-07-15-stock-market-data-service-design.md`
- `docs/architecture/backend.md`
