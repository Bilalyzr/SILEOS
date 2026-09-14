"""Render the editable architecture reference as a branded, paginated PDF."""
import json
import re
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'output/pdf/SashaInfinity_Architecture_and_Workflows.pdf'
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
INK=colors.HexColor('#172136'); ORANGE=colors.HexColor('#b23c05'); MUTED=colors.HexColor('#596579'); LIGHT=colors.HexColor('#F3F6FA')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyA',fontName='Helvetica',fontSize=9.1,leading=14,textColor=INK,spaceAfter=8,splitLongWords=True))
styles.add(ParagraphStyle(name='HeadingA',fontName='Helvetica-Bold',fontSize=19,leading=24,textColor=INK,spaceAfter=15,keepWithNext=True))
styles.add(ParagraphStyle(name='HeadingB',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=INK,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle(name='CellA',fontName='Helvetica',fontSize=7.5,leading=11,textColor=INK,splitLongWords=True))
styles.add(ParagraphStyle(name='LabelA',fontName='Helvetica-Bold',fontSize=9,leading=13,textColor=ORANGE,spaceAfter=12))
styles.add(ParagraphStyle(name='CoverA',fontName='Helvetica-Bold',fontSize=34,leading=39,textColor=INK,spaceAfter=24))
styles.add(ParagraphStyle(name='SubA',fontName='Helvetica',fontSize=16,leading=23,textColor=MUTED,spaceAfter=20))

def clean(s):
    return s.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-').replace('\u2192',' > ').replace('\u2019',"'").replace('\u2018',"'").replace('\u201c','"').replace('\u201d','"').replace('\u2022',' / ')

def inline(s):
    s=escape(clean(s))
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`(.*?)`',r'<font name="Courier" size="7.7">\1</font>',s)
    return s

def p(s,style='BodyA'): return Paragraph(inline(s),styles[style])

def diagram(kind):
    d=Drawing(475,214 if kind=='system' else 125)
    if kind=='system':
        labels=[['Web / Flutter clients','Web simulations','Recording worker'],['Nginx / API proxy','FastAPI + services','Local ASR runtime'],['Database / Redis','Private file storage','External providers']]
        bw,bh,gap=145,45,20
        for row,items in enumerate(labels):
            for col,label in enumerate(items):
                x=col*(bw+gap); y=164-row*72
                d.add(Rect(x,y,bw,bh,rx=8,fillColor=LIGHT if row!=1 else colors.HexColor('#FFF0E7'),strokeColor=colors.HexColor('#D9E0EA')))
                d.add(String(x+bw/2,y+18,label,textAnchor='middle',fontName='Helvetica-Bold',fontSize=9,fillColor=INK))
        def arrow(x1,y1,x2,y2):
            import math
            d.add(Line(x1,y1,x2,y2,strokeColor=ORANGE,strokeWidth=1.1))
            a=math.atan2(y2-y1,x2-x1); back=6; wing=3
            d.add(Polygon([x2,y2,x2-back*math.cos(a)+wing*math.sin(a),y2-back*math.sin(a)-wing*math.cos(a),x2-back*math.cos(a)-wing*math.sin(a),y2-back*math.sin(a)+wing*math.cos(a)],fillColor=ORANGE,strokeColor=ORANGE))
        arrow(145,186,165,186) # web client renders simulations
        arrow(72,164,72,137) # clients -> proxy
        arrow(145,113,165,113) # proxy -> API
        arrow(402,164,402,137) # recording worker -> local ASR
        arrow(238,92,72,65) # API -> database
        arrow(238,92,238,65) # API -> files
        arrow(238,92,402,65) # API -> providers
    else:
        labels=['Upload','Inspect + categorize','Preview','Restore new draft','Review','Publish'] if kind=='course' else ['Publish price slab','Select + snapshot','Gateway checkout','Verify payment','Generate + validate','Private delivery']
        for i,label in enumerate(labels):
            col=i%3;row=i//3;x=col*163;y=73-row*65
            d.add(Rect(x,y,148,44,rx=7,fillColor=LIGHT,strokeColor=colors.HexColor('#D9E0EA')))
            d.add(String(x+10,y+27,str(i+1),fontName='Helvetica-Bold',fontSize=8,fillColor=ORANGE))
            d.add(String(x+10,y+12,label,fontName='Helvetica-Bold',fontSize=8.3,fillColor=INK))
    return d

def table(rows):
    n=len(rows[0]); widths=([102,180,197] if n==3 else [130,349] if n==2 else [479/n]*n)
    cells=[[p(cell,'CellA') for cell in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#FFE7D6')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#D9E0EA')),('INNERGRID',(0,0),(-1,-1),.35,colors.HexColor('#E3E8EF')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT])]))
    return t

def footer(canvas,doc):
    canvas.saveState()
    w,h=A4
    if doc.page>1:
        canvas.setFont('Helvetica-Bold',8);canvas.setFillColor(INK);canvas.drawString(58,h-32,'SASHA INFINITY')
        canvas.setFont('Helvetica',8);canvas.setFillColor(MUTED);canvas.drawRightString(w-58,h-32,'Architecture and workflows | 06 SEP 2026')
    canvas.setStrokeColor(ORANGE);canvas.setLineWidth(1);canvas.line(58,43,w-58,43)
    canvas.setFont('Helvetica',7.5);canvas.setFillColor(MUTED);canvas.drawString(58,29,'Local source reference - configuration and deployment checks remain environment-specific')
    canvas.drawRightString(w-58,29,str(doc.page));canvas.restoreState()

text=(ROOT/'docs/SASHA_SYSTEM_ARCHITECTURE.md').read_text(encoding='utf-8')
inventory=json.loads((ROOT/'docs/ARCHITECTURE_INVENTORY.json').read_text())
story=[Spacer(1,36),p('SASHA INFINITY / ENGINEERING REFERENCE','LabelA'),p('Learning platform<br/>architecture &amp;<br/>workflows'.replace('&amp;','&'),'CoverA'),p('A practical guide to the product, its operating processes and the code that implements them.','SubA'),Spacer(1,15)]
# Intentional line breaks use separate paragraphs, preserving literal escaping.
story[2]=Paragraph('Learning platform<br/>architecture &amp;<br/>workflows',styles['CoverA'])
story += [table([['Snapshot','Coverage'],['6 September 2026','Web application, backend, labs, commerce, live teaching, mobile boundaries and operational recovery'],['Code inventory',f"{inventory['counts']['route_patterns']} web route patterns / {inventory['counts']['lazy_page_modules']} lazy pages / {inventory['counts']['router_mounts']} API router registrations"],['Delivery scope','Local workspace implementation. No production deployment or physical XR certification.']]),Spacer(1,24),p('INCLUDED IN THIS UPDATE','LabelA')]
for s in ['Supplied 59-lab collection with reviewed ZIP import and export','GLB labels, guided assessments, AR / VR controls and teacher review','Offline learning with enrollment-checked synchronization','Orange gradient theme, accessibility and bilingual learning controls','Architecture, release readiness, backup recovery and source reference']:
    story.append(p('- '+s))
story += [Spacer(1,18),p('Companion files: docs/SASHA_SYSTEM_ARCHITECTURE.md, docs/CODEBASE_INDEX.md and docs/ARCHITECTURE_INVENTORY.json.')]
lines=text.splitlines();i=0
while i<len(lines):
    line=lines[i]
    if line.startswith('### '):
        story.append(p(line[4:],'HeadingB'));i+=1;continue
    if line.startswith('## '):
        story.append(PageBreak());story.append(p(line[3:],'HeadingA'));i+=1;continue
    if not any(l.startswith('## ') for l in lines[:i]):i+=1;continue
    if line.startswith('```'):
        block=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
        kind='system' if any('flowchart TD' in b for b in block) else 'course' if any('Upload[' in b for b in block) else 'payment'
        story += [diagram(kind),Spacer(1,12)];i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            row=[c.strip() for c in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[-: ]+',c) for c in row):rows.append(row)
            i+=1
        story += [table(rows),Spacer(1,12)];continue
    if not line.strip():i+=1;continue
    paragraph=[line];i+=1
    while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```')):
        if re.match(r'\d+\. ',lines[i]):break
        paragraph.append(lines[i]);i+=1
    story.append(p(' '.join(paragraph)))

doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,rightMargin=58,leftMargin=58,topMargin=62,bottomMargin=62,title='SashaInfinity - Architecture and Workflows',author='SashaInfinity',subject='Local architecture, feature processes and maintenance reference')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUTPUT)
