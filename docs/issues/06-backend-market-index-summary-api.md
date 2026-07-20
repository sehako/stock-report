---
name: 기능 구현
about: 새로운 기능 구현 또는 기존 기능 확장을 위한 이슈
title: "[Feature] 지수 최신 수치 조회 API 구현"
labels: feature
assignees: ""
---

## 개요

Spring Boot 백엔드에서 코스피와 코스닥의 최신 수치, 전일 대비 값, 등락률을 조회하는 API를 제공한다.

## 작업 범위

- [x] `GET /api/market-indexes` 엔드포인트를 구현한다.
- [x] `KOSPI`, `KOSDAQ`의 최신 거래일 데이터를 조회한다.
- [x] 최신 종가, 전일 대비 값, 등락률 퍼센트(`changeRatePercent`)를 응답에 포함한다.
- [x] API 응답은 `KOSPI`, `KOSDAQ` 두 항목을 항상 포함하며, 데이터가 없는 지수는 `EMPTY`, 일부 값이 없는 지수는 `PARTIAL` 상태로 응답한다.
- [x] `docs/architecture/backend.md`의 도메인 중심 계층 구조를 따른다.

## 검증 흐름

- [x] 저장된 지수 일봉 데이터가 있을 때 `GET /api/market-indexes`가 코스피와 코스닥 최신 수치를 반환하는지 테스트한다.
- [x] `MarketIndexServiceTest`로 `AVAILABLE`, `PARTIAL`, `EMPTY` 상태와 수치 계산을 검증한다.
- [x] `MarketIndexPriceRepositoryImplTest`로 PostgreSQL에서 지수별 최신 두 거래일 조회를 검증한다.
- [x] `MarketIndexControllerTest`로 `GET /api/market-indexes` HTTP 200 응답과 JSON 계약을 검증한다.
- [x] `app/backend`에서 `GRADLE_USER_HOME=$PWD/.gradle-local ./gradlew clean test -q`를 실행해 전체 백엔드 테스트 통과를 확인한다.

## 제외 범위

- 지수 차트 조회 API는 제외한다.
- 종목 조회 API는 제외한다.
- Python 배치 구현은 제외한다.
- React 화면 구현은 제외한다.

## 완료 기준

- [x] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [x] 관련 테스트 또는 검증 결과를 기록한다.
- [x] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [x] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

## 참고 문서

- `docs/specs/2026-07-15-stock-market-data-service-design.md`
- `docs/architecture/backend.md`
- `docs/plans/backend/issue-06-backend-market-index-summary-api.md`

## 구현 결과

- `app/backend/build.gradle.kts`에 `spring-boot-starter-web`을 추가했다.
- `app/backend/src/main/kotlin/com/stockreport/marketindex` 아래에 `presentation`, `application`, `domain`, `infrastructure.persistence` 계층을 추가했다.
- `GET /api/market-indexes`는 최상위 `items` 객체 배열로 `KOSPI`, `KOSDAQ` 두 항목을 고정 순서로 반환한다.
- 저장 데이터가 없으면 `EMPTY`, 최신 row는 있지만 전일 대비 값 또는 등락률 퍼센트가 비면 `PARTIAL`, 모든 수치가 있으면 `AVAILABLE`을 반환한다.
- 등락률 퍼센트는 `market_index_price.change_rate * 100`으로 계산하며, 전일 대비 값은 최신 종가에서 저장된 직전 거래일 종가를 빼서 계산한다.
