"""
Módulo de exportação PDF moderno e profissional.
Gera relatórios de conciliação com design atraente e métricas visuais.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from io import BytesIO
import pandas as pd
from datetime import datetime


class PDFReportExporter:
    """Exportador PDF moderno com design profissional."""
    
    # Paleta de cores moderna
    COLORS = {
        'primary': colors.HexColor('#6366f1'),      # Índigo
        'conciliado': colors.HexColor('#10b981'),   # Verde
        'apenas_banco': colors.HexColor('#f59e0b'), # Laranja
        'apenas_diario': colors.HexColor('#ef4444'),# Vermelho
        'dark': colors.HexColor('#1e293b'),         # Azul escuro
        'text': colors.HexColor('#334155'),         # Cinza escuro
        'light': colors.HexColor('#f8fafc'),        # Cinza claro
        'border': colors.HexColor('#e2e8f0'),       # Borda
    }
    
    def __init__(self, company_name="Empresa X", start_date=None, end_date=None):
        """
        Inicializa o exportador PDF.
        
        Args:
            company_name: Nome da empresa
            start_date: Data inicial do período
            end_date: Data final do período
        """
        self.company_name = company_name
        self.start_date = start_date
        self.end_date = end_date
        self.buffer = BytesIO()
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configura estilos personalizados."""
        # Título principal
        if 'CustomReportTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomReportTitle',
                parent=self.styles['Heading1'],
                fontSize=20,
                textColor=self.COLORS['dark'],
                alignment=TA_CENTER,
                spaceAfter=8,
                fontName='Helvetica-Bold',
            ))
        
        # Subtítulo
        if 'CustomReportSubtitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomReportSubtitle',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica-Oblique',
            ))
        
        # Cabeçalho de seção
        if 'CustomSectionHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomSectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=self.COLORS['primary'],
                spaceAfter=12,
                spaceBefore=15,
                fontName='Helvetica-Bold',
            ))
        
        # Texto normal
        if 'CustomBodyText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomBodyText',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=self.COLORS['text'],
            ))

    def _create_metric_card(self, label, value, color):
        """
        Cria um card visual para métricas.
        
        Args:
            label: Rótulo da métrica
            value: Valor da métrica
            color: Cor do card
            
        Returns:
            Table formatada como card
        """
        data = [[label], [str(value)]]
        t = Table(data, colWidths=[4*cm])
        
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('BACKGROUND', (0, 1), (-1, 1), self.COLORS['light']),
            ('TEXTCOLOR', (0, 1), (-1, 1), color),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, 1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
            ('BOX', (0, 0), (-1, -1), 2, color),
        ]))
        
        return t

    def _create_summary_section(self, summary_metrics, rows_data):
        """
        Cria seção de resumo executivo com métricas visuais.
        
        Args:
            summary_metrics: Dicionário com métricas calculadas
            rows_data: Lista com todas as transações
        """
        self.elements.append(Paragraph("Resumo Executivo", self.styles['CustomSectionHeader']))
        self.elements.append(Spacer(1, 10))
        
        # Calcular métricas
        total = len(rows_data)
        conciliados = len([r for r in rows_data if 'Conciliado' in r.get('status', '')])
        apenas_banco = len([r for r in rows_data if r.get('status') == 'Apenas no Banco'])
        apenas_diario = len([r for r in rows_data if r.get('status') == 'Apenas no Diário'])
        taxa_conciliacao = (conciliados / total * 100) if total > 0 else 0
        
        # Cards de métricas em linha
        metrics_table_data = [[
            self._create_metric_card('Total de\nTransações', total, self.COLORS['primary']),
            self._create_metric_card('Conciliadas', conciliados, self.COLORS['conciliado']),
            self._create_metric_card('Apenas\nBanco', apenas_banco, self.COLORS['apenas_banco']),
            self._create_metric_card('Apenas\nDiário', apenas_diario, self.COLORS['apenas_diario']),
        ]]
        
        metrics_table = Table(metrics_table_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(metrics_table)
        self.elements.append(Spacer(1, 20))
        
        # Taxa de conciliação destacada
        taxa_text = f"<b>Taxa de Conciliação:</b> {taxa_conciliacao:.1f}%"
        taxa_color = self.COLORS['conciliado'] if taxa_conciliacao >= 80 else (
            self.COLORS['apenas_banco'] if taxa_conciliacao >= 50 else self.COLORS['apenas_diario']
        )
        
        taxa_style = ParagraphStyle(
            name='TaxaStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=taxa_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        )
        
        self.elements.append(Paragraph(taxa_text, taxa_style))
        self.elements.append(Spacer(1, 25))

    def _create_discrepancy_table(self, df, title, color_theme):
        """
        Cria tabela detalhada de discrepâncias com design moderno.
        
        Args:
            df: DataFrame com as transações
            title: Título da seção
            color_theme: Cor do tema
        """
        if df.empty:
            self.elements.append(Paragraph(title, self.styles['CustomSectionHeader']))
            self.elements.append(Spacer(1, 6))
            self.elements.append(Paragraph(
                "✓ Nenhuma discrepância encontrada nesta categoria.",
                self.styles['CustomBodyText']
            ))
            self.elements.append(Spacer(1, 20))
            return
        
        self.elements.append(Paragraph(title, self.styles['CustomSectionHeader']))
        self.elements.append(Spacer(1, 8))
        
        # Preparar dados
        display_data = [['Data', 'Descrição', 'Valor (R$)']]
        
        for _, row in df.head(50).iterrows():  # Limitar a 50 linhas por tabela
            # Formatar data
            d = row['date']
            if isinstance(d, (datetime, pd.Timestamp)):
                d_str = d.strftime('%d/%m/%Y')
            else:
                d_str = str(d)
            
            # Formatar valor
            amt = f"{row['amount']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Truncar descrição
            desc = str(row['description'])[:55]
            if len(str(row['description'])) > 55:
                desc += '...'
            
            display_data.append([d_str, desc, amt])
        
        # Criar tabela
        t = Table(display_data, colWidths=[2.5*cm, 10*cm, 3*cm])
        
        # Estilo moderno com zebra striping
        table_style = [
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), color_theme),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Dados
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Data centralizada
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Descrição à esquerda
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # Valor à direita
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.COLORS['text']),
            
            # Bordas
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('BOX', (0, 0), (-1, -1), 1.5, color_theme),
            
            # Padding
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Valign
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Adicionar zebra striping
        for i in range(1, len(display_data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), self.COLORS['light']))
        
        t.setStyle(TableStyle(table_style))
        
        self.elements.append(t)
        
        # Mostrar contagem se houver mais registros
        if len(df) > 50:
            self.elements.append(Spacer(1, 8))
            self.elements.append(Paragraph(
                f"<i>Mostrando 50 de {len(df)} registros. Exporte para Excel para ver todos.</i>",
                self.styles['CustomBodyText']
            ))
        
        self.elements.append(Spacer(1, 20))

    def _add_header_footer(self, canvas, doc):
        """Adiciona cabeçalho e rodapé personalizados."""
        canvas.saveState()
        
        # Rodapé
        footer_text = f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm, 1.5*cm, footer_text)
        
        # Número da página
        page_num = f"Página {doc.page}"
        canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, page_num)
        
        canvas.restoreState()

    def generate(self, summary_metrics, df_unmatched_bank, df_unmatched_ledger, all_rows=None):
        """
        Gera o relatório PDF completo.
        
        Args:
            summary_metrics: Dicionário com métricas de resumo
            df_unmatched_bank: DataFrame com transações apenas no banco
            df_unmatched_ledger: DataFrame com transações apenas no diário
            all_rows: Lista de todas as transações (opcional)
            
        Returns:
            bytes do PDF gerado
        """
        # Cabeçalho do relatório
        self.elements.append(Paragraph(
            f"Relatório de Conciliação Bancária",
            self.styles['CustomReportTitle']
        ))
        
        self.elements.append(Paragraph(
            self.company_name,
            self.styles['CustomReportSubtitle']
        ))
        
        # Período
        if self.start_date and self.end_date:
            period = f"Período: {self.start_date} a {self.end_date}"
        else:
            period = "Período: Completo"
        
        self.elements.append(Paragraph(period, self.styles['CustomReportSubtitle']))
        self.elements.append(Spacer(1, 20))
        
        # Seção de resumo (se temos dados de all_rows)
        if all_rows:
            self._create_summary_section(summary_metrics, all_rows)
        
        # Discrepâncias
        self._create_discrepancy_table(
            df_unmatched_bank,
            "Transações Apenas no Banco",
            self.COLORS['apenas_banco']
        )
        
        self._create_discrepancy_table(
            df_unmatched_ledger,
            "Transações Apenas no Diário",
            self.COLORS['apenas_diario']
        )
        
        # Construir PDF
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm,
            title="Relatório de Conciliação"
        )
        
        doc.build(self.elements, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        
        self.buffer.seek(0)
        return self.buffer.getvalue()
