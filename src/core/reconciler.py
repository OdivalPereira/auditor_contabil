import pandas as pd

class Reconciler:
    def reconcile(self, df_ledger: pd.DataFrame, df_bank: pd.DataFrame, date_tolerance: int = 3):
        """
        Reconciles Ledger and Bank transactions using strict Date/Amount matching.
        Returns:
            - matched_ledger (DataFrame)
            - matched_bank (DataFrame)
            - unmatched_ledger (DataFrame)
            - unmatched_bank (DataFrame)
        """
        if df_ledger.empty or df_bank.empty:
            return df_ledger, df_bank, df_ledger, df_bank

        # Ensure columns exist
        required_cols = ['date', 'amount', 'description', 'source']
        for col in required_cols:
            if col not in df_ledger.columns: df_ledger[col] = None
            if col not in df_bank.columns: df_bank[col] = None

        # Sort for deterministic matching
        df_ledger = df_ledger.sort_values(by=['date', 'amount']).reset_index(drop=True)
        df_bank = df_bank.sort_values(by=['date', 'amount']).reset_index(drop=True)
        
        df_ledger['matched'] = False
        df_bank['matched'] = False
        df_ledger['match_id'] = None
        df_bank['match_id'] = None
        
        match_counter = 0

            # 1. Exact Date Match (with Tolerance on Absolute Amount)
        for l_idx, l_row in df_ledger.iterrows():
            # Use EXACT signed amount match: abs(bank_amt - ledger_amt) < 0.01
            candidates = df_bank[
                (df_bank['date'] == l_row['date']) &
                (abs(df_bank['amount'] - l_row['amount']) < 0.01) &
                (df_bank['matched'] == False)
            ]
            
            if not candidates.empty:
                b_idx = candidates.index[0]
                df_bank.at[b_idx, 'matched'] = True
                df_ledger.at[l_idx, 'matched'] = True
                
                # Assign Match ID
                mid = f"S-{match_counter}"
                match_counter += 1
                df_bank.at[b_idx, 'match_id'] = mid
                df_ledger.at[l_idx, 'match_id'] = mid

        # 2. Tolerant Match (Date +/- tolerance days, Signed Amount)
        TOLERANCE_DAYS = date_tolerance
        unmatched_ledger_indices = df_ledger[df_ledger['matched'] == False].index
        
        for l_idx in unmatched_ledger_indices:
            l_row = df_ledger.loc[l_idx]
            l_date = l_row['date']
            l_amt = l_row['amount']
            
            # Filter candidates by Signed Amount Tolerance FIRST
            candidates = df_bank[
                (df_bank['matched'] == False) &
                (abs(df_bank['amount'] - l_amt) < 0.01)
            ].copy()
            
            if not candidates.empty:
                # Calculate absolute day difference
                candidates['date_diff'] = candidates['date'].apply(lambda x: abs((x - l_date).days))
                
                valid_candidates = candidates[candidates['date_diff'] <= TOLERANCE_DAYS].sort_values('date_diff')
                
                if not valid_candidates.empty:
                    b_idx = valid_candidates.index[0]
                    df_bank.at[b_idx, 'matched'] = True
                    df_ledger.at[l_idx, 'matched'] = True

                    # Assign Match ID
                    mid = f"S-{match_counter}"
                    match_counter += 1
                    df_bank.at[b_idx, 'match_id'] = mid
                    df_ledger.at[l_idx, 'match_id'] = mid

        # Split results
        matched_ledger = df_ledger[df_ledger['matched'] == True].copy()
        unmatched_ledger = df_ledger[df_ledger['matched'] == False].copy()
        
        matched_bank = df_bank[df_bank['matched'] == True].copy()
        unmatched_bank = df_bank[df_bank['matched'] == False].copy()
        
        return matched_ledger, matched_bank, unmatched_ledger, unmatched_bank
