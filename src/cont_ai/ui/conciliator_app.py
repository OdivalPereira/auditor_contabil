import streamlit as st
import pandas as pd
import io
import os
import tkinter as tk
from tkinter import filedialog
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
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    selected_folder = filedialog.askdirectory(master=root)
    root.destroy() # Ensure cleanup
    if selected_folder:
        st.session_state['folder_input'] = selected_folder

def render_conciliator_view():
    st.header("🕵️ Auditor Contábil - Reconciliação Bancária")
    
    # --- SIDEBAR: INPUTS ---
    st.sidebar.header("1. Livro Diário")
    ledger_file = st.sidebar.file_uploader("Upload do PDF ou CSV", type=["pdf", "csv"], key="ledger_uploader")
    
    st.sidebar.header("2. Extratos Bancários")
    
    # CHECK FOR IMPORTED DATA
    imported_df = st.session_state.get('imported_transactions_df')
    use_imported = False
    
    bank_files = []

    if imported_df is not None:
        st.sidebar.success(f"✅ Usando {len(imported_df)} transações importadas.")
        if st.sidebar.button("❌ Limpar Importação", key="clear_import_sidebar"):
            del st.session_state['imported_transactions_df']
            st.experimental_rerun()
        use_imported = True
    else:
        input_method = st.sidebar.radio("Fonte dos Arquivos:", ["Upload Manual", "Escanear Pasta"], key="input_method_radio")
        
        if input_method == "Upload Manual":
            uploaded_files = st.sidebar.file_uploader("Arquivos (PDF/OFX)", type=["pdf", "ofx"], accept_multiple_files=True, key="bank_uploader")
            if uploaded_files:
                for f in uploaded_files:
                    bank_files.append({'file': f, 'name': f.name, 'type': 'upload'})
    
        else: # Escanear Pasta
            if 'folder_input' not in st.session_state:
                st.session_state['folder_input'] = ''
            if 'last_scanned_path' not in st.session_state:
                st.session_state['last_scanned_path'] = ''
        
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                folder_path = st.text_input("Caminho da Pasta", key='folder_input')
            with col2:
                st.button("📂", on_click=select_folder_callback)
            
            should_scan = False
            if folder_path and os.path.exists(folder_path):
                if folder_path != st.session_state['last_scanned_path']:
                    should_scan = True
                elif 'scan_results' not in st.session_state:
                    should_scan = True
                    
            if st.sidebar.button("Forçar Escaneamento"):
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
                st.sidebar.error("Pasta não encontrada.")
    
    # --- MAIN INTERFACE ---
        if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
            st.subheader("📂 Arquivos Encontrados")
            
            column_config = {
                "selected": st.column_config.CheckboxColumn("Selecionar", default=False),
                "filename": "Arquivo",
                "type": "Tipo",
                "bank": "Banco",
                "agency": "Agência",
                "account": "Conta",
                "period": "Período",
                "path": "Caminho Completo"
            }
            
            edited_df = st.data_editor(
                st.session_state['scan_results'],
                column_config=column_config,
                disabled=["filename", "type", "bank", "agency", "account", "period", "path"],
                hide_index=True,
                width=None,
                use_container_width=True
            )
            
            selected_rows = edited_df[edited_df['selected'] == True]
            st.write(f"**Selecionados:** {len(selected_rows)} arquivos")
            
            for index, row in selected_rows.iterrows():
                bank_files.append({
                    'file': row['path'], 
                    'name': row['filename'],
                    'type': 'path'
                })

        # --- EXECUTE RECONCILIATION ---
        
        if st.button("Executar Reconciliação", type="primary"):
            if not ledger_file:
                st.error("⚠️ Por favor, faça o upload do Livro Diário.")
                st.stop()
            elif not bank_files and not use_imported:
                st.error("⚠️ Nenhum extrato bancário selecionado.")
                st.stop()
            
            with st.spinner("Processando arquivos..."):
                # 1. Parse Ledger
                try:
                    ledger_parser = LedgerParser()
                    df_ledger = ledger_parser.parse(ledger_file)
                    df_ledger['amount'] = pd.to_numeric(df_ledger['amount'], errors='coerce').fillna(0.0)
                    st.success(f"✅ Diário processado: {len(df_ledger)} transações.")
                except Exception as e:
                    st.error(f"❌ Erro ao processar Diário: {e}")
                    st.stop()

                # 2. Get Bank Data
                df_bank = pd.DataFrame()
                
                if use_imported:
                    df_bank = imported_df.copy()
                    if 'amount' in df_bank.columns:
                         df_bank['amount'] = pd.to_numeric(df_bank['amount'], errors='coerce').fillna(0.0)
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
                                if fname.lower().endswith('.ofx'):
                                     import tempfile
                                     with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fname)[1]) as tmp:
                                         tmp.write(fobj.getvalue())
                                         tmp_path = tmp.name
                                     parser = OfxParser()
                                     input_arg = tmp_path
                                elif fname.lower().endswith('.pdf'):
                                     import tempfile
                                     with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fname)[1]) as tmp:
                                         tmp.write(fobj.getvalue())
                                         tmp_path = tmp.name
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
                        with st.expander("⚠️ Erros de Leitura"):
                            for e in errors:
                                st.write(e)

                    if all_bank_dfs:
                        df_bank = TransactionConsolidator.consolidate(all_bank_dfs)
                    else:
                        st.error("❌ Nenhuma transação bancária válida extraída.")
                        st.stop()

                # Common Bank Processing (Filter Zeros)
                initial_count = len(df_bank)
                df_bank = df_bank[abs(df_bank['amount']) > 0.009].copy()
                removed_zeros = initial_count - len(df_bank)
                
                st.success(f"✅ Extratos processados: {len(df_bank)} transações. {removed_zeros} itens de valor zero removidos.")
    
                # 3. Filter Bank by Ledger Period
                if not df_ledger.empty:
                    start_date = df_ledger['date'].min()
                    end_date = df_ledger['date'].max()
                    
                    df_bank = df_bank[
                        (df_bank['date'] >= start_date) & 
                        (df_bank['date'] <= end_date)
                    ].copy()
                    st.info(f"📅 Período do Diário: {start_date} a {end_date} | Transações Bancárias no Período: {len(df_bank)}")
    
                # 4. Reconcile
                st.sidebar.divider()
                st.sidebar.header("3. Configurações")
                tolerance = st.sidebar.slider("Tolerância de Datas (Dias)", min_value=0, max_value=60, value=3, help="Aceitar transações com datas próximas até X dias.")
                
                reconciler = Reconciler()
                matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(df_ledger, df_bank, date_tolerance=tolerance)
    
                # --- COMBINATORIAL MATCHING ---
                with st.spinner("🧩 Tentando encaixar combinações (Muitos-para-Um)..."):
                    matcher = CombinatorialMatcher()
                    # Run combinatorial strategy on the leftovers
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
    
    
    # --- RENDERING FROM SESSION STATE ---
    if st.session_state.get('data_processed', False):
        results = st.session_state['reconcile_results']
        
        df_ledger = results['df_ledger']
        df_bank = results['df_bank']
        matched_l = results['matched_l']
        matched_b = results['matched_b']
        comb_matches = results['comb_matches']
        remaining_l = results['remaining_l']
        remaining_b = results['remaining_b']
        start_date = results['start_date']
        end_date = results['end_date']
        
        # Calculate metrics again from stored data
        # Check if we have original unmatched or calculate from 'remaining' + 'comb'
        # Actually session state has 'unmatched_l' (initial diff).
        unmatched_l_initial = results['unmatched_l']
        unmatched_b_initial = results['unmatched_b']
        
        diff = abs(unmatched_l_initial['amount'].sum() - unmatched_b_initial['amount'].sum())
        new_diff = abs(remaining_l['amount'].sum() - remaining_b['amount'].sum())
        
        # --- RESULTS DISPLAY ---
        st.divider()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Diário", len(df_ledger))
        col2.metric("Total Banco", len(df_bank))
        col3.metric("Dif. Inicial (1x1)", f"R$ {diff:,.2f}")
        col4.metric("Dif. Final (Comb.)", f"R$ {new_diff:,.2f}", delta=f"{len(comb_matches)} combinações", delta_color="normal")
    
        st.subheader("🔍 Discrepâncias e Soluções (Visão Unificada)")
        
        # --- UNIFIED VIEW ---
        uv_controller = UnifiedViewController()
        df_view = uv_controller.build_view_data(matched_l, matched_b, comb_matches, remaining_l, remaining_b)
        
        # Filters
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            options = ['Conciliado', 'Conciliado (Comb)', 'Pendente - Banco', 'Pendente - Diário']
            default_options = ['Pendente - Banco', 'Pendente - Diário'] 
            selected_status = st.multiselect("Filtrar por Status", options, default=default_options)
        
        with col_f2:
            search_term = st.text_input("Buscar (Descrição ou Valor)", "")
            
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
                height=500
            )
        else:
            st.info("Nenhum dado para exibir.")
    
        # --- EXPORT FULL REPORT ---
        st.divider()
        st.subheader("📄 Exportar Relatório")
        
        # Generate Excel in memory
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            remaining_l.to_excel(writer, sheet_name='So_no_Diario', index=False)
            remaining_b.to_excel(writer, sheet_name='So_no_Banco', index=False)
            matched_l.to_excel(writer, sheet_name='Conciliados', index=False)
            
        st.download_button(
            label="📥 Baixar Relatório (Excel)",
            data=buffer.getvalue(),
            file_name="relatorio_conciliacao.xlsx",
            mime="application/vnd.ms-excel"
        )
    
        # --- PDF EXPORT ---
        pdf_exporter = PDFReportExporter(
            company_name="1266 - MCM FOODS LTDA",
            start_date=start_date.strftime('%d/%m/%Y') if not df_ledger.empty else None,
            end_date=end_date.strftime('%d/%m/%Y') if not df_ledger.empty else None
        )
        
        # Prepare summary metrics
        summary_metrics = {
            'bank_total': df_bank['amount'].sum(),
            'ledger_total': df_ledger['amount'].sum(),
            'net_diff': new_diff,
            'unmatched_bank_count': len(remaining_b),
            'unmatched_ledger_count': len(remaining_l)
        }
        
        pdf_bytes = pdf_exporter.generate(summary_metrics, remaining_b, remaining_l)
        
        st.download_button(
            label="📄 Baixar Relatório (PDF)",
            data=pdf_bytes,
            file_name="relatorio_conciliacao.pdf",
            mime="application/pdf"
        )
