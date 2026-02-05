"""
State management for the Streamlit app
Initializes services and demo data
"""

import streamlit as st
from datetime import datetime, timedelta
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.models.bonus import BonusConfig
from src.models.commission import CommissionPeriod
from src.models.user import User
from src.services.affiliate_service import AffiliateService
from src.services.commission_calculator import CommissionCalculator
from src.services.bonus_service import BonusService
from src.utils.enums import (
    CommissionPlanType, BaseType, RateMode, DSRIndicator,
    CalculationType, BonusType, BonusStatus
)


def initialize_state():
    """Initialize session state with services and demo data"""

    if 'initialized' not in st.session_state:
        # Initialize services
        st.session_state.affiliate_service = AffiliateService()
        st.session_state.commission_calculator = CommissionCalculator(st.session_state.affiliate_service)
        st.session_state.bonus_service = BonusService()

        # Load demo data
        _load_demo_data()

        st.session_state.initialized = True


def _load_demo_data():
    """Load comprehensive demo data for showcase"""

    aff_service = st.session_state.affiliate_service
    bonus_service = st.session_state.bonus_service

    # ==================== Create Affiliates ====================

    # 1. Master Affiliate with Revenue Share DSR
    dsr_tiers = [
        DSRTier(min_value=Decimal("0"), max_value=Decimal("10000"), rate=Decimal("0.25")),
        DSRTier(min_value=Decimal("10000"), max_value=Decimal("50000"), rate=Decimal("0.30")),
        DSRTier(min_value=Decimal("50000"), max_value=Decimal("100000"), rate=Decimal("0.35")),
        DSRTier(min_value=Decimal("100000"), max_value=None, rate=Decimal("0.40")),
    ]

    master_plan = CommissionPlan(
        plan_type=CommissionPlanType.REVENUE_SHARE,
        name="Premium Revenue Share (DSR)",
        base_type=BaseType.NGR,
        rate_mode=RateMode.DSR,
        dsr_indicator=DSRIndicator.NGR,
        dsr_tiers=dsr_tiers,
        calculation_type=CalculationType.FLAT,
    )

    master = Affiliate(
        name="Master Agency Corp",
        admin_royalty_rate=Decimal("0.05"),
        upline_commission_rate=Decimal("0.10"),
        commission_plans=[master_plan],
    )
    aff_service.register_affiliate(master)
    st.session_state.master_affiliate_id = master.affiliate_id

    # 2. Sub-Affiliate A - Wager based
    wager_plan = CommissionPlan(
        plan_type=CommissionPlanType.WAGER_RAKEBACK,
        name="Wager Commission",
        base_type=BaseType.TOTAL_BET,
        rate_mode=RateMode.FIXED,
        fixed_rate=Decimal("0.005"),
    )

    sub_a = Affiliate(
        name="Agency Alpha",
        parent_affiliate_id=master.affiliate_id,
        admin_royalty_rate=Decimal("0.03"),
        upline_commission_rate=Decimal("0.10"),
        commission_plans=[wager_plan],
    )
    aff_service.register_affiliate(sub_a)

    # 3. Sub-Affiliate B - Hybrid (Signup + First Deposit)
    signup_plan = CommissionPlan(
        plan_type=CommissionPlanType.SIGNUP,
        name="Signup Bonus",
        fixed_payout_per_event=Decimal("15.00"),
    )

    fd_plan = CommissionPlan(
        plan_type=CommissionPlanType.FIRST_DEPOSIT,
        name="First Deposit Bonus",
        fixed_payout_per_event=Decimal("50.00"),
    )

    sub_b = Affiliate(
        name="Agency Beta",
        parent_affiliate_id=master.affiliate_id,
        admin_royalty_rate=Decimal("0.02"),
        commission_plans=[signup_plan, fd_plan],
    )
    aff_service.register_affiliate(sub_b)

    # 4. Sub-Sub Affiliate under Alpha
    rs_plan = CommissionPlan(
        plan_type=CommissionPlanType.REVENUE_SHARE,
        name="Standard Revenue Share",
        base_type=BaseType.NGR,
        rate_mode=RateMode.FIXED,
        fixed_rate=Decimal("0.25"),
    )

    sub_a1 = Affiliate(
        name="Agent A1",
        parent_affiliate_id=sub_a.affiliate_id,
        admin_royalty_rate=Decimal("0.02"),
        commission_plans=[rs_plan],
    )
    aff_service.register_affiliate(sub_a1)

    sub_a2 = Affiliate(
        name="Agent A2",
        parent_affiliate_id=sub_a.affiliate_id,
        admin_royalty_rate=Decimal("0.02"),
        commission_plans=[rs_plan],
    )
    aff_service.register_affiliate(sub_a2)

    # ==================== Create Users ====================

    # Users for Master
    for i in range(5):
        user = User(
            username=f"master_vip_{i+1}",
            affiliate_id=master.affiliate_id,
            total_bets=Decimal(str(50000 + i * 20000)),
            total_payouts=Decimal(str(45000 + i * 18000)),
            total_deposits=Decimal(str(20000 + i * 5000)),
            total_withdrawals=Decimal(str(8000 + i * 2000)),
            total_bonus_used=Decimal(str(1000 + i * 200)),
            is_active=True,
        )
        user.first_deposit_date = datetime.now() - timedelta(days=60)
        aff_service.register_user(user)

    # Users for Sub-A
    for i in range(8):
        user = User(
            username=f"alpha_player_{i+1}",
            affiliate_id=sub_a.affiliate_id,
            total_bets=Decimal(str(30000 + i * 10000)),
            total_payouts=Decimal(str(27000 + i * 9000)),
            total_deposits=Decimal(str(15000 + i * 3000)),
            total_withdrawals=Decimal(str(5000 + i * 1000)),
            total_bonus_used=Decimal(str(500 + i * 100)),
            is_active=i % 3 != 0,
        )
        if i < 5:
            user.first_deposit_date = datetime.now() - timedelta(days=30)
        aff_service.register_user(user)

    # Users for Sub-B
    for i in range(6):
        user = User(
            username=f"beta_player_{i+1}",
            affiliate_id=sub_b.affiliate_id,
            total_bets=Decimal(str(10000 + i * 5000)),
            total_payouts=Decimal(str(9000 + i * 4500)),
            total_deposits=Decimal(str(5000 + i * 1000)),
            total_withdrawals=Decimal(str(2000 + i * 500)),
            is_active=True,
        )
        if i < 4:
            user.first_deposit_date = datetime.now() - timedelta(days=15)
        aff_service.register_user(user)

    # Users for Sub-A1
    for i in range(3):
        user = User(
            username=f"agent_a1_player_{i+1}",
            affiliate_id=sub_a1.affiliate_id,
            total_bets=Decimal(str(20000 + i * 8000)),
            total_payouts=Decimal(str(18000 + i * 7000)),
            total_deposits=Decimal(str(10000 + i * 2000)),
            total_withdrawals=Decimal(str(3000 + i * 500)),
            is_active=True,
        )
        user.first_deposit_date = datetime.now() - timedelta(days=20)
        aff_service.register_user(user)

    # ==================== Configure Bonus ====================

    # Deposit Bonus
    deposit_config = BonusConfig(
        bonus_type=BonusType.DEPOSIT,
        name="Welcome Deposit Bonus",
        rate=Decimal("1.00"),
        max_bonus=Decimal("500.00"),
        min_trigger_amount=Decimal("50.00"),
        wagering_requirement=Decimal("30"),
        expiry_days=30,
    )
    bonus_service.register_bonus_config(deposit_config)
    st.session_state.deposit_bonus_config_id = deposit_config.config_id

    # Rakeback
    rakeback_config = BonusConfig(
        bonus_type=BonusType.RAKEBACK,
        name="VIP Rakeback",
        rate=Decimal("0.005"),
        expiry_days=7,
    )
    bonus_service.register_bonus_config(rakeback_config)
    st.session_state.rakeback_config_id = rakeback_config.config_id

    # Cashback
    cashback_config = BonusConfig(
        bonus_type=BonusType.CASHBACK,
        name="Weekly Cashback",
        rate=Decimal("0.10"),
        expiry_days=7,
    )
    bonus_service.register_bonus_config(cashback_config)
    st.session_state.cashback_config_id = cashback_config.config_id

    # Issue some demo bonuses
    users = list(aff_service._users.values())[:5]
    for user in users:
        # Deposit bonus
        bonus_service.issue_deposit_bonus(user, Decimal("200.00"), deposit_config)
        # Rakeback
        bonus_service.accumulate_rakeback(user, user.total_bets, rakeback_config)
        # Cashback for those with losses
        if user.net_loss > 0:
            bonus_service.issue_cashback_bonus(user, cashback_config)

    # Store commission period
    st.session_state.current_period = CommissionPeriod(
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 2, 28),
    )


def reset_demo_data():
    """Reset all demo data"""
    if 'initialized' in st.session_state:
        del st.session_state.initialized
    initialize_state()
