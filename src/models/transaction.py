"""
Transaction model for the Affiliate & Bonus System
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from ..utils.enums import TransactionType


@dataclass
class Transaction:
    """Represents a transaction in the system"""

    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    transaction_type: TransactionType = TransactionType.BET
    amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    created_at: datetime = field(default_factory=datetime.now)

    # For rollback tracking
    is_rollback: bool = False
    original_transaction_id: Optional[str] = None

    # Provider info
    provider_id: Optional[str] = None
    game_id: Optional[str] = None

    def __repr__(self) -> str:
        return f"Transaction({self.transaction_type.value}, amount={self.amount}, user={self.user_id[:8]})"
