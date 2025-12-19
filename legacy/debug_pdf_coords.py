import pdfplumber
import sys

def debug_pdf(path):
    print(f"\n--- Debugging: {path} ---")
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        for w in words:
            if "/" in w['text'] and len(w['text']) >= 5:
                line_words = [ow for ow in words if abs(ow['top'] - w['top']) < 2]
                line_text = " ".join([f"[{ow['x0']:.1f}-{ow['x1']:.1f}]{ow['text']}" for ow in sorted(line_words, key=lambda x: x['x0'])])
                print(line_text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_pdf(sys.argv[1])
    else:
        debug_pdf("extração_pdfs/pdf_modelos/Extrato Santander.pdf")
