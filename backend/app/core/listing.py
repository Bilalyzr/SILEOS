"""Allowlisted ordering, bounded pagination and spreadsheet-safe CSV."""
import csv
import io
from app.core.csv_safety import sanitize_csv_cell
from sqlalchemy import or_, cast, String


def filtered(query, search, columns):
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(or_(*(cast(c, String).ilike("%" + escaped + "%", escape="\\") for c in columns)))
    return query


def paginate(query, page, page_size, sort, order, sort_columns, tie_column):
    if sort not in sort_columns or order not in ("asc", "desc"):
        raise ValueError("Choose a supported sort column and direction.")
    column = sort_columns[sort]
    total = query.order_by(None).count()
    rows = query.order_by(None).order_by(column.desc() if order == "desc" else column.asc(), tie_column.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, {"total": total, "page": page, "page_size": page_size}


def csv_stream(rows, columns):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(columns)
    yield "\ufeff" + buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
    for row in rows:
        values = []
        for col in columns:
            value = str(row.get(col, "") if row.get(col) is not None else "")
            values.append(sanitize_csv_cell(value))
        writer.writerow(values)
        yield buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
