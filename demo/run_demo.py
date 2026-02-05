#!/usr/bin/env python3
"""
Demo Runner for Affiliate & Bonus System
Based on Functional Specification Document v1.0

This demo showcases:
1. Multi-level affiliate structure
2. Various commission plan types (Revenue Share, Wager, Count-based, Hybrid)
3. DSR (Dynamic Slicing Rule) with Flat and Non-Flat calculations
4. Admin cost and deductions
5. Bonus system (Deposit, Rakeback, Cashback, Special)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from decimal import Decimal

from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.models.bonus import Bonus, BonusConfig
from src.models.commission import CommissionPeriod
from src.models.user import User
from src.services.affiliate_service import AffiliateService
from src.services.commission_calculator import CommissionCalculator
from src.services.bonus_service import BonusService
from src.utils.enums import (
    CommissionPlanType,
    BaseType,
    RateMode,
    DSRIndicator,
    CalculationType,
    BonusType,
    BonusStatus,
)


def print_header(title: str) -> None:
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


def demo_affiliate_structure(affiliate_service: AffiliateService) -> dict:
    """
    Demo 1: Create multi-level affiliate structure

    Structure:
    Master Affiliate (Level 0)
    ├── Sub-Affiliate A (Level 1)
    │   ├── Sub-Sub-Affiliate A1 (Level 2)
    │   └── Sub-Sub-Affiliate A2 (Level 2)
    └── Sub-Affiliate B (Level 1)
    """
    print_header("DEMO 1: Multi-Level Affiliate Structure")

    # Create master affiliate with Revenue Share plan
    revenue_share_plan = CommissionPlan(
        plan_type=CommissionPlanType.REVENUE_SHARE,
        name="Premium Revenue Share",
        base_type=BaseType.NGR,
        rate_mode=RateMode.FIXED,
        fixed_rate=Decimal("0.35"),  # 35% revenue share
    )

    master = Affiliate(
        name="Master Affiliate Corp",
        admin_royalty_rate=Decimal("0.05"),  # 5% admin cost
        upline_commission_rate=Decimal("0.10"),  # 10% to upline
        commission_plans=[revenue_share_plan],
    )
    affiliate_service.register_affiliate(master)

    # Create sub-affiliate A with Wager plan
    wager_plan = CommissionPlan(
        plan_type=CommissionPlanType.WAGER_RAKEBACK,
        name="Wager Commission",
        base_type=BaseType.TOTAL_BET,
        rate_mode=RateMode.FIXED,
        fixed_rate=Decimal("0.005"),  # 0.5% of total wagers
    )

    sub_a = Affiliate(
        name="Sub-Affiliate A",
        parent_affiliate_id=master.affiliate_id,
        admin_royalty_rate=Decimal("0.03"),
        upline_commission_rate=Decimal("0.10"),
        commission_plans=[wager_plan],
    )
    affiliate_service.register_affiliate(sub_a)

    # Create sub-affiliate B with Count-based plans (Hybrid)
    signup_plan = CommissionPlan(
        plan_type=CommissionPlanType.SIGNUP,
        name="Signup Bonus",
        fixed_payout_per_event=Decimal("10.00"),  # $10 per signup
    )

    first_deposit_plan = CommissionPlan(
        plan_type=CommissionPlanType.FIRST_DEPOSIT,
        name="First Deposit Bonus",
        fixed_payout_per_event=Decimal("25.00"),  # $25 per first deposit
    )

    sub_b = Affiliate(
        name="Sub-Affiliate B",
        parent_affiliate_id=master.affiliate_id,
        admin_royalty_rate=Decimal("0.02"),
        commission_plans=[signup_plan, first_deposit_plan],  # Hybrid!
    )
    affiliate_service.register_affiliate(sub_b)

    # Create sub-sub affiliates
    sub_a1 = Affiliate(
        name="Sub-Sub-Affiliate A1",
        parent_affiliate_id=sub_a.affiliate_id,
        admin_royalty_rate=Decimal("0.02"),
        commission_plans=[
            CommissionPlan(
                plan_type=CommissionPlanType.REVENUE_SHARE,
                name="Basic Revenue Share",
                base_type=BaseType.NGR,
                rate_mode=RateMode.FIXED,
                fixed_rate=Decimal("0.25"),
            )
        ],
    )
    affiliate_service.register_affiliate(sub_a1)

    sub_a2 = Affiliate(
        name="Sub-Sub-Affiliate A2",
        parent_affiliate_id=sub_a.affiliate_id,
        commission_plans=[
            CommissionPlan(
                plan_type=CommissionPlanType.DEPOSIT_WITHDRAWAL,
                name="Deposit Net Plan",
                rate_mode=RateMode.FIXED,
                fixed_rate=Decimal("0.02"),  # 2% of net deposits
            )
        ],
    )
    affiliate_service.register_affiliate(sub_a2)

    # Print tree structure
    print("\nAffiliate Tree Structure:")
    print(affiliate_service.print_affiliate_tree(master.affiliate_id))

    # Show upline chain for sub_a1
    print_subheader("Upline Chain for Sub-Sub-Affiliate A1")
    upline = affiliate_service.get_upline_chain(sub_a1.affiliate_id)
    for i, aff in enumerate(upline):
        print(f"  Level {i + 1}: {aff.name}")

    return {
        "master": master,
        "sub_a": sub_a,
        "sub_b": sub_b,
        "sub_a1": sub_a1,
        "sub_a2": sub_a2,
    }


def demo_dsr_calculation(affiliate_service: AffiliateService) -> Affiliate:
    """
    Demo 2: DSR (Dynamic Slicing Rule) Commission Calculation

    Shows both Flat and Non-Flat calculation methods.
    """
    print_header("DEMO 2: DSR (Dynamic Slicing Rule) Commission")

    # Create DSR tiers
    dsr_tiers = [
        DSRTier(min_value=Decimal("0"), max_value=Decimal("10000"), rate=Decimal("0.25")),
        DSRTier(min_value=Decimal("10000"), max_value=Decimal("50000"), rate=Decimal("0.30")),
        DSRTier(min_value=Decimal("50000"), max_value=Decimal("100000"), rate=Decimal("0.35")),
        DSRTier(min_value=Decimal("100000"), max_value=None, rate=Decimal("0.40")),
    ]

    print("\nDSR Tiers Configuration:")
    for tier in dsr_tiers:
        max_str = "∞" if tier.max_value is None else f"${tier.max_value:,.2f}"
        print(f"  ${tier.min_value:,.2f} - {max_str}: {tier.rate * 100}%")

    # Create affiliate with DSR FLAT plan
    dsr_flat_plan = CommissionPlan(
        plan_type=CommissionPlanType.REVENUE_SHARE,
        name="DSR Flat Revenue Share",
        base_type=BaseType.NGR,
        rate_mode=RateMode.DSR,
        dsr_indicator=DSRIndicator.NGR,
        dsr_tiers=dsr_tiers.copy(),
        calculation_type=CalculationType.FLAT,
    )

    dsr_affiliate = Affiliate(
        name="DSR Demo Affiliate",
        admin_royalty_rate=Decimal("0.05"),
        commission_plans=[dsr_flat_plan],
    )
    affiliate_service.register_affiliate(dsr_affiliate)

    # Demonstrate FLAT calculation
    print_subheader("FLAT Calculation (single rate for entire base)")
    test_ngr_values = [Decimal("5000"), Decimal("25000"), Decimal("75000"), Decimal("150000")]

    for ngr in test_ngr_values:
        rate = dsr_flat_plan.get_dsr_rate(ngr)
        commission = ngr * rate
        print(f"  NGR ${ngr:,.2f} → Rate: {rate * 100}% → Commission: ${commission:,.2f}")

    # Create affiliate with DSR NON-FLAT plan
    dsr_nonflat_plan = CommissionPlan(
        plan_type=CommissionPlanType.REVENUE_SHARE,
        name="DSR Non-Flat Revenue Share",
        base_type=BaseType.NGR,
        rate_mode=RateMode.DSR,
        dsr_indicator=DSRIndicator.NGR,
        dsr_tiers=dsr_tiers.copy(),
        calculation_type=CalculationType.NON_FLAT,
    )

    # Demonstrate NON-FLAT (Marginal) calculation
    print_subheader("NON-FLAT Calculation (marginal rate per tier)")
    print("  NGR $75,000 breakdown:")
    print("    $0 - $10,000 (10k) × 25% = $2,500")
    print("    $10,000 - $50,000 (40k) × 30% = $12,000")
    print("    $50,000 - $75,000 (25k) × 35% = $8,750")
    print("    Total Commission = $23,250")

    ngr = Decimal("75000")
    nonflat_commission = dsr_nonflat_plan.calculate_dsr_non_flat(ngr, ngr)
    print(f"\n  Calculated: ${nonflat_commission:,.2f}")

    return dsr_affiliate


def demo_users_and_transactions(
    affiliate_service: AffiliateService,
    affiliates: dict,
) -> list:
    """
    Demo 3: Create users and simulate transactions
    """
    print_header("DEMO 3: Users and Transaction Simulation")

    users = []

    # Create users for Master affiliate
    for i in range(3):
        user = User(
            username=f"master_player_{i+1}",
            affiliate_id=affiliates["master"].affiliate_id,
            total_bets=Decimal(str(10000 + i * 5000)),
            total_payouts=Decimal(str(8000 + i * 4000)),
            total_deposits=Decimal(str(5000 + i * 2000)),
            total_withdrawals=Decimal(str(2000 + i * 1000)),
            total_bonus_used=Decimal(str(200 + i * 100)),
            is_active=True,
        )
        user.first_deposit_date = datetime.now() - timedelta(days=30)
        affiliate_service.register_user(user)
        users.append(user)

    # Create users for Sub-Affiliate A
    for i in range(5):
        user = User(
            username=f"sub_a_player_{i+1}",
            affiliate_id=affiliates["sub_a"].affiliate_id,
            total_bets=Decimal(str(20000 + i * 3000)),
            total_payouts=Decimal(str(18000 + i * 2500)),
            total_deposits=Decimal(str(8000 + i * 1000)),
            total_withdrawals=Decimal(str(3000 + i * 500)),
            total_bonus_used=Decimal(str(500 + i * 50)),
            is_active=i % 2 == 0,  # Some active, some not
        )
        if i < 3:
            user.first_deposit_date = datetime.now() - timedelta(days=15)
        affiliate_service.register_user(user)
        users.append(user)

    # Create users for Sub-Affiliate B (count-based plans)
    for i in range(4):
        user = User(
            username=f"sub_b_player_{i+1}",
            affiliate_id=affiliates["sub_b"].affiliate_id,
            total_bets=Decimal(str(5000)),
            total_payouts=Decimal(str(4500)),
            is_active=True,
        )
        if i < 2:
            user.first_deposit_date = datetime.now() - timedelta(days=5)
        affiliate_service.register_user(user)
        users.append(user)

    # Print user summary
    print("\nUsers Created:")
    for aff_name, aff in affiliates.items():
        aff_users = affiliate_service.get_affiliate_users(aff.affiliate_id)
        if aff_users:
            print(f"\n  {aff.name}:")
            for user in aff_users:
                print(f"    - {user.username}: Bets=${user.total_bets:,.2f}, GGR=${user.ggr:,.2f}")

    return users


def demo_commission_calculation(
    affiliate_service: AffiliateService,
    commission_calculator: CommissionCalculator,
    affiliates: dict,
) -> None:
    """
    Demo 4: Calculate commissions for all affiliates
    """
    print_header("DEMO 4: Commission Calculation")

    # Create commission period (current month)
    period = CommissionPeriod(
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 2, 28),
    )

    print(f"\nCommission Period: {period.start_date.date()} to {period.end_date.date()}")

    # Calculate for each affiliate
    for aff_name, affiliate in affiliates.items():
        if not affiliate.is_active:
            continue

        metrics = affiliate_service.get_affiliate_metrics(affiliate.affiliate_id)
        if metrics["total_users"] == 0:
            continue

        statement = commission_calculator.calculate_commission(affiliate, period, metrics)

        print_subheader(f"Commission Statement: {affiliate.name}")
        print(f"  Players: {statement.total_players} (Active: {statement.active_players})")
        print(f"  Total Bets: ${statement.total_bets:,.2f}")
        print(f"  Total Payouts: ${statement.total_payouts:,.2f}")
        print(f"  GGR: ${statement.ggr:,.2f}")
        print(f"  NGR: ${statement.ngr:,.2f}")

        print("\n  Commission Breakdown:")
        for breakdown in statement.plan_breakdowns:
            print(f"    [{breakdown.plan_type}] {breakdown.plan_name}:")
            print(f"      Base: ${breakdown.base_value:,.2f}")
            print(f"      Rate: {breakdown.rate_applied * 100:.2f}%")
            print(f"      Gross: ${breakdown.gross_commission:,.2f}")

        print(f"\n  Total Gross Commission: ${statement.total_gross_commission:,.2f}")
        print(f"  Admin Cost ({affiliate.admin_royalty_rate * 100:.1f}%): -${statement.admin_cost:,.2f}")
        print(f"  Net After Cost: ${statement.net_after_cost:,.2f}")
        print(f"  Manual Adjustment: ${statement.manual_adjustment:,.2f}")
        print(f"  Net Commission: ${statement.net_commission:,.2f}")


def demo_bonus_system(bonus_service: BonusService, users: list) -> None:
    """
    Demo 5: Bonus System
    """
    print_header("DEMO 5: Bonus System")

    # Configure bonus rules
    deposit_config = BonusConfig(
        bonus_type=BonusType.DEPOSIT,
        name="Welcome Deposit Bonus",
        rate=Decimal("0.100"),  # 100% match
        max_bonus=Decimal("500.00"),
        min_trigger_amount=Decimal("50.00"),
        wagering_requirement=Decimal("30"),  # 30x wagering
        expiry_days=30,
    )
    bonus_service.register_bonus_config(deposit_config)

    rakeback_config = BonusConfig(
        bonus_type=BonusType.RAKEBACK,
        name="VIP Rakeback",
        rate=Decimal("0.005"),  # 0.5% rakeback
        expiry_days=7,
    )
    bonus_service.register_bonus_config(rakeback_config)

    cashback_config = BonusConfig(
        bonus_type=BonusType.CASHBACK,
        name="Weekly Cashback",
        rate=Decimal("0.10"),  # 10% cashback on losses
        expiry_days=7,
    )
    bonus_service.register_bonus_config(cashback_config)

    print("\nBonus Configurations:")
    print(f"  1. {deposit_config.name}: {deposit_config.rate * 100}% match up to ${deposit_config.max_bonus}")
    print(f"     Wagering: {deposit_config.wagering_requirement}x, Expires: {deposit_config.expiry_days} days")
    print(f"  2. {rakeback_config.name}: {rakeback_config.rate * 100}% of wagers")
    print(f"  3. {cashback_config.name}: {cashback_config.rate * 100}% of net losses")

    # Issue bonuses to users
    if users:
        user = users[0]

        print_subheader(f"Issuing Bonuses to {user.username}")

        # Deposit bonus
        deposit_bonus = bonus_service.issue_deposit_bonus(
            user, Decimal("1000.00"), deposit_config
        )
        if deposit_bonus:
            print(f"  Deposit Bonus: ${deposit_bonus.amount:,.2f}")
            print(f"    Wagering Required: ${deposit_bonus.wagering_requirement:,.2f}")
            print(f"    Status: {deposit_bonus.status.value}")

        # Rakeback accumulation
        bonus_service.accumulate_rakeback(user, Decimal("5000.00"), rakeback_config)
        rakeback_bonus = bonus_service._find_active_rakeback(user.user_id)
        if rakeback_bonus:
            print(f"  Rakeback Accumulated: ${rakeback_bonus.amount:,.2f}")
            print(f"    Status: {rakeback_bonus.status.value}")

        # Cashback
        cashback_bonus = bonus_service.issue_cashback_bonus(user, cashback_config)
        if cashback_bonus:
            print(f"  Cashback Bonus: ${cashback_bonus.amount:,.2f}")
            print(f"    Based on Net Loss: ${user.net_loss:,.2f}")

        # Special bonus from admin
        special_bonus = bonus_service.issue_special_bonus(
            user,
            amount=Decimal("100.00"),
            admin_id="admin_001",
            admin_note="VIP reward for loyalty",
            wagering_requirement=Decimal("10"),  # 10x wagering
        )
        print(f"  Special Bonus: ${special_bonus.amount:,.2f}")
        print(f"    Note: {special_bonus.admin_note}")

        # Wagering progress simulation
        print_subheader("Wagering Progress Simulation")
        print(f"  Simulating ${10000:,.2f} in bets...")

        # Update wagering for active bonuses
        now_claimable = bonus_service.update_wagering_progress(
            user.user_id, Decimal("10000.00")
        )

        if now_claimable:
            print(f"  Bonuses now claimable: {len(now_claimable)}")
            for b in now_claimable:
                print(f"    - {b.bonus_type.value}: ${b.amount:,.2f}")

        # Show user's bonuses
        print_subheader(f"All Bonuses for {user.username}")
        all_bonuses = bonus_service.get_user_bonuses(user.user_id)
        for bonus in all_bonuses:
            wr_str = ""
            if bonus.wagering_requirement:
                wr_str = f" (WR: {bonus.wagering_progress:.0f}/{bonus.wagering_requirement:.0f})"
            print(f"  {bonus.bonus_type.value}: ${bonus.amount:,.2f} - {bonus.status.value}{wr_str}")

    # Bonus statistics
    print_subheader("Bonus Statistics")
    stats = bonus_service.get_bonus_statistics()
    print(f"  Total Issued: ${stats['total_issued']:,.2f}")
    print(f"  Total Pending: ${stats['total_pending']:,.2f}")
    print(f"  By Type:")
    for type_name, amount in stats['by_type'].items():
        if amount > 0:
            print(f"    {type_name}: ${amount:,.2f}")


def demo_manual_adjustment(
    affiliate_service: AffiliateService,
    commission_calculator: CommissionCalculator,
    affiliates: dict,
) -> None:
    """
    Demo 6: Manual Adjustment
    """
    print_header("DEMO 6: Manual Adjustment")

    master = affiliates["master"]

    # Set manual adjustment
    print(f"\nSetting manual adjustment of +$500.00 for {master.name}")
    affiliate_service.set_manual_adjustment(master.affiliate_id, Decimal("500.00"))

    # Recalculate commission
    period = CommissionPeriod(
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 2, 28),
    )

    metrics = affiliate_service.get_affiliate_metrics(master.affiliate_id)
    statement = commission_calculator.calculate_commission(master, period, metrics)

    print(f"\n  Net After Cost: ${statement.net_after_cost:,.2f}")
    print(f"  Manual Adjustment: +${statement.manual_adjustment:,.2f}")
    print(f"  Final Net Commission: ${statement.net_commission:,.2f}")


def demo_multi_level_commission(
    affiliate_service: AffiliateService,
    commission_calculator: CommissionCalculator,
    affiliates: dict,
) -> None:
    """
    Demo 7: Multi-Level Commission Distribution
    """
    print_header("DEMO 7: Multi-Level Commission Distribution")

    sub_a = affiliates["sub_a"]
    master = affiliates["master"]

    period = CommissionPeriod(
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 2, 28),
    )

    # Calculate Sub-A's commission
    metrics = affiliate_service.get_affiliate_metrics(sub_a.affiliate_id)
    if metrics["total_users"] > 0:
        statement = commission_calculator.calculate_commission(sub_a, period, metrics)

        print(f"\n{sub_a.name} Commission:")
        print(f"  Net Commission: ${statement.net_commission:,.2f}")

        # Calculate upline commission
        upline_rate = sub_a.upline_commission_rate
        upline_commission = statement.net_commission * upline_rate

        print(f"\nUpline Commission to {master.name}:")
        print(f"  Rate: {upline_rate * 100:.1f}%")
        print(f"  Amount: ${upline_commission:,.2f}")

        statement.upline_commission_paid = upline_commission
        statement.final_payable = statement.net_commission - upline_commission

        print(f"\n{sub_a.name} Final Payable:")
        print(f"  Net Commission: ${statement.net_commission:,.2f}")
        print(f"  Less Upline: -${statement.upline_commission_paid:,.2f}")
        print(f"  Final Payable: ${statement.final_payable:,.2f}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print(" AFFILIATE & BONUS SYSTEM DEMO")
    print(" Based on Functional Specification Document v1.0")
    print("=" * 70)

    # Initialize services
    affiliate_service = AffiliateService()
    commission_calculator = CommissionCalculator(affiliate_service)
    bonus_service = BonusService()

    # Run demos
    affiliates = demo_affiliate_structure(affiliate_service)
    dsr_affiliate = demo_dsr_calculation(affiliate_service)
    affiliates["dsr"] = dsr_affiliate

    users = demo_users_and_transactions(affiliate_service, affiliates)
    demo_commission_calculation(affiliate_service, commission_calculator, affiliates)
    demo_bonus_system(bonus_service, users)
    demo_manual_adjustment(affiliate_service, commission_calculator, affiliates)
    demo_multi_level_commission(affiliate_service, commission_calculator, affiliates)

    print("\n" + "=" * 70)
    print(" DEMO COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
