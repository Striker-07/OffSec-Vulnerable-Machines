#!/usr/bin/env python3
import os
import re
import zipfile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 756, "OFFSEC GRIMOIRE — CASEFILE #08: KERBEROS DUST")
            self.drawRightString(576, 756, "CONFIDENTIAL / SOC INVESTIGATION")
            self.setStrokeColor(colors.HexColor("#cbd5e0"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)
            
        # Footer
        self.drawString(36, 25, "OffSec User-Generated Content (UGC) — Blue Team Threat Hunting")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 25, page_text)
        self.setStrokeColor(colors.HexColor("#cbd5e0"))
        self.setLineWidth(0.5)
        self.line(36, 35, 576, 35)
        
        self.restoreState()

def build_pdf(md_path, pdf_path):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=3
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor('#2d3748'),
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=4
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=12,
        spaceAfter=2
    )
    
    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor('#f7fafc'),
        backColor=colors.HexColor('#1a202c'),
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=5,
        rightIndent=5
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=colors.HexColor('#1a202c')
    )
    
    table_hdr_style = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1a365d')
    )

    story = []
    story.append(Paragraph('Casefile #08: Kerberos Dust — DFIR Report', title_style))
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#2b6cb0'), spaceAfter=8))
    
    with open(md_path) as f:
        content = f.read()
        
    lines = content.split('\n')
    i = 0
    in_code = False
    code_buf = []
    
    while i < len(lines):
        line = lines[i]
        
        if line.strip().startswith('```'):
            if in_code:
                code_text = '\n'.join(code_buf)
                story.append(Preformatted(code_text, code_style))
                code_buf = []
                in_code = False
            else:
                in_code = True
                code_buf = []
            i += 1
            continue
            
        if in_code:
            code_buf.append(line)
            i += 1
            continue
            
        if line.startswith('# '):
            pass
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, h1_style))
            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#cbd5e0'), spaceAfter=5))
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, h2_style))
        elif line.startswith('- ') or line.startswith('* '):
            raw_text = line[2:].strip()
            raw_text = raw_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            fmt_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', raw_text)
            fmt_text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#c53030">\1</font>', fmt_text)
            story.append(Paragraph(f'&bull; {fmt_text}', bullet_style))
        elif line.startswith('|') and '|' in line[1:]:
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            table_data = []
            for tline in table_lines:
                if '---' in tline:
                    continue
                cells = [c.strip() for c in tline.split('|')[1:-1]]
                row_cells = []
                is_hdr = (len(table_data) == 0)
                for c in cells:
                    c_esc = c.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    fmt_c = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', c_esc)
                    fmt_c = re.sub(r'`(.+?)`', r'<font name="Courier" color="#c53030">\1</font>', fmt_c)
                    s_to_use = table_hdr_style if is_hdr else table_cell_style
                    row_cells.append(Paragraph(fmt_c, s_to_use))
                table_data.append(row_cells)
                
            if table_data:
                num_cols = len(table_data[0])
                if num_cols == 3:
                    col_widths = [140, 220, 180]
                elif num_cols == 2:
                    col_widths = [180, 360]
                else:
                    col_widths = [540 / num_cols] * num_cols

                t = Table(table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#a0aec0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(Spacer(1, 3))
                story.append(t)
                story.append(Spacer(1, 4))
            continue
        elif line.strip():
            raw_text = line.strip()
            raw_text = raw_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            fmt_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', raw_text)
            fmt_text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#c53030">\1</font>', fmt_text)
            story.append(Paragraph(fmt_text, body_style))
            
        i += 1

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated {pdf_path}")

def package_artifacts(src_dir, zip_path):
    files = ["kerberos_traffic.pcap", "Security_Events.json", "Sysmon_Events.json", "Incident_Timeline.csv"]
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files:
            fpath = os.path.join(src_dir, f)
            if os.path.exists(fpath):
                z.write(fpath, arcname=f)
                print(f"  -> Added {f} ({os.path.getsize(fpath)} bytes)")
    print(f"[+] Created artifacts archive: {zip_path} ({os.path.getsize(zip_path)} bytes)")

if __name__ == "__main__":
    base_dir = "/Users/a1234/Desktop/Offsec/Grimoire_Kerberos_Dust"
    src_dir = os.path.join(base_dir, "artifacts_src")
    md_file = os.path.join(base_dir, "walkthrough.md")
    pdf_file = os.path.join(base_dir, "walkthrough.pdf")
    zip_file = os.path.join(base_dir, "artifacts.zip")
    
    # Build PDF
    build_pdf(md_file, pdf_file)
    
    # Package artifacts.zip
    package_artifacts(src_dir, zip_file)
    
    # Mirror to Downloads for submission
    dl_dir = "/Users/a1234/Downloads/grimoire-kerberos-dust"
    os.makedirs(dl_dir, exist_ok=True)
    import shutil
    shutil.copy(pdf_file, os.path.join(dl_dir, "walkthrough.pdf"))
    shutil.copy(zip_file, os.path.join(dl_dir, "artifacts.zip"))
    print(f"[+] Mirrored submission package to {dl_dir}")
