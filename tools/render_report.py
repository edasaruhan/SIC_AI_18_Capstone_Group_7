"""Optional deterministic Markdown-to-PDF renderer for the final report.

Requires reportlab from requirements-report.txt. Fonts are shipped by ReportLab;
no machine-specific font or office installation is required.
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/final/Group7_Final_Report.md'
OUTPUT = SOURCE.with_suffix('.pdf')
FONTS = Path(reportlab.__file__).parent / 'fonts'
pdfmetrics.registerFont(TTFont('Research', str(FONTS/'Vera.ttf')))
pdfmetrics.registerFont(TTFont('ResearchBold', str(FONTS/'VeraBd.ttf')))
pdfmetrics.registerFontFamily('Research', normal='Research', bold='ResearchBold', italic='Research', boldItalic='ResearchBold')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='ResearchBody', fontName='Research', fontSize=9.3, leading=13.7, spaceAfter=8, textColor=colors.HexColor('#222b35'), splitLongWords=True))
styles.add(ParagraphStyle(name='ResearchTitle', fontName='ResearchBold', fontSize=24, leading=29, spaceAfter=14, textColor=colors.black, keepWithNext=True))
styles.add(ParagraphStyle(name='ResearchHeading', fontName='ResearchBold', fontSize=13.3, leading=17.6, spaceBefore=15, spaceAfter=8, textColor=colors.black, keepWithNext=True))
styles.add(ParagraphStyle(name='ResearchCell', fontName='Research', fontSize=8, leading=11.2, textColor=colors.HexColor('#222b35')))
styles.add(ParagraphStyle(name='ResearchTableHeader', parent=styles['ResearchCell'], fontName='ResearchBold', textColor=colors.black))
styles.add(ParagraphStyle(name='ResearchCaption', fontName='Research', fontSize=8, leading=11, textColor=colors.HexColor('#52606d'), spaceAfter=12))

def inline(value):
    value = escape(value.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-'))
    value = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8">\1</font>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', value)
    return value

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Research', 7.5)
    canvas.setFillColor(colors.HexColor('#52606d'))
    canvas.drawString(48, 30, 'Group 7 | Open Play research | 18 November 2026')
    canvas.drawRightString(A4[0]-48, 30, str(doc.page))
    canvas.restoreState()

def main():
    lines = SOURCE.read_text().splitlines()
    story = []
    width = A4[0] - 96
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]), styles['ResearchTitle'])); i+=1
        elif line.startswith('## '):
            story.append(Paragraph(inline(line[3:]), styles['ResearchHeading'])); i+=1
        elif line.startswith('|'):
            rows=[]
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', c) for c in cells):
                    rows.append(cells)
                i+=1
            n=len(rows[0]); ratios = {2:[.59,.41],3:[.42,.29,.29],4:[.38,.2,.2,.22],5:[.25,.18,.18,.19,.20]}[n]
            data=[[Paragraph(inline(c), styles['ResearchTableHeader'] if r==0 else styles['ResearchCell']) for c in row] for r,row in enumerate(rows)]
            tbl=Table(data, colWidths=[width*v for v in ratios], repeatRows=1, hAlign='LEFT')
            tbl.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7edef')),
                                     ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f5f7f8')]),
                                     ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                                     ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([tbl,Spacer(1,10)])
        elif line.startswith('!['):
            match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
            path=(SOURCE.parent/match.group(2)).resolve()
            im=Image(str(path)); target_width=width*.94; scale=target_width/im.imageWidth
            im.drawWidth=target_width; im.drawHeight=im.imageHeight*scale
            caption=Paragraph(inline(match.group(1))+'. Aggregate held-out evaluation; no participant-level data.', styles['ResearchCaption'])
            story.append(KeepTogether([im,Spacer(1,6),caption])); i+=1
        else:
            paragraph=[line];i+=1
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![')):
                paragraph.append(lines[i].strip());i+=1
            story.append(Paragraph(inline(' '.join(paragraph)),styles['ResearchBody']))
    doc=SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=48,leftMargin=48,topMargin=43,bottomMargin=48,
                          title='Problematic Gaming Early Warning Final Research Report',author='SIC Capstone Group 7')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUTPUT)

if __name__=='__main__':
    main()
