"""
Dashboard page - Overview with key metrics and visualizations
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from decimal import Decimal


def render():
    """Render the dashboard page"""

    st.markdown("<h1 class='main-header'>Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Affiliate & Bonus System Overview</p>", unsafe_allow_html=True)
    st.markdown("---")

    aff_service = st.session_state.affiliate_service
    bonus_service = st.session_state.bonus_service

    # ==================== Key Metrics ====================
    col1, col2, col3, col4 = st.columns(4)

    total_affiliates = len(aff_service._affiliates)
    total_users = len(aff_service._users)
    active_users = len([u for u in aff_service._users.values() if u.is_active])

    total_bets = sum(u.total_bets for u in aff_service._users.values())
    total_ggr = sum(u.ggr for u in aff_service._users.values())
    total_ngr = sum(u.ngr for u in aff_service._users.values())

    with col1:
        st.metric("Total Affiliates", total_affiliates, delta="Active")
    with col2:
        st.metric("Total Players", total_users, delta=f"{active_users} active")
    with col3:
        st.metric("Total GGR", f"${total_ggr:,.2f}")
    with col4:
        st.metric("Total NGR", f"${total_ngr:,.2f}")

    st.markdown("---")

    # ==================== Charts Row 1 ====================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue by Affiliate")

        # Calculate revenue per affiliate
        revenue_data = []
        for aff in aff_service._affiliates.values():
            metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
            revenue_data.append({
                "Affiliate": aff.name[:20],
                "GGR": float(metrics['ggr']),
                "NGR": float(metrics['ngr']),
                "Players": metrics['total_users'],
            })

        if revenue_data:
            df = pd.DataFrame(revenue_data)
            fig = px.bar(
                df,
                x="Affiliate",
                y=["GGR", "NGR"],
                barmode="group",
                color_discrete_sequence=["#1f77b4", "#2ca02c"],
            )
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Player Distribution")

        # Player distribution pie chart
        player_data = []
        for aff in aff_service._affiliates.values():
            count = len(aff.coded_users)
            if count > 0:
                player_data.append({
                    "Affiliate": aff.name[:15],
                    "Players": count,
                })

        if player_data:
            df = pd.DataFrame(player_data)
            fig = px.pie(
                df,
                values="Players",
                names="Affiliate",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ==================== Charts Row 2 ====================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("DSR Tier Structure")

        # Get master affiliate's DSR tiers
        master_id = st.session_state.get('master_affiliate_id')
        if master_id:
            master = aff_service.get_affiliate(master_id)
            if master and master.commission_plans:
                plan = master.commission_plans[0]
                if plan.dsr_tiers:
                    tier_data = []
                    for tier in plan.dsr_tiers:
                        max_val = tier.max_value if tier.max_value else Decimal("150000")
                        tier_data.append({
                            "Tier": f"${tier.min_value:,.0f} - ${max_val:,.0f}" if tier.max_value else f"${tier.min_value:,.0f}+",
                            "Rate": float(tier.rate * 100),
                            "Min": float(tier.min_value),
                            "Max": float(max_val),
                        })

                    df = pd.DataFrame(tier_data)
                    fig = px.bar(
                        df,
                        x="Tier",
                        y="Rate",
                        color="Rate",
                        color_continuous_scale="Blues",
                        text="Rate",
                    )
                    fig.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
                    fig.update_layout(
                        height=350,
                        margin=dict(l=20, r=20, t=30, b=20),
                        showlegend=False,
                        yaxis_title="Commission Rate (%)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Bonus Overview")

        stats = bonus_service.get_bonus_statistics()
        bonus_data = [
            {"Type": "Deposit", "Amount": stats['by_type'].get('deposit', 0)},
            {"Type": "Rakeback", "Amount": stats['by_type'].get('rakeback', 0)},
            {"Type": "Cashback", "Amount": stats['by_type'].get('cashback', 0)},
            {"Type": "Special", "Amount": stats['by_type'].get('special', 0)},
        ]

        df = pd.DataFrame(bonus_data)
        fig = px.bar(
            df,
            x="Type",
            y="Amount",
            color="Type",
            color_discrete_sequence=["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        )
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
            yaxis_title="Amount ($)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==================== Affiliate Tree ====================
    st.markdown("---")
    st.subheader("Affiliate Network Structure")

    # Build tree visualization
    master_id = st.session_state.get('master_affiliate_id')
    if master_id:
        tree_text = aff_service.print_affiliate_tree(master_id)
        st.code(tree_text, language=None)

    # ==================== Quick Actions ====================
    st.markdown("---")
    st.subheader("Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Reset Demo Data", use_container_width=True):
            from webapp.state import reset_demo_data
            reset_demo_data()
            st.rerun()

    with col2:
        if st.button("📊 Calculate All Commissions", use_container_width=True):
            st.session_state.show_commission_calc = True
            st.info("Go to Commission page to see calculations")

    with col3:
        if st.button("🎁 Process Expired Bonuses", use_container_width=True):
            expired = bonus_service.process_expired_bonuses()
            st.success(f"Processed {len(expired)} expired bonuses")
