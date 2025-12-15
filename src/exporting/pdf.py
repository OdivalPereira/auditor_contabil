from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from io import BytesIO
import pandas as pd
from datetime import datetime

class PDFReportExporter:
    def __init__(self, company_name="Empresa X", start_date=None, end_date=None):
        self.company_name = company_name
        self.start_date = start_date
        self.end_date = end_date
        self.buffer = BytesIO()
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        # Professional Title
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            alignment=1, # Center
            spaceAfter=12
        ))
        
        # Subtitle
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.grey,
            alignment=1, # Center
            spaceAfter=20
        ))
        
        # Table Header
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        ))

    def _create_summary_table(self, summary_data):
        data = [
            ['Métrica', 'Valor'],
            ['Total Banco', f"R$ {summary_data.get('bank_total', 0):,.2f}"],
            ['Total Diário', f"R$ {summary_data.get('ledger_total', 0):,.2f}"],
            ['Diferença Líquida', f"R$ {summary_data.get('net_diff', 0):,.2f}"],
            ['Itens Não Conciliados (Banco)', str(summary_data.get('unmatched_bank_count', 0))],
            ['Itens Não Conciliados (Diário)', str(summary_data.get('unmatched_ledger_count', 0))]
        ]
        
        t = Table(data, colWidths=[6*cm, 6*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return t

    def _create_discrepancy_table(self, df, title, color_theme=colors.firebrick):
        if df.empty:
            return [Paragraph(f"{title}: Nenhuma diferença encontrada.", self.styles['Normal']), Spacer(1, 12)]
            
        # Prepare Data
        # Keep only relevant columns
        cols = ['date', 'amount', 'description']
        # Rename for display
        display_data = [['Data', 'Valor (R$)', 'Descrição']]
        
        for _, row in df.iterrows():
            d = row['date']
            if isinstance(d, (datetime, pd.Timestamp)):
                d_str = d.strftime('%d/%m/%Y')
            else:
                d_str = str(d)
                
            amt = f"{row['amount']:,.2f}"
            desc = str(row['description'])[:60] # Truncate description to fit portrait
            
            display_data.append([d_str, amt, desc])
        
        # PORTRAIT ADAPTATION: Reduced widths to fit A4 (approx 19cm usable width with smaller margins, or 15cm with large margins)
        # Margins are 30 (approx 1 inch/2.54cm). Total width 21cm. Usable ~15cm.
        # Let's reduce margins slightly or squeeze content.
        # Date: 2.5cm, Amount: 3.5cm, Desc: 10cm. Total: 16cm.
        t = Table(display_data, colWidths=[2.5*cm, 3.5*cm, 10*cm])
        
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), color_theme),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.whitesmoke, colors.beige]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True) # Ensure wrapping for description
        ]))
        
        elements = [
            Paragraph(title, self.styles['Heading2']),
            Spacer(1, 6),
            t,
            Spacer(1, 20)
        ]
        return elements

    def generate(self, summary_metrics, df_unmatched_bank, df_unmatched_ledger):
        # Header
        self.elements.append(Paragraph(f"Relatório de Conciliação - {self.company_name}", self.styles['ReportTitle']))
        range_str = f"Período: {self.start_date} a {self.end_date}" if self.start_date else "Período Completo"
        self.elements.append(Paragraph(range_str, self.styles['ReportSubtitle']))
        
        # Summary
        self.elements.append(Paragraph("Resumo da Conciliação", self.styles['Heading2']))
        self.elements.append(Spacer(1, 10))
        self.elements.append(self._create_summary_table(summary_metrics))
        self.elements.append(Spacer(1, 25))
        
        # Discrepancies
        # 1. In Bank only
        self.elements.extend(self._create_discrepancy_table(
            df_unmatched_bank, 
            "Itens no BANCO mas não no Diário (Faltam na Contabilidade)",
            colors.firebrick
        ))
        
        # 2. In Ledger only
        self.elements.extend(self._create_discrepancy_table(
            df_unmatched_ledger, 
            "Itens no DIÁRIO mas não no Banco (Faltam no Banco/Estorno)",
            colors.darkorange
        ))
        
        # Build - PORTRAIT A4
        # A4 = 21cm x 29.7cm.
        # Margins: 2cm sides -> 17cm usable.
        doc = SimpleDocTemplate(self.buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        doc.build(self.elements)
        
        self.buffer.seek(0)
        return self.buffer.getvalue()
