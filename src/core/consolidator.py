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
        
        # Deduplication Logic
        # Strictly remove duplicates where Date, Amount, and Description match exactly
        # We might want to be lenient on Description if it comes from different parsers?
        # For now, strict.
        
        # However, "Payment Receipt" descriptions might differ from "Monthly Statement" descriptions.
        # e.g. "Pagamento Boleto" vs "COMPROVANTE DE PAGAMENTO..."
        # If we have same Date and Amount, it's highly likely the same transaction.
        # Let's try deduplicating on Date + Amount first if they are on the SAME DAY.
        # But legitimate duplicate amounts exist (e.g. two transfers of 50.00).
        # So check description similarity or just keep strict first.
        
        # User requested: "detect repetition... duplicate entries during analysis"
        # Strategy: Drop exact duplicates first.
        
        deduplicated_df = combined_df.drop_duplicates(subset=['date', 'amount', 'description'], keep='first')
        
        # Conflict Check: Same Date/Amount but different Description (from diff files)
        # This is where we might double count if we are not careful.
        # But without a unique ID, we can't be sure.
        # Let's verify overlapping counts.
        
        # For the scope of this request, exact match deduplication is the safest start.
        
        return deduplicated_df.sort_values(by='date').reset_index(drop=True)
