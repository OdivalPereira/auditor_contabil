import pdfplumber
import re

f = r'extração_pdfs/pdf_modelos/Bradesco 01 2025.PDF'
with pdfplumber.open(f) as pdf:
    for page in pdf.pages:
        words = page.extract_words()
        lines = {}
        for w in words:
            top = int(w['top'] // 2) * 2
            lines.setdefault(top, []).append(w)
        
        for top in sorted(lines.keys()):
            l_words = sorted(lines[top], key=lambda x: x['x0'])
            txt = " ".join([w['text'] for w in l_words])
            
            # Look for that long ID or large amounts
            if "8424708" in txt or any(re.match(r"^-?[\d\.,]{10,}$", w['text']) for w in l_words):
                print(f"Page {page.page_number} Top {top}:")
                print(f"  Text: {txt}")
                print(f"  Elements: {[(w['text'], w['x0']) for w in l_words]}")
