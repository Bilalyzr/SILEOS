from pathlib import Path
import json, html, shutil
root=Path(__file__).resolve().parent
sources=json.loads((root/'audio_sources.json').read_text())
starts={'history':.7,'expansion':7.6,'name':13.35,'features':18.8,'close':37.0}
scenes=[('01-origin',0,18),('02-features',18,17),('03-pocket',35,10)]
esc=lambda x:html.escape(json.dumps(x,separators=(',',':')),quote=True)
audio=[]
for v in sources['voices']:
    audio.append(f'<audio id="voice-{v["id"]}" src="assets/audio/{v["id"]}.wav" data-start="{starts[v["id"]]}" data-duration="{v["duration"]}" data-track-index="10" data-volume="1.2"></audio>')
envelope={'version':1,'lanes':[{'target':'volume','points':[{'t':t,'v':v} for t,v in [(0,0),(.65,.085),(6.9,.085),(7.3,.13),(7.6,.085),(12.6,.085),(13,.15),(13.35,.08),(17.5,.08),(18.05,.28),(18.65,.085),(30.2,.085),(30.9,.36),(35.7,.36),(36.65,.08),(42.4,.08),(43,.24),(44.9,0)]]}]}
eq={'version':1,'nodes':[{'id':'presence','type':'peaking','label':'Space for narration','params':{'frequency':2400,'gain':-3,'q':.7}}]}
audio.append(f'<audio id="music" src="assets/audio/music.wav" data-start="0" data-duration="45" data-track-index="11" data-automation="{esc(envelope)}" data-fx-chain="{esc(eq)}"></audio>')
sfx=[('riser',11.1,2.1,.12),('impact',13.3,1.5,.16),('whoosh',4.3,.7,.13),('whoosh',17.82,.7,.14),('whoosh',34.82,.7,.14),('impact',40.6,1.5,.15)]
for i in range(12):sfx.append(('click',18+i*1.4,.22,.28))
for i,(name,start,dur,vol) in enumerate(sfx):
    audio.append(f'<audio id="sfx-{i}" src="assets/audio/{name}.mp3" data-start="{start}" data-duration="{dur}" data-track-index="{20+i}" data-volume="{vol}"></audio>')
hosts='\n'.join(f'<div id="macro-{sid}" class="scene"><div class="clip scene" data-composition-id="{sid}" data-composition-src="compositions/frames/{sid}.html" data-start="{start}" data-duration="{dur}" data-width="1080" data-height="1920" data-track-index="1"></div></div>' for sid,start,dur in scenes)
doc='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1080,height=1920"><title>SILeos — Coming soon</title><script src="assets/gsap.min.js"></script><style>*{box-sizing:border-box}html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#0b2540}#root{position:relative;width:1080px;height:1920px;overflow:hidden}.scene,.base{position:absolute;inset:0;width:1080px;height:1920px}.base{background:#f6f8fc}audio{display:none}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="45" data-width="1080" data-height="1920"><div class="clip base" data-start="0" data-duration="45" data-track-index="0"></div>'''+hosts+'\n'+'\n'.join(audio)+'''</div><script>window.__timelines=window.__timelines||{};window.__timelines["main"]=gsap.timeline({paused:true});
// <seams:auto>
// </seams:auto>
</script></body></html>'''
(root/'index.html').write_text(doc,encoding='utf8')
ledger={'fps':30,'seams':[{'id':'origin-to-features','cut':18,'technique':'cut-the-curve LEFT','exit':{'selector':'#macro-01-origin','axis':'x','dir':-1,'dur':.25},'entry':{'selector':'#macro-02-features','axis':'x','dir':-1,'dur':.32,'travel':10}},{'id':'features-to-pocket','cut':35,'technique':'cut-the-curve LEFT','exit':{'selector':'#macro-02-features','axis':'x','dir':-1,'dur':.25},'entry':{'selector':'#macro-03-pocket','axis':'x','dir':-1,'dur':.32,'travel':10}}]}
(root/'ledger.json').write_text(json.dumps(ledger,indent=2))
story=(root/'STORYBOARD.md').read_text().replace('status: outline','status: animated')
story=story.replace('assets/sileos-mark.svg, assets/sileos-mark-white.svg, original phone illustration','assets/sileos-mark.svg').replace('assets/sileos-mark.svg, original feature SVG glyphs','assets/sileos-mark.svg').replace('assets/sileos-mark.svg, assets/sileos-mark-white.svg','assets/sileos-mark.svg')
(root/'STORYBOARD.md').write_text(story)
tokens={'title':'SILeos','description':'Learning and teaching operating system','colors':['#ff751f','#fbbf24','#17233a','#0b2540','#f6f8fc'],'fonts':['Plus Jakarta Sans']}
(root/'capture/extracted/tokens.json').write_text(json.dumps(tokens,indent=2))
(root/'capture/extracted/visible-text.txt').write_text((root/'BRIEF.md').read_text())
(root/'capture/extracted/asset-descriptions.md').write_text('No website capture. Source is user brief and implemented LMS capabilities. Original infinity-book vector mark, pearl-glass feature symbols and conceptual phone illustration; local product fonts. Audio from HeyGen voice synthesis and catalog.\n')
(root/'audio_meta.json').write_text(json.dumps({'voices':[dict(frame=1 if v['id'] in ['history','expansion','name'] else 2 if v['id']=='features' else 3,path=f'assets/audio/{v["id"]}.wav',start=starts[v['id']],duration=v['duration']) for v in sources['voices']],'bgm':{'path':'assets/audio/music.wav','provider':'HeyGen catalog','id':sources['music']['id']},'captions':'designed titles; no duplicate caption strip'},indent=2))
print('Master built:45seconds,3scenes,5voice segments,12feature impacts.')
