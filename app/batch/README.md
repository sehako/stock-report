# 주식 종목 Universe, 종목 일봉, 지수 일봉 적재 배치

이 배치는 `FinanceDataReader.StockListing("KRX")`로 KRX 종목 목록을 조회하고, 거래량 상위 200개 종목을 `stock` 테이블의 현재 조회 대상(`tracked = true`)으로 갱신한다.

기본 실행은 종목 universe 갱신이 끝난 뒤 `tracked = true` 종목의 일봉 가격을 `FinanceDataReader.DataReader(stock_code, start)`로 조회해 `stock_price`에 저장한다. 최초 적재 종목은 `1900-01-01`부터 조회하고, 이미 적재된 종목은 `stock_price`에 저장된 마지막 거래일 다음 날부터 조회한다. 저장은 `(stock_id, trade_date)` 기준 upsert를 사용하므로 같은 배치를 반복 실행해도 같은 종목과 거래일의 중복 row가 생기지 않아야 한다.

종목 일봉 적재가 끝나면 기본 실행은 코스피와 코스닥 지수 일봉도 적재한다. 내부 지수 코드 `KOSPI`, `KOSDAQ`은 각각 FinanceDataReader 지수 심볼 `KS11`, `KQ11`로 조회하고, 결과는 `market_index_price`에 저장한다. 최초 적재 지수는 `1900-01-01`부터 조회하고, 이미 적재된 지수는 `market_index_price`에 저장된 마지막 거래일 다음 날부터 조회한다. 저장은 `(index_code, trade_date)` 기준 upsert를 사용하므로 같은 배치를 반복 실행해도 같은 지수와 거래일의 중복 row가 생기지 않아야 한다.

## 준비

```bash
cd app/batch
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e ".[dev]"
```

로컬 PostgreSQL 접속 정보는 다음 값을 사용한다.

```bash
DATABASE_URL=postgresql://app:app@localhost:5432/stock_report
LOG_LEVEL=INFO
```

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

지수 일봉 중복 여부는 다음 쿼리로 확인한다.

```sql
SELECT COUNT(*)
FROM (
    SELECT index_code, trade_date
    FROM market_index_price
    GROUP BY index_code, trade_date
    HAVING COUNT(*) > 1
) duplicated;
```

기대 결과는 `0`이다.
