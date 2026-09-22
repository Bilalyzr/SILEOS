from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'index.html'
s=p.read_text().replace('window.__timelines["main"]=gsap.timeline({paused:true});','const tl=gsap.timeline({paused:true});window.__timelines["main"]=tl;')
s=s.replace('<div class="clip base"','<div id="base-ground" class="clip base"')
for name in ['01-origin','02-features','03-pocket']:
    s=s.replace(f'<div class="clip scene" data-composition-id="{name}"',f'<div id="host-{name}" class="clip scene" data-composition-id="{name}"')
p.write_text(s)
p=root/'compositions/frames/01-origin.html'
s=p.read_text().replace('<div class="clip origin-bg"','<div id="origin-ground" class="clip origin-bg"')
s=s.replace('tl.set("#origin-chapter, #origin-bright, #origin-expansion, #origin-initials, #origin-reveal", {autoAlpha:0},0);','tl.set("#origin-chapter, #origin-bright, #origin-expansion, #origin-initials, #origin-reveal", {autoAlpha:0},0);')
s=s.replace('const tl=gsap.timeline({paused:true});','const tl=gsap.timeline({paused:true});gsap.set("#origin-chapter, #origin-bright, #origin-expansion, #origin-initials, #origin-reveal",{autoAlpha:0});')
s=s.replace('FOR LEARNERS.<br/>FOR EDUCATORS.','<div>FOR LEARNERS.</div><div>FOR EDUCATORS.</div>')
p.write_text(s)
p=root/'compositions/frames/02-features.html'
s=p.read_text().replace('02-features-','features-')
s=s.replace('tl.set(groups,{autoAlpha:0},0);','gsap.set(groups,{autoAlpha:0});tl.set(groups,{autoAlpha:0},0);')
p.write_text(s)
p=root/'compositions/frames/03-pocket.html'
s=p.read_text().replace('<div class="clip f03-ground"','<div id="pocket-ground" class="clip f03-ground"')
s=s.replace('const tl=gsap.timeline({paused:true});','const tl=gsap.timeline({paused:true});gsap.set("#f03-brand-stage",{autoAlpha:0});')
p.write_text(s)
print('Fixed master registration and deterministic initial states.')
