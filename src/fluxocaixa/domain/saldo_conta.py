"""Domain schemas for SaldoConta (Bank Account Balance)."""
from datetime import date
from pydantic import BaseModel, Field


class SaldoContaCreate(BaseModel):
    """Schema for creating a new bank account balance record."""
    seq_conta: int = Field(..., description="Bank account sequence ID")
    dat_saldo: date = Field(..., description="Balance date")
    val_saldo: float = Field(..., description="Balance value")
    
    class Config:
        from_attributes = True


class SaldoContaUpdate(BaseModel):
    """Schema for updating an existing bank account balance record."""
    val_saldo: float = Field(..., description="Updated balance value")
    
    class Config:
        from_attributes = True
