import os
import pdfplumber
import pandas as pd

def analyze_layouts(directories):
    results = []
    for directory in directories:
        if not os.path.exists(directory):
            continue
        for root_dir, _, files in os.walk(directory):
            for file in files:
                if not file.lower().endswith('.pdf'):
                    continue
                path = os.path.join(root_dir, file)
                try:
                    with pdfplumber.open(path) as pdf:
                        first_page = pdf.pages[0].extract_text() or ""
                        sample = first_page[:500].replace('\n', ' ')
                        
                        # Identify bank by rough markers
                        sample_up = sample.upper()
                        bank = "Unknown"
                        if "BANCO DO BRASIL" in sample_up or "BRASIL" in sample_up: bank = "BB"
                        elif "ITAU" in sample_up: bank = "Itau"
                        elif "SANTANDER" in sample_up: bank = "Santander"
                        elif "CAIXA" in sample_up or "CEF" in sample_up: bank = "CEF"
                        elif "SICREDI" in sample_up or "COOP CRED" in sample_up: bank = "Sicredi"
                        elif "BRADESCO" in sample_up: bank = "Bradesco"
                        elif "SICOOB" in sample_up: bank = "Sicoob"
                        elif "STONE" in sample_up: bank = "Stone"
                        
                        results.append({
                            "file": file,
                            "bank": bank,
                            "sample": sample[:300],
                            "path": path
                        })
                except Exception as e:
                    results.append({"file": file, "bank": "Error", "sample": str(e), "path": path})
    
    df = pd.DataFrame(results)
    return df

dirs = [
    r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extração_pdfs/pdf_modelos",
    r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extratos"
]

inventory = analyze_layouts(dirs)
print(inventory[['bank', 'file', 'sample']].to_string(index=False))

# Save mapping to review
inventory.to_csv("layout_inventory.csv", index=False)
