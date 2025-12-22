"""
Módulo de exportação Excel moderno e profissional.
Gera relatórios de conciliação com formatação avançada, gráficos e múltiplas abas.
"""
from io import BytesIO
from datetime import datetime
import pandas as pd
from xlsxwriter.utility import xl_range


class ExcelExporter:
    """Exportador Excel moderno com formatação profissional."""
    
    # Paleta de cores do sistema
    COLORS = {
        'conciliado': '#10b981',      # Verde
        'apenas_banco': '#f59e0b',    # Laranja
        'apenas_diario': '#ef4444',   # Vermelho
        'header_bg': '#1e293b',       # Azul escuro
        'header_text': '#ffffff',     # Branco
        'zebra_light': '#f8fafc',     # Cinza muito claro
        'zebra_dark': '#f1f5f9',      # Cinza claro
        'accent': '#6366f1',          # Roxo/Índigo
        'positive': '#10b981',        # Verde para valores positivos
        'negative': '#ef4444',        # Vermelho para valores negativos
    }
    
    def __init__(self, company_name="Empresa", start_date=None, end_date=None):
        """
        Inicializa o exportador Excel.
        
        Args:
            company_name: Nome da empresa
            start_date: Data inicial do período
            end_date: Data final do período
        """
        self.company_name = company_name
        self.start_date = start_date
        self.end_date = end_date
        self.buffer = BytesIO()
        self.workbook = None
        self.formats = {}
        
    def _create_formats(self):
        """Cria formatos reutilizáveis para células."""
        # Cabeçalho principal
        self.formats['header'] = self.workbook.add_format({
            'bold': True,
            'font_color': self.COLORS['header_text'],
            'bg_color': self.COLORS['header_bg'],
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
        })
        
        # Título da aba
        self.formats['title'] = self.workbook.add_format({
            'bold': True,
            'font_size': 18,
            'font_color': self.COLORS['accent'],
            'align': 'left',
        })
        
        # Subtítulo
        self.formats['subtitle'] = self.workbook.add_format({
            'font_size': 11,
            'font_color': '#64748b',
            'italic': True,
        })
        
        # Célula de dados normal
        self.formats['cell'] = self.workbook.add_format({
            'border': 1,
            'border_color': '#e2e8f0',
            'valign': 'vcenter',
        })
        
        # Célula zebrada clara
        self.formats['cell_zebra_light'] = self.workbook.add_format({
            'border': 1,
            'border_color': '#e2e8f0',
            'bg_color': self.COLORS['zebra_light'],
            'valign': 'vcenter',
        })
        
        # Célula zebrada escura
        self.formats['cell_zebra_dark'] = self.workbook.add_format({
            'border': 1,
            'border_color': '#e2e8f0',
            'bg_color': self.COLORS['zebra_dark'],
            'valign': 'vcenter',
        })
        
        # Valores monetários positivos
        self.formats['currency_positive'] = self.workbook.add_format({
            'num_format': 'R$ #,##0.00',
            'border': 1,
            'border_color': '#e2e8f0',
            'font_color': self.COLORS['positive'],
            'bold': True,
        })
        
        # Valores monetários negativos
        self.formats['currency_negative'] = self.workbook.add_format({
            'num_format': 'R$ #,##0.00',
            'border': 1,
            'border_color': '#e2e8f0',
            'font_color': self.COLORS['negative'],
            'bold': True,
        })
        
        # Total
        self.formats['total'] = self.workbook.add_format({
            'bold': True,
            'font_size': 12,
            'border': 2,
            'bg_color': '#cbd5e1',
            'num_format': 'R$ #,##0.00',
        })
        
        # Métrica label
        self.formats['metric_label'] = self.workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': self.COLORS['header_bg'],
            'font_color': self.COLORS['header_text'],
            'border': 1,
        })
        
        # Métrica valor
        self.formats['metric_value'] = self.workbook.add_format({
            'font_size': 11,
            'border': 1,
            'bg_color': '#f8fafc',
            'num_format': '#,##0',
        })
        
        # Data
        self.formats['date'] = self.workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'border_color': '#e2e8f0',
            'align': 'center',
        })
        
    def _create_summary_sheet(self, rows_data, summary_metrics):
        """
        Cria aba de resumo com métricas e gráfico.
        
        Args:
            rows_data: Lista de dicionários com todas as transações
            summary_metrics: Dicionário com métricas calculadas
        """
        sheet = self.workbook.add_worksheet('Resumo')
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 20)
        
        row = 0
        
        # Título
        sheet.write(row, 0, f"Relatório de Conciliação - {self.company_name}", self.formats['title'])
        row += 1
        
        # Período
        if self.start_date and self.end_date:
            period = f"Período: {self.start_date} a {self.end_date}"
        else:
            period = "Período: Completo"
        sheet.write(row, 0, period, self.formats['subtitle'])
        row += 2
        
        # Data de geração
        sheet.write(row, 0, f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", self.formats['subtitle'])
        row += 3
        
        # Métricas
        sheet.write(row, 0, "Métricas de Conciliação", self.formats['header'])
        sheet.write(row, 1, "Valor", self.formats['header'])
        row += 1
        
        # Contagens por status
        conciliados = len([r for r in rows_data if 'Conciliado' in r.get('status', '')])
        apenas_banco = len([r for r in rows_data if r.get('status') == 'Apenas no Banco'])
        apenas_diario = len([r for r in rows_data if r.get('status') == 'Apenas no Diário'])
        total = len(rows_data)
        
        metrics = [
            ("Total de Transações", total),
            ("Transações Conciliadas", conciliados),
            ("Apenas no Banco", apenas_banco),
            ("Apenas no Diário", apenas_diario),
            ("Taxa de Conciliação", f"{(conciliados/total*100):.1f}%" if total > 0 else "0%"),
        ]
        
        for label, value in metrics:
            sheet.write(row, 0, label, self.formats['metric_label'])
            if isinstance(value, str):
                sheet.write(row, 1, value, self.formats['metric_value'])
            else:
                sheet.write(row, 1, value, self.formats['metric_value'])
            row += 1
        
        # Adicionar gráfico de pizza (se há dados)
        if total > 0:
            chart = self.workbook.add_chart({'type': 'pie'})
            
            # Preparar dados para o gráfico
            chart_row = row + 2
            sheet.write(chart_row, 3, "Status", self.formats['header'])
            sheet.write(chart_row, 4, "Quantidade", self.formats['header'])
            
            chart_data = [
                ("Conciliado", conciliados, self.COLORS['conciliado']),
                ("Apenas no Banco", apenas_banco, self.COLORS['apenas_banco']),
                ("Apenas no Diário", apenas_diario, self.COLORS['apenas_diario']),
            ]
            
            for i, (status, count, color) in enumerate(chart_data):
                sheet.write(chart_row + 1 + i, 3, status)
                sheet.write(chart_row + 1 + i, 4, count)
            
            chart.add_series({
                'name': 'Distribuição de Status',
                'categories': ['Resumo', chart_row + 1, 3, chart_row + 3, 3],
                'values': ['Resumo', chart_row + 1, 4, chart_row + 3, 4],
                'points': [
                    {'fill': {'color': self.COLORS['conciliado']}},
                    {'fill': {'color': self.COLORS['apenas_banco']}},
                    {'fill': {'color': self.COLORS['apenas_diario']}},
                ],
            })
            
            chart.set_title({'name': 'Distribuição de Transações por Status'})
            chart.set_style(10)
            
            # Inserir gráfico
            sheet.insert_chart('D2', chart, {'x_scale': 1.5, 'y_scale': 1.5})
    
    def _create_data_sheet(self, sheet_name, rows_data, header_color):
        """
        Cria aba com dados de transações.
        
        Args:
            sheet_name: Nome da aba
            rows_data: Lista de dicionários com os dados
            header_color: Cor do cabeçalho
        """
        sheet = self.workbook.add_worksheet(sheet_name)
        
        # Configurar larguras de colunas
        sheet.set_column('A:A', 12)  # Data
        sheet.set_column('B:B', 10)  # Origem
        sheet.set_column('C:C', 50)  # Descrição
        sheet.set_column('D:D', 15)  # Valor
        sheet.set_column('E:E', 20)  # Status
        sheet.set_column('F:F', 10)  # Grupo
        
        # Congelar primeira linha
        sheet.freeze_panes(1, 0)
        
        # Cabeçalho customizado com cor
        header_format = self.workbook.add_format({
            'bold': True,
            'font_color': '#ffffff',
            'bg_color': header_color,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
        })
        
        headers = ['Data', 'Origem', 'Descrição', 'Valor', 'Status', 'Grupo']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Dados
        for row_idx, row_data in enumerate(rows_data, start=1):
            # Determinar formato zebrado
            cell_format = self.formats['cell_zebra_light'] if row_idx % 2 == 0 else self.formats['cell_zebra_dark']
            
            # Data
            date_val = row_data.get('date', '')
            if isinstance(date_val, (datetime, pd.Timestamp)):
                sheet.write_datetime(row_idx, 0, date_val, self.formats['date'])
            else:
                sheet.write(row_idx, 0, date_val, cell_format)
            
            # Origem
            sheet.write(row_idx, 1, row_data.get('source', ''), cell_format)
            
            # Descrição
            sheet.write(row_idx, 2, row_data.get('description', ''), cell_format)
            
            # Valor - com formatação condicional
            amount = row_data.get('amount', 0)
            if amount >= 0:
                fmt = self.formats['currency_positive']
            else:
                fmt = self.formats['currency_negative']
            
            # Aplicar zebrado ao formato de moeda
            if row_idx % 2 == 0:
                fmt = self.workbook.add_format({
                    'num_format': 'R$ #,##0.00',
                    'border': 1,
                    'border_color': '#e2e8f0',
                    'font_color': self.COLORS['positive'] if amount >= 0 else self.COLORS['negative'],
                    'bold': True,
                    'bg_color': self.COLORS['zebra_light'],
                })
            else:
                fmt = self.workbook.add_format({
                    'num_format': 'R$ #,##0.00',
                    'border': 1,
                    'border_color': '#e2e8f0',
                    'font_color': self.COLORS['positive'] if amount >= 0 else self.COLORS['negative'],
                    'bold': True,
                    'bg_color': self.COLORS['zebra_dark'],
                })
            
            sheet.write_number(row_idx, 3, amount, fmt)
            
            # Status
            sheet.write(row_idx, 4, row_data.get('status', ''), cell_format)
            
            # Grupo
            group_id = row_data.get('group_id', '-1')
            if group_id != '-1':
                sheet.write(row_idx, 5, group_id, cell_format)
            else:
                sheet.write(row_idx, 5, '', cell_format)
        
        # Adicionar linha de total se houver dados
        if rows_data:
            total_row = len(rows_data) + 1
            sheet.write(total_row, 2, 'TOTAL:', self.formats['total'])
            
            # Fórmula de soma
            sum_range = xl_range(1, 3, len(rows_data), 3)
            sheet.write_formula(total_row, 3, f'=SUM({sum_range})', self.formats['total'])
    
    def generate(self, rows_data):
        """
        Gera o arquivo Excel completo.
        
        Args:
            rows_data: Lista de dicionários com todas as transações
            
        Returns:
            BytesIO buffer com o conteúdo Excel
        """
        self.workbook = pd.ExcelWriter(self.buffer, engine='xlsxwriter').book
        self._create_formats()
        
        # Separar dados por status
        conciliados = [r for r in rows_data if 'Conciliado' in r.get('status', '')]
        apenas_banco = [r for r in rows_data if r.get('status') == 'Apenas no Banco']
        apenas_diario = [r for r in rows_data if r.get('status') == 'Apenas no Diário']
        
        # Criar abas
        summary_metrics = {
            'total': len(rows_data),
            'conciliados': len(conciliados),
            'apenas_banco': len(apenas_banco),
            'apenas_diario': len(apenas_diario),
        }
        
        self._create_summary_sheet(rows_data, summary_metrics)
        self._create_data_sheet('Conciliados', conciliados, self.COLORS['conciliado'])
        self._create_data_sheet('Apenas no Banco', apenas_banco, self.COLORS['apenas_banco'])
        self._create_data_sheet('Apenas no Diário', apenas_diario, self.COLORS['apenas_diario'])
        
        # Fechar workbook
        self.workbook.close()
        self.buffer.seek(0)
        
        return self.buffer.getvalue()
