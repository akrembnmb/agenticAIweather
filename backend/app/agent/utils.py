import re
import datetime
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

def resolve_relative_date(expr: str, reference_date: datetime.date = None) -> str:
    """Convert relative date expressions (from LLM) to ISO format."""
    if reference_date is None:
        reference_date = datetime.date.today()

    expr = expr.lower().strip()

    # Basic expressions
    if expr == "today" or expr == "now":
        return reference_date.isoformat()
    if expr == "tomorrow":
        return (reference_date + datetime.timedelta(days=1)).isoformat()
    if expr == "yesterday":
        return (reference_date - datetime.timedelta(days=1)).isoformat()

    # Regex-based relative date expressions
    patterns = [
        (r'in (\d+) days?', lambda m: reference_date + datetime.timedelta(days=int(m.group(1)))),
        (r'(\d+) days? ago', lambda m: reference_date - datetime.timedelta(days=int(m.group(1)))),
        (r'next week', lambda m: reference_date + datetime.timedelta(weeks=1)),
        (r'last week', lambda m: reference_date - datetime.timedelta(weeks=1)),
        (r'next month', lambda m: reference_date + relativedelta(months=1)),
        (r'last month', lambda m: reference_date - relativedelta(months=1)),
        (r'this week', lambda m: reference_date + datetime.timedelta(days=(6 - reference_date.weekday()))),
        (r'last monday', lambda m: reference_date - datetime.timedelta(days=reference_date.weekday() + 7)),
        (r'last sunday', lambda m: reference_date - datetime.timedelta(days=reference_date.weekday() + 1)),
    ]

    for pattern, func in patterns:
        match = re.fullmatch(pattern, expr)
        if match:
            return func(match).isoformat()

    # Final fallback: use fuzzy parser (if date was something like "August 3rd")
    try:
        parsed = date_parser.parse(expr, fuzzy=True, default=datetime.datetime.combine(reference_date, datetime.time()))
        return parsed.date().isoformat()
    except Exception:
        return reference_date.isoformat()
