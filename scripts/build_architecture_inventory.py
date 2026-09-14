"""Static source inventory; never imports application modules or reads secrets."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    app = (ROOT / 'frontend/src/App.tsx').read_text(encoding='utf-8-sig')
    routes = sorted(set(re.findall(r'\bpath="([^"]+)"', app)))
    pages = sorted(set(re.findall(r'import\("(@/pages/[^"]+)"\)', app)))
    tree = ast.parse((ROOT / 'backend/app/main.py').read_text(encoding='utf-8-sig'))
    mounts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'include_router':
            opts = {k.arg: ast.literal_eval(k.value) for k in node.keywords if isinstance(k.value, (ast.Constant, ast.List))}
            mounts.append({'router':ast.unparse(node.args[0]),'prefix':opts.get('prefix',''), 'line':node.lineno})
    tables=[]
    for file in sorted((ROOT/'backend/app/models').glob('*.py')):
        for match in re.finditer(r'__tablename__\s*=\s*[\x27\x22]([^\x27\x22]+)',file.read_text(encoding='utf-8-sig')):
            tables.append({'table':match[1],'file':file.relative_to(ROOT).as_posix()})
    prefixes = ['backend/app','backend/alembic','backend/scripts','frontend/src','frontend/labs','frontend/scripts','flutter_app/lib','streaming-service','nginx','scripts']
    extensions={'.py','.ts','.tsx','.js','.jsx','.mjs','.cjs','.css','.html','.dart','.conf','.sh','.ps1'}
    sources=[]
    for prefix in prefixes:
        base=ROOT/prefix
        if not base.exists(): continue
        for file in sorted(base.rglob('*')):
            rel=file.relative_to(ROOT).as_posix()
            if not file.is_file() or file.suffix not in extensions or any(p in file.parts for p in ('__pycache__','node_modules','vendor','.venv')): continue
            if '/__tests__/' in rel or file.name.endswith(('.test.ts','.test.tsx')): continue
            sources.append({'file':rel,'lines':len(file.read_text(encoding='utf-8-sig',errors='replace').splitlines())})
    result={'snapshot':'2026-09-06','scope':'Outer workspace source; static inventory, not a claim all modules are mounted or runtime-tested.',
        'counts':{'route_patterns':len(routes),'lazy_page_modules':len(pages),'router_mounts':len(mounts),'declared_tables':len(tables),'source_files':len(sources)},
        'routes':routes,'page_modules':pages,'api_router_mounts':sorted(mounts,key=lambda m:m['line']),'declared_tables':tables,'source_files':sources}
    (ROOT/'docs/ARCHITECTURE_INVENTORY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Codebase index','', 'Generated from the outer workspace on 6 September 2026. Secrets, runtime data, duplicate checkouts and vendor bundles are excluded. File presence does not prove runtime use.','', '## Frontend route patterns','']
    lines.extend(f'- `{route}`' for route in routes)
    lines.extend(['','## Backend router registrations','','| Router | Prefix | main.py line |','|---|---|---|'])
    lines.extend(f"| {m['router']} | `{m['prefix']}` | {m['line']} |" for m in result['api_router_mounts'])
    lines.extend(['','## Declared database tables','','| Table | Model source |','|---|---|'])
    lines.extend(f"| `{t['table']}` | `{t['file']}` |" for t in tables)
    lines.extend(['','## Source file inventory','','| File | Lines |','|---|---|'])
    lines.extend(f"| `{s['file']}` | {s['lines']} |" for s in sources)
    (ROOT/'docs/CODEBASE_INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result['counts']))
    return result

if __name__ == '__main__': build()
