#!/usr/bin/env python3
# PURPOSE: Review consolidated PDF and extract metadata
# DEPENDENCIES: pypdf, pathlib
# MODIFICATION NOTES: v1.0 - PDF review utility

import sys
from pathlib import Path
import json

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import pypdf as PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyPDF2 not available for PDF review")


def review_consolidated_pdf(pdf_path):
    """Review the consolidated PDF and extract information."""
    print(f"📄 Reviewing Consolidated PDF: {pdf_path}")
    print("=" * 60)
    
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    # Basic file info
    file_size = pdf_file.stat().st_size
    print(f"📊 File Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    if not PDF_AVAILABLE:
        print("⚠️  PyPDF2 not available - limited review possible")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # PDF metadata
            num_pages = len(pdf_reader.pages)
            print(f"📄 Total Pages: {num_pages}")
            
            # Document info
            if pdf_reader.metadata:
                print(f"\n📋 Document Metadata:")
                for key, value in pdf_reader.metadata.items():
                    if value:
                        print(f"   {key}: {value}")
            
            # Page-by-page analysis
            print(f"\n📖 Page Analysis:")
            for i, page in enumerate(pdf_reader.pages):
                page_num = i + 1
                text = page.extract_text()
                word_count = len(text.split()) if text else 0
                char_count = len(text) if text else 0
                
                print(f"   Page {page_num}: {word_count} words, {char_count} characters")
                
                # Show first 100 characters of text
                if text:
                    preview = text[:100].replace('\n', ' ').strip()
                    print(f"      Preview: {preview}...")
                else:
                    print(f"      Preview: [No text content]")
            
            # Check for images or other content
            print(f"\n🔍 Content Analysis:")
            total_images = 0
            for i, page in enumerate(pdf_reader.pages):
                if '/XObject' in page['/Resources']:
                    xObject = page['/Resources']['/XObject'].get_object()
                    for obj in xObject:
                        if xObject[obj]['/Subtype'] == '/Image':
                            total_images += 1
            
            print(f"   Total Images: {total_images}")
            
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")


def compare_with_original_pdfs():
    """Compare consolidated PDF with original individual PDFs."""
    print(f"\n🔄 Comparing with Original PDFs")
    print("=" * 40)
    
    # Get original PDFs
    downloads_dir = Path("downloads/birchwood")
    original_pdfs = []
    
    for pdf_file in downloads_dir.glob("*.pdf"):
        if pdf_file.stat().st_size > 1000:  # Only real PDFs
            original_pdfs.append(pdf_file)
    
    print(f"📊 Original PDFs ({len(original_pdfs)} files):")
    total_original_size = 0
    total_original_pages = 0
    
    for pdf in original_pdfs:
        size = pdf.stat().st_size
        total_original_size += size
        print(f"   - {pdf.name}: {size:,} bytes")
        
        if PDF_AVAILABLE:
            try:
                with open(pdf, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    pages = len(reader.pages)
                    total_original_pages += pages
                    print(f"     Pages: {pages}")
            except:
                pass
    
    # Consolidated PDF info
    consolidated_path = "/mnt/flex-1/consolidated_documents/birchwood/Birchwood_2025-08-06_ConsolidatedDocuments.pdf"
    consolidated_size = Path(consolidated_path).stat().st_size
    
    print(f"\n📈 Consolidation Summary:")
    print(f"   Original total size: {total_original_size:,} bytes")
    print(f"   Consolidated size: {consolidated_size:,} bytes")
    print(f"   Size difference: {total_original_size - consolidated_size:,} bytes")
    print(f"   Compression ratio: {(1 - consolidated_size/total_original_size)*100:.1f}%")
    
    if PDF_AVAILABLE:
        try:
            with open(consolidated_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                consolidated_pages = len(reader.pages)
                print(f"   Original total pages: {total_original_pages}")
                print(f"   Consolidated pages: {consolidated_pages}")
                print(f"   Page difference: {total_original_pages - consolidated_pages}")
        except:
            pass


def main():
    """Main function to review the consolidated PDF."""
    print("🔍 Consolidated PDF Review")
    print("=" * 60)
    
    pdf_path = "/mnt/flex-1/consolidated_documents/birchwood/Birchwood_2025-08-06_ConsolidatedDocuments.pdf"
    
    # Review the consolidated PDF
    review_consolidated_pdf(pdf_path)
    
    # Compare with original PDFs
    compare_with_original_pdfs()
    
    print(f"\n✅ Review Complete!")
    print(f"📁 Consolidated PDF: {pdf_path}")
    print(f"📊 Ready for VOD integration")


if __name__ == "__main__":
    main()
