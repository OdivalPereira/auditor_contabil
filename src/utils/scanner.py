import os
import logging
import pandas as pd
from ..parsing.facade import ParserFacade

logger = logging.getLogger(__name__)

class FileScanner:
    def scan_folder(self, folder_path):
        results = []
        
        # Recursive walk
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.pdf', '.ofx')):
                    full_path = os.path.join(root, file)
                    meta = self.extract_metadata(full_path, file)
                    results.append(meta)
                    
        return pd.DataFrame(results)

    def extract_metadata(self, file_path, filename):
        meta = {
            'selected': False,
            'filename': filename,
            'type': filename.split('.')[-1].upper(),
            'bank': '',
            'agency': '',
            'account': '',
            'period': '',
            'path': file_path
        }
        
        try:
            # Use Factory to get the correct parser
            parser = ParserFactory.get_parser(file_path)
            if parser:
                # Parse to get metadata
                _, doc_meta = parser.parse(file_path)
                
                meta['bank'] = doc_meta.get('bank', '')
                meta['agency'] = doc_meta.get('agency', '')
                meta['account'] = doc_meta.get('account', '')
                
                s_date = doc_meta.get('start_date')
                e_date = doc_meta.get('end_date')
                
                if s_date and e_date:
                    meta['period'] = f"{s_date.strftime('%d/%m/%Y')} - {e_date.strftime('%d/%m/%Y')}"
                elif s_date:
                    meta['period'] = f"Inicio: {s_date.strftime('%d/%m/%Y')}"
            else:
                meta['bank'] = "Desconhecido"
                
        except Exception as e:
            # On error, just return basic info
            logger.error(f"Error scanning {filename}: {e}")
            
        return meta

