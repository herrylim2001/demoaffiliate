"""
Commission page - Calculate and view commissions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from decimal import Decimal
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.commission import CommissionPeriod
from src.utils.enums import RateMode, CalculationType


def render():
    """Render the commission page"""

    st.markdown("<h1 class='main-header'>Commission Calculator</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Calculate and analyze affiliate commissions</p>", unsafe_allow_html=True)
    st.markdown("---")

    aff_service = st.session_state.affiliate_service
    calculator = st.session_state.commission_calculator

    tab1, tab2, tab3 = st.tabs(["📊 Calculate Commission", "🔢 DSR Simulator", "📑 All Statements"])

    # ==================== Tab 1: Calculate Commission ====================
    with tab1:
        st.subheader("Calculate Commission for Affiliate")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Affiliate selector
            aff_options = {aff.name: aff.affiliate_id for aff in aff_service._affiliates.values()}

            if aff_options:
                selected_name = st.selectbox(
                    "Select Affiliate",
                    options=list(aff_options.keys()),
                    key="calc_affiliate"
                )
                selected_id = aff_options[selected_name]

        with col2:
            # Period selector
            period_start = st.date_input("Period Start", value=datetime(2026, 2, 1))
            period_end = st.date_input("Period End", value=datetime(2026, 2, 28))

        if st.button("Calculate Commission", type="primary", use_container_width=True):
            affiliate = aff_service.get_affiliate(selected_id)

            if affiliate:
                period = CommissionPeriod(
                    start_date=datetime.combine(period_start, datetime.min.time()),
                    end_date=datetime.combine(period_end, datetime.max.time()),
                )

                metrics = aff_service.get_affiliate_metrics(affiliate.affiliate_id)
                statement = calculator.calculate_commission(affiliate, period, metrics)

                # Store for display
                st.session_state.current_statement = statement
                st.session_state.current_affiliate = affiliate

        # Display statement if calculated
        if hasattr(st.session_state, 'current_statement'):
            statement = st.session_state.current_statement
            affiliate = st.session_state.current_affiliate

            st.markdown("---")
            st.subheader(f"Commission Statement: {affiliate.name}")

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Players", statement.total_players)
            with col2:
                st.metric("Active Players", statement.active_players)
            with col3:
                st.metric("First Deposits", statement.first_deposits)
            with col4:
                st.metric("Period", f"{statement.period.start_date.strftime('%b %d')} - {statement.period.end_date.strftime('%b %d')}")

            st.markdown("---")

            # Revenue breakdown
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Revenue Metrics")

                revenue_data = {
                    "Metric": ["Total Bets", "Total Payouts", "GGR", "Bonus Cost", "NGR"],
                    "Amount": [
                        f"${statement.total_bets:,.2f}",
                        f"${statement.total_payouts:,.2f}",
                        f"${statement.ggr:,.2f}",
                        f"-${statement.total_bonus_cost:,.2f}",
                        f"${statement.ngr:,.2f}",
                    ]
                }
                df = pd.DataFrame(revenue_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Visual
                fig = go.Figure(go.Waterfall(
                    name="Revenue",
                    orientation="v",
                    x=["Total Bets", "Payouts", "GGR", "Bonus Cost", "NGR"],
                    y=[
                        float(statement.total_bets),
                        -float(statement.total_payouts),
                        0,
                        -float(statement.total_bonus_cost),
                        0,
                    ],
                    measure=["absolute", "relative", "total", "relative", "total"],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("#### Commission Breakdown")

                if statement.plan_breakdowns:
                    for breakdown in statement.plan_breakdowns:
                        with st.expander(f"📋 {breakdown.plan_name}", expanded=True):
                            st.write(f"**Plan Type:** {breakdown.plan_type}")
                            st.write(f"**Base Value:** ${breakdown.base_value:,.2f}")
                            st.write(f"**Rate Applied:** {breakdown.rate_applied * 100:.2f}%")
                            st.write(f"**Gross Commission:** ${breakdown.gross_commission:,.2f}")

                st.markdown("---")

                # Commission calculation
                calc_data = {
                    "Description": [
                        "Total Gross Commission",
                        f"Admin Cost ({statement.admin_royalty_rate * 100:.1f}%)",
                        "Bonus Deduction",
                        "Balance Deduction",
                        "Net After Cost",
                        "Manual Adjustment",
                        "Net Commission",
                    ],
                    "Amount": [
                        f"${statement.total_gross_commission:,.2f}",
                        f"-${statement.admin_cost:,.2f}",
                        f"-${statement.bonus_deduction:,.2f}",
                        f"-${statement.balance_deduction:,.2f}",
                        f"${statement.net_after_cost:,.2f}",
                        f"+${statement.manual_adjustment:,.2f}" if statement.manual_adjustment >= 0 else f"-${abs(statement.manual_adjustment):,.2f}",
                        f"${statement.net_commission:,.2f}",
                    ]
                }
                df = pd.DataFrame(calc_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

            # Final result
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gross Commission", f"${statement.total_gross_commission:,.2f}")
            with col2:
                st.metric("Total Deductions", f"${statement.admin_cost + statement.bonus_deduction:,.2f}")
            with col3:
                st.metric("Net Commission", f"${statement.net_commission:,.2f}", delta=f"After adjustments")

    # ==================== Tab 2: DSR Simulator ====================
    with tab2:
        st.subheader("DSR (Dynamic Slicing Rule) Simulator")

        st.markdown("""
        **DSR** memungkinkan commission rate berbeda berdasarkan tier NGR/GGR.
        Simulasi di bawah menunjukkan perbedaan antara **Flat** dan **Non-Flat** calculation.
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### DSR Tier Configuration")

            # Default tiers
            tier1_max = st.number_input("Tier 1 Max ($)", value=10000, step=1000)
            tier1_rate = st.slider("Tier 1 Rate (%)", 0, 50, 25)

            tier2_max = st.number_input("Tier 2 Max ($)", value=50000, step=5000)
            tier2_rate = st.slider("Tier 2 Rate (%)", 0, 50, 30)

            tier3_max = st.number_input("Tier 3 Max ($)", value=100000, step=10000)
            tier3_rate = st.slider("Tier 3 Rate (%)", 0, 50, 35)

            tier4_rate = st.slider("Tier 4 Rate (%) - Unlimited", 0, 50, 40)

        with col2:
            st.markdown("#### Simulation")

            ngr_value = st.number_input(
                "NGR Value ($)",
                min_value=0,
                max_value=500000,
                value=75000,
                step=5000
            )

            st.markdown("---")

            # Calculate FLAT
            if ngr_value <= tier1_max:
                flat_rate = tier1_rate
            elif ngr_value <= tier2_max:
                flat_rate = tier2_rate
            elif ngr_value <= tier3_max:
                flat_rate = tier3_rate
            else:
                flat_rate = tier4_rate

            flat_commission = ngr_value * (flat_rate / 100)

            # Calculate NON-FLAT (Marginal)
            non_flat_commission = 0

            # Tier 1
            tier1_portion = min(ngr_value, tier1_max)
            non_flat_commission += tier1_portion * (tier1_rate / 100)

            # Tier 2
            if ngr_value > tier1_max:
                tier2_portion = min(ngr_value - tier1_max, tier2_max - tier1_max)
                non_flat_commission += tier2_portion * (tier2_rate / 100)

            # Tier 3
            if ngr_value > tier2_max:
                tier3_portion = min(ngr_value - tier2_max, tier3_max - tier2_max)
                non_flat_commission += tier3_portion * (tier3_rate / 100)

            # Tier 4
            if ngr_value > tier3_max:
                tier4_portion = ngr_value - tier3_max
                non_flat_commission += tier4_portion * (tier4_rate / 100)

            # Display results
            st.markdown("##### FLAT Calculation")
            st.info(f"NGR ${ngr_value:,.2f} falls in {flat_rate}% tier")
            st.metric("Commission", f"${flat_commission:,.2f}")

            st.markdown("##### NON-FLAT (Marginal) Calculation")
            breakdown_text = []
            if ngr_value > 0:
                t1 = min(ngr_value, tier1_max)
                breakdown_text.append(f"${0:,} - ${tier1_max:,}: ${t1:,} × {tier1_rate}% = ${t1 * tier1_rate / 100:,.2f}")
            if ngr_value > tier1_max:
                t2 = min(ngr_value - tier1_max, tier2_max - tier1_max)
                breakdown_text.append(f"${tier1_max:,} - ${tier2_max:,}: ${t2:,} × {tier2_rate}% = ${t2 * tier2_rate / 100:,.2f}")
            if ngr_value > tier2_max:
                t3 = min(ngr_value - tier2_max, tier3_max - tier2_max)
                breakdown_text.append(f"${tier2_max:,} - ${tier3_max:,}: ${t3:,} × {tier3_rate}% = ${t3 * tier3_rate / 100:,.2f}")
            if ngr_value > tier3_max:
                t4 = ngr_value - tier3_max
                breakdown_text.append(f"${tier3_max:,}+: ${t4:,} × {tier4_rate}% = ${t4 * tier4_rate / 100:,.2f}")

            for line in breakdown_text:
                st.write(line)

            st.metric("Commission", f"${non_flat_commission:,.2f}")

            # Comparison
            st.markdown("---")
            diff = flat_commission - non_flat_commission
            st.markdown(f"**Difference:** ${abs(diff):,.2f} ({'Flat higher' if diff > 0 else 'Non-Flat higher'})")

        # Visualization
        st.markdown("---")
        st.markdown("#### Commission Comparison Chart")

        # Generate comparison data
        ngr_range = list(range(0, 200001, 10000))
        flat_values = []
        nonflat_values = []

        for ngr in ngr_range:
            # Flat
            if ngr <= tier1_max:
                flat_values.append(ngr * tier1_rate / 100)
            elif ngr <= tier2_max:
                flat_values.append(ngr * tier2_rate / 100)
            elif ngr <= tier3_max:
                flat_values.append(ngr * tier3_rate / 100)
            else:
                flat_values.append(ngr * tier4_rate / 100)

            # Non-flat
            nf = 0
            nf += min(ngr, tier1_max) * tier1_rate / 100
            if ngr > tier1_max:
                nf += min(ngr - tier1_max, tier2_max - tier1_max) * tier2_rate / 100
            if ngr > tier2_max:
                nf += min(ngr - tier2_max, tier3_max - tier2_max) * tier3_rate / 100
            if ngr > tier3_max:
                nf += (ngr - tier3_max) * tier4_rate / 100
            nonflat_values.append(nf)

        df = pd.DataFrame({
            "NGR": ngr_range,
            "Flat": flat_values,
            "Non-Flat (Marginal)": nonflat_values,
        })

        fig = px.line(
            df,
            x="NGR",
            y=["Flat", "Non-Flat (Marginal)"],
            labels={"value": "Commission ($)", "variable": "Method"},
            color_discrete_sequence=["#1f77b4", "#ff7f0e"],
        )
        fig.add_vline(x=ngr_value, line_dash="dash", line_color="green", annotation_text=f"Current: ${ngr_value:,}")
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ==================== Tab 3: All Statements ====================
    with tab3:
        st.subheader("Calculate All Commission Statements")

        if st.button("Calculate for All Affiliates", type="primary"):
            period = st.session_state.current_period

            all_statements = []
            for aff in aff_service._affiliates.values():
                if aff.is_active:
                    metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
                    if metrics['total_users'] > 0:
                        statement = calculator.calculate_commission(aff, period, metrics)
                        all_statements.append(statement)

            st.session_state.all_statements = all_statements

        if hasattr(st.session_state, 'all_statements') and st.session_state.all_statements:
            statements = st.session_state.all_statements

            st.markdown("---")

            # Summary table
            summary_data = []
            for stmt in statements:
                summary_data.append({
                    "Affiliate": stmt.affiliate_name,
                    "Players": stmt.total_players,
                    "GGR": f"${stmt.ggr:,.2f}",
                    "NGR": f"${stmt.ngr:,.2f}",
                    "Gross Comm.": f"${stmt.total_gross_commission:,.2f}",
                    "Admin Cost": f"${stmt.admin_cost:,.2f}",
                    "Net Comm.": f"${stmt.net_commission:,.2f}",
                })

            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Totals
            total_net = sum(s.net_commission for s in statements)
            total_gross = sum(s.total_gross_commission for s in statements)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Gross Commission", f"${total_gross:,.2f}")
            with col2:
                st.metric("Total Net Commission", f"${total_net:,.2f}")
