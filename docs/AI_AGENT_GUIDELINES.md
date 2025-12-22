# AI Agent Guidelines - Auditor Contábil

> **Purpose**: This document provides guidelines for AI agents (like yourself) working on this codebase to ensure consistency and adherence to project standards.

## Project Overview

This is a **Brazilian accounting reconciliation system** that:
- Parses bank statement PDFs and ledger files
- Matches transactions between bank and accounting records
- Identifies discrepancies and provides detailed reports

## Critical Policies

### 1. Layout-Specific Parsing Only

**RULE**: Every bank statement layout MUST have its own dedicated parser method.

```python
# ✅ CORRECT APPROACH
class BBMonthlyPDFParser(BaseParser):
    def extract_page(self, page):
        if "G331" in text:
            return self._extract_g331(page)  # Specific method
        elif self._has_full_format(text):
            return self._extract_full_format(page)  # Specific method
        else:
            raise LayoutNotIdentifiedException()

# ❌ WRONG APPROACH
class BBMonthlyPDFParser(BaseParser):
    def extract_page(self, page):
        # Generic regex that tries to work for everything
        return self.extract_transactions_smart(page)
```

**Why**: Generic parsing fails silently and produces incorrect data. Layout-specific parsing ensures accuracy.

### 2. Clear Error Messages for Unknown Layouts

When a layout cannot be identified:

```python
# ✅ CORRECT: Tell user exactly which file and why
raise LayoutNotIdentifiedException(
    f"Layout não identificado para arquivo '{filename}'. "
    f"Banco detectado: {bank_name}. "
    f"Por favor, crie um layout específico para este extrato."
)

# ❌ WRONG: Silent failure or vague error
return []  # No idea what went wrong
```

### 3. Brazilian Number Formats

**Always** use Brazilian number format:
- Thousands separator: `.` (dot)
- Decimal separator: `,` (comma)
- Example: `1.234,56` = one thousand, two hundred thirty-four point fifty-six

```python
# ✅ CORRECT
def _parse_br_amount(self, value_str: str) -> float:
    cleaned = value_str.replace('.', '').replace(',', '.')
    return float(cleaned)

# ❌ WRONG: Assumes US format
float(value_str)  # Will fail on "1.234,56"
```

### 4. Date Formats

Brazilian PDFs use `DD/MM/YYYY` format:

```python
# ✅ CORRECT
dt = datetime.strptime(date_str, "%d/%m/%Y").date()

# ❌ WRONG
dt = datetime.strptime(date_str, "%m/%d/%Y").date()  # US format
```

## Code Organization

### Parser Structure

```
src/parsing/
├── banks/              # Bank-specific parsers
│   ├── bb.py          # Banco do Brasil
│   ├── itau.py        # Itaú
│   ├── santander.py   # Santander
│   └── ...
├── sources/           # Source type parsers
│   ├── ledger_csv.py
│   ├── ledger_pdf.py
│   └── ofx.py
├── config/            # Configuration
│   └── registry.py    # Layout registry
└── pipeline.py        # Extraction pipeline
```

### When Adding a New Bank Parser

1. **Create file** in `src/parsing/banks/`
2. **Inherit from** `BaseParser`
3. **Implement** layout detection
4. **Create** specific extraction methods
5. **Add to** `PARSERS` dict in `__init__.py`
6. **Test thoroughly** before committing

### When Updating an Existing Parser

1. **Understand** the current layout(s) it handles
2. **Add new method** for new layout variant (don't modify existing)
3. **Update** layout detection logic
4. **Test** all layouts to ensure no regressions
5. **Document** the new layout in docstrings

## Testing Requirements

### Before Committing Parser Changes

- [ ] Extract sample PDF manually to count transactions
- [ ] Run parser and verify count matches exactly
- [ ] Check that no header lines are extracted as transactions
- [ ] Verify date parsing (no year 2020 when it should be 2025!)
- [ ] Validate amount signs (debits negative, credits positive)
- [ ] Test with multiple PDFs of same layout
- [ ] Add test case if possible

### Red Flags During Testing

- ⚠️ Transaction count doesn't match manual count
- ⚠️ Dates are wrong (common: 2-digit year parsed incorrectly)
- ⚠️ Amounts are all positive (forgot to apply sign)
- ⚠️ Descriptions include amounts or dates (multi-line issue)
- ⚠️ Header lines appear as transactions
- ⚠️ Balance check fails significantly

## Common Patterns and Conventions

### Naming Conventions

```python
# Parser classes
class BBMonthlyPDFParser(BaseParser):  # Bank + type + Format + Parser

# Extraction methods
def _extract_g331(self, page):         # _extract_<layout_name>
def _extract_full_format(self, page):  # _extract_<descriptive_name>

# Detection methods
def _has_full_format(self, text):      # _has_<layout_name>
def _is_g331_layout(self, page):       # _is_<layout_name>_layout
```

### Return Format

All extraction methods must return:

```python
# Format: (rows, bal_start, bal_end)
rows = [
    {
        'date': datetime.date,
        'amount': float,  # Negative for debits, positive for credits
        'description': str,
        'source': 'Bank'  # or 'Ledger'
    },
    # ...
]
bal_start = float or None  # Optional
bal_end = float or None    # Optional

return rows, bal_start, bal_end
```

### Error Handling

```python
# ✅ GOOD: Specific exceptions with context
try:
    dt = datetime.strptime(dt_str, "%d/%m/%Y").date()
except ValueError as e:
    logger.error(f"Failed to parse date '{dt_str}': {e}")
    continue  # Skip this line, continue processing

# ❌ BAD: Silent failures
try:
    dt = datetime.strptime(dt_str, "%d/%m/%Y").date()
except:
    pass  # User won't know extraction failed
```

## User-Facing Features

### Upload Error Messages

When extraction fails, tell user:
1. **Which file** has the problem
2. **What bank** was detected (if any)
3. **What to do**: "Layout não identificado - contate o suporte"

```python
# In upload endpoint
try:
    result = pipeline.process_file(file_path)
except LayoutNotIdentifiedException as e:
    return {
        "error": str(e),
        "file": filename,
        "action": "create_layout"
    }
```

### Progress Feedback

For multi-file uploads:
```python
for i, file in enumerate(files, 1):
    logger.info(f"Processing file {i}/{len(files)}: {file.filename}")
    # ... process
```

## Architecture Principles

### 1. Single Responsibility
Each parser handles ONE bank. Each method handles ONE layout.

### 2. Fail Fast
If you can't identify the layout, stop immediately. Don't guess.

### 3. Explicit Over Implicit
```python
# ✅ Clear what's happening
if sign == 'D':
    amount = -abs(amount)
else:
    amount = abs(amount)

# ❌ Clever but unclear
amount = -abs(amount) if sign == 'D' else abs(amount)
```

### 4. Logging for Debugging
```python
logger.info(f"Detected layout: {layout_name}")
logger.debug(f"Extracted {len(rows)} transactions")
logger.warning(f"Skipped line: {line}")  # For potential issues
```

## Common Mistakes to Avoid

### 1. Not Handling Multi-Line Descriptions

Many bank PDFs split descriptions across lines:

```
03/01/2025 Transfer
ência recebida PIX
João Silva 1.000,00 C
```

Solution: Look ahead to next lines and concatenate.

### 2. Confusing C/D with +/-

- Some banks use `C` (credit) / `D` (debit)
- Others use `(+)` / `(-)`
- **Always normalize** to negative for debits, positive for credits

### 3. Year Parsing Issues

`datetime.strptime("31/12/25", "%d/%m/%y")` → 2025 ✅
BUT some PDFs have `31/12/2025`, so use `%Y` for 4-digit years

Solution: Detect format first, then parse.

### 4. Assuming One Transaction Per Line

Not all banks follow this. Some have:
- Date on one line
- Details on next line
- Amount on third line

Always analyze the actual PDF structure first.

## When in Doubt

1. **Look at existing parsers** for patterns
2. **Analyze the PDF manually** - open it and count transactions
3. **Ask for clarification** before implementing
4. **Test thoroughly** with real data
5. **Document your decisions** in code comments

## Quick Reference

### Must-Have Methods in Every Bank Parser

```python
class MyBankParser(BaseParser):
    bank_name = "Bank Name"  # Required
    
    def parse(self, file_path_or_buffer):
        """Entry point, delegates to parse_pdf"""
        return self.parse_pdf(file_path_or_buffer)
    
    def extract_page(self, page):
        """Main extraction logic, detects layout"""
        # Layout detection logic here
        # Delegate to specific extraction methods
    
    def _extract_layout_variant_1(self, page):
        """Specific extraction for layout variant 1"""
        # Implementation
    
    def _parse_br_amount(self, value_str):
        """Parse Brazilian number format"""
        # Inherited from BaseParser, usually don't override
```

### Useful BaseParser Methods

```python
self._parse_br_amount("1.234,56")  # → 1234.56
self.parse_pdf(file_path)           # Parse entire PDF
self.extract_transactions_smart()    # Fallback (use sparingly!)
```

## Summary for AI Agents

When working on this project:

1. ✅ **Create specific parsers** for each layout
2. ✅ **Fail clearly** when layout is unknown
3. ✅ **Test thoroughly** with real data
4. ✅ **Document decisions** in code and commits
5. ✅ **Follow Brazilian formats** (dates, numbers)
6. ❌ **Never use** generic parsing as primary method
7. ❌ **Never silently fail** - always log and report errors
8. ❌ **Never assume** layouts are the same across banks or even within one bank

**Remember**: Accuracy is more important than coverage. It's better to return an error for an unknown layout than to extract incorrect data.
