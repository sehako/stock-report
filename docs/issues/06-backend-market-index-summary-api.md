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

- [ ] `GET /api/market-indexes` 엔드포인트를 구현한다.
- [ ] `KOSPI`, `KOSDAQ`의 최신 거래일 데이터를 조회한다.
- [ ] 최신 종가, 전일 대비 값, 등락률 퍼센트(`changeRatePercent`)를 응답에 포함한다.
- [ ] API 응답은 `KOSPI`, `KOSDAQ` 두 항목을 항상 포함하며, 데이터가 없는 지수는 `EMPTY`, 일부 값이 없는 지수는 `PARTIAL` 상태로 응답한다.
- [ ] `docs/architecture/backend.md`의 도메인 중심 계층 구조를 따른다.

## 검증 흐름

- [ ] 저장된 지수 일봉 데이터가 있을 때 `GET /api/market-indexes`가 코스피와 코스닥 최신 수치를 반환하는지 테스트한다.

## 제외 범위

- 지수 차트 조회 API는 제외한다.
- 종목 조회 API는 제외한다.
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
