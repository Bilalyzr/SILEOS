"""Bounded authenticated read-load evidence. Does not charge, send, or mutate data.

Set GROWTH_LOAD_TOKEN privately. Remote targets require --allow-remote.
This is a rehearsal, not certification of a large consumer deployment.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import statistics
import time
from urllib.parse import urlsplit
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--requests',type=int,default=120)
    parser.add_argument('--concurrency',type=int,default=8)
    parser.add_argument('--p95-ms',type=float,default=1500)
    parser.add_argument('--allow-remote',action='store_true')
    parser.add_argument('--admin',action='store_true',help='Also exercise the admin growth snapshot; token must be an admin')
    parser.add_argument('--release-ref',required=True)
    args=parser.parse_args()
    parsed=urlsplit(args.url)
    local=parsed.hostname in {'localhost','127.0.0.1','::1'}
    if parsed.scheme not in {'http','https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('Supply a plain HTTP(S) base URL, without credentials or query strings')
    if not local and (not args.allow_remote or parsed.scheme != 'https'):
        parser.error('Remote validation requires HTTPS and explicit --allow-remote')
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 64:
        parser.error('Use 1..10000 requests and 1..64 concurrent clients; larger rehearsals need a distributed load plan')
    token=os.environ.get('GROWTH_LOAD_TOKEN','').strip()
    if not token:
        parser.error('Set GROWTH_LOAD_TOKEN in the private process environment; never put credentials in arguments')
    paths=['/api/v1/platform/growth/my-billing','/api/v1/platform/growth/my-offers','/api/v1/platform/growth/offers']
    if args.admin:
        paths.append('/api/v1/platform/growth/admin')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*unused):
            return None
    def sample(index):
        start=time.perf_counter(); path=paths[index%len(paths)]
        request=urllib.request.Request(args.url.rstrip('/')+path,headers={'Authorization':'Bearer '+token})
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:
                json.loads(response.read())
                status=response.status
        except Exception as exc:
            status=getattr(exc,'code',0)
        return {'route':path,'status':status,'ms':round((time.perf_counter()-start)*1000,2)}
    start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        samples=list(executor.map(sample,range(args.requests)))
    latency=sorted(s['ms'] for s in samples)
    failures=sum(s['status'] != 200 for s in samples)
    report={'release_ref':args.release_ref,'target':args.url,'requests':args.requests,'concurrency':args.concurrency,
        'p50_ms':statistics.median(latency),'p95_ms':latency[min(len(latency)-1,int(len(latency)*.95))],
        'failures':failures,'duration_seconds':round(time.perf_counter()-start,2),'capacity_certified':False,
        'scope':'Authenticated read journeys only. Payment, browser, PostgreSQL failover and sustained distributed load remain separate gates.'}
    report['passed']=failures == 0 and report['p95_ms'] <= args.p95_ms
    out=Path(__file__).resolve().parents[1]/'.local/growth-load-evidence.json'
    out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
