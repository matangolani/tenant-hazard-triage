"""
Tenant Hazard Triage — turn a severity into indicative calendar deadlines.

Awaab's Law (Hazards in Social Housing Regulations) timescales, per the gov.uk landlord guidance:
  emergency   — investigate and make safe within 24 hours of becoming aware
  significant — investigate within 10 working days; make safe within 5 working days of the
                investigation concluding; written summary to the tenant within 3 working days of it
Working days exclude weekends and England & Wales bank holidays (data/bank_holidays_england_wales.json,
from gov.uk). The dates are indicative decision support: the clock starts when the landlord becomes aware,
which this tool approximates with the time the report was received.
"""
import json, os
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")

_BH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bank_holidays_england_wales.json")
try:
    BANK_HOLIDAYS = {date.fromisoformat(d) for d in json.load(open(_BH_PATH))["dates"]}
except FileNotFoundError:          # still usable without the file; weekends are always excluded
    BANK_HOLIDAYS = set()


def is_working_day(d):
    return d.weekday() < 5 and d not in BANK_HOLIDAYS


def add_working_days(start, n):
    """The date n working days after `start` (a date or datetime). Day 0 is the start date itself."""
    d = start.astimezone(UK).date() if isinstance(start, datetime) else start   # UK calendar day
    while n > 0:
        d += timedelta(days=1)
        if is_working_day(d):
            n -= 1
    return d


def deadlines(severity, received_at):
    """Indicative deadlines for a severity. received_at: timezone-aware datetime."""
    if severity == "emergency":
        return {"make_safe_by": (received_at + timedelta(hours=24)).isoformat(timespec="minutes"),
                "basis": "investigate and make safe within 24 hours"}
    if severity == "significant":
        return {"investigate_by": add_working_days(received_at, 10).isoformat(),
                "make_safe": "within 5 working days of the investigation",
                "written_summary": "within 3 working days of the investigation",
                "basis": "investigate within 10 working days (weekends and bank holidays excluded)"}
    if severity == "routine":
        return {"basis": "outside Awaab's Law timescales; normal repair policy"}
    return {"basis": "refer to a human to gather more information"}
