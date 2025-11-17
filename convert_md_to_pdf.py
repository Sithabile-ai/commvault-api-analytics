"""
Convert all Markdown files to PDF
Uses markdown and weasyprint libraries
"""
import os
import glob
from pathlib import Path

# Check and install required libraries
def install_if_needed():
    try:
        import markdown
    except ImportError:
        print("Installing markdown...")
        os.system("pip install markdown -q")

    try:
        from weasyprint import HTML
    except ImportError:
        print("Installing weasyprint...")
        os.system("pip install weasyprint -q")

print("Checking required libraries...")
install_if_needed()

import markdown
from weasyprint import HTML
from io import BytesIO

# HTML template with styling
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
            margin-top: 25px;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin-left: 0;
            color: #555;
            font-style: italic;
        }}
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .page-break {{
            page-break-after: always;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 30px 0;
        }}
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""

def convert_md_to_pdf(md_file, output_dir="PDF_Exports"):
    """Convert a markdown file to PDF"""
    try:
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )

        # Wrap in HTML template
        full_html = HTML_TEMPLATE.format(content=html_content)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename
        base_name = Path(md_file).stem
        pdf_file = os.path.join(output_dir, f"{base_name}.pdf")

        # Convert HTML to PDF
        HTML(string=full_html).write_pdf(pdf_file)

        return pdf_file
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 80)
    print("MARKDOWN TO PDF CONVERTER")
    print("=" * 80)
    print()

    # Find all markdown files
    md_files = glob.glob("*.md")

    if not md_files:
        print("No markdown files found in current directory")
        return

    print(f"Found {len(md_files)} markdown files")
    print()

    # Create output directory
    output_dir = "PDF_Exports"
    os.makedirs(output_dir, exist_ok=True)

    # Convert each file
    success_count = 0
    failed_count = 0

    for i, md_file in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] Converting: {md_file}...", end=" ")

        result = convert_md_to_pdf(md_file, output_dir)

        if result.startswith("ERROR"):
            print(f"❌ FAILED")
            print(f"    {result}")
            failed_count += 1
        else:
            print(f"✅ SUCCESS")
            print(f"    → {result}")
            success_count += 1

    print()
    print("=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Total Files: {len(md_files)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print()
    print(f"PDF files saved to: {os.path.abspath(output_dir)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
