import streamlit as st
import re
import pandas as pd
import json
import os
import pdfplumber
from datetime import datetime
from src.parsing.config.layout import BankLayout, ColumnDef

def render_rule_builder():
    st.header("🛠️ Construtor de Regras (Layouts)")
    st.markdown("Crie suporte para novos bancos testando suas Regras (Regex) em tempo real.")

    # --- INPUT SECTION ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Amostra de Texto")
        
        # New: PDF Upload
        uploaded_pdf = st.file_uploader("Carregar PDF Modelo", type=["pdf"], key="rb_pdf_uploader")
        
        if uploaded_pdf:
            if st.button("📄 Extrair Texto do PDF"):
                with st.spinner("Lendo PDF..."):
                    try:
                        full_text = ""
                        with pdfplumber.open(uploaded_pdf) as pdf:
                            for page in pdf.pages:
                                t = page.extract_text()
                                if t: full_text += t + "\n"
                        
                        st.session_state['rb_sample_text'] = full_text
                        st.success("Texto extraído com sucesso!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao ler PDF: {e}")

        st.caption("Ou cole o texto manualmente abaixo:")
        sample_text = st.text_area("Texto do Extrato", height=300, key="rb_sample_text")

    with col2:
        st.subheader("2. Configuração do Layout")
        bank_name = st.text_input("Nome do Layout (ex: Banco X - Mensal)")
        bank_id = st.text_input("Código do Banco (ex: 999)")
        keywords_str = st.text_input("Palavras-Chave (separadas por vírgula)", help="Texto que DEVE existir no PDF para identificar esse banco.")
        
    # --- REGEX PLAYGROUND ---
    st.divider()
    st.subheader("3. Teste de Regex (Linha)")
    
    # AI SECTION
    with st.expander("🤖 Assistente de IA (Gemini)", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password", key="gemini_key", help="Gerar em aistudio.google.com")
        if st.button("✨ Detectar Padrão Automaticamente"):
            if not api_key:
                st.warning("⚠️ Insira a API Key primeiro.")
            elif not sample_text:
                st.warning("⚠️ Cole uma amostra de texto primeiro.")
            else:
                with st.spinner("A IA está analisando o extrato..."):
                    try:
                        from src.parsing.extractors.ai_generation import GeminiLayoutGenerator
                        generator = GeminiLayoutGenerator(api_key)
                        config = generator.generate_layout(sample_text)
                        
                        if config and 'regex' in config:
                            st.session_state['ai_suggested_regex'] = config['regex']
                            st.session_state['ai_suggested_name'] = config.get('bank_name', '')
                            # Store columns for later mapping if needed
                            st.session_state['ai_suggested_columns'] = config.get('columns', [])
                            st.success("Analise Concluída! Regex sugerido aplicado.")
                        else:
                            st.error("Falha ao gerar configuração. Tente novamente.")
                            
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")

    # Use AI suggestion if available
    default_regex = st.session_state.get('ai_suggested_regex', r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d\.,]+)\s+([CD])")
    
    # Auto-fill Name if suggested
    if 'ai_suggested_name' in st.session_state and not bank_name:
         # Hack to update text_input is tricky without rerun, but user might see it next run
         # or we can rely on manual copy if we want strict control.
         # For now, let's keep it simple. The Regex is the hard part.
         st.info(f"Sugestão de Nome: {st.session_state['ai_suggested_name']}")

    regex_pattern = st.text_input("Padrão Regex", value=default_regex)
    
    if sample_text and regex_pattern:
        try:
            matches = []
            lines = sample_text.split('\n')
            
            # Test Regex
            compiled_re = re.compile(regex_pattern)
            
            for line in lines:
                match = compiled_re.match(line)
                if match:
                    matches.append(match.groups())
            
            if matches:
                st.success(f"✅ {len(matches)} linhas identificadas!")
                
                # --- COLUMN MAPPING ---
                st.subheader("4. Mapeamento de Colunas")
                st.markdown("Associe os grupos capturados (colunas 1, 2, 3...) aos campos do sistema.")
                
                # Dynamic Columns based on groups found
                num_groups = len(matches[0])
                df_preview = pd.DataFrame(matches, columns=[f"Grupo {i+1}" for i in range(num_groups)])
                
                st.dataframe(df_preview.head(), use_container_width=True)
                
                # Mappers
                cols = st.columns(num_groups)
                column_defs = []
                
                
                possible_fields = ["Ignorar", "date", "memo", "amount", "type", "doc_id", "amount_debit", "amount_credit"]
                
                for i in range(num_groups):
                    with cols[i]:
                        # A.I. Auto-Mapping
                        default_idx = 0
                        suggested_cols = st.session_state.get('ai_suggested_columns', [])
                        
                        if suggested_cols and i < len(suggested_cols):
                            suggestion = suggested_cols[i]
                            if suggestion in possible_fields:
                                default_idx = possible_fields.index(suggestion)
                        
                        role = st.selectbox(f"Grupo {i+1} é:", possible_fields, key=f"col_map_{i}", index=default_idx)
                        
                        if role != "Ignorar":
                            column_defs.append({
                                "name": role,
                                "match_group": i + 1
                            })
                            
                # --- VALIDATION & SAVE ---
                st.divider()
                st.subheader("5. Salvar Layout")
                
                valid = True
                if not bank_name: valid = False
                if not keywords_str: valid = False
                
                # Check critical fields
                # Check critical fields
                roles = [c['name'] for c in column_defs]
                has_date = 'date' in roles
                has_amount = 'amount' in roles or ('amount_debit' in roles or 'amount_credit' in roles)
                
                if not has_date or not has_amount:
                    st.warning("⚠️ Você precisa mapear 'date' e pelo menos um campo de valor ('amount', 'amount_debit' ou 'amount_credit').")
                    valid = False
                
                if st.button("💾 Salvar Arquivo JSON", disabled=not valid, type="primary"):
                    # Construct Layout Dict
                    layout_dict = {
                        "name": bank_name,
                        "bank_id": bank_id,
                        "keywords": [k.strip() for k in keywords_str.split(',') if k.strip()],
                        "line_pattern": regex_pattern,
                        "columns": column_defs,
                        "amount_decimal_separator": ",", # Default, could make configurable
                        "amount_thousand_separator": ".",
                        "date_format": "%d/%m/%Y", # Default
                        "has_balance_cleanup": True
                    }
                    
                    # Save to layouts dir
                    filename = f"{bank_name.lower().replace(' ', '_').replace('-', '_')}.json"
                    save_path = os.path.join(os.getcwd(), 'src', 'parsing', 'layouts', filename)
                    
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(layout_dict, f, indent=4, ensure_ascii=False)
                        
                    st.toast(f"Layout salvo em {filename}!")
                    st.success(f"Layout **{bank_name}** salvo com sucesso! Agora o extrator irá reconhecê-lo.")
                    
            else:
                st.warning("⚠️ Nenhuma linha correspondeu ao Regex. Verifique o padrão.")
                
        except re.error as e:
            st.error(f"Erro de Sintaxe no Regex: {e}")
