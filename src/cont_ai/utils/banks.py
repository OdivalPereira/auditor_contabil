
"""
Database of Brazilian Banks (Code -> Name).
Source: FEBRABAN / BACEN (Partial List of Major Banks)
"""

BRAZILIAN_BANKS = {
    "001": "Banco do Brasil S.A.",
    "003": "Banco da Amazônia S.A.",
    "004": "Banco do Nordeste do Brasil S.A.",
    "021": "BANESTES S.A. Banco do Estado do Espírito Santo",
    "033": "Banco Santander (Brasil) S.A.",
    "041": "Banco do Estado do Rio Grande do Sul S.A.",
    "047": "Banco do Estado de Sergipe S.A.",
    "070": "BRB - Banco de Brasília S.A.",
    "077": "Banco Inter S.A.",
    "104": "Caixa Econômica Federal",
    "208": "Banco BTG Pactual S.A.",
    "212": "Banco Original S.A.",
    "237": "Banco Bradesco S.A.",
    "260": "Nu Pagamentos S.A. (Nubank)",
    "336": "Banco C6 S.A.",
    "341": "Itaú Unibanco S.A.",
    "389": "Banco Mercantil do Brasil S.A.",
    "422": "Banco Safra S.A.",
    "655": "Banco Votorantim S.A.",
    "745": "Banco Citibank S.A.",
    "748": "Banco Cooperativo Sicredi S.A.",
    "756": "Banco Cooperativo do Brasil S.A. (SICOOB)",
    "633": "Banco Rendimento S.A.",
    "290": "PagSeguro Internet S.A.",
    "323": "Mercado Pago IP Ltda.",
    "074": "Banco Safra S.A.",
    "637": "Banco Sofisa S.A.",
    "643": "Banco Pine S.A.",
    "653": "Banco Voiter S.A.",
    "079": "Banco Original do Agronegócio S.A.",
}

def get_bank_name(code: str) -> str:
    """Returns the name of the bank or 'Desconhecido'."""
    return BRAZILIAN_BANKS.get(code.replace(".", "").strip(), "Banco Desconhecido")
