---
name: 기능 구현
about: 새로운 기능 구현 또는 기존 기능 확장을 위한 이슈
title: "[Feature] tracked 종목 일봉 적재 배치 구현"
labels: feature
assignees: ""
---

## 개요

Python 배치에서 `tracked = true` 종목의 일봉 가격 데이터를 수집해 `stock_price`에 저장한다.

## 작업 범위

- [ ] `stock.tracked = true` 종목을 대상으로 일봉 가격 데이터를 수집한다.
- [ ] tracked 종목별 마지막 적재일은 `stock_price.MAX(trade_date)`로 계산한다.
- [ ] 최초 적재 대상 종목은 `FinanceDataReader.DataReader(stock_code, "1900-01-01")`로 조회 가능한 최대 기간의 일봉을 요청한다.
- [ ] 이후 실행 대상 종목은 마지막 적재 거래일 다음 날부터 일봉을 조회하며, 주말과 공휴일은 별도로 보정하지 않는다.
- [ ] 수집한 시가, 고가, 저가, 종가, 거래량, 등락률을 `stock_price`에 upsert한다.
- [ ] `change_rate`는 FinanceDataReader의 `Change` 원값을 저장하고, 값이 없거나 변환할 수 없으면 `NULL`로 저장할 수 있다.
- [ ] upsert는 `stock_id`, `trade_date` 기준으로 수행하며, 충돌 시 FinanceDataReader 원천 데이터 기준으로 가격 값을 갱신한다.
- [ ] 종목별 수집 성공, 스킵, 실패 결과를 로그로 남긴다.
- [ ] 한 종목 수집 실패가 나머지 종목 수집을 중단하지 않게 처리한다.

## 검증 흐름

- [ ] 같은 종목 일봉 적재 배치를 반복 실행해도 `stock_id`, `trade_date` 기준 중복 row가 생기지 않는지 확인한다.
- [ ] `stock_price` 저장 SQL이 `ON CONFLICT (stock_id, trade_date) DO UPDATE` 의도를 충족하는지 확인한다.
- [ ] FinanceDataReader가 빈 결과를 반환하면 실패가 아니라 스킵으로 기록되는지 확인한다.
- [ ] 한 종목 수집 또는 저장 실패가 다음 종목 처리를 막지 않는지 확인한다.
- [ ] 선행 `stock_universe` 작업이 실패하면 `stock_daily_price` 작업이 실행되지 않는지 확인한다.

## 제외 범위

- 거래량 상위 200개 종목 선정 내부 로직은 제외한다.
- 지수 일봉 가격 수집은 제외한다.
- 지정 재수집 옵션은 제외한다.
- 배치 실패 이력 테이블 저장은 제외한다.
- 데이터 삭제와 강제 초기화 작업은 제외한다.

## 완료 기준

- [ ] 구현 범위가 이슈 목적을 벗어나지 않는다.
- [ ] 개별 종목 실패는 `stock_daily_price` 작업 전체 실패로 처리하지 않는다.
- [ ] 필수 설정 누락, DB 연결 실패, tracked 종목 목록 조회 실패, 선행 `stock_universe` 실패는 전체 배치 실패로 처리한다.
- [ ] `stock_price` 저장 트랜잭션은 종목 단위로 처리한다.
- [ ] 관련 테스트 또는 검증 결과를 기록한다.
- [ ] 필요한 경우 문서 또는 구현 계획을 작성하거나 갱신한다.
- [ ] API, DB, 화면 계약 변경이 있다면 영향 범위를 확인한다.

## 참고 문서

- `docs/specs/2026-07-15-stock-market-data-service-design.md`
