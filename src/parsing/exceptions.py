"""
Custom exception for when a bank statement layout cannot be identified.
"""

class LayoutNotIdentifiedException(Exception):
    """
    Raised when a PDF bank statement layout cannot be identified.
    
    This exception should include:
    - The filename that failed
    - The detected bank (if any)
    - Sample text or markers that were found
    - Suggested action for the user
    """
    
    def __init__(self, message: str, filename: str = None, bank_id: str = None, sample_text: str = None):
        self.filename = filename
        self.bank_id = bank_id
        self.sample_text = sample_text
        
        # Build detailed message
        details = []
        if filename:
            details.append(f"Arquivo: {filename}")
        if bank_id:
            details.append(f"Banco detectado: {bank_id}")
        if sample_text:
            details.append(f"Amostra: {sample_text[:200]}...")
        
        full_message = f"{message}\n" + "\n".join(details) if details else message
        super().__init__(full_message)
