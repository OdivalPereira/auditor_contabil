from fastapi import APIRouter, Request
from src.api.state import get_session_state
from src.core.reconciler import Reconciler
from src.core.matcher import CombinatorialMatcher
from src.ui.unified_view import UnifiedViewController
from src.common.logging_config import get_logger
import pandas as pd

logger = get_logger(__name__)
router = APIRouter()

@router.post("/")
def run_reconciliation(request: Request, tolerance: int = 3):
    state = get_session_state(request)
    start = state.ledger_df
    bank = state.bank_df
    
    if start.empty or bank.empty:
        return {"error": "Missing data", "ledger_count": len(start), "bank_count": len(bank)}

    # 1. Filter Bank by Ledger Period
    start_date = start['date'].min()
    end_date = start['date'].max()
    
    bank_filtered = bank[
        (bank['date'] >= start_date) & 
        (bank['date'] <= end_date)
    ].copy()

    logger.info("Reconciliation started.", ledger_range=(str(start_date), str(end_date)), bank_tx_count=len(bank_filtered))
    
    # 2. Reconcile
    reconciler = Reconciler()
    matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(start, bank_filtered, date_tolerance=tolerance)
    
    logger.info("Exact matching completed.", matched_count=len(matched_l), unmatched_ledger=len(unmatched_l))
    
    # 3. Combinatorial
    matcher = CombinatorialMatcher()
    comb_matches, remaining_l, remaining_b = matcher.find_matches(
        unmatched_l, unmatched_b, tolerance_days=tolerance
    )
    
    logger.info("Combinatorial matching completed.", comb_matches=len(comb_matches), remaining_ledger=len(remaining_l))

    # 4. Save results in session state (for export/pdf generation later if needed)
    state.reconcile_results = {
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
    df_view['date'] = pd.to_datetime(df_view['date']).dt.strftime('%Y-%m-%d')
    if 'cluster_date' in df_view.columns:
        df_view['cluster_date'] = pd.to_datetime(df_view['cluster_date']).dt.strftime('%Y-%m-%d')
        
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
    merged['date'] = pd.to_datetime(merged['date']).dt.strftime('%Y-%m-%d')
    chart_data = merged.rename(columns={'amount_x': 'ledger', 'amount_y': 'bank'}).to_dict(orient='records')
    
    # Log status distribution for debugging
    status_counts = {}
    for row in results:
        status = row.get('status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    logger.info(
        "Reconciliation completed",
        bank_total=metrics['bank_total'],
        ledger_total=metrics['ledger_total'],
        comb_matches=len(comb_matches),
        status_distribution=status_counts
    )

    return {
        "metrics": metrics,
        "rows": results,
        "chart": chart_data
    }
