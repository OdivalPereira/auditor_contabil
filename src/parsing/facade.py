import os
import pandas as pd
from .pipeline import ExtractorPipeline
from .config.registry import LayoutRegistry
from .sources.ofx import OfxParser

class ParserFacade:
    """
    Facade to bridge legacy ParserFactory calls to the new Unified Pipeline.
    """
    
    def __init__(self):
        # Locate layouts relative to this file or project root
        # Assuming run from root
        root = os.getcwd()
        layouts_dir = os.path.join(root, 'src', 'parsing', 'layouts')
        self.registry = LayoutRegistry(layouts_dir)
        self.pipeline = ExtractorPipeline(self.registry)
        self.ofx_parser = OfxParser()

    def parse(self, file_path: str):
        """
        Unified parse method. Dispatches to appropriate parser.
        Returns: (pd.DataFrame, dict) -> (transactions, metadata)
        """
        if file_path.lower().endswith('.ofx'):
            return self.ofx_parser.parse(file_path)
        
        # Default to PDF Pipeline
        result = self.pipeline.process_file(file_path)
        
        # Convert Pipeline result (Dict) to Legacy format (DataFrame, Dict)
        metadata = result.get('account_info', {})
        # Map some keys if necessary
        if 'bank_id' in metadata:
            # Try to fetch bank name if possible or just use ID
            metadata['bank'] = f"Bank {metadata['bank_id']}"
            
        txs = result.get('transactions', [])
        
        if not txs:
             return pd.DataFrame(), metadata

        # Convert UnifiedTransaction objects to dicts
        data = [t.to_dict() for t in txs]
        df = pd.DataFrame(data)
        
        # Adaptation for Conciliator (expects 'description', 'source')
        # UnifiedTransaction has: date, amount, memo, type, doc_id, fitid
        if 'memo' in df.columns:
            df = df.rename(columns={'memo': 'description'})
        
        df['source'] = 'Bank'
        
        # Ensure date is date object
        if 'date' in df.columns:
             df['date'] = pd.to_datetime(df['date']).dt.date
             
        return df, metadata

    @classmethod
    def get_parser(cls, file_path: str):
        """
        Mimics factory pattern. Returns an instance of this facade
        which can handle the file.
        """
        # In the new architecture, the Facade handles dispatching internally
        # so we just return the facade itself.
        return cls()
