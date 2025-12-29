
def _parse_ledger_csv(file_obj):
    import pandas as pd
    import io
    
    company_name = "Empresa"  # Valor padrão
    
    # Read file content
    if hasattr(file_obj, 'read'):
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('latin1', errors='ignore')
    else:
        with open(file_obj, 'r', encoding='latin1', errors='ignore') as f:
            content = f.read()
    
    lines = content.split('\n')
    
    # Extract company name from line 1 (index 1)
    # Format: "Consulta de lançamentos da empresa [CÓDIGO] - [NOME]"
    try:
        if len(lines) > 1:
            second_line = lines[1].strip()
            if 'empresa' in second_line.lower():
                parts = second_line.split(' - ', 1)
                if len(parts) > 1:
                    full_name = parts[1].strip()
                    empresa_part = parts[0]
                    if 'empresa' in empresa_part.lower():
                        code_match = empresa_part.split('empresa')[-1].strip()
                        if code_match:
                            company_name = f"{code_match} - {full_name}"
                        else:
                            company_name = full_name
                    else:
                        company_name = full_name
    except Exception as e:
        print(f"Could not extract company name: {e}")
    
    # Manual parsing to handle field mismatch
    # CSV structure:
    # Line 0: blank
    # Line 1: title
    # Line 2: blank  
    # Line 3: headers (19 fields)
    # Line 4: blank
    # Line 5+: data (20 fields - mismatch!)
    
    # Parse data lines starting from line 5
    data_rows = []
    for line in lines[5:]:
        if not line.strip():
            continue
        
        fields = line.strip().split(';')
        
        # Skip if not enough fields
        if len(fields) < 12:
            continue
        
        try:
            # Field mapping based on investigation:
            # [0]: Transação
            # [1]: Chave  
            # [2]: Data (DD/MM/YYYY)
            # [3]: Débito (account code)
            # [7]: Crédito (account code)
            # [11]: Valor
            # [15]: Complemento (description)
            
            data_rows.append({
                'transaction_id': fields[0],
                'key': fields[1],
                'date': fields[2],
                'debit_account': fields[3] if len(fields) > 3 else '',
                'credit_account': fields[7] if len(fields) > 7 else '',
                'amount': fields[11] if len(fields) > 11 else '0',
                'description': fields[15] if len(fields) > 15 else ''
            })
        except Exception as e:
            # Skip malformed rows
            continue
    
    if not data_rows:
        # Fallback to standard pandas if manual parsing failed
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        return pd.read_csv(file_obj), company_name
    
    # Create DataFrame
    df = pd.DataFrame(data_rows)
    
    # Parse dates
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    
    # Remove rows with invalid dates
    df = df.dropna(subset=['date'])
    
    # Parse amounts
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    
    # Determine sign based on debit/credit accounts
    # Find the most common account (likely the bank account)
    try:
        all_accounts = pd.concat([
            df['debit_account'], 
            df['credit_account']
        ])
        # Filter out empty/null values
        all_accounts = all_accounts[~all_accounts.isin(['', '0', 'nan'])]
        
        if not all_accounts.empty:
            bank_account = all_accounts.mode()[0]
            
            # If bank in credit -> outflow (negative)
            is_credit = df['credit_account'] == bank_account
            df.loc[is_credit, 'amount'] = -df.loc[is_credit, 'amount'].abs()
            
            # If bank in debit -> inflow (positive)
            is_debit = df['debit_account'] == bank_account
            df.loc[is_debit, 'amount'] = df.loc[is_debit, 'amount'].abs()
    except Exception as e:
        print(f"Sign detection failed: {e}. Using absolute values.")
    
    print(f"Successfully parsed {len(df)} ledger entries from CSV")
    
    return df, company_name

