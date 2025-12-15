import pandas as pd
import streamlit as st

class UnifiedViewController:
    def __init__(self):
        pass

    def build_view_data(self, matched_l, matched_b, comb_matches, unmatched_l, unmatched_b):
        """
        Consolidates all transaction sets into a single timeline DataFrame.
        """
        rows = []
        
        # 1. Matched Pairs (1-to-1)
        # We need to pair them up. Reconciler usually returns aligned indices or just DFs.
        # Assuming matched_l and matched_b are aligned by index (row 0 of l matches row 0 of b) 
        # based on how Reconciler constructs them? 
        # Let's check Reconciler logic. Usually it returns filters.
        # IF Reconciler returns just lists of rows, they might not be index-aligned if they were sorted differently?
        # Actually Reconciler returns `matched_ledger` and `matched_bank` which are subsets of original DFs.
        # They might NOT be strictly row-aligned 1-to-1 in the returned DataFrame unless built that way.
        # But for the purpose of this view, we want to group them.
        # A simple approximation for now: Treat them as "Matched" but maybe not perfectly paired visually 
        # if the Reconciler doesn't export the Mapping ID.
        # WAITING: The Reconciler strictly pairs them. If I assume they are just "Matched", they get the Green/Blue color.
        # Ideally we want them next to each other.
        # Let's assign a "Group ID" based on Date + Amount to try to cluster them.
        
        group_id_counter = 0
        
        # Helper to add row
        def add_row(row, source, status, group_id=None, color_code=None):
            rows.append({
                'date': row['date'],
                'amount': row['amount'],
                'description': row['description'],
                'source': source,
                'status': status,
                'group_id': str(group_id) if group_id is not None and group_id != -1 else "-1",
                'color_code': color_code
            })

        # Process Standard Matches
        # Now we have 'match_id' from Reconciler!
        for _, row in matched_l.iterrows():
            gid = row.get('match_id') 
            if pd.isna(gid): gid = "-1"
            add_row(row, 'Diário', 'Conciliado', group_id=gid, color_code='matched_ledger')
            
        for _, row in matched_b.iterrows():
            gid = row.get('match_id')
            if pd.isna(gid): gid = "-1"
            add_row(row, 'Banco', 'Conciliado', group_id=gid, color_code='matched_bank')

        # Process Combinatorial Matches (These DO have grouping info)
        for m in comb_matches:
            # Generate a distinct Group ID for combos (e.g., C-0, C-1)
            gid = f"C-{group_id_counter}"
            group_id_counter += 1
            
            # Bank Item
            add_row(m['bank_item'], 'Banco', 'Conciliado (Comb)', gid, 'matched_bank')
            
            # Ledger Items
            for _, l_row in m['ledger_items'].iterrows():
                add_row(l_row, 'Diário', 'Conciliado (Comb)', gid, 'matched_ledger')

        # Process Unmatched (The most important ones)
        for _, row in unmatched_l.iterrows():
            add_row(row, 'Diário', 'Pendente - Diário', "-1", 'unmatched_ledger')
            
        for _, row in unmatched_b.iterrows():
            add_row(row, 'Banco', 'Pendente - Banco', "-1", 'unmatched_bank')
            
        df = pd.DataFrame(rows)
        if df.empty:
            return df
            
        # Enforce Types
        df['date'] = pd.to_datetime(df['date'])
        # Ensure group_id is string
        df['group_id'] = df['group_id'].astype(str)
        
        # Source Ordered Categorical
        df['source'] = pd.Categorical(
            df['source'], 
            categories=['Diário', 'Banco'], 
            ordered=True
        )
        
        # --- CLUSTER SORTING ---
        # We need groups to stay contiguous.
        # 1. Calculate min_date for each group_id != "-1"
        group_dates = df[df['group_id'] != "-1"].groupby('group_id')['date'].transform('min')
        
        # 2. Assign cluster_date
        # If part of a group, use group's min_date. Else use own date.
        df['cluster_date'] = df['date'] # Default
        df.loc[df['group_id'] != "-1", 'cluster_date'] = group_dates
        
        # 3. Sort
        # Primary: Cluster Date (Linear Time)
        # Secondary: Group ID (Keep members of same group together)
        # Tertiary: Source (Diário top)
        df = df.sort_values(by=['cluster_date', 'group_id', 'source'])
        
        # Reset index is crucial for styling logic (checking prev/next)
        df = df.reset_index(drop=True)
        
        return df

    def apply_styles(self, df):
        """
        Applies pandas Styler for color coding and borders.
        """
        # CRITICAL: Reset index so row.name matches iloc positions
        # This prevents IndexError when applying styles to filtered dataframes
        df = df.reset_index(drop=True)

        def style_row(row):
            styles = []
            
            # 1. Background Color
            code = row['color_code']
            custom_colors = {
                'matched_ledger': 'background-color: #cff4fc; color: #055160', # Light Blue
                'matched_bank':   'background-color: #d1e7dd; color: #0f5132', # Light Green
                'unmatched_ledger': 'background-color: #f8d7da; color: #842029', # Red/Pink
                'unmatched_bank':   'background-color: #ffe0b2; color: #BF360C', # Orange
            }
            bg_style = custom_colors.get(code, '')
            
            # 2. Border Logic for Combinatorial Groups
            border_style = ""
            gid = str(row['group_id'])
            
            if gid != "-1":
                # Common borders for the "Box"
                border_color = "#6c757d" # Gray
                border_width = "2px"
                
                # Check neighbors to decide Top/Bottom borders
                # We need the dataframe index to check neighbors.
                # 'row.name' contains the index if we iterate correctly.
                idx = row.name
                
                # Is First in Group?
                # True if: It's the first row (idx=0) OR previous row has different group_id
                is_first = False
                if idx == 0:
                    is_first = True
                elif df.iloc[idx-1]['group_id'] != gid:
                    is_first = True
                    
                # Is Last in Group?
                # True if: It's the last row OR next row has different group_id
                is_last = False
                if idx == len(df) - 1:
                    is_last = True
                elif df.iloc[idx+1]['group_id'] != gid:
                    is_last = True
                
                # Apply Borders
                # Left/Right always
                border_style += f"border-left: {border_width} solid {border_color}; "
                border_style += f"border-right: {border_width} solid {border_color}; "
                
                if is_first:
                    border_style += f"border-top: {border_width} solid {border_color}; "
                if is_last:
                    border_style += f"border-bottom: {border_width} solid {border_color}; "
            
            # Combine
            full_style = f"{bg_style}; {border_style}"
            
            return [full_style] * len(row)

        return df.style.apply(style_row, axis=1).format({'amount': "R$ {:,.2f}"})
