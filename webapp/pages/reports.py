"""
Reports page - Commission statements and bonus reports
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


def render():
    """Render the reports page"""

    st.markdown("<h1 class='main-header'>Reports & Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Commission statements and bonus reports</p>", unsafe_allow_html=True)
    st.markdown("---")

    aff_service = st.session_state.affiliate_service
    bonus_service = st.session_state.bonus_service
    calculator = st.session_state.commission_calculator

    tab1, tab2, tab3 = st.tabs(["📑 Commission Report", "🎁 Bonus Report", "📈 Analytics"])

    # ==================== Tab 1: Commission Report ====================
    with tab1:
        st.subheader("Commission Statement Report")

        col1, col2 = st.columns([2, 1])
        with col1:
            period_start = st.date_input("Period Start", value=datetime(2026, 2, 1), key="report_start")
            period_end = st.date_input("Period End", value=datetime(2026, 2, 28), key="report_end")

        if st.button("Generate Commission Report", type="primary"):
            period = CommissionPeriod(
                start_date=datetime.combine(period_start, datetime.min.time()),
                end_date=datetime.combine(period_end, datetime.max.time()),
            )

            statements = []
            for aff in aff_service._affiliates.values():
                if aff.is_active:
                    metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
                    if metrics['total_users'] > 0:
                        stmt = calculator.calculate_commission(aff, period, metrics)
                        statements.append(stmt)

            st.session_state.report_statements = statements

        if hasattr(st.session_state, 'report_statements') and st.session_state.report_statements:
            statements = st.session_state.report_statements

            st.markdown("---")
            st.markdown(f"### Commission Report: {period_start.strftime('%B %d')} - {period_end.strftime('%B %d, %Y')}")

            # Summary metrics
            total_ggr = sum(s.ggr for s in statements)
            total_ngr = sum(s.ngr for s in statements)
            total_gross = sum(s.total_gross_commission for s in statements)
            total_net = sum(s.net_commission for s in statements)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total GGR", f"${total_ggr:,.2f}")
            with col2:
                st.metric("Total NGR", f"${total_ngr:,.2f}")
            with col3:
                st.metric("Gross Commission", f"${total_gross:,.2f}")
            with col4:
                st.metric("Net Commission", f"${total_net:,.2f}")

            st.markdown("---")

            # Detailed table
            st.markdown("#### Detailed Breakdown by Affiliate")

            report_data = []
            for stmt in statements:
                plan_names = ", ".join([b.plan_name for b in stmt.plan_breakdowns])
                report_data.append({
                    "Affiliate": stmt.affiliate_name,
                    "Players": stmt.total_players,
                    "Active": stmt.active_players,
                    "Total Bets": f"${stmt.total_bets:,.2f}",
                    "Total Payouts": f"${stmt.total_payouts:,.2f}",
                    "GGR": f"${stmt.ggr:,.2f}",
                    "Bonus Cost": f"${stmt.total_bonus_cost:,.2f}",
                    "NGR": f"${stmt.ngr:,.2f}",
                    "Plans": plan_names[:30] + ("..." if len(plan_names) > 30 else ""),
                    "Gross Comm.": f"${stmt.total_gross_commission:,.2f}",
                    "Admin Cost": f"${stmt.admin_cost:,.2f}",
                    "Manual Adj.": f"${stmt.manual_adjustment:,.2f}",
                    "Net Comm.": f"${stmt.net_commission:,.2f}",
                })

            df = pd.DataFrame(report_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Chart
            st.markdown("---")
            st.markdown("#### Commission Distribution")

            chart_data = pd.DataFrame({
                "Affiliate": [s.affiliate_name for s in statements],
                "Gross": [float(s.total_gross_commission) for s in statements],
                "Net": [float(s.net_commission) for s in statements],
            })

            fig = px.bar(
                chart_data,
                x="Affiliate",
                y=["Gross", "Net"],
                barmode="group",
                color_discrete_sequence=["#1f77b4", "#2ca02c"],
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

            # Export option
            st.markdown("---")
            csv = df.to_csv(index=False)
            st.download_button(
                "Download Report (CSV)",
                csv,
                "commission_report.csv",
                "text/csv",
                use_container_width=True
            )

    # ==================== Tab 2: Bonus Report ====================
    with tab2:
        st.subheader("Bonus Report")

        stats = bonus_service.get_bonus_statistics()

        # Summary cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issued", f"${float(stats['total_issued']):,.2f}")
        with col2:
            st.metric("Total Claimed", f"${float(stats['total_claimed']):,.2f}")
        with col3:
            st.metric("Pending", f"${float(stats['total_pending']):,.2f}")
        with col4:
            st.metric("Expired", f"${float(stats['total_expired']):,.2f}")

        st.markdown("---")

        # Bonus breakdown
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Bonus by Type")

            type_data = pd.DataFrame({
                "Type": ["Deposit", "Rakeback", "Cashback", "Special"],
                "Amount": [
                    stats['by_type'].get('deposit', 0),
                    stats['by_type'].get('rakeback', 0),
                    stats['by_type'].get('cashback', 0),
                    stats['by_type'].get('special', 0),
                ]
            })

            fig = px.bar(
                type_data,
                x="Type",
                y="Amount",
                color="Type",
                color_discrete_sequence=["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Status Distribution")

            bonuses = list(bonus_service._bonuses.values())
            status_counts = {}
            for bonus in bonuses:
                status = bonus.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            status_data = pd.DataFrame({
                "Status": list(status_counts.keys()),
                "Count": list(status_counts.values()),
            })

            fig = px.pie(
                status_data,
                values="Count",
                names="Status",
                hole=0.4,
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # Detailed bonus table
        st.markdown("---")
        st.markdown("#### All Bonuses Detail")

        bonus_report = bonus_service.get_bonus_report()
        if bonus_report:
            df = pd.DataFrame(bonus_report)
            df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
            df.columns = ['ID', 'User', 'Type', 'Amount', 'Status', 'WR Progress', 'WR Required', 'Expiry', 'Claimable']
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Export
            csv = df.to_csv(index=False)
            st.download_button(
                "Download Bonus Report (CSV)",
                csv,
                "bonus_report.csv",
                "text/csv",
                use_container_width=True
            )

    # ==================== Tab 3: Analytics ====================
    with tab3:
        st.subheader("System Analytics")

        # Overall metrics
        all_users = list(aff_service._users.values())
        all_affiliates = list(aff_service._affiliates.values())

        total_bets = sum(u.total_bets for u in all_users)
        total_payouts = sum(u.total_payouts for u in all_users)
        total_ggr = sum(u.ggr for u in all_users)
        total_deposits = sum(u.total_deposits for u in all_users)
        total_withdrawals = sum(u.total_withdrawals for u in all_users)

        st.markdown("#### Key Performance Indicators")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Players", len(all_users))
            st.metric("Active Players", len([u for u in all_users if u.is_active]))
        with col2:
            st.metric("Total Affiliates", len(all_affiliates))
            st.metric("Total Bets", f"${total_bets:,.2f}")
        with col3:
            st.metric("Total GGR", f"${total_ggr:,.2f}")
            hold_pct = (total_ggr / total_bets * 100) if total_bets > 0 else 0
            st.metric("Hold %", f"{hold_pct:.2f}%")

        st.markdown("---")

        # Revenue trend (simulated)
        st.markdown("#### Revenue by Affiliate")

        revenue_data = []
        for aff in all_affiliates:
            metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
            if metrics['total_users'] > 0:
                revenue_data.append({
                    "Affiliate": aff.name,
                    "Players": metrics['total_users'],
                    "GGR": float(metrics['ggr']),
                    "NGR": float(metrics['ngr']),
                    "Bets": float(metrics['total_bets']),
                })

        if revenue_data:
            df = pd.DataFrame(revenue_data)

            # Scatter plot
            fig = px.scatter(
                df,
                x="Players",
                y="GGR",
                size="Bets",
                color="Affiliate",
                hover_data=["NGR"],
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Player distribution
        st.markdown("---")
        st.markdown("#### Player Value Distribution")

        if all_users:
            player_ggr = [float(u.ggr) for u in all_users]
            fig = px.histogram(
                x=player_ggr,
                nbins=20,
                labels={"x": "Player GGR ($)", "y": "Count"},
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # Top performers
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Top Affiliates by GGR")
            aff_by_ggr = []
            for aff in all_affiliates:
                metrics = aff_service.get_affiliate_metrics(aff.affiliate_id)
                aff_by_ggr.append({"Affiliate": aff.name, "GGR": float(metrics['ggr'])})

            aff_by_ggr.sort(key=lambda x: x['GGR'], reverse=True)
            df = pd.DataFrame(aff_by_ggr[:5])
            df['GGR'] = df['GGR'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("#### Top Players by Bets")
            top_players = sorted(all_users, key=lambda u: u.total_bets, reverse=True)[:5]
            player_data = []
            for p in top_players:
                player_data.append({
                    "Username": p.username,
                    "Total Bets": f"${p.total_bets:,.2f}",
                    "GGR": f"${p.ggr:,.2f}",
                })
            df = pd.DataFrame(player_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
