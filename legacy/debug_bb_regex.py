
import re
import pandas as pd

def _parse_br_amount(amount_str) -> float:
    clean_str = str(amount_str).replace('.', '').replace(',', '.')
    return abs(float(clean_str))

pattern = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"        # Date
    r"[\d\s\-X]+?\s+"                 # Junk numbers
    r"(.+?)\s+"                       # Description
    r"([^\s]+)\s+"                    # Document
    r"([\d\.]+,\d{2})\s+"             # Value
    r"([DC])"                         # Type
    r"(?:\s+[\d\.]+,\d{2}\s+[DC])?$" # Optional Balance (non-capturing)
)

lines = [
    "27/01/2025 0000 14397821 Pix - Recebido 379.982.592.361.551 9.000,00 C",
    "02/01/2025 0000 00000798 BB Rende Fácil 9.903 1.097,13 C 0,00 C",
    "28/01/2025 0000 00000798 BB Rende Fácil 9.903 37.512,37 C 0,00 C",
]

for line in lines:
    match = pattern.match(line)
    if match:
        print(f"MATCH: {match.groups()}")
    else:
        print(f"FAIL: {line}")
