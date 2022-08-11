import time
from typing import Union

import schedule

from crypto_parser import gsheets, p2p
from crypto_parser.constant import ASSETS, PAY_TYPES
from crypto_parser.p2p import TradeType, UnknownExchange
from crypto_parser.utils import current_datetime


def update_table_for_exchange(
    exchange: str,
    assets: list[str],
    trade_type: TradeType,
    pay_types: list[Union[str, None]],
    amount: int = 5000,
):
    start = time.time()

    try:
        range_updated_at, range_table = {
            "binance": {"buy": ["B3:B4", "C6:I8"], "sell": ["B12:B13", "C15:I17"]},
            "bybit": {"buy": ["K3:K4", "L6:R8"], "sell": ["K12:K13", "L15:R17"]},
            "garantex": {
                "buy": ["AU3:AU4", "AV6:AV8"],
                "sell": ["AU12:AU13", "AV15:AV17"],
            },
        }[exchange.lower()][trade_type.lower()]
    except KeyError:
        raise UnknownExchange(f"{exchange}/{trade_type}") from None

    try:
        data = p2p.get_data(
            exchange, assets, "RUB", trade_type, pay_types=pay_types, amount=amount
        )

        to_write = [
            {
                "range": range_updated_at,
                "values": [["Updated at"], [current_datetime()]],
            },
            {
                "range": range_table,
                "values": [
                    [p2p.best_price(data, asset, pt) for pt in pay_types]
                    for asset in assets
                ],
            },
        ]
        print(
            f"{exchange}/{trade_type} table updated:",
            gsheets.write_spread_data(to_write),
        )
        print("Duration:", round(time.time() - start, 2), "sec")
    except Exception as e:
        print("Error:", e.args[0])
    print()


schedule.every(30).minutes.do(
    update_table_for_exchange, "Binance", ASSETS, "BUY", PAY_TYPES
)
schedule.every(30).minutes.do(
    update_table_for_exchange, "Binance", ASSETS, "SELL", PAY_TYPES
)
schedule.every(30).minutes.do(
    update_table_for_exchange, "BYBIT", ASSETS, "BUY", PAY_TYPES
)
schedule.every(30).minutes.do(
    update_table_for_exchange, "BYBIT", ASSETS, "SELL", PAY_TYPES
)
schedule.every(30).minutes.do(
    update_table_for_exchange, "Garantex", ASSETS, "BUY", [None]
)
schedule.every(30).minutes.do(
    update_table_for_exchange, "Garantex", ASSETS, "SELL", [None]
)


if __name__ == "__main__":
    print("Crypto parser started...")
    while True:
        schedule.run_pending()
        time.sleep(1)
