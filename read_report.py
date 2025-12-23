import pdfplumber

pdf_path = 'conciliacao_2025-12-22_175914.pdf'
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
        if i > 2: # Just first few pages
            break
