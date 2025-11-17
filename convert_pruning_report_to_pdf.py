"""
Convert PRUNING_TYPES_ANALYSIS_REPORT.txt to PDF with proper formatting
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
import datetime

# Read the text report
with open('PRUNING_TYPES_ANALYSIS_REPORT.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Create PDF
pdf_filename = 'PRUNING_TYPES_ANALYSIS_REPORT.pdf'
doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    rightMargin=0.75*inch,
    leftMargin=0.75*inch,
    topMargin=1*inch,
    bottomMargin=0.75*inch
)

# Container for the 'Flowable' objects
elements = []

# Define styles
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1976D2'),
    spaceAfter=30,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

section_style = ParagraphStyle(
    'SectionHeader',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#333333'),
    spaceAfter=12,
    spaceBefore=20,
    fontName='Helvetica-Bold',
    borderWidth=1,
    borderColor=colors.HexColor('#667eea'),
    borderPadding=5,
    backColor=colors.HexColor('#f0f0f0')
)

subsection_style = ParagraphStyle(
    'SubSection',
    parent=styles['Heading3'],
    fontSize=12,
    textColor=colors.HexColor('#667eea'),
    spaceAfter=8,
    spaceBefore=12,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=10,
    textColor=colors.HexColor('#333333'),
    spaceAfter=6,
    alignment=TA_LEFT,
    fontName='Helvetica'
)

mono_style = ParagraphStyle(
    'MonoText',
    parent=styles['Code'],
    fontSize=9,
    textColor=colors.HexColor('#333333'),
    fontName='Courier',
    leftIndent=20,
    spaceAfter=6
)

alert_style = ParagraphStyle(
    'Alert',
    parent=styles['BodyText'],
    fontSize=10,
    textColor=colors.HexColor('#dc3545'),
    fontName='Helvetica-Bold',
    leftIndent=20,
    spaceAfter=6
)

warning_style = ParagraphStyle(
    'Warning',
    parent=styles['BodyText'],
    fontSize=10,
    textColor=colors.HexColor('#ff6b6b'),
    fontName='Helvetica-Bold',
    leftIndent=20,
    spaceAfter=6
)

info_style = ParagraphStyle(
    'Info',
    parent=styles['BodyText'],
    fontSize=10,
    textColor=colors.HexColor('#1976D2'),
    fontName='Helvetica-Bold',
    leftIndent=20,
    spaceAfter=6
)

# Add title
elements.append(Paragraph("COMPREHENSIVE PRUNING STRATEGY ANALYSIS", title_style))
elements.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
elements.append(Spacer(1, 0.3*inch))

# Parse content into sections
lines = content.split('\n')
current_section = None
in_table = False
table_data = []

for line in lines:
    line = line.rstrip()

    # Skip separator lines
    if line.startswith('===='):
        continue

    # Skip empty lines (but add spacing)
    if not line.strip():
        if not in_table:
            elements.append(Spacer(1, 0.1*inch))
        continue

    # Detect section headers
    if line.startswith('SECTION '):
        if in_table and table_data:
            # Finish previous table
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.2*inch))
            table_data = []
            in_table = False

        elements.append(PageBreak())
        elements.append(Paragraph(line, section_style))
        continue

    # Detect subsections with emojis or special markers
    if any(marker in line for marker in ['📚', '📊', '📦', '💾', '🚨', '💡', '🎯', '📋', '🔧', '🌳', '⚠️']):
        if in_table and table_data:
            # Finish previous table
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.2*inch))
            table_data = []
            in_table = False

        elements.append(Paragraph(line, subsection_style))
        continue

    # Detect tables (headers with multiple spaces or dashes)
    if '---' in line and len(line) > 50:
        in_table = True
        continue

    # Parse table rows
    if in_table:
        # Split by multiple spaces (2+)
        import re
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) > 1:
            table_data.append(parts)
        else:
            # End of table
            if table_data:
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.2*inch))
                table_data = []
            in_table = False
            # Process current line as regular text
            if line.strip():
                elements.append(Paragraph(line, body_style))
        continue

    # Detect alerts and warnings
    if line.strip().startswith('🔴') or 'CRITICAL' in line.upper() or 'URGENT' in line.upper():
        elements.append(Paragraph(line, alert_style))
    elif line.strip().startswith('🟠') or 'WARNING' in line.upper():
        elements.append(Paragraph(line, warning_style))
    elif line.strip().startswith('🔵') or line.strip().startswith('ℹ️'):
        elements.append(Paragraph(line, info_style))
    # Detect indented/structured content (starts with spaces or special chars)
    elif line.startswith('   ') or line.startswith('  ') or any(c in line[:3] for c in ['├', '└', '│', '•', '-', '✅', '❌']):
        # Use monospace for tree structures and lists
        elements.append(Preformatted(line, mono_style))
    else:
        # Regular paragraph
        elements.append(Paragraph(line, body_style))

# Finish any remaining table
if in_table and table_data:
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)

# Build PDF
doc.build(elements)

print(f"\nPDF created successfully: {pdf_filename}")
print(f"File location: {pdf_filename}")
print(f"Total pages: Generated from comprehensive pruning analysis")
