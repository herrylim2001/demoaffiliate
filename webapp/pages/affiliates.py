"""
Affiliates page - Manage and view affiliates
Enhanced with comprehensive commission plan configuration
"""

import streamlit as st
import pandas as pd
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.utils.enums import (
    CommissionPlanType, BaseType, RateMode, DSRIndicator, CalculationType, PeriodType
)


def render():
    """Render the affiliates page"""

    st.markdown("<h1 class='main-header'>Affiliate Management</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>View and manage affiliate network</p>", unsafe_allow_html=True)
    st.markdown("---")

    aff_service = st.session_state.affiliate_service

    tab1, tab2, tab3 = st.tabs(["📋 Affiliate List", "➕ Create Affiliate", "🔍 Affiliate Details"])

    # ==================== Tab 1: Affiliate List ====================
    with tab1:
        st.subheader("All Affiliates")

        # Build affiliate table
        aff_data = []
        for aff in aff_service._affiliates.values():
            metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
            parent_name = ""
            if aff.parent_affiliate_id:
                parent = aff_service.get_affiliate(aff.parent_affiliate_id)
                parent_name = parent.name if parent else ""

            plan_names = ", ".join([p.name for p in aff.commission_plans])

            aff_data.append({
                "ID": aff.affiliate_id[:8] + "...",
                "Name": aff.name,
                "Parent": parent_name or "-",
                "Status": aff.status.value.title(),
                "Plans": plan_names[:30] + ("..." if len(plan_names) > 30 else ""),
                "Players": metrics['total_users'],
                "Active": metrics['active_users'],
                "GGR": f"${metrics['ggr']:,.2f}",
                "NGR": f"${metrics['ngr']:,.2f}",
                "Admin Rate": f"{aff.admin_royalty_rate * 100:.1f}%",
            })

        if aff_data:
            df = pd.DataFrame(aff_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No affiliates found. Create one to get started.")

        # Tree Structure
        st.markdown("---")
        st.subheader("Network Tree")

        master_id = st.session_state.get('master_affiliate_id')
        if master_id:
            tree_text = aff_service.print_affiliate_tree(master_id)
            st.code(tree_text, language=None)

    # ==================== Tab 2: Create Affiliate ====================
    with tab2:
        render_create_affiliate_form(aff_service)

    # ==================== Tab 3: Affiliate Details ====================
    with tab3:
        render_affiliate_details(aff_service)


def render_create_affiliate_form(aff_service):
    """Render comprehensive create affiliate form"""

    st.subheader("Create New Affiliate")

    # Info box about the form
    st.info("""
    **Form ini sesuai dengan Functional Specification Document (FSD) v1.0**

    Konfigurasi lengkap untuk affiliate termasuk:
    - Basic Info & Hierarchy
    - Commission Settings (Admin Cost, Deductions)
    - Commission Plan (Fixed Rate atau DSR dengan Flat/Non-Flat)
    """)

    # ==================== SECTION 1: Basic Information ====================
    st.markdown("### 1️⃣ Basic Information")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            "Affiliate Name *",
            placeholder="e.g., Agency XYZ",
            help="Unique identifier name for the affiliate"
        )

        # Parent selection
        parent_options = {"None (Top Level)": None}
        for aff in aff_service._affiliates.values():
            parent_options[aff.name] = aff.affiliate_id

        parent_select = st.selectbox(
            "Parent Affiliate",
            options=list(parent_options.keys()),
            help="Select parent affiliate for multi-level structure. Depth is unlimited."
        )
        parent_id = parent_options[parent_select]

    with col2:
        status = st.selectbox(
            "Status",
            options=["Active", "Suspended"],
            help="Active affiliates can earn commissions"
        )

        period_type = st.selectbox(
            "Commission Period Type",
            options=["Calendar Month", "From Signup Date", "Custom"],
            help="How commission periods are calculated"
        )

    # ==================== SECTION 2: Commission Settings ====================
    st.markdown("---")
    st.markdown("### 2️⃣ Commission Settings")
    st.caption("Pengaturan admin cost dan deductions yang akan diterapkan pada perhitungan komisi")

    col1, col2, col3 = st.columns(3)

    with col1:
        admin_rate = st.number_input(
            "Admin Royalty Rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=5.0,
            step=0.5,
            help="Percentage of NGR deducted as admin cost"
        )
        st.caption("Formula: `AdminCost = NGR × Rate`")

    with col2:
        upline_rate = st.number_input(
            "Upline Commission Rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Percentage of net commission paid to upline"
        )
        st.caption("Formula: `UplineComm = NetComm × Rate`")

    with col3:
        manual_adj = st.number_input(
            "Manual Adjustment ($)",
            value=0.0,
            step=100.0,
            help="Fixed amount added/subtracted from final commission (can be negative)"
        )
        st.caption("Applied after all calculations")

    col1, col2 = st.columns(2)

    with col1:
        bonus_deduction = st.number_input(
            "Bonus Deduction ($)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="Fixed bonus amount to deduct from commission"
        )

    with col2:
        balance_deduction = st.number_input(
            "Balance Deduction ($)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="Carryover negative balance from previous period"
        )

    # ==================== SECTION 3: Commission Plan ====================
    st.markdown("---")
    st.markdown("### 3️⃣ Commission Plan Configuration")

    # Plan Type Selection
    plan_type = st.selectbox(
        "Plan Type *",
        options=[
            "Revenue Share",
            "Wager/Rakeback",
            "Signup (Count-based)",
            "First Deposit (Count-based)",
            "Active User (Count-based)",
            "Deposit - Withdrawal"
        ],
        help="Type of commission calculation method"
    )

    plan_name = st.text_input(
        "Plan Name",
        value=f"{plan_type.split(' (')[0]} Plan",
        help="Descriptive name for this commission plan"
    )

    # Show different fields based on plan type
    is_count_based = "Count-based" in plan_type
    is_rate_based = plan_type in ["Revenue Share", "Wager/Rakeback", "Deposit - Withdrawal"]

    # ========== COUNT-BASED PLANS ==========
    if is_count_based:
        st.markdown("#### Count-Based Configuration")
        st.info("💡 **Count-based plans** memberikan fixed payout untuk setiap event (signup, first deposit, atau active user)")

        col1, col2 = st.columns(2)
        with col1:
            fixed_payout = st.number_input(
                "Fixed Payout per Event ($) *",
                min_value=0.0,
                value=25.0,
                step=5.0,
                help="Amount paid for each qualifying event"
            )
        with col2:
            st.markdown("**Formula:**")
            st.code("Gross Commission = Event Count × Fixed Payout", language=None)

        # Preview
        st.markdown("##### Preview Calculation")
        preview_count = st.slider("Example Event Count", 0, 100, 10)
        preview_commission = preview_count * fixed_payout
        st.success(f"**{preview_count} events × ${fixed_payout:.2f} = ${preview_commission:.2f}**")

    # ========== RATE-BASED PLANS ==========
    if is_rate_based:
        st.markdown("#### Rate-Based Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Base Type
            if plan_type == "Revenue Share":
                base_type = st.selectbox(
                    "Base Type *",
                    options=["NGR (Net Gaming Revenue)", "GGR (Gross Gaming Revenue)"],
                    help="Base value for commission calculation"
                )
                st.caption("""
                - **GGR** = Total Bet - Total Payout
                - **NGR** = GGR - Bonus Cost
                """)
            elif plan_type == "Wager/Rakeback":
                base_type = st.selectbox(
                    "Base Type *",
                    options=["Total Bet", "Total Rake"],
                    help="Base value for wager/rakeback calculation"
                )
            else:  # Deposit - Withdrawal
                base_type = "Deposit Net"
                st.info("**Base:** Deposit - Withdrawal")

        with col2:
            # Rate Mode
            rate_mode = st.selectbox(
                "Rate Mode *",
                options=["Fixed Rate", "DSR (Dynamic Slicing Rule)"],
                help="Fixed applies single rate; DSR applies tier-based rates"
            )

        # ========== FIXED RATE MODE ==========
        if rate_mode == "Fixed Rate":
            st.markdown("##### Fixed Rate Configuration")

            col1, col2 = st.columns(2)
            with col1:
                fixed_rate = st.number_input(
                    "Commission Rate (%) *",
                    min_value=0.0,
                    max_value=100.0,
                    value=25.0,
                    step=1.0,
                    help="Single rate applied to entire base"
                )

            with col2:
                st.markdown("**Formula:**")
                st.code(f"Gross Commission = Base × {fixed_rate}%", language=None)

            # Preview
            st.markdown("##### Preview Calculation")
            preview_base = st.number_input("Example Base Value ($)", value=50000.0, step=1000.0)
            preview_commission = preview_base * (fixed_rate / 100)
            st.success(f"**${preview_base:,.2f} × {fixed_rate}% = ${preview_commission:,.2f}**")

        # ========== DSR MODE ==========
        else:  # DSR
            st.markdown("##### DSR (Dynamic Slicing Rule) Configuration")

            st.warning("""
            **DSR** memungkinkan rate berbeda berdasarkan tier/level revenue:
            - **FLAT**: Rate tier yang dicapai diterapkan ke seluruh base
            - **NON-FLAT (Marginal)**: Setiap segment base dikalikan rate tier masing-masing
            """)

            col1, col2 = st.columns(2)

            with col1:
                dsr_indicator = st.selectbox(
                    "DSR Indicator *",
                    options=["NGR", "GGR", "Player Count"],
                    help="Value used to determine which tier applies"
                )

            with col2:
                calculation_type = st.selectbox(
                    "Calculation Type *",
                    options=["FLAT", "NON-FLAT (Marginal)"],
                    help="How the rate is applied to the base value"
                )

            # Explanation
            with st.expander("📖 Penjelasan FLAT vs NON-FLAT", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    **FLAT Calculation:**
                    - Cari tier berdasarkan indicator value
                    - Terapkan rate tier tersebut ke **seluruh** base

                    Contoh (NGR = $75,000):
                    - Tier: $50k-$100k = 35%
                    - Commission = $75,000 × 35% = **$26,250**
                    """)
                with col2:
                    st.markdown("""
                    **NON-FLAT (Marginal) Calculation:**
                    - Bagi base ke setiap tier segment
                    - Terapkan rate masing-masing tier

                    Contoh (NGR = $75,000):
                    - $0-$10k × 25% = $2,500
                    - $10k-$50k × 30% = $12,000
                    - $50k-$75k × 35% = $8,750
                    - Total = **$23,250**
                    """)

            # DSR Tiers Configuration
            st.markdown("##### DSR Tiers Configuration")

            num_tiers = st.number_input(
                "Number of Tiers",
                min_value=1,
                max_value=10,
                value=4,
                help="Configure rate tiers"
            )

            # Initialize tiers in session state if not exists
            if 'dsr_tiers_config' not in st.session_state:
                st.session_state.dsr_tiers_config = [
                    {"min": 0, "max": 10000, "rate": 25.0},
                    {"min": 10000, "max": 50000, "rate": 30.0},
                    {"min": 50000, "max": 100000, "rate": 35.0},
                    {"min": 100000, "max": None, "rate": 40.0},
                ]

            # Adjust tiers list
            while len(st.session_state.dsr_tiers_config) < num_tiers:
                last_max = st.session_state.dsr_tiers_config[-1]["max"] or st.session_state.dsr_tiers_config[-1]["min"] + 50000
                st.session_state.dsr_tiers_config.append({
                    "min": last_max,
                    "max": last_max + 50000,
                    "rate": 40.0
                })
            while len(st.session_state.dsr_tiers_config) > num_tiers:
                st.session_state.dsr_tiers_config.pop()

            # Tier inputs
            tiers_data = []

            for i in range(int(num_tiers)):
                st.markdown(f"**Tier {i + 1}**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    min_val = st.number_input(
                        f"Min Value ($)",
                        min_value=0.0,
                        value=float(st.session_state.dsr_tiers_config[i]["min"]),
                        step=1000.0,
                        key=f"tier_{i}_min"
                    )

                with col2:
                    is_unlimited = i == num_tiers - 1
                    if is_unlimited:
                        max_val = st.text_input(
                            f"Max Value ($)",
                            value="∞ (Unlimited)",
                            disabled=True,
                            key=f"tier_{i}_max"
                        )
                        max_val_num = None
                    else:
                        max_val_num = st.number_input(
                            f"Max Value ($)",
                            min_value=0.0,
                            value=float(st.session_state.dsr_tiers_config[i]["max"] or 100000),
                            step=1000.0,
                            key=f"tier_{i}_max_num"
                        )

                with col3:
                    rate = st.number_input(
                        f"Rate (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(st.session_state.dsr_tiers_config[i]["rate"]),
                        step=1.0,
                        key=f"tier_{i}_rate"
                    )

                tiers_data.append({
                    "min": min_val,
                    "max": max_val_num if not is_unlimited else None,
                    "rate": rate
                })

            # Update session state
            st.session_state.dsr_tiers_config = tiers_data

            # DSR Preview/Simulator
            st.markdown("---")
            st.markdown("##### DSR Calculation Preview")

            preview_ngr = st.number_input(
                "Example NGR Value ($)",
                value=75000.0,
                step=5000.0,
                key="dsr_preview_ngr"
            )

            # Calculate FLAT
            flat_rate = 0
            for tier in tiers_data:
                tier_max = tier["max"] if tier["max"] else float('inf')
                if tier["min"] <= preview_ngr < tier_max or (tier["max"] is None and preview_ngr >= tier["min"]):
                    flat_rate = tier["rate"]
                    break
            flat_commission = preview_ngr * (flat_rate / 100)

            # Calculate NON-FLAT
            nonflat_commission = 0
            nonflat_breakdown = []
            remaining = preview_ngr

            for tier in tiers_data:
                if remaining <= 0:
                    break

                tier_min = tier["min"]
                tier_max = tier["max"] if tier["max"] else preview_ngr
                tier_rate = tier["rate"]

                if preview_ngr > tier_min:
                    segment = min(remaining, tier_max - tier_min) if tier["max"] else remaining
                    if segment > 0:
                        segment_commission = segment * (tier_rate / 100)
                        nonflat_commission += segment_commission
                        nonflat_breakdown.append({
                            "range": f"${tier_min:,.0f} - ${tier_max:,.0f}" if tier["max"] else f"${tier_min:,.0f}+",
                            "segment": segment,
                            "rate": tier_rate,
                            "commission": segment_commission
                        })
                        remaining -= segment

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**FLAT Result:**")
                st.info(f"""
                NGR ${preview_ngr:,.2f} → Tier Rate: {flat_rate}%

                **Commission = ${flat_commission:,.2f}**
                """)

            with col2:
                st.markdown("**NON-FLAT Result:**")
                breakdown_text = "\n".join([
                    f"- {b['range']}: ${b['segment']:,.0f} × {b['rate']}% = ${b['commission']:,.2f}"
                    for b in nonflat_breakdown
                ])
                st.success(f"""
                {breakdown_text}

                **Total = ${nonflat_commission:,.2f}**
                """)

            # Difference
            diff = flat_commission - nonflat_commission
            if diff > 0:
                st.warning(f"📊 **Difference:** ${diff:,.2f} (FLAT menghasilkan lebih tinggi)")
            elif diff < 0:
                st.warning(f"📊 **Difference:** ${abs(diff):,.2f} (NON-FLAT menghasilkan lebih tinggi)")
            else:
                st.info("📊 **Difference:** $0 (sama)")

    # ==================== SECTION 4: Summary & Submit ====================
    st.markdown("---")
    st.markdown("### 4️⃣ Summary & Create")

    # Show summary
    with st.expander("📋 Review Configuration", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Basic Info:**")
            st.write(f"- Name: {name or '(not set)'}")
            st.write(f"- Parent: {parent_select}")
            st.write(f"- Status: {status}")
            st.write(f"- Period: {period_type}")

            st.markdown("**Commission Settings:**")
            st.write(f"- Admin Rate: {admin_rate}%")
            st.write(f"- Upline Rate: {upline_rate}%")
            st.write(f"- Manual Adjustment: ${manual_adj:,.2f}")

        with col2:
            st.markdown("**Commission Plan:**")
            st.write(f"- Type: {plan_type}")
            st.write(f"- Name: {plan_name}")

            if is_count_based:
                st.write(f"- Payout/Event: ${fixed_payout:.2f}")
            elif is_rate_based:
                if rate_mode == "Fixed Rate":
                    st.write(f"- Rate Mode: Fixed")
                    st.write(f"- Rate: {fixed_rate}%")
                else:
                    st.write(f"- Rate Mode: DSR")
                    st.write(f"- Calculation: {calculation_type}")
                    st.write(f"- Tiers: {len(tiers_data)}")

    # Formula reminder
    st.markdown("**Commission Calculation Formula:**")
    st.code("""
Net_AfterCost = Total_Gross - AdminCost - BonusDeduction - BalanceDeduction
NetCommission = Net_AfterCost + ManualAdjustment
UplineCommission = NetCommission × UplineRate
    """, language=None)

    # Submit button
    if st.button("✅ Create Affiliate", type="primary", use_container_width=True):
        if not name:
            st.error("❌ Please enter an affiliate name.")
        else:
            # Map plan type
            plan_type_map = {
                "Revenue Share": CommissionPlanType.REVENUE_SHARE,
                "Wager/Rakeback": CommissionPlanType.WAGER_RAKEBACK,
                "Signup (Count-based)": CommissionPlanType.SIGNUP,
                "First Deposit (Count-based)": CommissionPlanType.FIRST_DEPOSIT,
                "Active User (Count-based)": CommissionPlanType.ACTIVE_USER,
                "Deposit - Withdrawal": CommissionPlanType.DEPOSIT_WITHDRAWAL,
            }

            # Map base type
            base_type_map = {
                "NGR (Net Gaming Revenue)": BaseType.NGR,
                "GGR (Gross Gaming Revenue)": BaseType.GGR,
                "Total Bet": BaseType.TOTAL_BET,
                "Total Rake": BaseType.TOTAL_RAKE,
            }

            # Create commission plan
            if is_count_based:
                plan = CommissionPlan(
                    plan_type=plan_type_map[plan_type],
                    name=plan_name,
                    fixed_payout_per_event=Decimal(str(fixed_payout)),
                )
            elif is_rate_based:
                if rate_mode == "Fixed Rate":
                    plan = CommissionPlan(
                        plan_type=plan_type_map[plan_type],
                        name=plan_name,
                        base_type=base_type_map.get(base_type, BaseType.NGR),
                        rate_mode=RateMode.FIXED,
                        fixed_rate=Decimal(str(fixed_rate / 100)),
                    )
                else:  # DSR
                    # Create DSR tiers
                    dsr_tier_objects = []
                    for tier in tiers_data:
                        dsr_tier_objects.append(DSRTier(
                            min_value=Decimal(str(tier["min"])),
                            max_value=Decimal(str(tier["max"])) if tier["max"] else None,
                            rate=Decimal(str(tier["rate"] / 100)),
                        ))

                    plan = CommissionPlan(
                        plan_type=plan_type_map[plan_type],
                        name=plan_name,
                        base_type=base_type_map.get(base_type, BaseType.NGR),
                        rate_mode=RateMode.DSR,
                        dsr_indicator=DSRIndicator.NGR if dsr_indicator == "NGR" else (DSRIndicator.GGR if dsr_indicator == "GGR" else DSRIndicator.COUNT),
                        dsr_tiers=dsr_tier_objects,
                        calculation_type=CalculationType.FLAT if "FLAT" in calculation_type else CalculationType.NON_FLAT,
                    )

            # Map period type
            period_type_map = {
                "Calendar Month": PeriodType.CALENDAR_MONTH,
                "From Signup Date": PeriodType.FROM_SIGNUP,
                "Custom": PeriodType.CUSTOM,
            }

            # Create affiliate
            new_aff = Affiliate(
                name=name,
                parent_affiliate_id=parent_id,
                admin_royalty_rate=Decimal(str(admin_rate / 100)),
                upline_commission_rate=Decimal(str(upline_rate / 100)),
                manual_adjustment=Decimal(str(manual_adj)),
                bonus_deduction=Decimal(str(bonus_deduction)),
                balance_deduction=Decimal(str(balance_deduction)),
                period_type=period_type_map[period_type],
                commission_plans=[plan],
            )

            aff_service.register_affiliate(new_aff)
            st.success(f"✅ Affiliate '{name}' created successfully!")
            st.balloons()

            # Clear DSR config
            if 'dsr_tiers_config' in st.session_state:
                del st.session_state.dsr_tiers_config


def render_affiliate_details(aff_service):
    """Render affiliate details view"""

    st.subheader("Affiliate Details")

    # Affiliate selector
    aff_options = {aff.name: aff.affiliate_id for aff in aff_service._affiliates.values()}

    if aff_options:
        selected_name = st.selectbox("Select Affiliate", options=list(aff_options.keys()))
        selected_id = aff_options[selected_name]
        affiliate = aff_service.get_affiliate(selected_id)

        if affiliate:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Basic Info")
                st.write(f"**ID:** `{affiliate.affiliate_id[:16]}...`")
                st.write(f"**Name:** {affiliate.name}")
                st.write(f"**Status:** {affiliate.status.value.title()}")
                st.write(f"**Period Type:** {affiliate.period_type.value}")

                if affiliate.parent_affiliate_id:
                    parent = aff_service.get_affiliate(affiliate.parent_affiliate_id)
                    st.write(f"**Parent:** {parent.name if parent else 'N/A'}")
                else:
                    st.write("**Parent:** None (Top Level)")

            with col2:
                st.markdown("#### Commission Settings")
                st.write(f"**Admin Royalty Rate:** {affiliate.admin_royalty_rate * 100:.1f}%")
                st.write(f"**Upline Rate:** {affiliate.upline_commission_rate * 100:.1f}%")
                st.write(f"**Manual Adjustment:** ${affiliate.manual_adjustment:,.2f}")
                st.write(f"**Bonus Deduction:** ${affiliate.bonus_deduction:,.2f}")
                st.write(f"**Balance Deduction:** ${affiliate.balance_deduction:,.2f}")

            st.markdown("---")
            st.markdown("#### Commission Plans")

            for plan in affiliate.commission_plans:
                with st.expander(f"📋 {plan.name} ({plan.plan_type.value})", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {plan.plan_type.value}")
                        st.write(f"**Base:** {plan.base_type.value}")
                        st.write(f"**Rate Mode:** {plan.rate_mode.value}")
                        if plan.rate_mode == RateMode.DSR:
                            st.write(f"**DSR Indicator:** {plan.dsr_indicator.value}")
                            st.write(f"**Calculation:** {plan.calculation_type.value}")
                    with col2:
                        if plan.rate_mode == RateMode.FIXED:
                            st.write(f"**Fixed Rate:** {plan.fixed_rate * 100:.2f}%")
                        if plan.fixed_payout_per_event > 0:
                            st.write(f"**Payout/Event:** ${plan.fixed_payout_per_event:,.2f}")

                    if plan.dsr_tiers:
                        st.markdown("**DSR Tiers:**")
                        tier_data = []
                        for tier in plan.dsr_tiers:
                            max_str = f"${tier.max_value:,.0f}" if tier.max_value else "∞"
                            tier_data.append({
                                "Range": f"${tier.min_value:,.0f} - {max_str}",
                                "Rate": f"{tier.rate * 100:.0f}%"
                            })
                        st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Players")

            users = aff_service.get_affiliate_users(affiliate.affiliate_id)
            if users:
                user_data = []
                for user in users:
                    user_data.append({
                        "Username": user.username,
                        "Status": "🟢 Active" if user.is_active else "⚪ Inactive",
                        "Total Bets": f"${user.total_bets:,.2f}",
                        "GGR": f"${user.ggr:,.2f}",
                        "NGR": f"${user.ngr:,.2f}",
                    })
                df = pd.DataFrame(user_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No players registered under this affiliate.")

            # Upline chain
            st.markdown("---")
            st.markdown("#### Upline Chain")
            upline = aff_service.get_upline_chain(affiliate.affiliate_id)
            if upline:
                for i, up in enumerate(upline):
                    st.write(f"**Level {i+1}:** {up.name} (Rate: {up.upline_commission_rate * 100:.1f}%)")
            else:
                st.info("This is a top-level affiliate.")

    else:
        st.info("No affiliates available. Create one first.")
