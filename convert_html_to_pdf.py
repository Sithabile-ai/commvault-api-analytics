"""
Convert HTML files to PDF using pdfkit (wkhtmltopdf wrapper)
This provides a reliable cross-platform PDF generation solution
"""
import os
import glob
import sys
from pathlib import Path

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_and_install_libraries():
    """Check and install required libraries"""
    try:
        import pdfkit
    except ImportError:
        print("Installing pdfkit...")
        os.system("pip install pdfkit -q")
        import pdfkit

    # Check if wkhtmltopdf is installed
    try:
        import pdfkit
        # Try to create a simple PDF to test if wkhtmltopdf is available
        pdfkit.from_string("test", False)
    except Exception as e:
        if "No wkhtmltopdf executable found" in str(e):
            print()
            print("=" * 80)
            print("⚠️  WKHTMLTOPDF NOT FOUND")
            print("=" * 80)
            print()
            print("pdfkit requires wkhtmltopdf to be installed.")
            print()
            print("Download and install from:")
            print("https://wkhtmltopdf.org/downloads.html")
            print()
            print("For Windows:")
            print("1. Download the installer from the link above")
            print("2. Run the installer")
            print("3. Add to PATH or specify location in this script")
            print()
            print("=" * 80)
            return False
    return True

def convert_html_to_pdf(html_file, output_dir="PDF_Exports"):
    """Convert an HTML file to PDF"""
    try:
        import pdfkit

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename
        base_name = Path(html_file).stem
        pdf_file = os.path.join(output_dir, f"{base_name}.pdf")

        # Configure pdfkit options for better PDF output
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None
        }

        # Convert HTML to PDF
        pdfkit.from_file(html_file, pdf_file, options=options)

        return pdf_file
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 80)
    print("HTML TO PDF CONVERTER")
    print("=" * 80)
    print()

    # Check if libraries are available
    print("Checking required libraries...")
    if not check_and_install_libraries():
        sys.exit(1)

    print("✅ All required libraries available")
    print()

    # Find all HTML files in HTML_Exports directory
    html_dir = "HTML_Exports"
    if not os.path.exists(html_dir):
        print(f"❌ ERROR: {html_dir} directory not found")
        print("Please run convert_md_to_html.py first")
        sys.exit(1)

    html_files = sorted(glob.glob(os.path.join(html_dir, "*.html")))

    # Exclude index.html from conversion
    html_files = [f for f in html_files if not f.endswith("index.html")]

    if not html_files:
        print(f"No HTML files found in {html_dir}")
        return

    print(f"Found {len(html_files)} HTML files to convert")
    print()

    # Create output directory
    output_dir = "PDF_Exports"
    os.makedirs(output_dir, exist_ok=True)

    # Convert each file
    success_count = 0
    failed_count = 0
    successful_files = []

    for i, html_file in enumerate(html_files, 1):
        filename = Path(html_file).name
        print(f"[{i:2}/{len(html_files)}] Converting: {filename:<50}", end=" ")

        result = convert_html_to_pdf(html_file, output_dir)

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
    print(f"Total Files: {len(html_files)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print()
    print(f"PDF files saved to: {os.path.abspath(output_dir)}")
    print()
    print("=" * 80)
    print()

    # List converted files
    if successful_files:
        print("Converted PDF files:")
        for pdf_file in successful_files:
            print(f"  📄 {Path(pdf_file).name}")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
