# 주식 분석 프로토타입

FinanceDataReader 기반 주식 데이터 수집, 기술지표 계산, 스캐너 실험 산출물을 보관한다.

## 구성

- `scripts/`: CSV 생성 및 기술지표 스캐너 실험 스크립트
- `data/`: 스크립트로 생성한 종목별 CSV 샘플 데이터
- `candle-chart.html`: CSV 데이터를 확인하기 위한 차트 프로토타입

## 실행 기준

스크립트는 이 디렉터리(`docs/prototypes/stock-analysis`)를 작업 디렉터리로 두고 실행하는 것을 기준으로 한다.

```bash
python scripts/finance_data_to_csv.py
```

## 제외 항목

기존 `stock/.venv`, `stock/__pycache__`는 로컬 실행 부산물이므로 문서 산출물로 이동하지 않았다.
