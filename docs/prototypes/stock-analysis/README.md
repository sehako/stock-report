# 주식 분석 프로토타입

FinanceDataReader 기반 주식 데이터 수집, 기술지표 계산, 스캐너 실험 산출물을 보관한다.

## 구성

- `scripts/`: CSV 생성 및 기술지표 스캐너 실험 스크립트
- `data/`: 스크립트 실행 시 생성되는 로컬 종목별 CSV 샘플 데이터 디렉터리
- `candle-chart.html`: CSV 데이터를 확인하기 위한 차트 프로토타입

## MVP 기준

MVP가 계승하는 기준 스크립트는 `scripts/stoch_macd_golden_cross_scanner.py`다. 이 스크립트의 종목 선정 조건과 Stoch MACD 골든크로스 계산 방식을 제품 기획의 기준으로 사용한다.

그 외 스크립트와 HTML은 데이터 수집, 보조 지표 계산, 차트 렌더링 가능성을 확인한 참고 산출물이다. `trend_state_scanner.py`의 다중 지표 상승 상태 스크리닝과 `finance_data_to_csv.py`의 RSI·Stoch RSI 계산은 MVP 신호 계산 기준에 포함하지 않는다.

## 실행 기준

스크립트는 이 디렉터리(`docs/prototypes/stock-analysis`)를 작업 디렉터리로 두고 실행하는 것을 기준으로 한다.

```bash
python scripts/finance_data_to_csv.py
```

## 제외 항목

기존 `stock/.venv`, `stock/__pycache__`는 로컬 실행 부산물이므로 문서 산출물로 이동하지 않았다.
