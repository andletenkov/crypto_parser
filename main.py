import logging
import sys
import time
from typing import Union

import schedule

from crypto_parser import gsheets, p2p
from crypto_parser.constant import *
from crypto_parser.p2p import TradeType, UnknownExchange
from crypto_parser.utils import current_datetime

PAY_TYPES = (TINKOFF, ROSBANK, QIWI, YANDEX, ALFA, POCHTA, RAIFFEISEN)
ASSETS = (USDT, BTC, ETH)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)

logger.addHandler(handler)


def update_table_for_exchange(
    exchange: str,
    assets: list[str],
    trade_type: TradeType,
    pay_types: list[Union[str, None]],
    amount: int = 5000,
):
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
        data = p2p.get_data(
            exchange, assets, "RUB", trade_type, pay_types=pay_types, amount=amount
        )

        values = [
            [p2p.best_price(data, asset, pt) for pt in pay_types] for asset in assets
        ]
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
            f"{exchange}/{trade_type} table updated: {gsheets.write_spread_data(to_write)}"
        )
    except Exception as e:
        logger.error("Error:", str(e))


schedule.every(5).minutes.do(
    update_table_for_exchange, "Binance", ASSETS, "BUY", PAY_TYPES
)
schedule.every(5).minutes.do(
    update_table_for_exchange, "Binance", ASSETS, "SELL", PAY_TYPES
)
schedule.every(5).minutes.do(
    update_table_for_exchange, "BYBIT", ASSETS, "BUY", PAY_TYPES
)
schedule.every(5).minutes.do(
    update_table_for_exchange, "BYBIT", ASSETS, "SELL", PAY_TYPES
)
schedule.every(5).minutes.do(
    update_table_for_exchange, "Garantex", ASSETS, "BUY", [None]
)
schedule.every(5).minutes.do(
    update_table_for_exchange, "Garantex", ASSETS, "SELL", [None]
)


if __name__ == "__main__":
    logger.info("Crypto parser started")
    while True:
        schedule.run_pending()
        time.sleep(1)
