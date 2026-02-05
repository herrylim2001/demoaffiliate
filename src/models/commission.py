"""
Commission statement and period models
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List
from uuid import uuid4


@dataclass
class CommissionPeriod:
    """Represents a commission calculation period"""

    period_id: str = field(default_factory=lambda: str(uuid4()))
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    is_closed: bool = False
    closed_at: Optional[datetime] = None

    def __repr__(self) -> str:
        status = "closed" if self.is_closed else "open"
        return f"CommissionPeriod({self.start_date.date()} to {self.end_date.date()}, {status})"


@dataclass
class PlanBreakdown:
    """Breakdown of commission from a single plan"""

    plan_id: str = ""
    plan_name: str = ""
    plan_type: str = ""
    base_value: Decimal = field(default_factory=lambda: Decimal("0.00"))
    rate_applied: Decimal = field(default_factory=lambda: Decimal("0.00"))
    gross_commission: Decimal = field(default_factory=lambda: Decimal("0.00"))


@dataclass
class CommissionStatement:
    """Commission statement for an affiliate for a period"""

    statement_id: str = field(default_factory=lambda: str(uuid4()))
    affiliate_id: str = ""
    affiliate_name: str = ""
    period: CommissionPeriod = field(default_factory=CommissionPeriod)

    # Metrics
    total_players: int = 0
    active_players: int = 0
    new_signups: int = 0
    first_deposits: int = 0

    # Revenue metrics
    total_bets: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_payouts: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_deposits: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_withdrawals: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_bonus_cost: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Calculated values
    ggr: Decimal = field(default_factory=lambda: Decimal("0.00"))
    ngr: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Commission breakdown by plan
    plan_breakdowns: List[PlanBreakdown] = field(default_factory=list)

    # Commission totals
    total_gross_commission: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Deductions
    admin_cost: Decimal = field(default_factory=lambda: Decimal("0.00"))
    admin_royalty_rate: Decimal = field(default_factory=lambda: Decimal("0.00"))
    bonus_deduction: Decimal = field(default_factory=lambda: Decimal("0.00"))
    balance_deduction: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Net after deductions
    net_after_cost: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Manual adjustment
    manual_adjustment: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Final commission
    net_commission: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Upline commission (for child affiliates)
    upline_commission_paid: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Final payable
    final_payable: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Status
    is_finalized: bool = False
    finalized_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_derived_values(self) -> None:
        """Calculate GGR and NGR from transaction totals"""
        self.ggr = self.total_bets - self.total_payouts
        self.ngr = self.ggr - self.total_bonus_cost

    def calculate_net_commission(self) -> None:
        """Calculate final net commission"""
        self.net_after_cost = (
            self.total_gross_commission
            - self.admin_cost
            - self.bonus_deduction
            - self.balance_deduction
        )
        self.net_commission = self.net_after_cost + self.manual_adjustment
        self.final_payable = self.net_commission - self.upline_commission_paid

    def to_dict(self) -> Dict:
        """Convert statement to dictionary for display"""
        return {
            "statement_id": self.statement_id,
            "affiliate_id": self.affiliate_id,
            "affiliate_name": self.affiliate_name,
            "period": f"{self.period.start_date.date()} to {self.period.end_date.date()}",
            "total_players": self.total_players,
            "active_players": self.active_players,
            "total_bets": float(self.total_bets),
            "total_payouts": float(self.total_payouts),
            "ggr": float(self.ggr),
            "ngr": float(self.ngr),
            "total_gross_commission": float(self.total_gross_commission),
            "admin_cost": float(self.admin_cost),
            "bonus_deduction": float(self.bonus_deduction),
            "balance_deduction": float(self.balance_deduction),
            "net_after_cost": float(self.net_after_cost),
            "manual_adjustment": float(self.manual_adjustment),
            "net_commission": float(self.net_commission),
            "upline_commission_paid": float(self.upline_commission_paid),
            "final_payable": float(self.final_payable),
        }

    def __repr__(self) -> str:
        return f"CommissionStatement(affiliate={self.affiliate_name}, net={self.net_commission})"
