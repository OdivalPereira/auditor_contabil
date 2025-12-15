import pdfplumber

pdf_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\pdf_modelos\Modelo Sicred 2.pdf"
output_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\sicredi_dump_2.txt"

with pdfplumber.open(pdf_path) as pdf:
    with open(output_path, "w", encoding="utf-8") as f:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                f.write(f"--- Page {i+1} ---\n")
                f.write(text)
                f.write("\n\n")
