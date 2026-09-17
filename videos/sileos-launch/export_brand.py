from pathlib import Path
import re,json
root=Path(__file__).resolve().parent
out=root/'brand';out.mkdir(exist_ok=True)
(out/'feature-icons').mkdir(exist_ok=True)
mark=(root/'assets/sileos-mark.svg').read_text()
white=(root/'assets/sileos-mark-white.svg').read_text()
(out/'SILeos-mark.svg').write_text(mark)
(out/'SILeos-mark-white.svg').write_text(white)
inner=re.sub(r'^<svg[^>]+>','',white).removesuffix('</svg>')
(out/'SILeos-app-icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 512 512"><defs><linearGradient id="app-fire" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse"><stop stop-color="#fbbf24"/><stop offset=".48" stop-color="#ff751f"/><stop offset="1" stop-color="#b23c05"/></linearGradient></defs><rect x="8" y="8" width="496" height="496" rx="114" fill="url(#app-fire)" stroke="#ffd6a8" stroke-width="3"/>'+inner+'</svg>')
feature_source=(root/'compositions/frames/02-features.html').read_text()
icons=re.findall(r"^\s+(\w+):'(<.+>)'[,]?$",feature_source,re.M)
for name,paths in icons:
    (out/'feature-icons'/f'{name}.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="192" height="192" fill="none" stroke="#b23c05" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round">'+paths+'</svg>')
index=[]
for a,b,c,d,e,f in re.findall(r"\['([^']+)','([^']+)','([^']+)','([^']+)','([^']+)','([^']+)'\]",feature_source):
    index.append({'segment':a,'icon':b,'features':[{'name':c.replace('&amp;','&'),'icon':d},{'name':e.replace('&amp;','&'),'icon':f}]})
(out/'feature-index.json').write_text(json.dumps(index,indent=2))
(out/'README.md').write_text('# SILeos identity\n\nNew identity created for the cinematic teaser: an infinity ribbon and open-book baseline. Orange #ff751f, golden #fbbf24, deep orange #b23c05, navy #0b2540. Wordmark: SILeos. Expansion used in the film: Sasha Infinity Learning & Education Operating System.\n\nThe feature symbols are editable original SVG artwork. Conceptual phone artwork in the video communicates coming soon, not current app-store availability.\n')
print(f'Exported3brand SVGs and{len(icons)}feature SVGs in brand/.')
