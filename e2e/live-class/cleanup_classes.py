from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
ids = [r[0] for r in db.execute(text("select id from live_classes where title like 'LC suite%' or title like 'End repro %'"))]
if not ids:
    print("no suite classes to remove")
else:
    fks = db.execute(text("""
        select cl.relname, att.attname from pg_constraint c
        join pg_class cl on cl.oid=c.conrelid join pg_class rf on rf.oid=c.confrelid
        join pg_attribute att on att.attrelid=c.conrelid and att.attnum=c.conkey[1]
        where c.contype='f' and rf.relname='live_classes'""")).fetchall()
    # live coding rows hang off live_coding_challenges, remove those children first
    db.execute(text("delete from live_coding_submissions where live_id in (select id from live_coding_challenges where class_id = any(:ids))"), {"ids": ids})
    for table, col in fks:
        n = db.execute(text(f'delete from "{table}" where "{col}" = any(:ids)'), {"ids": ids}).rowcount
        if n: print("  removed", n, "from", table)
    db.execute(text("delete from live_classes where id = any(:ids)"), {"ids": ids})
    db.commit()
    print("removed suite classes", ids)
