---
name: 기능 구현
about: 새로운 기능 구현 또는 기존 기능 확장을 위한 이슈
title: "[Feature] 지수 기간별 일봉 차트 API 구현"
labels: feature
assignees: ""
---

## 개요

Spring Boot 백엔드에서 코스피 또는 코스닥 지수의 기간별 일봉 차트 데이터를 조회하는 API를 제공한다.

## 작업 범위

- [ ] `GET /api/market-indexes/{indexCode}/prices?period=1M|3M|1Y` 엔드포인트를 구현한다.
- [ ] 내부 지수 코드 `KOSPI`, `KOSDAQ`만 지원한다.
- [ ] `period` 값에 따라 해당 지수의 저장된 최신 거래일을 기준으로 조회 시작일을 계산한다.
- [ ] 거래일 오름차순으로 일봉 데이터를 반환한다.
- [ ] 존재하지 않는 지수 코드는 404로 처리한다.
- [ ] 지원하지 않는 기간 값은 400으로 처리한다.
- [ ] `period`가 누락된 경우 400으로 처리한다.
- [ ] 데이터가 없는 경우 `startDate`, `endDate`가 `null`이고 `items`가 빈 목록인 200 응답을 반환한다.

## API 계약

- `indexCode`는 `KOSPI`, `KOSDAQ`만 허용하며, `kospi`, `Kospi`, `KS11`, `KQ11`은 존재하지 않는 지수 코드로 본다.
- `period`는 `1M`, `3M`, `1Y`만 허용한다.
- 기간 종료일(`endDate`)은 해당 지수의 저장된 최신 거래일이다.
- 기간 시작일(`startDate`)은 `endDate`에서 `period`에 해당하는 기간을 뺀 날짜다.
- 응답 최상위 필드는 `indexCode`, `period`, `startDate`, `endDate`, `items`를 사용한다.
- `items` 항목 필드는 `tradeDate`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `changeRatePercent`를 사용한다.
- `items`는 `startDate <= tradeDate <= endDate` 범위의 일봉을 거래일 오름차순으로 포함한다.

## 검증 흐름

- [ ] `KOSPI`와 `period=3M` 요청 시 지정 기간의 지수 일봉 목록이 거래일 오름차순으로 반환되는지 테스트한다.

## 제외 범위

- 지수 최신 수치 조회 API는 제외한다.
- 종목 차트 조회 API는 제외한다.
- Python 배치 구현은 제외한다.
- React 화면 구현은 제외한다.

## 완료 기준

- [ ] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [ ] 관련 테스트 또는 검증 결과를 기록한다.
- [ ] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [ ] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

## 참고 문서

- `docs/specs/2026-07-15-stock-market-data-service-design.md`
- `docs/architecture/backend.md`
- `docs/plans/backend/issue-07-backend-market-index-price-api.md`
