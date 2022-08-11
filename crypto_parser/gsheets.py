from pathlib import Path

import gspread

SPREAD_SHEETS_SERVICE_ACCOUNT = gspread.service_account(
    filename=Path(__file__).parent.parent / "service_account.json"
)


def write_spread_data(data: list[dict]):
    table = SPREAD_SHEETS_SERVICE_ACCOUNT.open_by_url(
        "https://docs.google.com/spreadsheets/d/1vBN0Tp37ZB7BUIOMbI72BerW2zn8rCV9UlnvPWegb6w"
    )
    sheet = table.worksheet("Лист1")
    return sheet.batch_update(data)
