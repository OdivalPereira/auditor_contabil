import pandas as pd

# Simple In-Memory State for MVP
# In production, use Redis or a Database
class AppState:
    def __init__(self):
        self.ledger_df: pd.DataFrame = pd.DataFrame()
        self.bank_df: pd.DataFrame = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None
        self.company_name = "Empresa"  # Nome padrão
    
    def clear(self):
        self.ledger_df = pd.DataFrame()
        self.bank_df = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None
        self.company_name = "Empresa"

# Global Instance
global_state = AppState()
