"""
Commission Calculator Service - handles all commission calculations
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ..models.affiliate import Affiliate, CommissionPlan
from ..models.commission import CommissionStatement, CommissionPeriod, PlanBreakdown
from ..models.user import User
from ..utils.enums import (
    CommissionPlanType,
    BaseType,
    RateMode,
    DSRIndicator,
    CalculationType,
)
from .affiliate_service import AffiliateService


class CommissionCalculator:
    """
    Commission calculation engine implementing all plan types:
    - Revenue Share (NGR/GGR based)
    - Wager/Rakeback
    - Count-based (Signup, First Deposit, Active User)
    - Deposit-Withdrawal
    - Hybrid (combination of multiple plans)

    Also handles:
    - DSR (Dynamic Slicing Rule) with Flat and Non-Flat calculations
    - Admin cost deductions
    - Multi-level affiliate commissions
    """

    def __init__(self, affiliate_service: AffiliateService):
        self.affiliate_service = affiliate_service

    def calculate_commission(
        self,
        affiliate: Affiliate,
        period: CommissionPeriod,
        metrics: Optional[Dict] = None,
    ) -> CommissionStatement:
        """
        Calculate commission for an affiliate for a given period.

        Args:
            affiliate: The affiliate to calculate commission for
            period: The commission period
            metrics: Optional pre-calculated metrics (if None, will be fetched)

        Returns:
            CommissionStatement with complete breakdown
        """
        # Get metrics if not provided
        if metrics is None:
            metrics = self.affiliate_service.get_affiliate_metrics(affiliate.affiliate_id)

        # Create statement
        statement = CommissionStatement(
            affiliate_id=affiliate.affiliate_id,
            affiliate_name=affiliate.name,
            period=period,
            total_players=metrics.get("total_users", 0),
            active_players=metrics.get("active_users", 0),
            new_signups=metrics.get("new_signups", 0),
            first_deposits=metrics.get("first_deposits", 0),
            total_bets=metrics.get("total_bets", Decimal("0.00")),
            total_payouts=metrics.get("total_payouts", Decimal("0.00")),
            total_deposits=metrics.get("total_deposits", Decimal("0.00")),
            total_withdrawals=metrics.get("total_withdrawals", Decimal("0.00")),
            total_bonus_cost=metrics.get("total_bonus_cost", Decimal("0.00")),
        )

        # Calculate GGR and NGR
        statement.calculate_derived_values()

        # Calculate commission for each plan (Hybrid support)
        total_gross = Decimal("0.00")

        for plan in affiliate.commission_plans:
            if not plan.is_active:
                continue

            breakdown = self._calculate_plan_commission(plan, statement, metrics)
            statement.plan_breakdowns.append(breakdown)
            total_gross += breakdown.gross_commission

        statement.total_gross_commission = total_gross

        # Apply admin cost
        statement.admin_royalty_rate = affiliate.admin_royalty_rate
        statement.admin_cost = statement.ngr * affiliate.admin_royalty_rate

        # Apply deductions
        statement.bonus_deduction = affiliate.bonus_deduction
        statement.balance_deduction = affiliate.balance_deduction

        # Apply manual adjustment
        statement.manual_adjustment = affiliate.manual_adjustment

        # Calculate final net commission
        statement.calculate_net_commission()

        return statement

    def _calculate_plan_commission(
        self,
        plan: CommissionPlan,
        statement: CommissionStatement,
        metrics: Dict,
    ) -> PlanBreakdown:
        """Calculate commission for a single plan"""
        breakdown = PlanBreakdown(
            plan_id=plan.plan_id,
            plan_name=plan.name,
            plan_type=plan.plan_type.value,
        )

        if plan.plan_type == CommissionPlanType.REVENUE_SHARE:
            self._calculate_revenue_share(plan, statement, metrics, breakdown)

        elif plan.plan_type == CommissionPlanType.WAGER_RAKEBACK:
            self._calculate_wager_rakeback(plan, statement, metrics, breakdown)

        elif plan.plan_type == CommissionPlanType.SIGNUP:
            self._calculate_count_based(plan, metrics.get("new_signups", 0), breakdown)

        elif plan.plan_type == CommissionPlanType.FIRST_DEPOSIT:
            self._calculate_count_based(plan, metrics.get("first_deposits", 0), breakdown)

        elif plan.plan_type == CommissionPlanType.ACTIVE_USER:
            self._calculate_count_based(plan, metrics.get("active_users", 0), breakdown)

        elif plan.plan_type == CommissionPlanType.DEPOSIT_WITHDRAWAL:
            self._calculate_deposit_withdrawal(plan, statement, breakdown)

        return breakdown

    def _calculate_revenue_share(
        self,
        plan: CommissionPlan,
        statement: CommissionStatement,
        metrics: Dict,
        breakdown: PlanBreakdown,
    ) -> None:
        """
        Calculate Revenue Share commission.
        Formula: Base_RS × Rate

        Where Base_RS = Σ(NGR) or Σ(GGR) depending on base_type
        Rate is determined by fixed rate or DSR
        """
        # Determine base value
        if plan.base_type == BaseType.NGR:
            breakdown.base_value = statement.ngr
        else:  # GGR
            breakdown.base_value = statement.ggr

        # Determine rate
        if plan.rate_mode == RateMode.FIXED:
            breakdown.rate_applied = plan.fixed_rate
            breakdown.gross_commission = breakdown.base_value * breakdown.rate_applied

        else:  # DSR
            indicator_value = self._get_dsr_indicator_value(plan, statement, metrics)

            if plan.calculation_type == CalculationType.FLAT:
                # Single tier rate applied to entire base
                breakdown.rate_applied = plan.get_dsr_rate(indicator_value)
                breakdown.gross_commission = breakdown.base_value * breakdown.rate_applied

            else:  # NON_FLAT (Marginal)
                # Marginal rate per tier segment
                breakdown.gross_commission = plan.calculate_dsr_non_flat(
                    indicator_value, breakdown.base_value
                )
                # Rate is averaged for display
                if breakdown.base_value > 0:
                    breakdown.rate_applied = breakdown.gross_commission / breakdown.base_value
                else:
                    breakdown.rate_applied = Decimal("0.00")

    def _calculate_wager_rakeback(
        self,
        plan: CommissionPlan,
        statement: CommissionStatement,
        metrics: Dict,
        breakdown: PlanBreakdown,
    ) -> None:
        """
        Calculate Wager/Rakeback commission.
        Formula: Base_RB × Rate

        Where Base_RB = Σ(Total Bet) or Σ(Total Rake)
        """
        if plan.base_type == BaseType.TOTAL_BET:
            breakdown.base_value = statement.total_bets
        else:  # TOTAL_RAKE (same as total bets for simplicity)
            breakdown.base_value = statement.total_bets

        # Determine rate
        if plan.rate_mode == RateMode.FIXED:
            breakdown.rate_applied = plan.fixed_rate
        else:  # DSR
            indicator_value = self._get_dsr_indicator_value(plan, statement, metrics)
            breakdown.rate_applied = plan.get_dsr_rate(indicator_value)

        breakdown.gross_commission = breakdown.base_value * breakdown.rate_applied

    def _calculate_count_based(
        self,
        plan: CommissionPlan,
        event_count: int,
        breakdown: PlanBreakdown,
    ) -> None:
        """
        Calculate count-based commission (Signup, First Deposit, Active User).
        Formula: Event Count × Fixed Payout
        """
        breakdown.base_value = Decimal(str(event_count))
        breakdown.rate_applied = plan.fixed_payout_per_event
        breakdown.gross_commission = breakdown.base_value * plan.fixed_payout_per_event

    def _calculate_deposit_withdrawal(
        self,
        plan: CommissionPlan,
        statement: CommissionStatement,
        breakdown: PlanBreakdown,
    ) -> None:
        """
        Calculate Deposit-Withdrawal commission.
        Formula: (Deposit - Withdrawal) × Rate
        """
        deposit_net = statement.total_deposits - statement.total_withdrawals
        breakdown.base_value = deposit_net

        if plan.rate_mode == RateMode.FIXED:
            breakdown.rate_applied = plan.fixed_rate
        else:
            breakdown.rate_applied = plan.fixed_rate  # Default to fixed for simplicity

        breakdown.gross_commission = breakdown.base_value * breakdown.rate_applied

    def _get_dsr_indicator_value(
        self,
        plan: CommissionPlan,
        statement: CommissionStatement,
        metrics: Dict,
    ) -> Decimal:
        """Get the indicator value used for DSR tier determination"""
        if plan.dsr_indicator == DSRIndicator.NGR:
            return statement.ngr
        elif plan.dsr_indicator == DSRIndicator.GGR:
            return statement.ggr
        else:  # COUNT (active users)
            return Decimal(str(metrics.get("active_users", 0)))

    def calculate_multi_level_commission(
        self,
        affiliate: Affiliate,
        child_net_commission: Decimal,
    ) -> Decimal:
        """
        Calculate upline commission from child affiliate's net commission.
        Formula: ChildNetCommission × UplineRate
        """
        upline_chain = self.affiliate_service.get_upline_chain(affiliate.affiliate_id)
        total_upline_paid = Decimal("0.00")

        for upline in upline_chain:
            if upline.is_active and upline.upline_commission_rate > 0:
                upline_commission = child_net_commission * upline.upline_commission_rate
                total_upline_paid += upline_commission
                # In real system, this would be recorded as a credit to the upline

        return total_upline_paid

    def calculate_all_affiliates(
        self,
        period: CommissionPeriod,
    ) -> List[CommissionStatement]:
        """
        Calculate commission for all affiliates in the system.
        Handles multi-level commission distribution.
        """
        statements = []
        processed = set()

        # Sort affiliates so children are processed before parents
        def get_depth(affiliate: Affiliate) -> int:
            depth = 0
            current = affiliate
            while current.parent_affiliate_id:
                parent = self.affiliate_service.get_affiliate(current.parent_affiliate_id)
                if parent:
                    depth += 1
                    current = parent
                else:
                    break
            return depth

        all_affiliates = list(self.affiliate_service._affiliates.values())
        sorted_affiliates = sorted(all_affiliates, key=get_depth, reverse=True)

        child_commissions: Dict[str, Decimal] = {}  # Track child commissions for upline calc

        for affiliate in sorted_affiliates:
            if affiliate.affiliate_id in processed or not affiliate.is_active:
                continue

            statement = self.calculate_commission(affiliate, period)

            # Calculate upline commission to be paid
            if affiliate.parent_affiliate_id:
                upline_paid = self.calculate_multi_level_commission(
                    affiliate, statement.net_commission
                )
                statement.upline_commission_paid = upline_paid
                statement.final_payable = statement.net_commission - upline_paid

                # Record for parent
                if affiliate.parent_affiliate_id not in child_commissions:
                    child_commissions[affiliate.parent_affiliate_id] = Decimal("0.00")
                child_commissions[affiliate.parent_affiliate_id] += (
                    statement.net_commission * affiliate.upline_commission_rate
                    if affiliate.upline_commission_rate > 0
                    else Decimal("0.00")
                )
            else:
                statement.final_payable = statement.net_commission

            statements.append(statement)
            processed.add(affiliate.affiliate_id)

        return statements

    def recalculate_commission(
        self,
        statement: CommissionStatement,
        affiliate: Affiliate,
        updated_metrics: Dict,
    ) -> CommissionStatement:
        """
        Recalculate commission with updated metrics (e.g., after rollback).
        Only works if period is still open.
        """
        if statement.period.is_closed:
            raise ValueError("Cannot recalculate commission for closed period")

        return self.calculate_commission(
            affiliate, statement.period, metrics=updated_metrics
        )
