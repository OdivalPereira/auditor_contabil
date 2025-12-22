# Parser Policy Summary

**Last Updated**: 2025-12-22

## Core Principle

> **NO GENERIC PARSING**  
> Every bank statement layout must have its own specific extraction logic.

## Rules

1. ❌ **Never** use generic/fallback parsing as the primary method
2. ✅ **Always** create a dedicated parser method for each identified layout
3. ⚠️ **Always** return clear errors when a layout is not identified, specifying the file name
4. ✅ **Always** test thoroughly with real PDFs before deployment

## When Unknown Layout is Encountered

1. **STOP** extraction immediately
2. **LOG** detailed information: bank, file name, sample text
3. **RETURN** error to user: `"Layout não identificado para arquivo '{filename}'. Por favor, crie um layout específico."`
4. **CREATE** new layout definition before allowing processing

## File Structure

- **Detailed Guidelines**: [`docs/PARSING_GUIDELINES.md`](./PARSING_GUIDELINES.md)
- **AI Agent Guidelines**: [`docs/AI_AGENT_GUIDELINES.md`](./AI_AGENT_GUIDELINES.md)
- **Bank Parsers**: `src/parsing/banks/`

## Quick Example

```python
# ✅ CORRECT
def extract_page(self, page):
    if self._is_layout_A(page):
        return self._extract_layout_a(page)
    elif self._is_layout_B(page):
        return self._extract_layout_b(page)
    else:
        raise LayoutNotIdentifiedException(f"Unknown layout in file: {filename}")

# ❌ WRONG  
def extract_page(self, page):
    return self.extract_transactions_smart(page)  # Generic fallback
```

---

For complete details, see the full documentation files linked above.
