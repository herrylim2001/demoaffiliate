"""
Affiliates page - Manage and view affiliates
"""

import streamlit as st
import pandas as pd
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.utils.enums import (
    CommissionPlanType, BaseType, RateMode, DSRIndicator, CalculationType
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
        st.subheader("Create New Affiliate")

        with st.form("create_affiliate_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Affiliate Name *", placeholder="e.g., Agency XYZ")

                # Parent selection
                parent_options = {"None (Top Level)": None}
                for aff in aff_service._affiliates.values():
                    parent_options[aff.name] = aff.affiliate_id

                parent_select = st.selectbox(
                    "Parent Affiliate",
                    options=list(parent_options.keys())
                )
                parent_id = parent_options[parent_select]

                admin_rate = st.slider(
                    "Admin Royalty Rate (%)",
                    min_value=0.0,
                    max_value=20.0,
                    value=5.0,
                    step=0.5
                )

            with col2:
                upline_rate = st.slider(
                    "Upline Commission Rate (%)",
                    min_value=0.0,
                    max_value=30.0,
                    value=10.0,
                    step=1.0
                )

                manual_adj = st.number_input(
                    "Manual Adjustment ($)",
                    value=0.0,
                    step=100.0
                )

            st.markdown("---")
            st.markdown("### Commission Plan")

            col1, col2 = st.columns(2)

            with col1:
                plan_type = st.selectbox(
                    "Plan Type *",
                    options=[
                        "Revenue Share",
                        "Wager/Rakeback",
                        "Signup",
                        "First Deposit",
                        "Active User",
                        "Deposit-Withdrawal"
                    ]
                )

                plan_name = st.text_input("Plan Name", value=f"{plan_type} Plan")

            with col2:
                if plan_type in ["Revenue Share", "Wager/Rakeback", "Deposit-Withdrawal"]:
                    rate_mode = st.selectbox("Rate Mode", ["Fixed", "DSR"])
                    fixed_rate = st.slider(
                        "Commission Rate (%)",
                        min_value=0.0,
                        max_value=50.0,
                        value=25.0,
                        step=1.0
                    )
                else:
                    fixed_payout = st.number_input(
                        "Fixed Payout per Event ($)",
                        min_value=0.0,
                        value=25.0,
                        step=5.0
                    )

            submitted = st.form_submit_button("Create Affiliate", use_container_width=True)

            if submitted:
                if not name:
                    st.error("Please enter an affiliate name.")
                else:
                    # Map plan type
                    plan_type_map = {
                        "Revenue Share": CommissionPlanType.REVENUE_SHARE,
                        "Wager/Rakeback": CommissionPlanType.WAGER_RAKEBACK,
                        "Signup": CommissionPlanType.SIGNUP,
                        "First Deposit": CommissionPlanType.FIRST_DEPOSIT,
                        "Active User": CommissionPlanType.ACTIVE_USER,
                        "Deposit-Withdrawal": CommissionPlanType.DEPOSIT_WITHDRAWAL,
                    }

                    # Create plan
                    if plan_type in ["Revenue Share", "Wager/Rakeback", "Deposit-Withdrawal"]:
                        plan = CommissionPlan(
                            plan_type=plan_type_map[plan_type],
                            name=plan_name,
                            base_type=BaseType.NGR if plan_type == "Revenue Share" else BaseType.TOTAL_BET,
                            rate_mode=RateMode.FIXED,
                            fixed_rate=Decimal(str(fixed_rate / 100)),
                        )
                    else:
                        plan = CommissionPlan(
                            plan_type=plan_type_map[plan_type],
                            name=plan_name,
                            fixed_payout_per_event=Decimal(str(fixed_payout)),
                        )

                    # Create affiliate
                    new_aff = Affiliate(
                        name=name,
                        parent_affiliate_id=parent_id,
                        admin_royalty_rate=Decimal(str(admin_rate / 100)),
                        upline_commission_rate=Decimal(str(upline_rate / 100)),
                        manual_adjustment=Decimal(str(manual_adj)),
                        commission_plans=[plan],
                    )

                    aff_service.register_affiliate(new_aff)
                    st.success(f"Affiliate '{name}' created successfully!")
                    st.rerun()

    # ==================== Tab 3: Affiliate Details ====================
    with tab3:
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
                    st.write(f"**ID:** {affiliate.affiliate_id[:16]}...")
                    st.write(f"**Name:** {affiliate.name}")
                    st.write(f"**Status:** {affiliate.status.value.title()}")

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

                st.markdown("---")
                st.markdown("#### Commission Plans")

                for plan in affiliate.commission_plans:
                    with st.expander(f"📋 {plan.name} ({plan.plan_type.value})", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Type:** {plan.plan_type.value}")
                            st.write(f"**Base:** {plan.base_type.value}")
                            st.write(f"**Rate Mode:** {plan.rate_mode.value}")
                        with col2:
                            if plan.rate_mode == RateMode.FIXED:
                                st.write(f"**Fixed Rate:** {plan.fixed_rate * 100:.2f}%")
                            if plan.fixed_payout_per_event > 0:
                                st.write(f"**Payout/Event:** ${plan.fixed_payout_per_event:,.2f}")

                        if plan.dsr_tiers:
                            st.markdown("**DSR Tiers:**")
                            for tier in plan.dsr_tiers:
                                max_str = f"${tier.max_value:,.0f}" if tier.max_value else "∞"
                                st.write(f"  - ${tier.min_value:,.0f} - {max_str}: {tier.rate * 100:.0f}%")

                st.markdown("---")
                st.markdown("#### Players")

                users = aff_service.get_affiliate_users(affiliate.affiliate_id)
                if users:
                    user_data = []
                    for user in users:
                        user_data.append({
                            "Username": user.username,
                            "Status": "Active" if user.is_active else "Inactive",
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
                        st.write(f"**Level {i+1}:** {up.name}")
                else:
                    st.info("This is a top-level affiliate.")

        else:
            st.info("No affiliates available. Create one first.")
