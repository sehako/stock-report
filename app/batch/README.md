# 주식 종목 Universe 선정 배치

이 배치는 `FinanceDataReader.StockListing("KRX")`로 KRX 종목 목록을 조회하고, 거래량 상위 200개 종목을 `stock` 테이블의 현재 조회 대상(`tracked = true`)으로 갱신한다.

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
