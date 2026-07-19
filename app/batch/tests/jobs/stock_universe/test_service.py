import pytest
from math import nan

from jobs.stock_universe.domain.service import StockUniverseSelectionError, select_top_volume_stocks


def krx_row(code: str, name: str, market: str, volume):
    return {
        "Code": code,
        "Name": name,
        "Market": market,
        "Volume": volume,
    }


def make_rows(size: int):
    return [
        krx_row(f"{index:06d}", f"종목{index}", "KOSPI" if index % 2 == 0 else "KOSDAQ", index)
        for index in range(1, size + 1)
    ]


def test_selects_only_top_200_by_volume_descending():
    rows = make_rows(201)

    result = select_top_volume_stocks(rows)

    assert len(result.stocks) == 200
    assert [stock.stock_code for stock in result.stocks[:3]] == ["000201", "000200", "000199"]
    assert "000001" not in {stock.stock_code for stock in result.stocks}


def test_uses_stock_code_ascending_when_volume_ties():
    rows = make_rows(198)
    rows.extend(
        [
            krx_row("999003", "동률3", "KOSPI", 1000),
            krx_row("999001", "동률1", "KOSPI", 1000),
            krx_row("999002", "동률2", "KOSDAQ", 1000),
        ]
    )

    result = select_top_volume_stocks(rows)

    assert [stock.stock_code for stock in result.stocks[:3]] == ["999001", "999002", "999003"]


def test_treats_missing_or_invalid_volume_as_zero():
    rows = make_rows(199)
    rows.extend(
        [
            krx_row("999001", "숫자문자열", "KOSPI", "10,000"),
            krx_row("999002", "결측거래량", "KOSPI", None),
            krx_row("999003", "잘못된거래량", "KOSDAQ", "N/A"),
        ]
    )

    result = select_top_volume_stocks(rows)

    selected_codes = [stock.stock_code for stock in result.stocks]
    assert selected_codes[0] == "999001"
    assert "999002" not in selected_codes
    assert "999003" not in selected_codes


def test_excludes_rows_without_required_stock_identity():
    rows = make_rows(199)
    rows.extend(
        [
            krx_row("", "코드없음", "KOSPI", 10000),
            krx_row("999001", "   ", "KOSPI", 10000),
            krx_row("999002", "정상", "KOSPI", 10000),
        ]
    )

    result = select_top_volume_stocks(rows)

    assert result.stocks[0].stock_code == "999002"
    assert result.excluded_counts["missing_stock_code"] == 1
    assert result.excluded_counts["missing_stock_name"] == 1


def test_excludes_nan_stock_identity_values():
    rows = make_rows(199)
    rows.extend(
        [
            krx_row(nan, "코드없음", "KOSPI", 10000),
            krx_row("999001", nan, "KOSPI", 10000),
            krx_row("999002", "정상", "KOSDAQ", 10000),
        ]
    )

    result = select_top_volume_stocks(rows)

    assert result.stocks[0].stock_code == "999002"
    assert result.excluded_counts["missing_stock_code"] == 1
    assert result.excluded_counts["missing_stock_name"] == 1


def test_excludes_markets_outside_kospi_and_kosdaq():
    rows = make_rows(199)
    rows.append(krx_row("999001", "코넥스종목", "KONEX", 10000))
    rows.append(krx_row("999002", "코스피종목", "KOSPI", 9000))

    result = select_top_volume_stocks(rows)

    assert result.stocks[0].stock_code == "999002"
    assert "999001" not in {stock.stock_code for stock in result.stocks}
    assert result.excluded_counts["unsupported_market"] == 1


def test_treats_kosdaq_global_as_kosdaq():
    rows = make_rows(199)
    rows.append(krx_row("999001", "코스닥글로벌종목", "KOSDAQ GLOBAL", 10000))

    result = select_top_volume_stocks(rows)

    assert result.stocks[0].stock_code == "999001"
    assert result.stocks[0].market == "KOSDAQ"


def test_keeps_non_common_stock_names_when_volume_is_high():
    rows = make_rows(199)
    rows.append(krx_row("999001", "ETF 우선주 ETN", "KOSPI", 10000))

    result = select_top_volume_stocks(rows)

    assert result.stocks[0].stock_code == "999001"
    assert result.stocks[0].stock_name == "ETF 우선주 ETN"


def test_uses_highest_volume_row_when_stock_code_is_duplicated():
    rows = make_rows(199)
    rows.extend(
        [
            krx_row("999001", "낮은거래량", "KOSPI", 100),
            krx_row("999001", "높은거래량", "KOSDAQ", 10000),
        ]
    )

    result = select_top_volume_stocks(rows)

    matching = [stock for stock in result.stocks if stock.stock_code == "999001"]
    assert len(matching) == 1
    assert matching[0].stock_name == "높은거래량"
    assert result.duplicate_stock_code_count == 1


def test_fails_when_valid_rows_are_less_than_selection_size():
    rows = make_rows(199)

    with pytest.raises(StockUniverseSelectionError, match="200"):
        select_top_volume_stocks(rows)
