
file_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\pdf_modelos\Banco do Brasil OFX - Setembro 2025.ofx"
output_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\example_dump.txt"

try:
    with open(file_path, 'rb') as f:
        content = f.read().decode('latin-1', errors='ignore')
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Dumped to {output_path}")

except Exception as e:
    print(f"Error: {e}")
