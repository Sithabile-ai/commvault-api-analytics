"""
Convert HTML files to PDF using playwright
This is a headless browser approach that works cross-platform
"""
import os
import glob
import sys
from pathlib import Path
import asyncio

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_and_install_libraries():
    """Check and install required libraries"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright...")
        os.system("pip install playwright -q")
        print("Installing playwright browsers...")
        os.system("playwright install chromium")
        from playwright.sync_api import sync_playwright
    return True

def convert_html_to_pdf(html_file, output_dir="PDF_Exports"):
    """Convert an HTML file to PDF using playwright"""
    try:
        from playwright.sync_api import sync_playwright

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename
        base_name = Path(html_file).stem
        pdf_file = os.path.join(output_dir, f"{base_name}.pdf")

        # Get absolute path for HTML file
        html_path = os.path.abspath(html_file)

        # Convert HTML to PDF using playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Load HTML file
            page.goto(f"file:///{html_path.replace(os.sep, '/')}")

            # Generate PDF with options
            page.pdf(
                path=pdf_file,
                format='Letter',
                margin={
                    'top': '0.75in',
                    'right': '0.75in',
                    'bottom': '0.75in',
                    'left': '0.75in'
                },
                print_background=True
            )

            browser.close()

        return pdf_file
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 80)
    print("HTML TO PDF CONVERTER (using Playwright)")
    print("=" * 80)
    print()

    # Check if libraries are available
    print("Checking required libraries...")
    try:
        if not check_and_install_libraries():
            sys.exit(1)
        print("✅ All required libraries available")
    except Exception as e:
        print(f"❌ ERROR: Could not install required libraries: {e}")
        sys.exit(1)

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
        print(f"[{i:2}/{len(html_files)}] Converting: {filename:<50}", end=" ", flush=True)

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
