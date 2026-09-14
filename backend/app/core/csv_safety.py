"""CSV formula-injection hardening.

Any CSV cell whose text begins with `=`, `+`, `-`, `@`, a tab, or a carriage
return is interpreted by Excel/LibreOffice/Google Sheets as a formula when
the file is opened — a display_name (or any other user-controlled string)
like `=cmd|'/c calc'!A1` executes on open. This is the standard CSV-
injection defense (OWASP): prefix such cells with a leading single-quote so
spreadsheet apps render them as literal text instead of evaluating them.

Shared by every CSV export endpoint that writes user-controlled strings —
do not build a one-off escaper per router.
"""
from typing import Any

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> Any:
    """Return `value` unchanged unless it's a string starting with a
    formula-triggering character, in which case a leading `'` is
    prepended. Non-string values (numbers, None, bool) pass through as-is
    — csv.writer stringifies them and none of them can start with a
    dangerous prefix."""
    if isinstance(value, str) and (value.startswith(_DANGEROUS_PREFIXES) or value.lstrip().startswith(_DANGEROUS_PREFIXES)):
        return "'" + value
    return value
