# 📋 Guia de Layouts JSON para Novos Bancos

Este guia explica como criar configurações de layout para extrair transações de novos formatos de extratos bancários em PDF.

## Visão Geral

O sistema usa arquivos JSON para definir regras de extração específicas para cada banco. Cada layout contém:
- **Keywords** para identificação automática do banco
- **Regex** para capturar linhas de transação
- **Mapeamento de colunas** para extrair campos (data, valor, descrição, tipo)
- **Configurações** de formatação (separadores, formato de data)

## Estrutura do Arquivo JSON

```json
{
    "name": "Nome do Banco - Tipo de Extrato",
    "bank_id": "CÓDIGO_BANCO",
    "keywords": ["Palavra1", "Palavra2"],
    "line_pattern": "REGEX_PARA_LINHAS_DE_TRANSACAO",
    "columns": [
        {"name": "date", "match_group": 1},
        {"name": "memo", "match_group": 2},
        {"name": "amount", "match_group": 3},
        {"name": "type", "match_group": 4}
    ],
    "amount_decimal_separator": ",",
    "amount_thousand_separator": ".",
    "date_format": "%d/%m/%Y",
    "has_balance_cleanup": true,
    "balance_start_pattern": "REGEX_SALDO_INICIAL",
    "balance_end_pattern": "REGEX_SALDO_FINAL"
}
```

## Campos Obrigatórios

### `name` (string)
Nome legível do layout para identificação.
```json
"name": "Banco do Brasil - Mensal"
```

### `bank_id` (string)
Código do banco (COMPE/ISPB).
```json
"bank_id": "001"  // Banco do Brasil
"bank_id": "748"  // Sicredi
"bank_id": "033"  // Santander
```

### `keywords` (array de strings)
Palavras-chave únicas para identificar este banco no PDF. O sistema verifica se **TODAS** as keywords estão presentes.

```json
// Exemplo: Banco do Brasil
"keywords": ["Extrato de Conta", "bb.com.br"]

// Exemplo: Sicredi  
"keywords": ["COOP CRED", "POUP E INVEST"]
```

> ⚠️ **Dica**: Use textos exclusivos que aparecem no cabeçalho/rodapé do extrato.

### `line_pattern` (string)
Expressão regular para capturar linhas de transação. Cada grupo de captura `()` será mapeado para uma coluna.

**Exemplo - Formato BB:**
```
Linha: "02.01.2025 Pagamento de Boleto 782,38 D"
Regex: ^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([CD])
         ├── Grupo 1: data      ├── Grupo 2: descrição ├── Grupo 3: valor   └── Grupo 4: tipo
```

```json
"line_pattern": "^(\\d{2}\\.\\d{2}\\.\\d{4})\\s+(.+?)\\s+([\\d\\.]+,\\d{2})\\s+([CD])"
```

> ⚠️ **Importante**: Em JSON, escape barras invertidas (`\` → `\\`).

### `columns` (array de objetos)
Mapeia grupos de captura do regex para campos da transação.

| Campo | Descrição | Obrigatório |
|-------|-----------|-------------|
| `date` | Data da transação | ✅ |
| `memo` | Descrição/histórico | ✅ |
| `amount` | Valor da transação | ✅ |
| `type` | Indicador D/C | Opcional |
| `amount_debit` | Valor débito (coluna separada) | Opcional |
| `amount_credit` | Valor crédito (coluna separada) | Opcional |
| `doc_id` | Número do documento | Opcional |

```json
"columns": [
    {"name": "date", "match_group": 1},
    {"name": "memo", "match_group": 2},
    {"name": "amount", "match_group": 3},
    {"name": "type", "match_group": 4}
]
```

## Campos Opcionais

### `amount_decimal_separator` (string)
Separador decimal do valor. Padrão: `,`
```json
"amount_decimal_separator": ","  // Brasil: 1.234,56
"amount_decimal_separator": "."  // USA: 1,234.56
```

### `amount_thousand_separator` (string)
Separador de milhar. Padrão: `.`
```json
"amount_thousand_separator": "."  // Brasil
"amount_thousand_separator": ","  // USA
```

### `date_format` (string)
Formato da data (sintaxe Python strftime). Padrão: `%d/%m/%Y`

| Formato | Exemplo |
|---------|---------|
| `%d/%m/%Y` | 02/01/2025 |
| `%d.%m.%Y` | 02.01.2025 |
| `%Y-%m-%d` | 2025-01-02 |

### `has_balance_cleanup` (boolean)
Se `true`, remove linhas contendo "saldo", "total", "transporte". Padrão: `true`

### `balance_start_pattern` (string)
Regex para encontrar saldo inicial (para validação).
```json
"balance_start_pattern": "(SALDO ANTERIOR)\\s+([\\d\\.]+,\\d{2})"
```
> Grupo 2 deve conter o valor.

### `balance_end_pattern` (string)
Regex para encontrar saldo final (para validação).
```json
"balance_end_pattern": "(SALDO ATUAL)\\s+([\\d\\.]+,\\d{2})"
```

---

## Passo a Passo: Criar Novo Layout

### 1. Extrair Texto do PDF

```python
import pdfplumber

with pdfplumber.open("extrato_novo_banco.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text())
```

### 2. Identificar Padrões

Procure no texto:
- **Headers únicos** → keywords
- **Linhas de transação** → line_pattern
- **Formato de data** → date_format
- **Formato de valor** → separadores

### 3. Testar Regex Online

Use [regex101.com](https://regex101.com/) com flavor Python para testar o regex.

### 4. Criar Arquivo JSON

Salve em: `src/cont_ai/layouts/nome_banco.json`

### 5. Testar Extração

```python
from src.parsing import LayoutRegistry, GenericPDFExtractor

registry = LayoutRegistry("src/cont_ai/layouts")
layout = registry.detect(texto_pdf)

if layout:
    extractor = GenericPDFExtractor(layout)
    result = extractor.extract("caminho/para/extrato.pdf")
    print(f"Transações: {len(result['transactions'])}")
    print(f"Validação: {result['validation']}")
```

---

## Exemplos Completos

### Banco do Brasil - Mensal
```json
{
    "name": "Banco do Brasil - Mensal",
    "bank_id": "001",
    "keywords": ["Extrato de Conta", "Conta Corrente", "bb.com.br"],
    "line_pattern": "^(\\d{2}\\.\\d{2}\\.\\d{4})\\s+(.+?)\\s+([\\d\\.]+,\\d{2})\\s+([CD])",
    "columns": [
        {"name": "date", "match_group": 1},
        {"name": "memo", "match_group": 2},
        {"name": "amount", "match_group": 3},
        {"name": "type", "match_group": 4}
    ],
    "date_format": "%d.%m.%Y",
    "has_balance_cleanup": true
}
```

### Layout com Colunas Separadas de Débito/Crédito
```json
{
    "name": "Banco Exemplo - Duas Colunas",
    "bank_id": "999",
    "keywords": ["Banco Exemplo S.A."],
    "line_pattern": "^(\\d{2}/\\d{2}/\\d{4})\\s+(.+?)\\s+([\\d\\.]+,\\d{2})?\\s+([\\d\\.]+,\\d{2})?$",
    "columns": [
        {"name": "date", "match_group": 1},
        {"name": "memo", "match_group": 2},
        {"name": "amount_debit", "match_group": 3},
        {"name": "amount_credit", "match_group": 4}
    ],
    "date_format": "%d/%m/%Y"
}
```

---

## Troubleshooting

### Problema: Layout não detectado
- Verifique se TODAS as keywords estão presentes no PDF
- Use keywords mais específicas

### Problema: Transações não capturadas
- Teste o regex em regex101.com
- Verifique se há variações no formato das linhas

### Problema: Valores incorretos
- Verifique separadores (decimal/milhar)
- Verifique se o grupo de captura está correto

### Problema: Data inválida
- Verifique `date_format` corresponde ao formato real
- Use strftime corretamente

---

## Geração Automática com IA

O sistema pode sugerir layouts automaticamente usando a API Gemini:

```python
from src.parsing import GeminiLayoutGenerator

generator = GeminiLayoutGenerator(api_key="SUA_API_KEY")
layout_sugerido = generator.generate_layout(texto_pdf)
print(layout_sugerido)
```

O resultado pode ser refinado manualmente antes de salvar.
