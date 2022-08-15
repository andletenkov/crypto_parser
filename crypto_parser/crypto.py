import itertools
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, Union

import requests
from requests.adapters import HTTPAdapter

from crypto_parser.constant import (
    ALFA,
    POCHTA,
    QIWI,
    RAIFFEISEN,
    ROSBANK,
    TINKOFF,
    YANDEX,
)


class UnknownExchange(Exception):
    pass


TradeType = Literal["BUY", "SELL"]
P2PAdv = namedtuple("P2PAdv", ("nick", "price", "quantity"))
P2PData = dict[tuple[str, str], list[P2PAdv]]
Symbol = float
MarketData = dict[tuple[str, str], Symbol]


HTTP_SESSION = requests.Session()
HTTP_SESSION.mount(
    "https://", HTTPAdapter(pool_connections=3, pool_maxsize=20, max_retries=3)
)


def fetch_binance_p2p(
    asset: str,
    fiat: str,
    trade_type: TradeType,
    *,
    pay_type: str,
    amount: int = 0,
) -> list[P2PAdv]:
    resp = HTTP_SESSION.post(
        "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
        json={
            "asset": asset,
            "tradeType": trade_type,
            "fiat": fiat,
            "transAmount": amount,
            "merchantCheck": True,
            "payTypes": [pay_type],
            "page": 1,
            "rows": 20,
            "filterType": "all",
        },
    )
    assert resp.status_code == 200, f"Error fetching Binance P2P data. {resp.text}"

    raw_data = resp.json()["data"]

    prices = [
        P2PAdv(
            row["advertiser"]["nickName"],
            float(row["adv"]["price"]),
            float(row["adv"]["tradableQuantity"]),
        )
        for row in raw_data
    ]
    return prices


def fetch_bybit_p2p(
    asset: str,
    fiat: str,
    trade_type: TradeType,
    *,
    pay_type: str,
    amount: int = 0,
) -> list[P2PAdv]:
    side = {"buy": 1, "sell": 0}[trade_type.lower()]
    payment = {
        ALFA: 1,
        POCHTA: 59,
        QIWI: 62,
        RAIFFEISEN: 64,
        TINKOFF: 75,
        ROSBANK: 185,
        YANDEX: 274,
    }[pay_type]

    resp = HTTP_SESSION.post(
        "https://api2.bybit.com/spot/api/otc/item/list",
        data={
            "tokenId": asset,
            "currencyId": fiat,
            "payment": payment,
            "side": side,
            "size": 10,
            "page": 1,
            "amount": amount,
        },
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/104.0.0.0 Safari/537.36",
            "Referer": "https://www.bybit.com/",
            "Origin": "https://www.bybit.com",
            "Pragma": "no-cache",
        },
    )

    assert resp.status_code == 200, f"Error fetching BYBIT P2P data. {resp.text}"

    raw_data = resp.json()["result"]["items"]

    return [
        P2PAdv(
            row["nickName"],
            float(row["price"]),
            float(row["quantity"]),
        )
        for row in raw_data
    ]


def fetch_garantex_p2p(
    asset: str,
    fiat: str,
    trade_type: TradeType,
    amount: int = 0,
    *args,
    **kwargs,
) -> list[P2PAdv]:
    market = asset.lower() + fiat.lower()
    resp = requests.get(
        "https://garantex.io/api/v2/depth",
        params={
            "market": market,
        },
    )
    assert resp.status_code == 200, f"Error fetching Garantex market data. {resp.text}"

    raw_data = resp.json()[{"buy": "asks", "sell": "bids"}[trade_type.lower()]]

    return [
        P2PAdv(None, float(row["price"]), float(row["volume"]))
        for row in raw_data
        if float(row["amount"]) >= amount
    ]


def fetch_market_data_binance(symbol: str) -> Symbol:
    resp = HTTP_SESSION.get(
        "https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol.upper()}
    )
    assert resp.status_code == 200, f"Error fetching Binance market data. {resp.text}"

    order = resp.json()
    return float(order["price"])


def fetch_market_data_bybit(symbol: str) -> Symbol:
    resp = HTTP_SESSION.get(
        "https://api-testnet.bybit.com/v2/public/orderBook/L2",
        params={"symbol": symbol.upper()},
    )

    assert resp.status_code == 200, f"Error fetching BYBIT market data. {resp.text}"

    book = resp.json().get("result")

    if not book:
        return 0.0

    order = [order for order in book if order["side"] == "Sell"][0]
    return float(order["price"])


def fetch_market_data_garantex(symbol: str) -> Symbol:
    resp = requests.get(
        "https://garantex.io/api/v2/depth",
        params={
            "market": symbol.lower(),
        },
    )
    assert resp.status_code == 200, f"Error fetching Garantex market data. {resp.text}"

    order = resp.json()["asks"][0]

    return float(order["price"])


def get_data_p2p(
    exchange: str,
    assets: list[str],
    fiat: str,
    trade_type: TradeType,
    *,
    pay_types: list[Union[str, None]],
    amount: int = 0,
) -> P2PData:
    try:
        fetcher = {
            "binance": fetch_binance_p2p,
            "bybit": fetch_bybit_p2p,
            "garantex": fetch_garantex_p2p,
        }[exchange.lower()]
    except KeyError:
        raise UnknownExchange(exchange) from None

    results = {}
    with ThreadPoolExecutor() as tpe:
        future_to_asset_pay_type = {
            tpe.submit(
                fetcher,
                asset,
                fiat,
                trade_type,
                amount=amount,
                pay_type=pay_type,
            ): (asset, pay_type)
            for asset, pay_type in itertools.product(assets, pay_types)
        }
    for future in as_completed(future_to_asset_pay_type):
        results[future_to_asset_pay_type[future]] = future.result()
    return results


def best_price(data: P2PData, asset: str, pay_type: Union[str, None]) -> str:
    adv_list = data[(asset, pay_type)]
    return adv_list[0].price if adv_list else 1_000_000_000


def get_market_data(exchanges: list[str], symbols: list[str]) -> MarketData:
    fetchers = {
        "binance": fetch_market_data_binance,
        "bybit": fetch_market_data_bybit,
        "garantex": fetch_market_data_garantex,
    }
    results = {}
    with ThreadPoolExecutor() as tpe:
        future_to_exchange_symbol = {
            tpe.submit(fetchers[exchange.lower()], symbol): (exchange, symbol)
            for exchange, symbol in itertools.product(exchanges, symbols)
        }
    for future in as_completed(future_to_exchange_symbol):
        results[future_to_exchange_symbol[future]] = future.result()
    return results


if __name__ == "__main__":
    md = get_market_data(["binance", "bybit", "garantex"], ["BTCUSDT", "ETHUSDT"])
    print(md)
