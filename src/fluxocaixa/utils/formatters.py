
def format_currency(value):
    """Format numbers to currency string using Bi/Mi for large numbers."""
    if value is None:
        return "R$ 0"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"R$ {value / 1_000_000_000:.1f} Bi"
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:.1f} Mi"
    return f"R$ {value:,.2f}"
