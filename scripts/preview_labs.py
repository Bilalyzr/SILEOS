"""Open the supplied labs without needing an LMS database or a frontend build.

Usage: python scripts/preview_labs.py --port 3412
Then open http://127.0.0.1:3412/labs/cbse/index.html
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=3412)
    args = parser.parse_args()
    public = Path(__file__).resolve().parents[1] / 'frontend/public'
    if not (public / 'labs/cbse/index.html').is_file():
        parser.error('The lab library is missing. In frontend/, run npm run labs:build.')
    handler = partial(SimpleHTTPRequestHandler, directory=str(public))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    print(f'Open http://127.0.0.1:{args.port}/labs/cbse/index.html', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
