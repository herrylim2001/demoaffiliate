"""
Affiliate model for the Affiliate & Bonus System
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from ..utils.enums import (
    AffiliateStatus,
    PeriodType,
    CommissionPlanType,
    BaseType,
    RateMode,
    DSRIndicator,
    CalculationType,
)


@dataclass
class DSRTier:
    """Dynamic Slicing Rule tier configuration"""

    tier_id: str = field(default_factory=lambda: str(uuid4()))
    min_value: Decimal = field(default_factory=lambda: Decimal("0.00"))
    max_value: Optional[Decimal] = None  # None means unlimited
    rate: Decimal = field(default_factory=lambda: Decimal("0.00"))  # Percentage as decimal (e.g., 0.10 = 10%)

    def contains(self, value: Decimal) -> bool:
        """Check if value falls within this tier"""
        if self.max_value is None:
            return value >= self.min_value
        return self.min_value <= value < self.max_value

    def __repr__(self) -> str:
        max_str = "∞" if self.max_value is None else str(self.max_value)
        return f"DSRTier({self.min_value}-{max_str}: {self.rate * 100}%)"


@dataclass
class CommissionPlan:
    """Commission plan configuration"""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    plan_type: CommissionPlanType = CommissionPlanType.REVENUE_SHARE
    name: str = ""

    # Base configuration
    base_type: BaseType = BaseType.NGR

    # Rate configuration
    rate_mode: RateMode = RateMode.FIXED
    fixed_rate: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # DSR configuration (if rate_mode == DSR)
    dsr_indicator: DSRIndicator = DSRIndicator.NGR
    dsr_tiers: List[DSRTier] = field(default_factory=list)
    calculation_type: CalculationType = CalculationType.FLAT

    # For count-based plans (signup, first_deposit, active_user)
    fixed_payout_per_event: Decimal = field(default_factory=lambda: Decimal("0.00"))

    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def get_dsr_rate(self, indicator_value: Decimal) -> Decimal:
        """Get the DSR rate based on indicator value (for FLAT calculation)"""
        for tier in sorted(self.dsr_tiers, key=lambda t: t.min_value, reverse=True):
            if tier.contains(indicator_value):
                return tier.rate
        return Decimal("0.00")

    def calculate_dsr_non_flat(self, indicator_value: Decimal, base_value: Decimal) -> Decimal:
        """Calculate commission using marginal (non-flat) DSR rates"""
        if indicator_value <= 0:
            return Decimal("0.00")

        total_commission = Decimal("0.00")
        remaining_value = base_value
        sorted_tiers = sorted(self.dsr_tiers, key=lambda t: t.min_value)

        for tier in sorted_tiers:
            if remaining_value <= 0:
                break

            tier_max = tier.max_value if tier.max_value else indicator_value
            tier_range = tier_max - tier.min_value

            if indicator_value > tier.min_value:
                # Calculate the portion of base_value that falls in this tier
                applicable_portion = min(remaining_value, tier_range)
                tier_commission = applicable_portion * tier.rate
                total_commission += tier_commission
                remaining_value -= applicable_portion

        return total_commission

    def __repr__(self) -> str:
        return f"CommissionPlan({self.plan_type.value}, {self.name})"


@dataclass
class Affiliate:
    """Affiliate entity"""

    affiliate_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    parent_affiliate_id: Optional[str] = None  # For multi-level structure
    status: AffiliateStatus = AffiliateStatus.ACTIVE

    # Commission configuration
    commission_plans: List[CommissionPlan] = field(default_factory=list)

    # Admin cost configuration
    admin_royalty_rate: Decimal = field(default_factory=lambda: Decimal("0.00"))  # Percentage

    # Manual adjustment (positive or negative)
    manual_adjustment: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Bonus deduction
    bonus_deduction: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Balance deduction (carryover negative balance)
    balance_deduction: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Period configuration
    period_type: PeriodType = PeriodType.CALENDAR_MONTH
    custom_period_start: Optional[datetime] = None
    custom_period_end: Optional[datetime] = None

    # Multi-level commission rate (for upline)
    upline_commission_rate: Decimal = field(default_factory=lambda: Decimal("0.00"))

    signup_date: datetime = field(default_factory=datetime.now)

    # List of user IDs coded under this affiliate
    coded_users: List[str] = field(default_factory=list)

    # List of child affiliate IDs
    child_affiliates: List[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status == AffiliateStatus.ACTIVE

    def add_commission_plan(self, plan: CommissionPlan) -> None:
        """Add a commission plan to the affiliate"""
        self.commission_plans.append(plan)

    def remove_commission_plan(self, plan_id: str) -> bool:
        """Remove a commission plan by ID"""
        for i, plan in enumerate(self.commission_plans):
            if plan.plan_id == plan_id:
                self.commission_plans.pop(i)
                return True
        return False

    def __repr__(self) -> str:
        return f"Affiliate(id={self.affiliate_id[:8]}, name={self.name}, plans={len(self.commission_plans)})"
