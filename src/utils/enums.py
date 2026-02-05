"""
Enums and constants for the Affiliate & Bonus System
"""
from enum import Enum
from decimal import Decimal


class AffiliateStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class PeriodType(Enum):
    CALENDAR_MONTH = "calendar_month"
    FROM_SIGNUP = "from_signup"
    CUSTOM = "custom"


class CommissionPlanType(Enum):
    REVENUE_SHARE = "revenue_share"
    WAGER_RAKEBACK = "wager_rakeback"
    SIGNUP = "signup"
    FIRST_DEPOSIT = "first_deposit"
    ACTIVE_USER = "active_user"
    DEPOSIT_WITHDRAWAL = "deposit_withdrawal"


class BaseType(Enum):
    NGR = "ngr"  # Net Gaming Revenue
    GGR = "ggr"  # Gross Gaming Revenue
    TOTAL_BET = "total_bet"
    TOTAL_RAKE = "total_rake"


class RateMode(Enum):
    FIXED = "fixed"
    DSR = "dsr"  # Dynamic Slicing Rule


class DSRIndicator(Enum):
    NGR = "ngr"
    GGR = "ggr"
    COUNT = "count"


class CalculationType(Enum):
    FLAT = "flat"  # Single rate applied to entire base
    NON_FLAT = "non_flat"  # Marginal rate applied per tier segment


class BonusType(Enum):
    DEPOSIT = "deposit"
    RAKEBACK = "rakeback"
    CASHBACK = "cashback"
    SPECIAL = "special"


class BonusStatus(Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    CLAIMABLE = "claimable"
    EXPIRED = "expired"
    CLAIMED = "claimed"


class TransactionType(Enum):
    BET = "bet"
    PAYOUT = "payout"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BONUS = "bonus"
    ROLLBACK = "rollback"


# Default values
DEFAULT_DECIMAL = Decimal("0.00")
