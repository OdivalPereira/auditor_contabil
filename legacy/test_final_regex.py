
import re

line = "02/01/2025 0000 00000798 BB Rende Fácil 9.903 1.097,13 C 0,00 C"
pattern = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"        # Date
    r"[\d\s\-X]+?\s+"                 # Junk numbers
    r"(.+?)\s+"                       # Description
    r"([^\s]+)\s+"                    # Document
    r"([\d\.]+,\d{2})\s+"             # Value
    r"([DC])"                         # Type
    r"(?:\s+[\d\.]+,\d{2}\s+[DC])?$" # Optional Balance
)

m = pattern.match(line)
if m:
    print(f"MATCH: {m.groups()}")
else:
    print("NO MATCH")

# Test without balance
line2 = "27/01/2025 0000 14397821 Pix - Recebido 379.982.592.361.551 9.000,00 C"
m2 = pattern.match(line2)
if m2:
    print(f"MATCH 2: {m2.groups()}")
else:
    print("NO MATCH 2")
