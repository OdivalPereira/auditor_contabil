import re

test_lines = [
    "26/02/2025 Crédito BASILIO PEREIRA 59,00 3.026,89",
    "26/02/2025 Crédito 44560265100 63,00 1.570,36",
    "28/03/2025 Crédito 60,00 8.973,34",
    "28/03/2025 Débito Tarifa -0,67 8.913,79",
    "30/03/2025 Débito Tarifa -0,46 123,45"
]

# New strategy:
# Match Date and Type at the start
# Match Amount and Balance at the end
# Capture Description in between
# Note: Amount and Balance MUST contain a comma and be at the end.

# Pattern explanation:
# ^(\d{2}/\d{2}/\d{2,4})         -> Date
# \s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+ -> Type
# (.*?)                           -> Description (non-greedy)
# \s+                             -> Spacer
# (-?(?:R\$\s*)?[\d\.]+,\d{2})    -> Amount (must have at least one comma and digits after)
# \s+                             -> Spacer
# (-?(?:R\$\s*)?[\d\.]+,\d{2})    -> Balance (same)
# $                               -> End of line

new_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(.*?)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')

# Alternative if description is empty (sometimes it is)
alt_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')

print("Testing new pattern:")
for line in test_lines:
    m = new_pattern.search(line)
    if not m:
        m = alt_pattern.search(line)
        if m:
            print(f"MATCH (ALT): {line}")
            print(f"  Groups: {m.groups()}")
        else:
            print(f"NO MATCH: {line}")
    else:
        print(f"MATCH: {line}")
        print(f"  Groups: {m.groups()}")
