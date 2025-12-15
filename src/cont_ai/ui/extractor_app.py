import streamlit as st
import tempfile
import os
import pandas as pd
from src.parsing.config.registry import LayoutRegistry
from src.parsing.pipeline import ExtractorPipeline
from src.exporting.ofx import OFXWriter

def render_extractor_view():
    st.header("📄 Conversor Inteligente (PDF -> OFX)")

    st.info("💡 Engine Cont.AI v4.0 (Modelos Unificados)")

    uploaded_files = st.file_uploader("Selecione os Extratos (PDF)", type=["pdf"], key="extractor_uploader", accept_multiple_files=True)

    if uploaded_files:
        if st.button("Converter & Unificar", key="convert_btn"):
            all_transactions = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            layouts_dir = os.path.join(os.getcwd(), 'src', 'parsing', 'layouts')
            registry = LayoutRegistry(layouts_dir)
            pipeline = ExtractorPipeline(registry)

            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processando {uploaded_file.name}...")
                
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    result = pipeline.process_file(tmp_path)
                    
                    # --- DISPLAY RESULTS FOR THIS FILE ---
                    bank_name = "Desconhecido"
                    if result.get('account_info'):
                        from src.cont_ai.utils.banks import get_bank_name
                        bank_code = result['account_info'].get('bank_id', '')
                        bank_name_db = get_bank_name(bank_code)
                        bank_name = f"{bank_name_db} ({bank_code})"
                    
                    # Audit Card
                    with st.expander(f"📊 Auditoria: {uploaded_file.name} - {bank_name}", expanded=True):
                        col_a, col_b, col_c = st.columns(3)
                        
                        # Validation Status
                        val = result.get('validation', {})
                        bal = result.get('balance_info', {})
                        
                        start_bal = bal.get('start')
                        end_bal = bal.get('end')
                        
                        with col_a:
                            st.caption("Status da Conciliação")
                            if val.get('is_valid') is True:
                                st.success(f"{val.get('msg')}")
                            elif val.get('is_valid') is False:
                                st.error(f"{val.get('msg')}")
                            else:
                                st.warning("Saldos não detectados no layout.")
                        
                        with col_b:
                            st.caption("Saldos Detectados")
                            s_txt = f"R$ {start_bal:,.2f}" if start_bal is not None else "N/A"
                            e_txt = f"R$ {end_bal:,.2f}" if end_bal is not None else "N/A"
                            st.markdown(f"**Inicial:** {s_txt}")
                            st.markdown(f"**Final:** {e_txt}")
                            
                        with col_c:
                            st.caption("Transações")
                            tx_count = len(result.get('transactions', []))
                            st.markdown(f"**Quantidade:** {tx_count}")

                    if result.get('transactions'):
                        all_transactions.extend(result['transactions'])
                    
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
                except Exception as e:
                    st.error(f"Erro em {uploaded_file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))

            status_text.text("Concluído!")
            
            if all_transactions:
                st.success(f"✅ Processamento Concluído! Total: {len(all_transactions)} transações.")
                
                # --- PREVIEW ---
                df_preview = pd.DataFrame([t.to_dict() for t in all_transactions])
                st.dataframe(df_preview.head(), use_container_width=True)
                
                # --- ACTIONS ---
                col1, col2 = st.columns(2)
                
                with col1:
                    # OFX Download
                     writer = OFXWriter() # Can improve to take specific bank info if unified
                     ofx_content = writer.generate(all_transactions)
                     st.download_button(
                        label="⬇️ Baixar OFX Unificado",
                        data=ofx_content,
                        file_name="extrato_unificado.ofx",
                        mime="application/x-ofx"
                    )

                with col2:
                    # Send to Reconciler
                    if st.button("🚀 Enviar para Auditoria", type="primary"):
                        st.session_state['imported_transactions_df'] = df_preview
                        st.session_state['active_tab'] = "reconciler" # Hint for UI switch if supported
                        st.success("Dados enviados! Vá para a aba 'Auditor Contábil'.")
                        
            else:
                st.warning("Nenhuma transação encontrada nos arquivos.")
