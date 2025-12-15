import streamlit as st
import pandas as pd
import io
import os
import tkinter as tk
from tkinter import filedialog
import plotly.express as px
import plotly.graph_objects as go

from src.parsing.sources.ledger_pdf import LedgerParser
from src.parsing.sources.ofx import OfxParser
from src.core.reconciler import Reconciler
from src.utils.scanner import FileScanner
from src.exporters.pdf_renderer import PDFReportExporter
from src.core.matcher import CombinatorialMatcher
from src.ui.unified_view import UnifiedViewController
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator

def select_folder_callback():
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        selected_folder = filedialog.askdirectory(master=root)
        root.destroy() # Ensure cleanup
        if selected_folder:
            st.session_state['folder_input'] = selected_folder
    except Exception as e:
        st.error(f"Erro ao abrir seletor de pasta: {e}")

def render_metrics_and_chart(ledger_df, bank_df, diff_initial, diff_final, comb_extracted):
    """
    Renderiza os cartões de métricas e o gráfico de evolução.
    """
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Lançamentos Diário", len(ledger_df))
    col2.metric("Total Lançamentos Banco", len(bank_df))
    col3.metric("Diferença Inicial (1x1)", f"R$ {diff_initial:,.2f}")
    col4.metric("Diferença Final (Comb.)", f"R$ {diff_final:,.2f}", delta=f"{comb_extracted} combinações", delta_color="normal")

    st.markdown("---")
    
    # Preparação para o Gráfico (Agrupado por Dia)
    # Assumindo colunas 'date' e 'amount'
    
    l_grouped = ledger_df.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Diário'})
    b_grouped = bank_df.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Banco'})
    
    # Merge para garantir que temos todas as datas
    df_chart = pd.merge(l_grouped, b_grouped, on='date', how='outer').fillna(0).sort_values('date')
    
    # Gráfico de Linha/Barra
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['Diário'], mode='lines+markers', name='Diário Total'))
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['Banco'], mode='lines+markers', name='Banco Total'))
    
    fig.update_layout(title="Evolução Diária de Movimentações (Soma dos Valores)",
                      xaxis_title="Data",
                      yaxis_title="Valor (R$)",
                      hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)


def render_conciliation_tab(results):
    matched_l = results['matched_l']
    matched_b = results['matched_b']
    comb_matches = results['comb_matches']
    remaining_l = results['remaining_l']
    remaining_b = results['remaining_b']
    
    # --- UNIFIED VIEW ---
    uv_controller = UnifiedViewController()
    df_view = uv_controller.build_view_data(matched_l, matched_b, comb_matches, remaining_l, remaining_b)
    
    # Filtros Horizontais Superiores
    with st.container():
        st.markdown("### 🔎 Filtros de Visualização")
        col_f1, col_f2 = st.columns([2, 1])
        
        with col_f1:
            options = ['Conciliado', 'Conciliado (Comb)', 'Pendente - Banco', 'Pendente - Diário']
            default_options = ['Pendente - Banco', 'Pendente - Diário'] 
            selected_status = st.multiselect("Status:", options, default=default_options, key="concilia_status_filter")
        
        with col_f2:
            search_term = st.text_input("Buscar (Descrição ou Valor)", "", key="concilia_search_term")
    
    st.divider()

    # Filter Data
    if not df_view.empty:
        # 1. Status Filter
        df_filtered = df_view[df_view['status'].isin(selected_status)]
        
        # 2. Search Filter
        if search_term:
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            df_filtered = df_filtered[mask]
        
        # Display
        st.dataframe(
            uv_controller.apply_styles(df_filtered), 
            width=None, 
            use_container_width=True,
            height=600
        )
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")
        
    # Export Section at bottom of conciliation
    st.subheader("📄 Exportações")
    col_exp1, col_exp2 = st.columns(2)
    
    # Generate Excel in memory
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        remaining_l.to_excel(writer, sheet_name='So_no_Diario', index=False)
        remaining_b.to_excel(writer, sheet_name='So_no_Banco', index=False)
        matched_l.to_excel(writer, sheet_name='Conciliados', index=False)
        
    with col_exp1:
        st.download_button(
            label="📥 Baixar Excel Completo",
            data=buffer.getvalue(),
            file_name="relatorio_conciliacao.xlsx",
            mime="application/vnd.ms-excel"
        )

    # PDF Export
    pdf_exporter = PDFReportExporter(
        company_name="1266 - MCM FOODS LTDA",
        start_date=results['start_date'].strftime('%d/%m/%Y') if not results['df_ledger'].empty else None,
        end_date=results['end_date'].strftime('%d/%m/%Y') if not results['df_ledger'].empty else None
    )
    
    # Re-calc summary metrics for PDF
    # (Reuse what we have)
    new_diff = abs(remaining_l['amount'].sum() - remaining_b['amount'].sum())
    summary_metrics = {
        'bank_total': results['df_bank']['amount'].sum(),
        'ledger_total': results['df_ledger']['amount'].sum(),
        'net_diff': new_diff,
        'unmatched_bank_count': len(remaining_b),
        'unmatched_ledger_count': len(remaining_l)
    }
    
    try:
        pdf_bytes = pdf_exporter.generate(summary_metrics, remaining_b, remaining_l)
        with col_exp2:
            st.download_button(
                label="📄 Baixar Relatório PDF",
                data=pdf_bytes,
                file_name="relatorio_conciliacao.pdf",
                mime="application/pdf"
            )
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")


def render_upload_tab():
    st.subheader("📂 Importação de Arquivos")
    
    col1, col2 = st.columns(2)
    
    ledger_file = None
    bank_files = []
    
    with col1:
        st.markdown("### 1. Livro Diário")
        ledger_file = st.file_uploader("Upload do PDF ou CSV", type=["pdf", "csv"], key="ledger_uploader_tab")
    
    with col2:
        st.markdown("### 2. Extratos Bancários")
        
        # CHECK FOR IMPORTED DATA
        imported_df = st.session_state.get('imported_transactions_df')
        use_imported = False
        
        if imported_df is not None:
            st.success(f"✅ Usando {len(imported_df)} transações importadas.")
            if st.button("❌ Limpar Importação", key="clear_import_tab"):
                del st.session_state['imported_transactions_df']
                st.rerun()
            use_imported = True
        else:
            input_method = st.radio("Fonte:", ["Upload Manual", "Escanear Pasta"], horizontal=True, key="input_method_radio_tab")
            
            if input_method == "Upload Manual":
                uploaded_files = st.file_uploader("Arquivos (PDF/OFX)", type=["pdf", "ofx"], accept_multiple_files=True, key="bank_uploader_tab")
                if uploaded_files:
                    for f in uploaded_files:
                        bank_files.append({'file': f, 'name': f.name, 'type': 'upload'})
        
            else: # Escanear Pasta
                if 'folder_input' not in st.session_state:
                    st.session_state['folder_input'] = ''
                if 'last_scanned_path' not in st.session_state:
                    st.session_state['last_scanned_path'] = ''
            
                sub_c1, sub_c2 = st.columns([3, 1])
                with sub_c1:
                    folder_path = st.text_input("Caminho da Pasta", key='folder_input_display', value=st.session_state.get('folder_input', ''))
                with sub_c2:
                    st.button("📂", on_click=select_folder_callback, key='btn_folder_select')
                
                # Logic to trigger scan
                should_scan = False
                if folder_path and os.path.exists(folder_path):
                    if folder_path != st.session_state['last_scanned_path']:
                        should_scan = True
                    elif 'scan_results' not in st.session_state:
                        should_scan = True
                        
                if st.button("Forçar Escaneamento", key="force_scan"):
                    should_scan = True
            
                if should_scan and folder_path:
                    with st.spinner("Escaneando arquivos e extraindo metadados..."):
                        try:
                            scanner = FileScanner()
                            df_scan = scanner.scan_folder(folder_path)
                            st.session_state['scan_results'] = df_scan
                            st.session_state['last_scanned_path'] = folder_path
                        except Exception as e:
                            st.error(f"Erro ao escanear: {e}") 
                elif folder_path and not os.path.exists(folder_path):
                    st.error("Pasta não encontrada.")
                    
                # Display Scan Results
                if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
                    st.write("---")
                    st.markdown("#### Arquivos Encontrados")
                    edited_df = st.data_editor(
                        st.session_state['scan_results'],
                        column_config={
                            "selected": st.column_config.CheckboxColumn("Selecionar", default=False),
                            "filename": "Arquivo",
                            "bank": "Banco",
                            "period": "Período"
                        },
                        disabled=["filename", "type", "bank", "agency", "account", "period", "path"],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    selected_rows = edited_df[edited_df['selected'] == True]
                    st.caption(f"**Selecionados:** {len(selected_rows)} arquivos")
                    
                    for index, row in selected_rows.iterrows():
                        bank_files.append({
                            'file': row['path'], 
                            'name': row['filename'],
                            'type': 'path'
                        })

    st.divider()
    
    # Configurações de Execução
    st.subheader("⚙️ Processamento")
    tolerance = st.slider("Tolerância de Datas (Dias)", min_value=0, max_value=60, value=3, help="Aceitar transações com datas próximas até X dias.", key="tolerance_slider")
    
    if st.button("🚀 Executar Reconciliação", type="primary", use_container_width=True):
        if not ledger_file:
            st.error("⚠️ Por favor, faça o upload do Livro Diário (Esquerda).")
            return
        elif not bank_files and not use_imported:
            st.error("⚠️ Nenhum extrato bancário selecionado (Direita).")
            return
        
        process_reconciliation(ledger_file, bank_files, use_imported, imported_df, tolerance)


def process_reconciliation(ledger_file, bank_files, use_imported, imported_df, tolerance):
    with st.spinner("Processando arquivos e conciliando..."):
        # 1. Parse Ledger
        try:
            ledger_parser = LedgerParser()
            if ledger_file.name.endswith('.csv'):
                # Basic CSV handling if LedgerParser supports or ad-hoc
                df_ledger = pd.read_csv(ledger_file)
                # Standardize columns if needed or rely on LedgerParser
            else:
                df_ledger = ledger_parser.parse(ledger_file)
                
            df_ledger['amount'] = pd.to_numeric(df_ledger['amount'], errors='coerce').fillna(0.0)
            df_ledger['date'] = pd.to_datetime(df_ledger['date'])
        except Exception as e:
            st.error(f"❌ Erro ao processar Diário: {e}")
            return

        # 2. Get Bank Data
        df_bank = pd.DataFrame()
        
        if use_imported:
            df_bank = imported_df.copy()
            if 'amount' in df_bank.columns:
                 df_bank['amount'] = pd.to_numeric(df_bank['amount'], errors='coerce').fillna(0.0)
            if 'date' in df_bank.columns:
                 df_bank['date'] = pd.to_datetime(df_bank['date'])
        else:
            # Parse Bank Files
            all_bank_dfs = []
            errors = []
            
            progress_bar = st.progress(0)
            for i, file_info in enumerate(bank_files):
                fname = file_info['name']
                fobj = file_info['file']
                
                try:
                    parser = None
                    input_arg = None
                    
                    if isinstance(fobj, str): # Path from scan
                        parser = ParserFacade.get_parser(fobj)
                        input_arg = fobj
                    else: # UploadedFile
                        # Create temp file
                        import tempfile
                        suffix = os.path.splitext(fname)[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(fobj.getvalue())
                            tmp_path = tmp.name
                        
                        if fname.lower().endswith('.ofx'):
                             parser = OfxParser()
                        else:
                             parser = ParserFacade.get_parser(tmp_path)
                             
                        input_arg = tmp_path
                             
                    if parser:
                        df, _ = parser.parse(input_arg)
                        df['source_file'] = fname
                        all_bank_dfs.append(df)
                    else:
                        errors.append(f"Parser não detectado para: {fname}")
                        
                except Exception as e:
                    errors.append(f"Erro em {fname}: {e}")
                
                progress_bar.progress((i + 1) / len(bank_files))

            if errors:
                for e in errors:
                    st.warning(e)

            if all_bank_dfs:
                df_bank = TransactionConsolidator.consolidate(all_bank_dfs)
                df_bank['date'] = pd.to_datetime(df_bank['date'])
            else:
                st.error("❌ Nenhuma transação bancária válida extraída.")
                return

        # Common Bank Processing (Filter Zeros)
        df_bank = df_bank[abs(df_bank['amount']) > 0.009].copy()
        
        # 3. Filter Bank by Ledger Period
        if not df_ledger.empty:
            start_date = df_ledger['date'].min()
            end_date = df_ledger['date'].max()
            
            df_bank = df_bank[
                (df_bank['date'] >= start_date) & 
                (df_bank['date'] <= end_date)
            ].copy()

        # 4. Reconcile
        reconciler = Reconciler()
        matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(df_ledger, df_bank, date_tolerance=tolerance)

        # --- COMBINATORIAL MATCHING ---
        matcher = CombinatorialMatcher()
        comb_matches, remaining_l, remaining_b = matcher.find_matches(
            unmatched_l, 
            unmatched_b, 
            tolerance_days=tolerance
        )
        
        # --- SAVE TO SESSION STATE ---
        st.session_state['reconcile_results'] = {
            'df_ledger': df_ledger,
            'df_bank': df_bank,
            'matched_l': matched_l,
            'matched_b': matched_b,
            'unmatched_l': unmatched_l,
            'unmatched_b': unmatched_b,
            'comb_matches': comb_matches,
            'remaining_l': remaining_l,
            'remaining_b': remaining_b,
            'start_date': start_date,
            'end_date': end_date
        }
        st.session_state['data_processed'] = True
        st.session_state['active_tab'] = 'Dashboard' # Switch logic if we could, but streamlit tabs are UI only usually
        
        st.success("✅ Processamento Concluído! Vá para a aba 'Dashboard' ou 'Conciliação' para ver os resultados.")


def render_conciliator_view():
    # st.set_page_config removed to avoid conflict with main app
    st.title("🕵️ Auditor Contábil - Painel de Conciliação")
    
    # Abas
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Conciliação Detalhada", "📂 Dados e Upload"])
    
    with tab1:
        if st.session_state.get('data_processed', False):
            results = st.session_state['reconcile_results']
            
            # Recalculate diffs for metrics
            unmatched_l_initial = results['unmatched_l']
            unmatched_b_initial = results['unmatched_b']
            remaining_l = results['remaining_l']
            remaining_b = results['remaining_b']
            
            diff_initial = abs(unmatched_l_initial['amount'].sum() - unmatched_b_initial['amount'].sum())
            diff_final = abs(remaining_l['amount'].sum() - remaining_b['amount'].sum())
            comb_extracted = len(results['comb_matches'])
            
            render_metrics_and_chart(results['df_ledger'], results['df_bank'], diff_initial, diff_final, comb_extracted)
        else:
            st.info("⚠️ Nenhum dado processado. Vá para a aba 'Dados e Upload' para iniciar.")

    with tab2:
        if st.session_state.get('data_processed', False):
            render_conciliation_tab(st.session_state['reconcile_results'])
        else:
            st.info("⚠️ Realize o upload e processamento na aba 'Dados e Upload' primeiro.")

    with tab3:
        render_upload_tab()

if __name__ == "__main__":
    render_conciliator_view()
