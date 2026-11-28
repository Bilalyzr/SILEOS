"""Remove the throwaway accounts and institutions made by a Campus role check.
Only touches institutions named 'Campus flow check %' and users 'campchk-%'."""
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
FK = """select cl.relname, att.attname, rf.relname from pg_constraint c
  join pg_class cl on cl.oid=c.conrelid join pg_class rf on rf.oid=c.confrelid
  join pg_attribute att on att.attrelid=c.conrelid and att.attnum=c.conkey[1]
  where c.contype='f' and array_length(c.conkey,1)=1"""
fks = db.execute(text(FK)).fetchall()
def purge(table, ids, seen=()):
    if not ids or table in seen: return
    for child, col, parent in fks:
        if parent != table or child == table: continue
        rows = [r[0] for r in db.execute(text(f'select id from "{child}" where "{col}" = any(:i)'), {"i": ids})] \
            if db.execute(text("select 1 from information_schema.columns where table_name=:t and column_name='id'"), {"t": child}).first() else None
        if rows: purge(child, rows, seen + (table,))
        db.execute(text(f'delete from "{child}" where "{col}" = any(:i)'), {"i": ids})
    db.execute(text(f'delete from "{table}" where id = any(:i)'), {"i": ids})
inst = [r[0] for r in db.execute(text("select id from institutions where name like 'Campus flow check %'"))]
purge("institutions", inst)
users = [r[0] for r in db.execute(text("select id from users where user_email like 'campchk-%@example.com'"))]
purge("users", users)
db.commit()
print("removed institutions", inst, "users", users)
