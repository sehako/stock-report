
import FinanceDataReader as fdr
import pandas as pd
import pandas_ta_classic as ta
import numpy as np
from datetime import datetime, timedelta
# 1. KRX 종목 리스트 및 1,000원 미만 필터링
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Close'] >= 1000]
top_50 = df_krx.sort_values(by='ChagesRatio', ascending=False).head(100)

results = []
end_date = datetime.now()
start_date = end_date - timedelta(days=3*365)

# 구간 상태를 채우는 함수
def fill_signal_state(df, k_col, d_col, new_col_name):
    """
    골든크로스 시점부터 1, 데드크로스 시점부터 -1로 채우는 로직
    """
    signals = np.zeros(len(df))
    current_state = 0 # 초기 상태 (신호 발생 전)

    # 지표 값 추출
    k_vals = df[k_col].values
    d_vals = df[d_col].values

    for i in range(1, len(df)):
        # 골든크로스 발생
        if k_vals[i-1] < d_vals[i-1] and k_vals[i] > d_vals[i]:
            current_state = 1
        # 데드크로스 발생
        elif k_vals[i-1] > d_vals[i-1] and k_vals[i] < d_vals[i]:
            current_state = -1

        signals[i] = current_state

    df[new_col_name] = signals
    return df

for index, row in top_50.iterrows():
    symbol = row['Code']
    name = row['Name']

    try:
        df = fdr.DataReader(symbol, start_date, end_date)
        if len(df) < 100: continue

        # --- 지표 계산 ---
        # A. RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)

        # B. RSI 기반 MACD
        macd_rsi = ta.macd(df['RSI'], fast=12, slow=26, signal=9)
        df['MACD_RSI_L'] = macd_rsi.iloc[:, 0] # MACD Line
        df['MACD_RSI_S'] = macd_rsi.iloc[:, 2] # Signal Line

        # C. RSI 기반 Stochastic
        stoch_rsi = ta.stoch(df['RSI'], df['RSI'], df['RSI'], k=14, d=3, smooth_k=3)
        df['Stoch_RSI_K'] = stoch_rsi.iloc[:, 0]
        df['Stoch_RSI_D'] = stoch_rsi.iloc[:, 1]

        # D. MACD 기반 Stochastic
        stoch_macd = ta.stoch(df['MACD_RSI_L'], df['MACD_RSI_L'], df['MACD_RSI_L'], k=14, d=3, smooth_k=3)
        df['Stoch_MACD_K'] = stoch_macd.iloc[:, 0]
        df['Stoch_MACD_D'] = stoch_macd.iloc[:, 1]

        # --- 구간 상태 컬럼 추가 ---
        df = fill_signal_state(df, 'MACD_RSI_L', 'MACD_RSI_S', 'State_A')
        df = fill_signal_state(df, 'Stoch_RSI_K', 'Stoch_RSI_D', 'State_B')
        df = fill_signal_state(df, 'Stoch_MACD_K', 'Stoch_MACD_D', 'State_C')

        # 3. 마지막 영업일 기준으로 세 상태가 모두 1인 종목 추출
        last_row = df.iloc[-1]   # 오늘 데이터
        prev_row = df.iloc[-2]   # 전날 데이터

        if last_row['State_A'] == 1 and last_row['State_B'] == 1 and last_row['State_C'] == 1:
            # 등락률 계산: ((오늘 종가 - 어제 종가) / 어제 종가) * 100
            change_rate = ((last_row['Close'] - prev_row['Close']) / prev_row['Close']) * 100

            results.append({
                '종목명': name,
                '시가': int(last_row['Open']),
                '고가': int(last_row['High']),
                '저가': int(last_row['Low']),
                '종가': int(last_row['Close']),
                '거래량': int(last_row['Volume']),
                '등락률': round(change_rate, 2)  # 소수점 2자리까지 반올림
            })

    except Exception as e:
        continue

# 최종 결과 출력
final_df = pd.DataFrame(results)
if not final_df.empty:
    print(f"### 분석 결과 (3개 지표 모두 상승 유지 구간 종목) ###")
    print(final_df.to_string(index=False))
else:
    print("현재 모든 지표가 '1'로 유지 중인 종목이 없습니다.")