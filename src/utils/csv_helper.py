
def _parse_ledger_csv(file_obj):
    import pandas as pd
    import io
    
    company_name = "Empresa"  # Valor padrão
    
    # Check if file_obj is bytes-like or path
    if isinstance(file_obj, (str, bytes)):
        # Path
        pass 
    else:
        # Streamlit UploadedFile
        # We need to make it seekable or read it
        pass

    # For Streamlit UploadedFile, we can pass it directly to read_csv?
    # Yes, but we need to handle the specific layout (latin1, ; sep, skip 4, header=None)
    
    try:
        # Try reading with specific parameters for "CONSULTA LANÇAMENTOS"
        # Since file_obj might be a buffer, we need to be careful with rewinding if first attempt fails.
        # But we know the format now.
        
        # First, read the first few lines to extract company name
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        # Read first 4 lines to extract company info
        try:
            if hasattr(file_obj, 'read'):
                # For file-like objects
                first_lines = []
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                for i in range(5):
                    line = file_obj.readline()
                    if isinstance(line, bytes):
                        line = line.decode('latin1', errors='ignore')
                    first_lines.append(line.strip())
                # Reset to beginning
                file_obj.seek(0)
            else:
                # For file paths
                with open(file_obj, 'r', encoding='latin1') as f:
                    first_lines = [f.readline().strip() for _ in range(5)]
            
            # Extract company name from line 2 (index 1)
            # Format: "Consulta de lançamentos da empresa [CÓDIGO] - [NOME]"
            if first_lines and len(first_lines) > 1:
                second_line = first_lines[1]
                print(f"DEBUG: Second line of CSV: {second_line}")
                
                # Try to extract from "Consulta de lançamentos da empresa XXX - NOME"
                if 'empresa' in second_line.lower():
                    # Split by ' - ' to get the name part
                    parts = second_line.split(' - ', 1)
                    if len(parts) > 1:
                        # Get everything after ' - '
                        full_name = parts[1].strip()
                        
                        # Also try to extract the code
                        # Pattern: "empresa CÓDIGO - NOME"
                        empresa_part = parts[0]
                        if 'empresa' in empresa_part.lower():
                            # Extract code after "empresa "
                            code_match = empresa_part.split('empresa')[-1].strip()
                            if code_match:
                                company_name = f"{code_match} - {full_name}"
                            else:
                                company_name = full_name
                        else:
                            company_name = full_name
                        
                        print(f"DEBUG: Extracted company name: {company_name}")
        except Exception as e:
            print(f"Could not extract company name: {e}")
        
        # If it's a buffer, reset pointer
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            
        # Manual CSV parsing to handle variable column counts
        # This is necessary because legacy systems export inconsistent CSVs
        import csv
        
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        # Read file content
        if hasattr(file_obj, 'read'):
            content = file_obj.read()
            if isinstance(content, bytes):
                content = content.decode('latin1', errors='ignore')
        else:
            with open(file_obj, 'r', encoding='latin1', errors='ignore') as f:
                content = f.read()
        
        lines = content.split('\n')[4:]  # Skip first 4 lines
        
        # Parse manually with csv reader to handle quoted fields
        rows = []
        reader = csv.reader(lines, delimiter=';')
        for line_num, row in enumerate(reader, 5):  # Start from line 5 (after skip)
            if len(row) >= 16:  # Need at least columns up to 15 (description)
                rows.append(row)
        
        # Create DataFrame from parsed rows
        df = pd.DataFrame(rows)
        
        # Now df has all rows regardless of column count
        print(f"DEBUG: Successfully parsed {len(df)} rows from CSV")
        
        # Check if it looks right (19 cols?)
        if len(df.columns) > 10:
             # Parse Date (Column 2) BEFORE renaming
             try:
                 df[2] = pd.to_datetime(df[2], dayfirst=True, errors='coerce')
             except Exception:
                 pass
             
             # Parse Amount (Column 11) - ensure numeric
             try:
                 # Amount is already parsed as float by read_csv usually
                 df[11] = pd.to_numeric(df[11], errors='coerce')
             except Exception:
                 pass
             
             # NOW apply mapping
             mapping = {2: 'date', 11: 'amount', 15: 'description'}
             df.rename(columns=mapping, inplace=True)

             # Determine Sign based on Debit/Credit columns (Indices 3 and 7)
             # Index 3: Debit Account, Index 7: Credit Account
             # We assume the most frequent account in these columns is the Bank Account.
             
             # Extract account columns
             try:
                 debit_accs = df[3].fillna(0).astype(str)
                 credit_accs = df[7].fillna(0).astype(str)
                 
                 # Find most common account
                 all_accs = pd.concat([debit_accs, credit_accs])
                 # Filter out '0', 'nan' if possible
                 all_accs = all_accs[~all_accs.isin(['0', '0.0', 'nan', ''])]
                 
                 if not all_accs.empty:
                     bank_acc_id = all_accs.mode()[0]
                     
                     # Apply signs
                     # If Bank in Debit -> Positive (Inflow)
                     # If Bank in Credit -> Negative (Outflow)
                     
                     # Mask for Bank in Credit
                     is_credit = df[7].astype(str) == bank_acc_id
                     
                     # Mask for Bank in Debit
                     is_debit = df[3].astype(str) == bank_acc_id
                     
                     # If row has Bank in Credit, multiply by -1
                     df.loc[is_credit, 'amount'] = -df.loc[is_credit, 'amount'].abs()
                     
                     # If row has Bank in Debit, ensure positive
                     df.loc[is_debit, 'amount'] = df.loc[is_debit, 'amount'].abs()
                     
             except Exception as e_sign:
                 print(f"Sign detection failed: {e_sign}. Defaulting to absolute.")

             return df, company_name
        else:
             # Fallback to standard read if it didn't look like our special CSV
             if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
             return pd.read_csv(file_obj), company_name

    except Exception:
        # Fallback
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        return pd.read_csv(file_obj), company_name
