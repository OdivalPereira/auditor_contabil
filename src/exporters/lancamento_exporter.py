"""
Exportador de lançamentos contábeis para formato TXT
"""
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd


class LancamentoExporter:
    """Classe para exportar transações no formato específico do sistema contábil"""
    
    def __init__(self):
        pass
    
    def format_transaction(
        self,
        numero: int,
        data: str,
        conta_debito: str,
        participante_debito: str,
        conta_credito: str,
        participante_credito: str,
        valor: float,
        historico: str,
        documento: str
    ) -> str:
        """
        Formata uma transação no formato específico.
        
        Formato: <numero>,<data>,<conta_debito>,<participante_debito>,<conta_credito>,<participante_credito>,<valor>,,<historico>,DCTO,,<documento>
        """
        # Formatar data para DD/MM/YYYY
        if isinstance(data, str):
            # Tentar converter de ISO format (YYYY-MM-DD)
            try:
                dt = datetime.strptime(data, '%Y-%m-%d')
                data_formatada = dt.strftime('%d/%m/%Y')
            except ValueError:
                # Se já estiver no formato correto, usar como está
                data_formatada = data
        else:
            data_formatada = data.strftime('%d/%m/%Y')
        
        # Formatar valor com 2 casas decimais
        valor_formatado = f"{valor:.2f}"
        
        # Garantir que participantes vazios sejam strings vazias
        participante_debito = participante_debito or ""
        participante_credito = participante_credito or ""
        
        # Garantir que documento seja string
        documento = str(documento) if documento else ""
        
        # Montar linha no formato correto
        linha = f"{numero},{data_formatada},{conta_debito},{participante_debito},{conta_credito},{participante_credito},{valor_formatado},,{historico},DCTO,,{documento}"
        
        return linha
    
    def export_transactions(self, transactions: List[Dict[str, Any]], company_name: str = "EMPRESA", month: int = 1, year: int = 2025, bank: str = "BANCO") -> str:
        """
        Exporta lista de transações para formato TXT.
        
        Args:
            transactions: Lista de dicionários com dados das transações
            company_name: Nome da empresa
            month: Mês do lançamento
            year: Ano do lançamento
            bank: Nome do banco
            
        Returns:
            String com conteúdo do arquivo formatado
        """
        linhas = []
        
        for idx, txn in enumerate(transactions, start=1):
            linha = self.format_transaction(
                numero=idx,
                data=txn.get('date', ''),
                conta_debito=txn.get('conta_debito', ''),
                participante_debito=txn.get('participante_debito', ''),
                conta_credito=txn.get('conta_credito', ''),
                participante_credito=txn.get('participante_credito', ''),
                valor=txn.get('amount', 0.0),
                historico=txn.get('description', ''),
                documento=txn.get('documento', '001')
            )
            linhas.append(linha)
        
        return '\n'.join(linhas)
    
    def generate_filename(self, company_name: str, month: int, year: int, bank: str) -> str:
        """Gera nome do arquivo no formato: lancamento_EMPRESA_MMYYYY BANCO.txt"""
        # Limpar nome da empresa (remover caracteres especiais)
        company_clean = company_name.replace(' ', '').upper()
        return f"lancamento_{company_clean}_{month}{year} {bank}.txt"
