
import pdfplumber

def debug_bb_coords(file_path):
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # Sort words by top, then x0
        words.sort(key=lambda w: (round(w['top']), w['x0']))
        
        print(f"{'Text':<30} | {'x0':<10} | {'top':<10}")
        print("-" * 60)
        
        # Look for headers
        for w in words:
            if w['text'] in ["Data", "Histórico", "Documento", "Valor", "Saldo", "Dt.", "movimento"]:
                print(f"{w['text']:<30} | {w['x0']:<10.2f} | {w['top']:<10.2f}")
        
        print("\n--- Rende Facil Line ---")
        for w in words:
            if "Rende" in w['text']:
                y = w['top']
                line_words = [sw for sw in words if abs(sw['top'] - y) < 3]
                line_words.sort(key=lambda sw: sw['x0'])
                for lw in line_words:
                    print(f"{lw['text']:<30} | {lw['x0']:<10.2f} | {lw['top']:<10.2f}")
                break

debug_bb_coords('extratos/01 2025/Extrato BB 01 2025.pdf')
