# 주식 종목 Universe 및 일봉 적재 배치

이 배치는 `FinanceDataReader.StockListing("KRX")`로 KRX 종목 목록을 조회하고, 거래량 상위 200개 종목을 `stock` 테이블의 현재 조회 대상(`tracked = true`)으로 갱신한다.

기본 실행은 종목 universe 갱신이 끝난 뒤 `tracked = true` 종목의 일봉 가격을 `FinanceDataReader.DataReader(stock_code, start)`로 조회해 `stock_price`에 저장한다. 최초 적재 종목은 `1900-01-01`부터 조회하고, 이미 적재된 종목은 `stock_price`에 저장된 마지막 거래일 다음 날부터 조회한다. 저장은 `(stock_id, trade_date)` 기준 upsert를 사용하므로 같은 배치를 반복 실행해도 같은 종목과 거래일의 중복 row가 생기지 않아야 한다.

## 준비

```bash
cd app/batch
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e ".[dev]"
```

`DATABASE_URL` 환경 변수에는 PostgreSQL 접속 문자열을 설정한다. 실제 값은 코드나 문서에 기록하지 않는다.

## 실행

```bash
cd app/batch
. .venv/bin/activate
python -m batch.main
```

## 테스트

```bash
cd app/batch
. .venv/bin/activate
pytest
```

## 수동 중복 확인

로컬 PostgreSQL과 외부 네트워크 접근이 가능한 환경에서 배치를 두 번 실행한 뒤 다음 쿼리로 중복 여부를 확인한다.

```sql
SELECT COUNT(*)
FROM (
    SELECT stock_id, trade_date
    FROM stock_price
    GROUP BY stock_id, trade_date
    HAVING COUNT(*) > 1
) duplicated;
```

기대 결과는 `0`이다.
