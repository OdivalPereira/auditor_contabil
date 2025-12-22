from fastapi import APIRouter
from src.api.state import global_state
from src.core.reconciler import Reconciler
from src.core.matcher import CombinatorialMatcher
from src.ui.unified_view import UnifiedViewController
import pandas as pd

router = APIRouter()

@router.post("/")
def run_reconciliation(tolerance: int = 3):
    start = global_state.ledger_df
    bank = global_state.bank_df
    
    if start.empty or bank.empty:
        return {"error": "Missing data", "ledger_count": len(start), "bank_count": len(bank)}

    # 1. Filter Bank by Ledger Period
    start_date = start['date'].min()
    end_date = start['date'].max()
    
    bank_filtered = bank[
        (bank['date'] >= start_date) & 
        (bank['date'] <= end_date)
    ].copy()

    print(f"DEBUG: Ledger range {start_date} to {end_date}")
    print(f"DEBUG: Bank transactions before filter: {len(bank)}")
    print(f"DEBUG: Bank transactions after filter: {len(bank_filtered)}")
    
    # 2. Reconcile
    reconciler = Reconciler()
    matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(start, bank_filtered, date_tolerance=tolerance)
    
    # 3. Combinatorial
    matcher = CombinatorialMatcher()
    comb_matches, remaining_l, remaining_b = matcher.find_matches(
        unmatched_l, unmatched_b, tolerance_days=tolerance
    )
    
    # 4. Save results in state (for export/pdf generation later if needed)
    global_state.reconcile_results = {
        'matched_l': matched_l,
        'matched_b': matched_b,
        'comb_matches': comb_matches,
        'remaining_l': remaining_l,
        'remaining_b': remaining_b
    }
    
    # 5. Build Unified View for Frontend
    # Frontend needs a flat JSON compatible list, UnifiedViewController produces a DF.
    uv = UnifiedViewController()
    df_view = uv.build_view_data(matched_l, matched_b, comb_matches, remaining_l, remaining_b)
    
    # Transform for JSON
    # Convert dates to ISO string
    df_view['date'] = df_view['date'].dt.strftime('%Y-%m-%d')
    if 'cluster_date' in df_view.columns:
        df_view['cluster_date'] = df_view['cluster_date'].dt.strftime('%Y-%m-%d')
        
    results = df_view.to_dict(orient='records')
    
    # Metrics
    metrics = {
        "ledger_total": int(len(start)),
        "bank_total": int(len(bank_filtered)),
        "diff_initial": abs(unmatched_l['amount'].sum() - unmatched_b['amount'].sum()),
        "diff_final": abs(remaining_l['amount'].sum() - remaining_b['amount'].sum()),
        "comb_count": len(comb_matches)
    }
    
    # Chart Data
    # Group by date for chart
    l_grouped = start.groupby('date')['amount'].sum().reset_index()
    b_grouped = bank_filtered.groupby('date')['amount'].sum().reset_index()
    
    # Merge for consistent dates
    merged = pd.merge(l_grouped, b_grouped, on='date', how='outer').fillna(0)
    merged['date'] = merged['date'].dt.strftime('%Y-%m-%d')
    chart_data = merged.rename(columns={'amount_x': 'ledger', 'amount_y': 'bank'}).to_dict(orient='records')
    
    return {
        "metrics": metrics,
        "rows": results,
        "chart": chart_data
    }
