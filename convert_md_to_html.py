"""
Convert all Markdown files to styled HTML (ready for PDF printing)
These HTML files can be opened in a browser and printed to PDF
"""
import os
import glob
from pathlib import Path
import sys

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Check and install markdown
try:
    import markdown
except ImportError:
    print("Installing markdown...")
    os.system("pip install markdown -q")
    import markdown

# HTML template with professional styling
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @media print {{
            body {{ margin: 0; padding: 20px; }}
            .no-print {{ display: none; }}
        }}

        body {{
            font-family: 'Segoe UI', 'Calibri', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
            background: #fff;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-top: 30px;
            font-size: 2.2em;
        }}

        h2 {{
            color: #34495e;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
            margin-top: 25px;
            font-size: 1.8em;
        }}

        h3 {{
            color: #555;
            margin-top: 20px;
            font-size: 1.4em;
        }}

        h4 {{
            color: #666;
            margin-top: 15px;
            font-size: 1.2em;
        }}

        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}

        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.9em;
        }}

        pre code {{
            background: none;
            padding: 0;
            color: #333;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 0.95em;
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

        tr:nth-child(even) {{
            background: #f8f9fa;
        }}

        tr:hover {{
            background: #e9ecef;
        }}

        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin-left: 0;
            color: #555;
            font-style: italic;
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 4px;
        }}

        a {{
            color: #667eea;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
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

        strong {{
            color: #2c3e50;
        }}

        em {{
            color: #555;
        }}

        .print-button {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
        }}

        .print-button:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }}

        .filename {{
            background: #e9ecef;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            color: #495057;
            margin-bottom: 20px;
        }}

        @page {{
            margin: 2cm;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">🖨️ Print to PDF</button>
    <div class="filename no-print">Source: {filename}</div>
    {content}
    <script>
        // Add target="_blank" to external links
        document.querySelectorAll('a[href^="http"]').forEach(link => {{
            link.setAttribute('target', '_blank');
        }});
    </script>
</body>
</html>
"""

def convert_md_to_html(md_file, output_dir="HTML_Exports"):
    """Convert a markdown file to HTML"""
    try:
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert markdown to HTML with extensions
        html_content = markdown.markdown(
            md_content,
            extensions=[
                'extra',        # Tables, code blocks, etc.
                'codehilite',   # Syntax highlighting
                'tables',       # Table support
                'fenced_code',  # Fenced code blocks
                'toc',          # Table of contents
            ]
        )

        # Get title from first heading or filename
        title = Path(md_file).stem.replace('_', ' ').replace('-', ' ')

        # Wrap in HTML template
        full_html = HTML_TEMPLATE.format(
            title=title,
            filename=md_file,
            content=html_content
        )

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename
        base_name = Path(md_file).stem
        html_file = os.path.join(output_dir, f"{base_name}.html")

        # Write HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(full_html)

        return html_file
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 80)
    print("MARKDOWN TO HTML CONVERTER (PDF-Ready)")
    print("=" * 80)
    print()

    # Find all markdown files
    md_files = sorted(glob.glob("*.md"))

    if not md_files:
        print("No markdown files found in current directory")
        return

    print(f"Found {len(md_files)} markdown files")
    print()

    # Create output directory
    output_dir = "HTML_Exports"
    os.makedirs(output_dir, exist_ok=True)

    # Convert each file
    success_count = 0
    failed_count = 0
    successful_files = []

    for i, md_file in enumerate(md_files, 1):
        print(f"[{i:2}/{len(md_files)}] Converting: {md_file:<50}", end=" ")

        result = convert_md_to_html(md_file, output_dir)

        if isinstance(result, str) and result.startswith("ERROR"):
            print(f"❌ FAILED")
            print(f"      {result}")
            failed_count += 1
        else:
            print(f"✅ SUCCESS")
            success_count += 1
            successful_files.append(result)

    print()
    print("=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Total Files: {len(md_files)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print()
    print(f"HTML files saved to: {os.path.abspath(output_dir)}")
    print()
    print("=" * 80)
    print("HOW TO CONVERT TO PDF")
    print("=" * 80)
    print()
    print("1. Open any HTML file in your web browser (Chrome, Edge, Firefox)")
    print("2. Press Ctrl+P (or Cmd+P on Mac) to print")
    print("3. Select 'Save as PDF' or 'Microsoft Print to PDF' as printer")
    print("4. Click 'Save' and choose location")
    print()
    print("OR use the 'Print to PDF' button in the top-right corner of each page")
    print()
    print("=" * 80)
    print()

    # Create an index file
    create_index(successful_files, output_dir)
    print(f"📄 Created index.html with links to all documents")
    print(f"   Open: {os.path.abspath(os.path.join(output_dir, 'index.html'))}")
    print()
    print("=" * 80)

def create_index(html_files, output_dir):
    """Create an index.html with links to all converted files"""
    index_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Commvault API Documentation - Index</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
        }
        .doc-list {
            list-style: none;
            padding: 0;
        }
        .doc-item {
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 5px;
            transition: all 0.3s;
        }
        .doc-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .doc-item a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1em;
        }
        .doc-item a:hover {
            color: #5568d3;
        }
        .category {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .stats {
            background: #e9ecef;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Commvault API Documentation</h1>

        <div class="stats">
            <strong>Total Documents:</strong> """ + str(len(html_files)) + """<br>
            <strong>Generated:</strong> """ + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>

        <h2>Documentation Files</h2>
        <ul class="doc-list">
"""

    # Categorize files
    categories = {
        'Getting Started': ['README', 'QUICKSTART', 'PROJECT_OVERVIEW'],
        'Implementation': ['IMPLEMENTATION_SUMMARY', 'FIXES_IMPLEMENTED', 'NEW_FEATURES_SUMMARY'],
        'Research & Analysis': ['POLICY_AND_POOL_RESEARCH', 'AGING_POLICY_RESEARCH', 'JOB_SCHEDULE_RESEARCH', 'AGING_SCHEDULE_CONFLICT_RESEARCH', 'API_FIXES_RESEARCH'],
        'Reports': ['STORAGE_RECLAMATION_REPORT', 'AGING_POLICY_SUMMARY', 'API_TEST_RESULTS'],
        'Guides': ['INFRASTRUCTURE_GUIDE', 'INFRASTRUCTURE_UPDATES', 'API_ACTIVITY_CARD', 'QUICK_WINS_SUMMARY'],
    }

    # Add links for each file
    for html_file in sorted(html_files):
        filename = Path(html_file).name
        title = Path(html_file).stem.replace('_', ' ').replace('-', ' ')

        # Determine category
        category = 'Other'
        for cat, files in categories.items():
            if any(f in Path(html_file).stem for f in files):
                category = cat
                break

        index_content += f"""            <li class="doc-item">
                <a href="{filename}">{title}</a>
                <div class="category">Category: {category}</div>
            </li>
"""

    index_content += """        </ul>

        <h2>How to Create PDFs</h2>
        <ol>
            <li>Click on any document link above</li>
            <li>Use the "Print to PDF" button in the top-right corner, OR</li>
            <li>Press <code>Ctrl+P</code> and select "Save as PDF"</li>
        </ol>
    </div>
</body>
</html>
"""

    index_file = os.path.join(output_dir, 'index.html')
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_content)

if __name__ == "__main__":
    main()
