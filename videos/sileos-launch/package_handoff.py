from pathlib import Path
import json,subprocess,shutil,zipfile,html
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent
out=root.parents[1]/'output/video/SILeos'
ff='C:/Users/Admin/AppData/Roaming/npm/ffmpeg.exe'
stills=out/'cinematic-stills';stills.mkdir(exist_ok=True)
selected=[('01-tradition',3.9),('02-new-chapter',6.5),('03-expanded-name',12.12),('04-sileos-reveal',16.9),('05-virtual-labs',22.9),('06-spatial-learning',24.4),('07-in-your-pocket',39.3),('08-coming-soon',43.5)]
for name,t in selected:
    subprocess.run([ff,'-y','-loglevel','error','-ss',str(t),'-i',str(out/'SILeos-Coming-Soon-1080p.mp4'),'-frames:v','1',str(stills/f'{name}.png')],check=True)
sheet=Image.new('RGB',(1440,1420),'#0b2540');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype(str(root/'assets/fonts/PlusJakartaSans.ttf'),20)
for i,(name,t) in enumerate(selected):
    im=Image.open(stills/f'{name}.png').convert('RGB');im.thumbnail((336,598))
    x=18+(i%4)*360;y=22+(i//4)*700
    sheet.paste(im,(x,y));draw.text((x,y+612),f'{t:05.2f}s / {name[3:]}',fill='#ffffff',font=font)
sheet.save(out/'SILeos-storyboard-contact-sheet.jpg',quality=94)
shutil.copytree(root/'brand',out/'brand',dirs_exist_ok=True)
captures=out/'product-captures'
times=json.loads((captures/'recording-timings.json').read_text())
for clip in times:
    # Portrait-friendly source panel, with the genuine interface and controls intact.
    subprocess.run([ff,'-y','-loglevel','error','-ss',str(clip['start']),'-i',str(captures/clip['raw']),'-t',str(clip['duration']),'-vf','crop=1140:770:230:56','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(captures/f'{clip["name"]}.mp4')],check=True)
sources=json.loads((root/'audio_sources.json').read_text())
starts={'history':.7,'expansion':7.6,'name':13.35,'features':18.8,'close':37}
timing=[{'file':f'{v["id"]}.wav','start':starts[v['id']],'duration':v['duration'],'words':v['word_timestamps']} for v in sources['voices']]
(out/'narration-timings.json').write_text(json.dumps(timing,indent=2))
project=out/'editable-project';project.mkdir(exist_ok=True)
for name in ['index.html','hyperframes.json','package.json','meta.json','frame.md','BRIEF.md','STORYBOARD.md','SCRIPT.md','ledger.json']:
    shutil.copy2(root/name,project/name)
for name in ['assets','compositions/frames']:
    shutil.copytree(root/name,project/name,dirs_exist_ok=True)
(project/'README.md').write_text('# Editable SILeos reference\n\nRequirements: Node22+, FFmpeg, and HyperFrames0.8.30. Local fonts, GSAP and audio are included; no provider login is needed to render existing assets.\n\nPreview: `npx --yes hyperframes@0.8.30 preview --background --port3405` (insert a space between --port and3405).\n\nCheck: `npx --yes hyperframes@0.8.30 check`\n\nRender: `npx --yes hyperframes@0.8.30 render --quality high --fps30 --workers1 --low-memory-mode --output SILeos.mp4` (use spaces: --fps30 means --fps 30; --workers1 means --workers 1).\n\nThe source renders the initial mix. The delivered MP4 has a final−16LUFS mastering pass. Keep that loudness target on re-export.\n')
# Keep commands immediately pasteable.
p=project/'README.md';s=p.read_text().replace('--port3405','--port 3405').replace(' (insert a space between --port and3405)','').replace('--fps30','--fps 30').replace('--workers1','--workers 1');s=s.split(' (use spaces:')[0]+'\n\nThe delivered MP4 has a final −16 LUFS mastering pass; preserve that target on re-export.\n';p.write_text(s)
readme='''# SILeos — complete video handoff

1. Upload **SILeos-Manus-Claude-Handoff.zip** to Manus or Claude.
2. Paste **MANUS_CLAUDE_PROMPT.md** as the task prompt.
3. The agent should follow **FRAME_BY_FRAME_SCRIPT.md**, using the included media.

## What is included

- A20-shot script with exact45-second timing, full narration, transitions and36capability names.
- Copy-paste rebuilding prompt.
- Finished1080pfilm and compact720pWhatsApp version.
- Eight clean cinematic PNG stills and a contact sheet.
- Real screenshots of the LMS library, DNA lab and molecule lab.
- Two silent H.264 product recordings: DNA unzipping and molecule switching/rotation. Raw WebM files remain in the local folder; the ZIP contains the clean trimmed MP4s.
- New logo/app icon/wordmark, plus36editable SVG feature symbols.
- Original narration, music and SFX; local fonts; editable HTML/GSAP source.

The cinematic phone and feature tiles are designed illustrations. Files under product-captures are genuine recordings/screenshots of the public local LMS, with no mocked API data. Desktop captures do not demonstrate physical AR/VR operation.

The brand expansion used in this cut is Sasha Infinity Learning & Education Operating System → SILeos. Both learning and teaching are explicitly stated.
'''
for a,b in [('A20','A 20'),('exact45','exact 45'),('and36','and 36'),('Finished1080pfilm','Finished 1080p film'),('compact720pWhatsApp','compact 720p WhatsApp'),('plus36editable','plus 36 editable')]:readme=readme.replace(a,b)
(out/'START_HERE.md').write_text(readme)
for f in ['FRAME_BY_FRAME_SCRIPT.md','MANUS_CLAUDE_PROMPT.md']:
    p=out/f;s=p.read_text()
    for a,b in [('polished45','polished 45'),('Build at1080','Build at 1080'),(',9:16,30fps,45seconds',', 9:16, 30 fps, 45 seconds'),('smaller720×1280WhatsApp','smaller 720×1280 WhatsApp'),('approximately−16LUFS','approximately −16 LUFS'),('below−1.5dBTP','below −1.5 dBTP'),('contains20editorial','contains 20 editorial'),('the12feature','the 12 feature'),('and36capability','and 36 capability'),('a6–8frame','a 6–8 frame'),('at00:','at 00:'),('approximately8.60','approximately 8.60'),('11.80seconds','11.80 seconds'),('before the13.30','before the 13.30'),('first11cards lasts1.40seconds','first 11 cards lasts 1.40 seconds'),('last lasts1.60seconds','last lasts 1.60 seconds'),('first0.35seconds','first 0.35 seconds'),('arrive0.20seconds','arrive 0.20 seconds'),('Starts18.80','Starts 18.80'),('Starts13.35','Starts 13.35'),('Starts37.00','Starts 37.00'),('Begins7.60','Begins 7.60'),('about30.22','about 30.22'),('at17.82','at 17.82'),('at34.82','at 34.82'),('at40.60','at 40.60'),('final1.8seconds','final 1.8 seconds'),('by44.90','by 44.90'),('first45seconds','first 45 seconds'),('and36editable','and 36 editable'),('count59','count 59')]:s=s.replace(a,b)
    p.write_text(s)
gallery='''<!doctype html><html><head><meta charset="utf-8"><title>SILeos · Launch kit</title><style>body{margin:0;padding:60px;background:#0b2540;color:#fff;font:18px system-ui}h1{font-size:64px;margin:0}p{color:#c5d4df}a{color:#ffb06e}video{width:320px;border-radius:24px;box-shadow:0 20px60px #0008}.row{display:flex;gap:24px;flex-wrap:wrap;margin:32px0}.row img{width:250px;border-radius:18px}.wide img{width:600px}.wide video{width:600px}</style></head><body><h1>SILeos</h1><p>The next chapter. Your complete launch handoff.</p><p><a href="FRAME_BY_FRAME_SCRIPT.md">Frame-by-frame script</a> · <a href="MANUS_CLAUDE_PROMPT.md">Manus / Claude prompt</a></p><video controls poster="cinematic-stills/08-coming-soon.png" src="SILeos-WhatsApp-720p.mp4"></video><h2>Cinematic stills</h2><div class="row">'''
gallery+=''.join(f'<a href="cinematic-stills/{name}.png"><img src="cinematic-stills/{name}.png" alt="{name}"></a>' for name,t in selected)
gallery+='</div><h2>Real product captures</h2><div class="row wide"><img src="product-captures/lab-library.png"><img src="product-captures/molecule-interaction-panel.png"></div><div class="row wide">'+''.join(f'<video controls src="product-captures/{c["name"]}.mp4"></video>' for c in times)+'</div></body></html>'
(out/'PREVIEW.html').write_text(gallery)
zpath=out.parent/'SILeos-Manus-Claude-Handoff.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.suffix!='.webm':z.write(p,p.relative_to(out).as_posix())
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    print(json.dumps({'zip':str(zpath),'files':len(z.infolist()),'MB':round(zpath.stat().st_size/1024/1024,2),'clean_stills':len(selected),'recordings':len(times)}))
