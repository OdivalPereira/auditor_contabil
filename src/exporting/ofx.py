from datetime import datetime
from typing import List, Dict, Any
import hashlib
from src.common.models import UnifiedTransaction

class OFXWriter:
    def __init__(self, bank_id: str = "000", acct_id: str = "00000", currency: str = "BRL"):
        self.bank_id = bank_id
        self.acct_id = acct_id
        self.currency = currency

    def generate(self, transactions: List[UnifiedTransaction]) -> str:
        """
        Generates a complete OFX string from UnifiedTransactions.
        """
        header = self._build_header()
        body = self._build_body(transactions)
        return header + body

    def _build_header(self) -> str:
        return """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
"""

    def _build_body(self, transactions: List[UnifiedTransaction]) -> str:
        now_str = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Calculate Aggregates
        start_date = min(t.date for t in transactions) if transactions else datetime.now()
        end_date = max(t.date for t in transactions) if transactions else datetime.now()
        
        start_str = start_date.strftime("%Y%m%d000000")
        end_str = end_date.strftime("%Y%m%d235959")
        
        out = []
        out.append("<OFX>")
        out.append("  <SIGNONMSGSRSV1>")
        out.append("    <SONRS>")
        out.append("      <STATUS>")
        out.append("        <CODE>0</CODE>")
        out.append("        <SEVERITY>INFO</SEVERITY>")
        out.append("      </STATUS>")
        out.append(f"      <DTSERVER>{now_str}</DTSERVER>")
        out.append("      <LANGUAGE>POR</LANGUAGE>")
        out.append("    </SONRS>")
        out.append("  </SIGNONMSGSRSV1>")
        out.append("  <BANKMSGSRSV1>")
        out.append("    <STMTTRNRS>")
        out.append(f"      <TRNUID>1001</TRNUID>")
        out.append("      <STATUS>")
        out.append("        <CODE>0</CODE>")
        out.append("        <SEVERITY>INFO</SEVERITY>")
        out.append("      </STATUS>")
        out.append("      <STMTRS>")
        out.append(f"        <CURDEF>{self.currency}</CURDEF>")
        out.append("        <BANKACCTFROM>")
        out.append(f"          <BANKID>{self.bank_id}</BANKID>")
        out.append(f"          <ACCTID>{self.acct_id}</ACCTID>")
        out.append("          <ACCTTYPE>CHECKING</ACCTTYPE>")
        out.append("        </BANKACCTFROM>")
        out.append("        <BANKTRANLIST>")
        out.append(f"          <DTSTART>{start_str}</DTSTART>")
        out.append(f"          <DTEND>{end_str}</DTEND>")
        
        for txn in transactions:
            out.append(self._build_transaction(txn))
            
        out.append("        </BANKTRANLIST>")
        out.append("        <LEDGERBAL>")
        out.append(f"          <BALAMT>0.00</BALAMT>")
        out.append(f"          <DTASOF>{now_str}</DTASOF>")
        out.append("        </LEDGERBAL>")
        out.append("      </STMTRS>")
        out.append("    </STMTTRNRS>")
        out.append("  </BANKMSGSRSV1>")
        out.append("</OFX>")
        
        return "\n".join(out)

    def _build_transaction(self, txn: UnifiedTransaction) -> str:
        date_str = txn.date.strftime("%Y%m%d%H%M%S")
        
        # Ensure proper type
        trn_type = txn.type.upper()
        if trn_type not in ['DEBIT', 'CREDIT', 'OTHER', 'PAYMENT', 'DEP']:
             # Fallback based on amount
             trn_type = 'DEBIT' if txn.amount < 0 else 'CREDIT'
        
        # Ensure FITID
        fitid = txn.fitid
        if not fitid:
            # Generate deterministic FITID
            # Hash of date + amount + memo to ensure uniqueness but consistency
            raw = f"{date_str}{txn.amount}{txn.memo}"
            fitid = hashlib.md5(raw.encode('utf-8')).hexdigest()

        # Check Number / Doc ID
        check_num_tag = ""
        if txn.doc_id:
            check_num_tag = f"          <CHECKNUM>{txn.doc_id}</CHECKNUM>\n"

        return f"""          <STMTTRN>
            <TRNTYPE>{trn_type}</TRNTYPE>
            <DTPOSTED>{date_str}</DTPOSTED>
            <TRNAMT>{txn.amount:.2f}</TRNAMT>
            <FITID>{fitid}</FITID>
{check_num_tag}            <MEMO>{txn.memo}</MEMO>
          </STMTTRN>"""
