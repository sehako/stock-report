from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from zoneinfo import ZoneInfo

from stock_report_worker.jobs.target_stocks import KrxTargetStockProvider, select_target_stocks
from stock_report_worker.krx.normalization import KrxListedStock


def listed(
    stock_id: int,
    stock_code: str,
    *,
    close_price: str,
    volume: int,
    stock_name: str | None = None,
) -> KrxListedStock:
    return KrxListedStock(
        stock_code=stock_code,
        stock_name=stock_name or f"stock-{stock_code}",
        market="KOSPI",
        industry_name="전기전자",
        listing_close_price=Decimal(close_price),
        listing_volume=volume,
        stock_id=stock_id,
    )


def test_select_target_stocks_filters_by_close_price_and_orders_by_volume_then_code() -> None:
    targets = select_target_stocks(
        [
            listed(1, "000003", close_price="999", volume=999_999),
            listed(2, "000002", close_price="1000", volume=100),
            listed(3, "000001", close_price="1500", volume=100),
            listed(4, "000004", close_price="2000", volume=200),
        ]
    )

    assert [(target.id, target.stock_code, target.selection_rank) for target in targets] == [
        (4, "000004", 1),
        (3, "000001", 2),
        (2, "000002", 3),
    ]
    assert [target.selection_volume for target in targets] == [200, 100, 100]
    assert [target.selection_close_price for target in targets] == [
        Decimal("2000"),
        Decimal("1500"),
        Decimal("1000"),
    ]


def test_select_target_stocks_limits_to_top_200_by_volume() -> None:
    stocks = [
        listed(index, f"{index:06d}", close_price="1000", volume=index)
        for index in range(1, 205)
    ]

    targets = select_target_stocks(stocks)

    assert len(targets) == 200
    assert targets[0].id == 204
    assert targets[-1].id == 5


def test_select_target_stocks_rejects_listed_stock_without_stock_id() -> None:
    stock = KrxListedStock(
        stock_code="005930",
        stock_name="삼성전자",
        market="KOSPI",
        industry_name="전기전자",
        listing_close_price=Decimal("85000"),
        listing_volume=123456,
    )

    try:
        select_target_stocks([stock])
    except ValueError as exc:
        assert "005930" in str(exc)
    else:
        raise AssertionError("expected ValueError")


class FakeKrxStockListingProvider:
    def __init__(self, stocks: list[KrxListedStock]) -> None:
        self.stocks = stocks
        self.calls: list[datetime] = []

    def collect(self, now: datetime) -> list[KrxListedStock]:
        self.calls.append(now)
        return self.stocks


def test_krx_target_stock_provider_collects_listing_and_returns_selected_targets() -> None:
    now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    listing_provider = FakeKrxStockListingProvider(
        [
            listed(1, "000001", close_price="1000", volume=10),
            listed(2, "000002", close_price="999", volume=999),
        ]
    )
    provider = KrxTargetStockProvider(listing_provider, now=lambda: now)

    targets = provider.list_for(date(2026, 7, 9))

    assert listing_provider.calls == [now]
    assert [target.id for target in targets] == [1]
