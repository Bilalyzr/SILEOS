"""Local development migration with an SQLite backup; never targets production."""
from pathlib import Path
from datetime import datetime
import json,os,sqlite3,subprocess,sys
root=Path(__file__).resolve().parents[1]
backend=root/'backend'
config=json.loads((root/'.claude/launch.json').read_text(encoding='utf-8'))['configurations'][0]
env={**os.environ,**{k:str(v) for k,v in config['env'].items()}}
assert env['DATABASE_URL']=='sqlite:///./visual_qa.db'
env['PYTHONPATH']=str(backend/'.astra-tools')
source=backend/'visual_qa.db'
backup=root/'.toolchains/implementation-audit'/('before-integrated-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.db')
with sqlite3.connect(source) as original,sqlite3.connect(backup) as target:
    original.backup(target)
    assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print('Development database backup verified.')
subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=backend,env=env,check=True)
with sqlite3.connect(source) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    print('Migration:',db.execute('select version_num from alembic_version').fetchone()[0])
