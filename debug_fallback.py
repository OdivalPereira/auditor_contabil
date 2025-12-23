
import sys
import logging

# Configure logging to print to stderr
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('src.parsing.banks.stone')
logger.setLevel(logging.DEBUG)

# Clear modules
keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser
import pandas as pd

parser = StonePDFParser()
# Parse just one page that we know has data to see if it generates rows or falls back
print("Parsing PDF...")
# Use specific file 
try:
    df, meta = parser.parse('extratos/Extrato Stones 03 2025.pdf')
    print(f"Extraction complete. Total rows: {len(df)}")
    
    pix_maq = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False)]
    standalone = pix_maq[pix_maq['description'].str.strip() == 'Pix | Maquininha']
    print(f"Standalone Pix entries: {len(standalone)}")
except Exception as e:
    print(f"Error: {e}")
