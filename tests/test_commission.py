"""
Tests for Commission Calculation
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from decimal import Decimal
from datetime import datetime

from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.models.user import User
from src.models.commission import CommissionPeriod
from src.services.affiliate_service import AffiliateService
from src.services.commission_calculator import CommissionCalculator
from src.utils.enums import (
    CommissionPlanType,
    BaseType,
    RateMode,
    DSRIndicator,
    CalculationType,
)


class TestRevenueShareCalculation(unittest.TestCase):
    """Test Revenue Share commission calculation"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

    def test_fixed_rate_ngr_base(self):
        """Test fixed rate revenue share with NGR base"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="Test RS",
            base_type=BaseType.NGR,
            rate_mode=RateMode.FIXED,
            fixed_rate=Decimal("0.30"),  # 30%
        )

        affiliate = Affiliate(name="Test Affiliate", commission_plans=[plan])
        self.affiliate_service.register_affiliate(affiliate)

        # Create user with known metrics
        user = User(
            username="test_user",
            affiliate_id=affiliate.affiliate_id,
            total_bets=Decimal("10000"),
            total_payouts=Decimal("8000"),
            total_bonus_used=Decimal("500"),
        )
        self.affiliate_service.register_user(user)

        # GGR = 10000 - 8000 = 2000
        # NGR = 2000 - 500 = 1500
        # Commission = 1500 * 0.30 = 450

        period = CommissionPeriod()
        statement = self.calculator.calculate_commission(affiliate, period)

        self.assertEqual(statement.ggr, Decimal("2000"))
        self.assertEqual(statement.ngr, Decimal("1500"))
        self.assertEqual(statement.total_gross_commission, Decimal("450.00"))

    def test_fixed_rate_ggr_base(self):
        """Test fixed rate revenue share with GGR base"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="Test RS GGR",
            base_type=BaseType.GGR,
            rate_mode=RateMode.FIXED,
            fixed_rate=Decimal("0.25"),
        )

        affiliate = Affiliate(name="Test Affiliate GGR", commission_plans=[plan])
        self.affiliate_service.register_affiliate(affiliate)

        user = User(
            username="test_user_ggr",
            affiliate_id=affiliate.affiliate_id,
            total_bets=Decimal("10000"),
            total_payouts=Decimal("8000"),
            total_bonus_used=Decimal("500"),
        )
        self.affiliate_service.register_user(user)

        # GGR = 10000 - 8000 = 2000
        # Commission = 2000 * 0.25 = 500

        period = CommissionPeriod()
        statement = self.calculator.calculate_commission(affiliate, period)

        self.assertEqual(statement.total_gross_commission, Decimal("500.00"))


class TestDSRCalculation(unittest.TestCase):
    """Test DSR (Dynamic Slicing Rule) calculation"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

        self.dsr_tiers = [
            DSRTier(min_value=Decimal("0"), max_value=Decimal("10000"), rate=Decimal("0.25")),
            DSRTier(min_value=Decimal("10000"), max_value=Decimal("50000"), rate=Decimal("0.30")),
            DSRTier(min_value=Decimal("50000"), max_value=None, rate=Decimal("0.35")),
        ]

    def test_dsr_flat_tier_1(self):
        """Test DSR flat calculation - tier 1"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="DSR Flat",
            base_type=BaseType.NGR,
            rate_mode=RateMode.DSR,
            dsr_indicator=DSRIndicator.NGR,
            dsr_tiers=self.dsr_tiers,
            calculation_type=CalculationType.FLAT,
        )

        # NGR = 5000, should get 25% rate
        rate = plan.get_dsr_rate(Decimal("5000"))
        self.assertEqual(rate, Decimal("0.25"))

    def test_dsr_flat_tier_2(self):
        """Test DSR flat calculation - tier 2"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="DSR Flat",
            base_type=BaseType.NGR,
            rate_mode=RateMode.DSR,
            dsr_indicator=DSRIndicator.NGR,
            dsr_tiers=self.dsr_tiers,
            calculation_type=CalculationType.FLAT,
        )

        # NGR = 25000, should get 30% rate
        rate = plan.get_dsr_rate(Decimal("25000"))
        self.assertEqual(rate, Decimal("0.30"))

    def test_dsr_flat_tier_3(self):
        """Test DSR flat calculation - tier 3 (unlimited)"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="DSR Flat",
            base_type=BaseType.NGR,
            rate_mode=RateMode.DSR,
            dsr_indicator=DSRIndicator.NGR,
            dsr_tiers=self.dsr_tiers,
            calculation_type=CalculationType.FLAT,
        )

        # NGR = 100000, should get 35% rate
        rate = plan.get_dsr_rate(Decimal("100000"))
        self.assertEqual(rate, Decimal("0.35"))

    def test_dsr_non_flat(self):
        """Test DSR non-flat (marginal) calculation"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="DSR Non-Flat",
            base_type=BaseType.NGR,
            rate_mode=RateMode.DSR,
            dsr_indicator=DSRIndicator.NGR,
            dsr_tiers=self.dsr_tiers,
            calculation_type=CalculationType.NON_FLAT,
        )

        # NGR = 30000
        # Tier 1: 0-10000 (10000) * 25% = 2500
        # Tier 2: 10000-30000 (20000) * 30% = 6000
        # Total = 8500

        commission = plan.calculate_dsr_non_flat(Decimal("30000"), Decimal("30000"))
        self.assertEqual(commission, Decimal("8500.00"))


class TestWagerCommission(unittest.TestCase):
    """Test Wager/Rakeback commission"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

    def test_wager_commission(self):
        """Test wager-based commission calculation"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.WAGER_RAKEBACK,
            name="Wager Plan",
            base_type=BaseType.TOTAL_BET,
            rate_mode=RateMode.FIXED,
            fixed_rate=Decimal("0.005"),  # 0.5%
        )

        affiliate = Affiliate(name="Wager Affiliate", commission_plans=[plan])
        self.affiliate_service.register_affiliate(affiliate)

        user = User(
            username="wager_user",
            affiliate_id=affiliate.affiliate_id,
            total_bets=Decimal("100000"),
            total_payouts=Decimal("95000"),
        )
        self.affiliate_service.register_user(user)

        # Commission = 100000 * 0.005 = 500
        period = CommissionPeriod()
        statement = self.calculator.calculate_commission(affiliate, period)

        self.assertEqual(statement.total_gross_commission, Decimal("500.000"))


class TestCountBasedCommission(unittest.TestCase):
    """Test count-based commissions (signup, first deposit, active user)"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

    def test_signup_commission(self):
        """Test signup-based commission"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.SIGNUP,
            name="Signup Bonus",
            fixed_payout_per_event=Decimal("10.00"),
        )

        affiliate = Affiliate(name="Signup Affiliate", commission_plans=[plan])
        self.affiliate_service.register_affiliate(affiliate)

        # Create 5 users (5 signups)
        for i in range(5):
            user = User(
                username=f"signup_user_{i}",
                affiliate_id=affiliate.affiliate_id,
            )
            self.affiliate_service.register_user(user)

        # Commission = 5 * 10 = 50 (but we don't track new_signups in basic flow)
        # This test validates the formula logic
        period = CommissionPeriod()
        metrics = self.affiliate_service.get_affiliate_metrics(affiliate.affiliate_id)
        metrics["new_signups"] = 5  # Override for test

        statement = self.calculator.calculate_commission(affiliate, period, metrics)
        self.assertEqual(statement.total_gross_commission, Decimal("50.00"))


class TestAdminCostDeduction(unittest.TestCase):
    """Test admin cost deduction"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

    def test_admin_cost_calculation(self):
        """Test admin cost is correctly calculated"""
        plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="Test RS",
            base_type=BaseType.NGR,
            rate_mode=RateMode.FIXED,
            fixed_rate=Decimal("0.30"),
        )

        affiliate = Affiliate(
            name="Test Affiliate",
            commission_plans=[plan],
            admin_royalty_rate=Decimal("0.05"),  # 5% admin cost
        )
        self.affiliate_service.register_affiliate(affiliate)

        user = User(
            username="test_user",
            affiliate_id=affiliate.affiliate_id,
            total_bets=Decimal("10000"),
            total_payouts=Decimal("8000"),  # GGR = 2000, NGR = 2000
        )
        self.affiliate_service.register_user(user)

        # Admin cost = NGR * 5% = 2000 * 0.05 = 100
        period = CommissionPeriod()
        statement = self.calculator.calculate_commission(affiliate, period)

        self.assertEqual(statement.admin_cost, Decimal("100.00"))
        # Gross = 600, Admin = 100, Net = 500
        self.assertEqual(statement.net_after_cost, Decimal("500.00"))


class TestHybridPlan(unittest.TestCase):
    """Test hybrid commission plans (multiple plans)"""

    def setUp(self):
        self.affiliate_service = AffiliateService()
        self.calculator = CommissionCalculator(self.affiliate_service)

    def test_hybrid_commission(self):
        """Test affiliate with multiple commission plans"""
        rs_plan = CommissionPlan(
            plan_type=CommissionPlanType.REVENUE_SHARE,
            name="Revenue Share",
            base_type=BaseType.NGR,
            rate_mode=RateMode.FIXED,
            fixed_rate=Decimal("0.20"),
        )

        signup_plan = CommissionPlan(
            plan_type=CommissionPlanType.SIGNUP,
            name="Signup Bonus",
            fixed_payout_per_event=Decimal("5.00"),
        )

        affiliate = Affiliate(
            name="Hybrid Affiliate",
            commission_plans=[rs_plan, signup_plan],
        )
        self.affiliate_service.register_affiliate(affiliate)

        user = User(
            username="hybrid_user",
            affiliate_id=affiliate.affiliate_id,
            total_bets=Decimal("5000"),
            total_payouts=Decimal("4000"),  # NGR = 1000
        )
        self.affiliate_service.register_user(user)

        period = CommissionPeriod()
        metrics = self.affiliate_service.get_affiliate_metrics(affiliate.affiliate_id)
        metrics["new_signups"] = 3

        statement = self.calculator.calculate_commission(affiliate, period, metrics)

        # RS = 1000 * 0.20 = 200
        # Signup = 3 * 5 = 15
        # Total = 215

        self.assertEqual(len(statement.plan_breakdowns), 2)
        self.assertEqual(statement.total_gross_commission, Decimal("215.00"))


if __name__ == "__main__":
    unittest.main()
