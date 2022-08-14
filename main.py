import logging
import sys
import time

import schedule

from crypto_parser import gsheets
from crypto_parser.constant import *
from crypto_parser.crypto import (
    TradeType,
    UnknownExchange,
    best_price,
    get_data_p2p,
    get_market_data,
)
from crypto_parser.utils import current_datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)

logger.addHandler(handler)


def update_p2p_data_table_for_exchange(
    exchange: str,
    trade_type: TradeType,
    amount: int = 5000,
):
    pay_types = (
        (TINKOFF, ROSBANK, QIWI, YANDEX, ALFA, POCHTA, RAIFFEISEN)
        if exchange.lower() != "garantex"
        else [None]
    )
    assets = (USDT, BTC, ETH)

    try:
        range_updated_at, range_table = {
            "binance": {"buy": ["B2:B3", "C5:I7"], "sell": ["B9:B10", "C12:I14"]},
            "bybit": {"buy": ["K2:K3", "L5:R7"], "sell": ["K9:K10", "L12:R14"]},
            "garantex": {
                "buy": ["AU2:AU3", "AV5:AV7"],
                "sell": ["AU9:AU10", "AV12:AV14"],
            },
        }[exchange.lower()][trade_type.lower()]
    except KeyError:
        raise UnknownExchange(f"{exchange}/{trade_type}") from None

    try:
        data = get_data_p2p(
            exchange, assets, "RUB", trade_type, pay_types=pay_types, amount=amount
        )

        values = [[best_price(data, asset, pt) for pt in pay_types] for asset in assets]
        current_dt = current_datetime()
        to_write = [
            {
                "range": range_updated_at,
                "values": [["Updated at"], [current_dt]],
            },
            {
                "range": range_table,
                "values": values,
            },
        ]
        logger.info(
            f"{exchange}/{trade_type} P2P table updated: {gsheets.write_spread_data(to_write)}"
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")


def update_market_data_tables():
    ranges = {
        "binance": {
            ETHUSDT: "C16",
            BTCUSDT: "C17",
            ETHBTC: "E16",
            USDTETH: "E17",
            USDTBTC: "G16",
            BTCETH: "G17",
        },
        "bybit": {
            ETHUSDT: "L16",
            BTCUSDT: "L17",
            ETHBTC: "N16",
            USDTETH: "N17",
            USDTBTC: "P16",
            BTCETH: "P17",
        },
        "garantex": {
            ETHUSDT: "AV16",
            BTCUSDT: "AV17",
            ETHBTC: "AX16",
            USDTETH: "AX17",
            USDTBTC: "AZ16",
            BTCETH: "AZ17",
        },
    }

    exchanges = ("binance", "bybit", "garantex")
    symbols = (BTCUSDT, ETHUSDT, ETHBTC, USDTETH, USDTBTC, BTCETH)

    try:
        data = get_market_data(exchanges, symbols)

        to_write = [
            {"range": ranges[e.lower()][s.upper()], "values": [[data[(e, s)]]]}
            for e in exchanges
            for s in symbols
        ]

        logger.info(
            f"Market data tables updated: {gsheets.write_spread_data(to_write)}"
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    logger.info("Crypto parser started")

    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "Binance", "BUY")
    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "Binance", "SELL")
    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "BYBIT", "BUY")
    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "BYBIT", "SELL")
    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "Garantex", "BUY")
    schedule.every(5).minutes.do(update_p2p_data_table_for_exchange, "Garantex", "SELL")
    schedule.every(5).minutes.do(update_market_data_tables)
    logger.info(f"Jobs scheduled: {schedule.get_jobs()}")

    while True:
        schedule.run_pending()
        time.sleep(1)
