import pandas as pd
from itertools import combinations
from datetime import timedelta

class CombinatorialMatcher:
    def __init__(self):
        pass

    def find_matches(self, unmatched_ledger, unmatched_bank, tolerance_days=3, max_combination_size=4):
        """
        Attempts to solve the "Puzzle":
        For each Unmatched Bank Item, find a subset of Unmatched Ledger Items 
        (within date tolerance) that sums up to the Bank amount.
        
        Returns:
            - combined_matches: List of dicts {'bank_item': row, 'ledger_items': [rows], 'sum_diff': float}
            - remaining_ledger: DataFrame
            - remaining_bank: DataFrame
        """
        if unmatched_bank.empty or unmatched_ledger.empty:
            return [], unmatched_ledger, unmatched_bank

        # Make copies to manipulate
        df_l = unmatched_ledger.copy()
        df_b = unmatched_bank.copy()
        
        # Ensure dates are datetime.date objects for consistent comparison
        df_l['date'] = pd.to_datetime(df_l['date']).dt.date
        df_b['date'] = pd.to_datetime(df_b['date']).dt.date
        
        # Track used indices
        used_ledger_indices = set()
        used_bank_indices = set()
        
        matches = []
        
        # Sort bank items by date ? Usually helps.
        df_b = df_b.sort_values('date')
        
        for b_idx, b_row in df_b.iterrows():
            if b_idx in used_bank_indices:
                continue
                
            b_amt = abs(b_row['amount'])
            b_date = b_row['date']
            
            # Filter Ledger Candidates:
            # 1. Not used
            # 2. Date within tolerance
            candidates = df_l[
                (~df_l.index.isin(used_ledger_indices)) &
                (df_l['date'] >= b_date - timedelta(days=tolerance_days)) &
                (df_l['date'] <= b_date + timedelta(days=tolerance_days))
            ]
            
            # Optimization: Sort candidates by amount (optional, but might speed up logic?)
            # Or filtering candidates that are smaller than B_amt?? 
            # Not necessarily, because Ledger sum might include negative adjustment? 
            # But we are using absolute logic so amounts are positive.
            # So sum(L_subset) = B_amt. Thus individual L items usually smaller than B_amt.
            # Unless we support "Splitting" (Ledger > Bank)? No, user said "140 + 10 = 150".
            # So Ledger items must be <= B_amt (mostly).
            # But floating point issues? Let's check abs(sum - B) < 0.01.
            
            candidates = candidates[candidates['amount'].abs() <= b_amt + 0.01]
            
            # If too many candidates, optimization becomes critical.
            # Limit to top N candidates closest in date? Or just strict count limit.
            if len(candidates) > 20: 
                 # If too many, maybe skip to avoid hanging? Or reduce search.
                 # Prioritize closest amounts or dates.
                 candidates = candidates.head(20)
            
            found_combo = False
            candidate_rows = candidates.to_dict('records')
            candidate_indices = candidates.index.tolist()
            
            # Try combinations of 2 up to max_combination_size
            for r in range(2, max_combination_size + 1):
                # We need indices to track usage
                for combo_indices in combinations(candidate_indices, r):
                    # Get the actual amounts
                    # We can map indices back to amounts
                    current_sum = 0
                    subset_rows = []
                    
                    for idx in combo_indices:
                        val = df_l.at[idx, 'amount']
                        current_sum += abs(val) # ABS matching strategy
                    
                    if abs(current_sum - b_amt) < 0.02: # Float tolerance
                        # MATCH FOUND!
                        found_combo = True
                        
                        # retrieve rows
                        subset_rows = df_l.loc[list(combo_indices)]
                        
                        match_info = {
                            'bank_item': b_row,
                            'ledger_items': subset_rows,
                            'type': f'Combined ({r} items)'
                        }
                        matches.append(match_info)
                        
                        # Mark as used
                        used_bank_indices.add(b_idx)
                        used_ledger_indices.update(combo_indices)
                        break # Stop looking for combos for this bank item
                
                if found_combo:
                    break
        
        # Remove matched items from DataFrames
        remaining_bank = df_b[~df_b.index.isin(used_bank_indices)]
        remaining_ledger = df_l[~df_l.index.isin(used_ledger_indices)]
        
        return matches, remaining_ledger, remaining_bank
