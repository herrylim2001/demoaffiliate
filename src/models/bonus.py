"""
Bonus model for the Affiliate & Bonus System
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from ..utils.enums import BonusType, BonusStatus


@dataclass
class BonusConfig:
    """Configuration for bonus rules"""

    config_id: str = field(default_factory=lambda: str(uuid4()))
    bonus_type: BonusType = BonusType.DEPOSIT
    name: str = ""

    # Rate configuration
    rate: Decimal = field(default_factory=lambda: Decimal("0.00"))  # e.g., 0.10 = 10%

    # Limits
    max_bonus: Optional[Decimal] = None  # Maximum bonus amount
    min_trigger_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))  # Minimum deposit/bet to trigger

    # Wagering requirement
    wagering_requirement: Optional[Decimal] = None  # e.g., 30x means bonus * 30

    # Expiry configuration
    expiry_days: int = 30  # Days until bonus expires

    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_bonus(self, trigger_amount: Decimal) -> Decimal:
        """Calculate bonus amount based on trigger amount"""
        if trigger_amount < self.min_trigger_amount:
            return Decimal("0.00")

        bonus = trigger_amount * self.rate

        if self.max_bonus is not None:
            bonus = min(bonus, self.max_bonus)

        return bonus

    def __repr__(self) -> str:
        return f"BonusConfig({self.bonus_type.value}, rate={self.rate * 100}%)"


@dataclass
class Bonus:
    """Individual bonus instance issued to a user"""

    bonus_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    bonus_type: BonusType = BonusType.DEPOSIT
    config_id: Optional[str] = None  # Reference to BonusConfig

    # Amounts
    amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    wagering_requirement: Optional[Decimal] = None
    wagering_progress: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Status
    status: BonusStatus = BonusStatus.ACTIVE

    # Dates
    issued_at: datetime = field(default_factory=datetime.now)
    expiry_date: Optional[datetime] = None
    claimed_at: Optional[datetime] = None

    # Admin notes (for special bonus)
    admin_note: Optional[str] = None
    issued_by: Optional[str] = None  # Admin ID

    @property
    def is_expired(self) -> bool:
        """Check if bonus has expired"""
        if self.expiry_date is None:
            return False
        return datetime.now() > self.expiry_date

    @property
    def is_claimable(self) -> bool:
        """Check if bonus can be claimed"""
        if self.status != BonusStatus.ACTIVE and self.status != BonusStatus.CLAIMABLE:
            return False
        if self.is_expired:
            return False
        if self.wagering_requirement is not None:
            return self.wagering_progress >= self.wagering_requirement
        return True

    @property
    def wagering_remaining(self) -> Decimal:
        """Get remaining wagering requirement"""
        if self.wagering_requirement is None:
            return Decimal("0.00")
        return max(Decimal("0.00"), self.wagering_requirement - self.wagering_progress)

    def update_wagering_progress(self, bet_amount: Decimal) -> None:
        """Update wagering progress with a bet amount"""
        self.wagering_progress += bet_amount
        if self.wagering_requirement and self.wagering_progress >= self.wagering_requirement:
            self.status = BonusStatus.CLAIMABLE

    def claim(self) -> bool:
        """Attempt to claim the bonus"""
        if not self.is_claimable:
            return False
        self.status = BonusStatus.CLAIMED
        self.claimed_at = datetime.now()
        return True

    def expire(self) -> None:
        """Mark bonus as expired"""
        self.status = BonusStatus.EXPIRED

    def check_and_update_expiry(self) -> bool:
        """Check expiry and update status if needed"""
        if self.is_expired and self.status not in [BonusStatus.EXPIRED, BonusStatus.CLAIMED]:
            self.expire()
            return True
        return False

    def __repr__(self) -> str:
        return f"Bonus({self.bonus_type.value}, amount={self.amount}, status={self.status.value})"
