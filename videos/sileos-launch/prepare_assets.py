from pathlib import Path
import json, urllib.request, concurrent.futures

root=Path(__file__).resolve().parent
data=json.loads((root/'audio_sources.json').read_text())
items=[(v['audio_url'],root/'assets/audio'/f"{v['id']}.wav") for v in data['voices']]
items.append((data['music']['audio_url'],root/'assets/audio/music.wav'))
items.append(('https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js',root/'assets/gsap.min.js'))
def download(pair):
    url,dest=pair
    if not dest.exists():
        with urllib.request.urlopen(url,timeout=90) as response:
            dest.write_bytes(response.read())
    return {'file':str(dest.relative_to(root)), 'bytes':dest.stat().st_size}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    print(json.dumps(list(pool.map(download,items))))
