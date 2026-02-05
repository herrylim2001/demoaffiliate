"""
User model for the Affiliate & Bonus System
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass
class User:
    """Represents a player/user in the system"""

    user_id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    affiliate_id: Optional[str] = None  # The affiliate this user is coded under
    signup_date: datetime = field(default_factory=datetime.now)
    first_deposit_date: Optional[datetime] = None
    is_active: bool = True

    # Aggregated metrics (updated by transactions)
    total_deposits: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_withdrawals: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_bets: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_payouts: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_bonus_used: Decimal = field(default_factory=lambda: Decimal("0.00"))

    @property
    def ggr(self) -> Decimal:
        """Gross Gaming Revenue = Total Bet - Total Payout"""
        return self.total_bets - self.total_payouts

    @property
    def ngr(self) -> Decimal:
        """Net Gaming Revenue = GGR - Bonus Cost"""
        return self.ggr - self.total_bonus_used

    @property
    def net_deposit(self) -> Decimal:
        """Net Deposit = Deposits - Withdrawals"""
        return self.total_deposits - self.total_withdrawals

    @property
    def net_loss(self) -> Decimal:
        """Net Loss = max(0, Bet - Payout)"""
        return max(Decimal("0.00"), self.total_bets - self.total_payouts)

    def __repr__(self) -> str:
        return f"User(id={self.user_id[:8]}, username={self.username}, affiliate={self.affiliate_id[:8] if self.affiliate_id else None})"
