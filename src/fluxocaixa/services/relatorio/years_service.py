"""Years service - extract available years from data."""
from ...repositories.lancamento_repository import LancamentoRepository
from ...repositories.pagamento_repository import PagamentoRepository


def get_available_years() -> list[int]:
    """Get list of years with lancamentos or pagamentos data.
    
    Returns:
        List of years sorted in descending order
    """
    lancamento_repo = LancamentoRepository()
    pagamento_repo = PagamentoRepository()
    
    lancamento_years = set(lancamento_repo.get_available_years())
    pagamento_years = set(pagamento_repo.get_available_years())
    
    years = sorted(lancamento_years | pagamento_years, reverse=True)
    return years
