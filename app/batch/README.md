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

옵션 없이 실행하면 기본 배치 흐름을 수행한다. 실행 순서는 종목 universe 갱신, tracked 종목 일봉 적재, 코스피/코스닥 지수 일봉 적재다.

```bash
cd app/batch
. .venv/bin/activate
python -m batch.main
```

특정 종목의 지정 기간 일봉만 다시 수집하려면 `--stock-code`, `--start-date`, `--end-date`를 함께 지정한다. `--stock-code`는 6자리 숫자 문자열만 허용한다.

```bash
python -m batch.main --stock-code 005930 --start-date 2024-01-01 --end-date 2024-01-31
```

특정 지수의 지정 기간 일봉만 다시 수집하려면 `--index-code`, `--start-date`, `--end-date`를 함께 지정한다. 지원 지수 코드는 `KOSPI`, `KOSDAQ`이며, 입력 대소문자는 구분하지 않는다.

```bash
python -m batch.main --index-code kospi --start-date 2024-01-01 --end-date 2024-01-31
```

`--start-date`와 `--end-date`는 `YYYY-MM-DD` 형식이며 둘 다 지정해야 한다. 기간 옵션만 단독으로 지정하거나, `--stock-code`와 `--index-code`를 동시에 지정하면 배치는 외부 FDR 호출과 DB 쓰기 전에 실패한다. 시작일이 종료일보다 늦은 경우, 지원하지 않는 지수 코드, 6자리 숫자가 아닌 종목 코드도 실패한다.

지정 종목 재수집은 `stock` 테이블에 이미 존재하는 종목만 처리한다. 종목이 없으면 기본 배치로 universe를 먼저 갱신한 뒤 다시 실행한다.

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

지정 종목 재수집 후 특정 기간의 저장 범위는 다음 쿼리로 확인한다.

```sql
SELECT s.stock_code, COUNT(*) AS row_count, MIN(sp.trade_date), MAX(sp.trade_date)
FROM stock_price sp
JOIN stock s ON s.id = sp.stock_id
WHERE s.stock_code = '005930'
  AND sp.trade_date BETWEEN DATE '2024-01-01' AND DATE '2024-01-31'
GROUP BY s.stock_code;
```

지정 지수 재수집 후 특정 기간의 저장 범위는 다음 쿼리로 확인한다.

```sql
SELECT index_code, COUNT(*) AS row_count, MIN(trade_date), MAX(trade_date)
FROM market_index_price
WHERE index_code = 'KOSPI'
  AND trade_date BETWEEN DATE '2024-01-01' AND DATE '2024-01-31'
GROUP BY index_code;
```
