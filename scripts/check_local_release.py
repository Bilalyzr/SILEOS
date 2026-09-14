"""Bounded local-only load check and isolated database restore rehearsal."""
import concurrent.futures,json,sqlite3,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.toolchains/implementation-audit'
OUT.mkdir(parents=True,exist_ok=True)
endpoints=['/health','/api/v1/virtual-labs','/api/v1/lab-studio/curriculum']
def request(path):
    start=time.perf_counter()
    try:
        with urllib.request.urlopen('http://127.0.0.1:8012'+path,timeout=20) as response:
            data=response.read();status=response.status
        return {'path':path,'status':status,'ms':round((time.perf_counter()-start)*1000,2),'bytes':len(data)}
    except Exception as exc:return {'path':path,'error':type(exc).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    samples=list(pool.map(request,endpoints*20))
latencies=sorted(s['ms'] for s in samples if 'ms' in s)
report={'target':'local development API :8012','concurrency':8,'requests':60,'failures':[s for s in samples if s.get('status')!=200], 'p50_ms':latencies[len(latencies)//2] if latencies else None,'p95_ms':latencies[min(len(latencies)-1,int(len(latencies)*.95))] if latencies else None,'samples':samples}
snapshot=OUT/'integrated-recovery-snapshot.db';restored=OUT/'integrated-recovery-restored.db'
with sqlite3.connect(ROOT/'backend/visual_qa.db') as source,sqlite3.connect(snapshot) as backup:source.backup(backup)
with sqlite3.connect(snapshot) as backup,sqlite3.connect(restored) as target:
    backup.backup(target)
    assert target.execute('pragma integrity_check').fetchone()[0]=='ok'
    tables=[r[0] for r in backup.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
    for name in tables:
        safe='"'+name.replace('"','""')+'"'
        assert backup.execute('select count(*) from '+safe).fetchone()==target.execute('select count(*) from '+safe).fetchone()
    report['isolated_restore']={'integrity':'ok','tables_compared':len(tables),'migration':target.execute('select version_num from alembic_version').fetchone()[0]}
(OUT/'integrated-release-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
if report['failures']:raise SystemExit(1)
