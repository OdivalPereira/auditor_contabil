from src.utils.scanner import FileScanner
import pandas as pd

FOLDER_PATH = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extratos"

def test_scanner():
    print(f"Scanning folder: {FOLDER_PATH}")
    scanner = FileScanner()
    df = scanner.scan_folder(FOLDER_PATH)
    
    if df.empty:
        print("No files found.")
    else:
        print(f"Found {len(df)} files.")
        print("\nMetadata Sample:")
        print(df[['filename', 'type', 'bank', 'period']].head(15))
        
        # Verify if we got any metadata
        has_bank = df['bank'].str.len() > 0
        print(f"\nFiles with Bank detected: {has_bank.sum()} / {len(df)}")
        
        has_period = df['period'].str.len() > 0
        print(f"Files with Period detected: {has_period.sum()} / {len(df)}")
        
        # Check specific parser detection
        stones = df[df['bank'] == 'Stone']
        print(f"\nStone files detected: {len(stones)}")
        
        bbs = df[df['bank'] == 'Banco do Brasil']
        print(f"BB files detected: {len(bbs)}")

if __name__ == "__main__":
    test_scanner()
