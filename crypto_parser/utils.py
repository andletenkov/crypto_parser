import datetime
import zoneinfo


def current_datetime(tz: str = "Europe/Moscow") -> str:
    return datetime.datetime.now(zoneinfo.ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")
