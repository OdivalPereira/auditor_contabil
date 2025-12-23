import pandas as pd

class TransactionConsolidator:
    @staticmethod
    def consolidate(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        if not dataframes:
            return pd.DataFrame(columns=['date', 'amount', 'description', 'source', 'source_file'])
            
        combined_df = pd.concat(dataframes, ignore_index=True)
        
        # Ensure correct types
        combined_df['date'] = pd.to_datetime(combined_df['date']).dt.date
        combined_df['amount'] = pd.to_numeric(combined_df['amount'])
        combined_df['description'] = combined_df['description'].fillna('').astype(str).str.strip()
        
        # Deduplication Strategy:
        # We now use 'source_file' and 'internal_id' (added by BaseParser) 
        # as a unique composite key for each physical transaction in each file.
        # This keeps legitimate duplicates (same day/amount/desc) within a file,
        # but removes redundant data if the same file is uploaded multiple times.
        if 'internal_id' in combined_df.columns and 'source_file' in combined_df.columns:
            deduplicated_df = combined_df.drop_duplicates(subset=['source_file', 'internal_id'], keep='first')
        else:
            # Fallback for legacy/other data sources
            deduplicated_df = combined_df.drop_duplicates(subset=['date', 'amount', 'description'], keep='first')
        
        # Conflict Check: Same Date/Amount but different Description (from diff files)
        # This is where we might double count if we are not careful.
        # But without a unique ID, we can't be sure.
        # Let's verify overlapping counts.
        
        # For the scope of this request, exact match deduplication is the safest start.
        
        return deduplicated_df.sort_values(by='date').reset_index(drop=True)
