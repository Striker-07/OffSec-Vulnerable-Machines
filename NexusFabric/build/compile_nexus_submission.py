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
            self.drawString(36, 756, "OFFSEC CHAINED LAB — NEXUS-FABRIC (3-HOST CLUSTER)")
            self.drawRightString(576, 756, "OFFICIAL PENETRATION TESTING REPORT")
            self.setStrokeColor(colors.HexColor("#cbd5e0"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)
            
        # Footer
        self.drawString(36, 25, "OffSec User-Generated Content (UGC) — Standalone Chain Attack Linux")
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
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'DocH3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    code_block_style = ParagraphStyle(
        'CodeBlock',
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                code_text = "".join(code_lines).rstrip()
                code_p = Preformatted(code_text, code_block_style)
                code_table = Table([[code_p]], colWidths=[540])
                code_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(code_table)
                story.append(Spacer(1, 6))
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not stripped:
            continue

        if stripped.startswith("# "):
            clean_text = stripped[2:].strip()
            story.append(Paragraph(clean_text, title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))
        elif stripped.startswith("## "):
            clean_text = stripped[3:].strip()
            story.append(Paragraph(clean_text, h2_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=6))
        elif stripped.startswith("### "):
            clean_text = stripped[4:].strip()
            story.append(Paragraph(clean_text, h3_style))
        elif stripped.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e0"), spaceAfter=6))
        else:
            # Inline code and bold parsing
            formatted = stripped
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<font face="Courier" color="#b91c1c">\1</font>', formatted)
            story.append(Paragraph(formatted, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated {pdf_path}")

def package_submission():
    base_dir = "/Users/a1234/Desktop/Offsec/NexusFabric"
    build_dir = f"{base_dir}/build"
    artifacts_zip = f"{base_dir}/artifacts.zip"
    
    # 1. Package artifacts.zip
    build_scripts = ["build-vm1.sh", "build-vm2.sh", "build-vm3.sh"]
    with zipfile.ZipFile(artifacts_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for s in build_scripts:
            spath = os.path.join(build_dir, s)
            if os.path.exists(spath):
                z.write(spath, arcname=s)
                print(f"  -> Added {s} ({os.path.getsize(spath)} bytes)")
    print(f"[+] Created artifacts archive: {artifacts_zip} ({os.path.getsize(artifacts_zip)} bytes)")

    # 2. Compile Walkthrough PDF
    md_path = f"{base_dir}/walkthrough.md"
    pdf_path = f"{base_dir}/walkthrough.pdf"
    build_pdf(md_path, pdf_path)

    # 3. Outer submission package
    final_zip = "/Users/a1234/Downloads/standalone-chain-attack-nexusfabric.zip"
    with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(f"{base_dir}/autopwn.py", arcname="autopwn.py")
        z.write(f"{base_dir}/build-guide.md", arcname="build-guide.md")
        z.write(pdf_path, arcname="walkthrough.pdf")
        z.write(artifacts_zip, arcname="artifacts.zip")
        
    print(f"[+] Successfully built clean OffSec Chained submission: {final_zip} ({os.path.getsize(final_zip)} bytes)")

if __name__ == "__main__":
    package_submission()
