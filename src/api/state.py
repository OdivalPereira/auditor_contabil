import pandas as pd

# Simple In-Memory State for MVP
# In production, use Redis or a Database
class AppState:
    def __init__(self):
        self.ledger_df: pd.DataFrame = pd.DataFrame()
        self.bank_df: pd.DataFrame = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None
    
    def clear(self):
        self.ledger_df = pd.DataFrame()
        self.bank_df = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None

# Global Instance
global_state = AppState()
