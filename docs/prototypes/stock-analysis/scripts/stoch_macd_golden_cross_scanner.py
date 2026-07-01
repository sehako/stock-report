
import FinanceDataReader as fdr
import pandas as pd
import pandas_ta_classic as ta
import numpy as np
import time
from datetime import datetime, timedelta

ONE_YEAR = 365

# 1. KRX 종목 리스트 필터링
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Close'] >= 1000]
top_100 = df_krx.sort_values(by = 'Volume', ascending = False).head(200)
# print(top_100.head(5))

results = []
end_date = datetime.now()
# start_date = end_date - timedelta(days=3*365)
# 1년으로 단축
start_date = end_date - timedelta(days = ONE_YEAR)

for index, row in top_100.iterrows():
    symbol = row['Code']
    name = row['Name']

    try:
        # 데이터 호출 간 지연 시간 추가 (0.2초)
        # API 서버 부하 방지 및 IP 차단 예방
        # time.sleep(0.2)

        df = fdr.DataReader(symbol, start_date, end_date)
        if len(df) < 110: continue # 지표 계산을 위한 충분한 데이터 확보

        # 2. MACD 계산
        macd = ta.macd(df['Close'])
        if macd is None: continue
        macd_line = macd.iloc[:, 0]

        # 3. MACD 기반 Stochastic 계산
        stoch_macd = ta.stoch(macd_line, macd_line, macd_line, k=14, d=3, smooth_k=3)
        if stoch_macd is None: continue

        k_line = stoch_macd.iloc[:, 0] # STOCHk_14_3_3
        d_line = stoch_macd.iloc[:, 1] # STOCHd_14_3_3

        # 4. 최근 3일 이내 골든크로스 체크 루프
        # -1(오늘), -2(어제), -3(그저께)
        found_cross = False
        cross_date = ""

        for i in range(1, 4): # 1, 2, 3일 전부터 오늘까지 확인
            idx = -i
            prev_idx = -(i + 1)

            curr_k, curr_d = k_line.iloc[idx], d_line.iloc[idx]
            prev_k, prev_d = k_line.iloc[prev_idx], d_line.iloc[prev_idx]

            # 골든크로스 조건
            if prev_k < prev_d and curr_k > curr_d:
                found_cross = True
                cross_date = df.index[idx].strftime('%Y-%m-%d')
                break # 가장 최근 크로스만 확인하고 탈출

        if found_cross:
            results.append({
                '종목코드': symbol,
                '종목명': name,
                '크로스일자': cross_date,
                '현재가': df['Close'].iloc[-1],
                'K_값': round(k_line.iloc[-1], 2),
                'D_값': round(d_line.iloc[-1], 2)
            })

    except Exception as e:
        continue

# 5. 결과 출력
print(f"\n### 최근 3일 이내 Stoch MACD 골든크로스 종목 ###")
if results:
    result_df = pd.DataFrame(results)
    # 날짜 기준 내림차순 정렬 (최신순)
    print(result_df.sort_values(by='크로스일자', ascending=False).to_string(index=False))
else:
    print("조건에 맞는 종목이 없습니다.")