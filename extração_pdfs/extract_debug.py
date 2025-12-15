import pdfplumber
import os

pdf_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\MCM set25.pdf"
output_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\extraction_output.txt"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    exit(1)

try:
    with pdfplumber.open(pdf_path) as pdf:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Pages: {len(pdf.pages)}\n")
            for i, page in enumerate(pdf.pages):
                f.write(f"\n--- Page {i+1} ---\n")
                
                # Extract Text
                text = page.extract_text()
                if text:
                    f.write("TEXT CONTENT:\n")
                    f.write(text)
                    f.write("\n")
                
                # Extract Tables
                tables = page.extract_tables()
                if tables:
                    f.write("TABLE CONTENT:\n")
                    for table in tables:
                        for row in table:
                            # Clean up row data
                            clean_row = [str(cell).replace('\n', ' ') if cell else '' for cell in row]
                            f.write(" | ".join(clean_row))
                            f.write("\n")
                        f.write("\n")
                f.write("-" * 50 + "\n")
    print(f"Extraction complete. Saved to {output_path}")

except Exception as e:
    print(f"An error occurred: {e}")
