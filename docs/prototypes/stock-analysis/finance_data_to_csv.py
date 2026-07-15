from datetime import datetime, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd
import pandas_ta_classic as ta
import time


START_DATE = "2015-06-15"
DATA_DIR = Path("data")
TOP_N = 100
MIN_CLOSE_PRICE = 1000
REQUEST_DELAY_SECONDS = 0.2
INDICATOR_LOOKBACK_DAYS = 365
MOVING_AVERAGE_WINDOWS = [5, 10, 20, 60, 120, 200]
REQUIRED_INDICATOR_COLUMNS = [
    "RSI",
    "MACD_L",
    "MACD_H",
    "MACD_S",
    "Stoch_RSI_K",
    "Stoch_RSI_D",
    "Stoch_MACD_K",
    "Stoch_MACD_D",
    "MA_5",
    "MA_10",
    "MA_20",
    "MA_60",
    "MA_120",
    "MA_200",
]


def get_top_volume_stocks():
    """KRX 종목 중 현재가 1,000원 이상인 거래량 상위 종목을 반환한다."""
    df_krx = fdr.StockListing("KRX")
    df_krx = df_krx[df_krx["Close"] >= MIN_CLOSE_PRICE]
    return df_krx.sort_values(by="Volume", ascending=False).head(TOP_N)


def read_last_saved_date(csv_path):
    """기존 CSV 파일에서 마지막으로 저장된 거래일을 읽는다."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None

    date_rows = pd.read_csv(csv_path, usecols=["Date"])
    if date_rows.empty:
        return None

    dates = pd.to_datetime(date_rows["Date"], errors="coerce").dropna()
    if dates.empty:
        return None

    return dates.max().normalize()


def has_required_indicator_columns(csv_path):
    """기존 CSV에 저장해야 할 지표 컬럼이 모두 있는지 확인한다."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return False

    columns = pd.read_csv(csv_path, nrows=0).columns
    return all(column in columns for column in REQUIRED_INDICATOR_COLUMNS)


def load_stock_data(symbol, start_date, end_date):
    """FDR에서 종목 일봉 데이터를 가져오고 Date 컬럼을 표준화한다."""
    df = fdr.DataReader(symbol, start_date, end_date)
    if df.empty:
        return df

    df = df.reset_index()
    if "index" in df.columns:
        df = df.rename(columns={"index": "Date"})

    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    return df


def add_indicators(df):
    """RSI, MACD, Stochastic, 이동평균 지표 컬럼을 추가한다."""
    if df.empty:
        return df

    df = df.copy()

    for window in MOVING_AVERAGE_WINDOWS:
        df[f"MA_{window}"] = df["Close"].rolling(window=window).mean()

    df["RSI"] = ta.rsi(df["Close"], length=14)

    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd is None or macd.empty:
        df["MACD_L"] = float("nan")
        df["MACD_H"] = float("nan")
        df["MACD_S"] = float("nan")
    else:
        df["MACD_L"] = macd.iloc[:, 0]
        df["MACD_H"] = macd.iloc[:, 1]
        df["MACD_S"] = macd.iloc[:, 2]

    stoch_rsi = ta.stoch(df["RSI"], df["RSI"], df["RSI"], k=14, d=3, smooth_k=3)
    if stoch_rsi is None or stoch_rsi.empty:
        df["Stoch_RSI_K"] = float("nan")
        df["Stoch_RSI_D"] = float("nan")
    else:
        df["Stoch_RSI_K"] = stoch_rsi.iloc[:, 0]
        df["Stoch_RSI_D"] = stoch_rsi.iloc[:, 1]

    macd_line = pd.to_numeric(df["MACD_L"], errors="coerce")
    stoch_macd = ta.stoch(macd_line, macd_line, macd_line, k=14, d=3, smooth_k=3)
    if stoch_macd is None or stoch_macd.empty:
        df["Stoch_MACD_K"] = float("nan")
        df["Stoch_MACD_D"] = float("nan")
    else:
        df["Stoch_MACD_K"] = stoch_macd.iloc[:, 0]
        df["Stoch_MACD_D"] = stoch_macd.iloc[:, 1]

    return df


def get_download_start_date(last_saved_date, needs_full_refresh):
    """전체 재계산 여부에 따라 FDR 조회 시작일을 결정한다."""
    if needs_full_refresh or last_saved_date is None:
        return START_DATE

    return (last_saved_date - timedelta(days=INDICATOR_LOOKBACK_DAYS)).strftime("%Y-%m-%d")


def save_stock_data(csv_path, df, last_saved_date, replace_file=False):
    """신규 파일은 전체 저장하고, 기존 파일은 마지막 Date 이후 데이터만 append한다."""
    if df.empty:
        return 0

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    if replace_file or last_saved_date is None:
        df.to_csv(csv_path, index=False, encoding="utf-8")
        return len(df)

    new_rows = df[pd.to_datetime(df["Date"]) > last_saved_date]
    if new_rows.empty:
        return 0

    existing_columns = pd.read_csv(csv_path, nrows=0).columns.tolist()
    new_rows = new_rows.reindex(columns=existing_columns)
    new_rows.to_csv(csv_path, mode="a", header=False, index=False, encoding="utf-8")
    return len(new_rows)


def main():
    """거래량 상위 종목의 CSV 파일을 생성하거나 최신 일봉 데이터로 갱신한다."""
    DATA_DIR.mkdir(exist_ok=True)

    top_stocks = get_top_volume_stocks()
    end_date = datetime.now().strftime("%Y-%m-%d")
    failures = []
    saved_count = 0
    skipped_count = 0

    for _, row in top_stocks.iterrows():
        symbol = row["Code"]
        name = row["Name"]
        csv_path = DATA_DIR / f"{symbol}.csv"

        try:
            last_saved_date = read_last_saved_date(csv_path)
            needs_full_refresh = csv_path.exists() and not has_required_indicator_columns(csv_path)
            start_date = get_download_start_date(last_saved_date, needs_full_refresh)

            df = load_stock_data(symbol, start_date, end_date)
            df = add_indicators(df)
            rows_saved = save_stock_data(
                csv_path,
                df,
                last_saved_date,
                replace_file=needs_full_refresh,
            )

            if rows_saved > 0:
                saved_count += 1
                action = "REFRESH" if needs_full_refresh else "SAVE"
                print(f"[{action}] {symbol} {name}: {rows_saved} rows")
            else:
                skipped_count += 1
                print(f"[SKIP] {symbol} {name}: up to date")

        except Exception as e:
            failures.append((symbol, name, str(e)))
            print(f"[FAIL] {symbol} {name}: {e}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print("\n### finance data csv update result ###")
    print(f"saved/updated: {saved_count}")
    print(f"skipped: {skipped_count}")
    print(f"failed: {len(failures)}")

    if failures:
        print("\n### failures ###")
        for symbol, name, error in failures:
            print(f"{symbol} {name}: {error}")


if __name__ == "__main__":
    main()
