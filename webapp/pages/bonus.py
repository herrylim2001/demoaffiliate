"""
Bonus page - Manage and issue bonuses
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from decimal import Decimal
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.bonus import BonusConfig
from src.utils.enums import BonusType, BonusStatus


def render():
    """Render the bonus page"""

    st.markdown("<h1 class='main-header'>Bonus Management</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Issue and track player bonuses</p>", unsafe_allow_html=True)
    st.markdown("---")

    aff_service = st.session_state.affiliate_service
    bonus_service = st.session_state.bonus_service

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🎁 Issue Bonus", "⚙️ Configuration", "📋 All Bonuses"])

    # ==================== Tab 1: Overview ====================
    with tab1:
        st.subheader("Bonus Overview")

        stats = bonus_service.get_bonus_statistics()

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issued", f"${float(stats['total_issued']):,.2f}")
        with col2:
            st.metric("Total Claimed", f"${float(stats['total_claimed']):,.2f}")
        with col3:
            st.metric("Total Pending", f"${float(stats['total_pending']):,.2f}")
        with col4:
            st.metric("Total Expired", f"${float(stats['total_expired']):,.2f}")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Bonus by Type")

            bonus_type_data = [
                {"Type": "Deposit", "Amount": stats['by_type'].get('deposit', 0)},
                {"Type": "Rakeback", "Amount": stats['by_type'].get('rakeback', 0)},
                {"Type": "Cashback", "Amount": stats['by_type'].get('cashback', 0)},
                {"Type": "Special", "Amount": stats['by_type'].get('special', 0)},
            ]
            df = pd.DataFrame(bonus_type_data)

            fig = px.pie(
                df,
                values="Amount",
                names="Type",
                hole=0.4,
                color_discrete_sequence=["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            )
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Bonus by Status")

            status_counts = {
                BonusStatus.ACTIVE: 0,
                BonusStatus.CLAIMABLE: 0,
                BonusStatus.CLAIMED: 0,
                BonusStatus.EXPIRED: 0,
            }

            for bonus in bonus_service._bonuses.values():
                if bonus.status in status_counts:
                    status_counts[bonus.status] += 1

            status_data = [
                {"Status": "Active", "Count": status_counts[BonusStatus.ACTIVE]},
                {"Status": "Claimable", "Count": status_counts[BonusStatus.CLAIMABLE]},
                {"Status": "Claimed", "Count": status_counts[BonusStatus.CLAIMED]},
                {"Status": "Expired", "Count": status_counts[BonusStatus.EXPIRED]},
            ]
            df = pd.DataFrame(status_data)

            fig = px.bar(
                df,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_sequence=["#1f77b4", "#2ca02c", "#9467bd", "#7f7f7f"],
            )
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Bonus Formulas
        st.markdown("---")
        st.markdown("#### Bonus Formulas")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **Deposit Bonus**
            ```
            Bonus = min(Deposit × Rate, Max Bonus)
            ```

            **Rakeback Bonus**
            ```
            Rakeback = Total Bet × Rakeback Rate
            ```
            """)

        with col2:
            st.markdown("""
            **Cashback Bonus**
            ```
            NetLose = max(0, Bet - Payout)
            Cashback = NetLose × Cashback Rate
            ```

            **Special Bonus**
            ```
            Manual amount set by admin
            ```
            """)

    # ==================== Tab 2: Issue Bonus ====================
    with tab2:
        st.subheader("Issue Bonus")

        # Get all users
        users = list(aff_service._users.values())

        if not users:
            st.warning("No users available. Create users first.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # User selector
                user_options = {f"{u.username} (${u.total_bets:,.0f} bets)": u.user_id for u in users}
                selected_user_name = st.selectbox("Select User", options=list(user_options.keys()))
                selected_user_id = user_options[selected_user_name]
                selected_user = aff_service.get_user(selected_user_id)

                # Bonus type
                bonus_type = st.selectbox(
                    "Bonus Type",
                    options=["Deposit Bonus", "Rakeback", "Cashback", "Special Bonus"]
                )

            with col2:
                # User info
                if selected_user:
                    st.markdown("#### User Info")
                    st.write(f"**Username:** {selected_user.username}")
                    st.write(f"**Total Bets:** ${selected_user.total_bets:,.2f}")
                    st.write(f"**GGR:** ${selected_user.ggr:,.2f}")
                    st.write(f"**Net Loss:** ${selected_user.net_loss:,.2f}")

            st.markdown("---")

            # Bonus-specific forms
            if bonus_type == "Deposit Bonus":
                st.markdown("#### Deposit Bonus")

                col1, col2 = st.columns(2)
                with col1:
                    deposit_amount = st.number_input("Deposit Amount ($)", min_value=0.0, value=200.0, step=50.0)

                config_id = st.session_state.get('deposit_bonus_config_id')
                config = bonus_service.get_bonus_config(config_id) if config_id else None

                if config:
                    st.info(f"Config: {config.rate * 100:.0f}% match up to ${config.max_bonus}, {config.wagering_requirement}x wagering")

                    calculated = min(Decimal(str(deposit_amount)) * config.rate, config.max_bonus)
                    st.metric("Calculated Bonus", f"${calculated:,.2f}")

                if st.button("Issue Deposit Bonus", type="primary"):
                    if config and selected_user:
                        bonus = bonus_service.issue_deposit_bonus(
                            selected_user, Decimal(str(deposit_amount)), config
                        )
                        if bonus:
                            st.success(f"Deposit bonus of ${bonus.amount:,.2f} issued!")
                        else:
                            st.error("Could not issue bonus. Check minimum deposit requirement.")

            elif bonus_type == "Rakeback":
                st.markdown("#### Rakeback Bonus")

                bet_amount = st.number_input("Bet Amount ($)", min_value=0.0, value=float(selected_user.total_bets), step=1000.0)

                config_id = st.session_state.get('rakeback_config_id')
                config = bonus_service.get_bonus_config(config_id) if config_id else None

                if config:
                    st.info(f"Config: {config.rate * 100:.2f}% of wagers")

                    calculated = Decimal(str(bet_amount)) * config.rate
                    st.metric("Calculated Rakeback", f"${calculated:,.2f}")

                if st.button("Accumulate Rakeback", type="primary"):
                    if config and selected_user:
                        bonus = bonus_service.accumulate_rakeback(
                            selected_user, Decimal(str(bet_amount)), config
                        )
                        st.success(f"Rakeback of ${bonus.amount:,.2f} accumulated!")

            elif bonus_type == "Cashback":
                st.markdown("#### Cashback Bonus")

                config_id = st.session_state.get('cashback_config_id')
                config = bonus_service.get_bonus_config(config_id) if config_id else None

                if config and selected_user:
                    st.info(f"Config: {config.rate * 100:.0f}% of net losses")

                    net_loss = selected_user.net_loss
                    calculated = net_loss * config.rate if net_loss > 0 else Decimal("0")

                    st.write(f"**Net Loss:** ${net_loss:,.2f}")
                    st.metric("Calculated Cashback", f"${calculated:,.2f}")

                    if net_loss <= 0:
                        st.warning("User has no net loss. Cashback not applicable.")

                if st.button("Issue Cashback", type="primary"):
                    if config and selected_user:
                        bonus = bonus_service.issue_cashback_bonus(selected_user, config)
                        if bonus:
                            st.success(f"Cashback of ${bonus.amount:,.2f} issued!")
                        else:
                            st.error("Could not issue cashback. User may not have net losses.")

            elif bonus_type == "Special Bonus":
                st.markdown("#### Special Bonus (Manual)")

                col1, col2 = st.columns(2)
                with col1:
                    bonus_amount = st.number_input("Bonus Amount ($)", min_value=0.0, value=100.0, step=10.0)
                    admin_note = st.text_input("Admin Note *", placeholder="e.g., VIP reward, promotion")

                with col2:
                    wagering_req = st.number_input("Wagering Requirement (x)", min_value=0, value=0, step=5)
                    expiry_days = st.number_input("Expiry (days)", min_value=1, value=30, step=1)

                if st.button("Issue Special Bonus", type="primary"):
                    if not admin_note:
                        st.error("Admin note is required for special bonuses.")
                    elif selected_user:
                        wagering = Decimal(str(wagering_req)) if wagering_req > 0 else None
                        bonus = bonus_service.issue_special_bonus(
                            selected_user,
                            amount=Decimal(str(bonus_amount)),
                            admin_id="admin_demo",
                            admin_note=admin_note,
                            wagering_requirement=wagering,
                            expiry_days=expiry_days,
                        )
                        st.success(f"Special bonus of ${bonus.amount:,.2f} issued!")

    # ==================== Tab 3: Configuration ====================
    with tab3:
        st.subheader("Bonus Configurations")

        # Show existing configs
        configs = list(bonus_service._bonus_configs.values())

        if configs:
            for config in configs:
                with st.expander(f"⚙️ {config.name} ({config.bonus_type.value})", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {config.bonus_type.value}")
                        st.write(f"**Rate:** {config.rate * 100:.2f}%")
                        if config.max_bonus:
                            st.write(f"**Max Bonus:** ${config.max_bonus:,.2f}")
                    with col2:
                        if config.min_trigger_amount:
                            st.write(f"**Min Trigger:** ${config.min_trigger_amount:,.2f}")
                        if config.wagering_requirement:
                            st.write(f"**Wagering Req:** {config.wagering_requirement}x")
                        st.write(f"**Expiry:** {config.expiry_days} days")
                        st.write(f"**Active:** {'Yes' if config.is_active else 'No'}")

        st.markdown("---")
        st.subheader("Create New Configuration")

        with st.form("create_bonus_config"):
            col1, col2 = st.columns(2)

            with col1:
                config_name = st.text_input("Config Name", placeholder="e.g., Weekend Bonus")
                config_type = st.selectbox(
                    "Bonus Type",
                    options=["Deposit", "Rakeback", "Cashback", "Special"]
                )
                rate = st.slider("Rate (%)", min_value=0.0, max_value=200.0, value=100.0, step=5.0)

            with col2:
                max_bonus = st.number_input("Max Bonus ($)", min_value=0.0, value=500.0, step=50.0)
                min_trigger = st.number_input("Min Trigger Amount ($)", min_value=0.0, value=50.0, step=10.0)
                wagering = st.number_input("Wagering Requirement (x)", min_value=0, value=30, step=5)
                expiry = st.number_input("Expiry (days)", min_value=1, value=30, step=1)

            submitted = st.form_submit_button("Create Configuration", use_container_width=True)

            if submitted:
                type_map = {
                    "Deposit": BonusType.DEPOSIT,
                    "Rakeback": BonusType.RAKEBACK,
                    "Cashback": BonusType.CASHBACK,
                    "Special": BonusType.SPECIAL,
                }

                new_config = BonusConfig(
                    bonus_type=type_map[config_type],
                    name=config_name,
                    rate=Decimal(str(rate / 100)),
                    max_bonus=Decimal(str(max_bonus)) if max_bonus > 0 else None,
                    min_trigger_amount=Decimal(str(min_trigger)) if min_trigger > 0 else None,
                    wagering_requirement=Decimal(str(wagering)) if wagering > 0 else None,
                    expiry_days=expiry,
                )
                bonus_service.register_bonus_config(new_config)
                st.success(f"Configuration '{config_name}' created!")
                st.rerun()

    # ==================== Tab 4: All Bonuses ====================
    with tab4:
        st.subheader("All Bonuses")

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_type = st.multiselect(
                "Filter by Type",
                options=["deposit", "rakeback", "cashback", "special"],
                default=["deposit", "rakeback", "cashback", "special"]
            )
        with col2:
            filter_status = st.multiselect(
                "Filter by Status",
                options=["active", "claimable", "claimed", "expired"],
                default=["active", "claimable"]
            )

        # Get filtered bonuses
        bonuses = list(bonus_service._bonuses.values())
        filtered = [
            b for b in bonuses
            if b.bonus_type.value in filter_type and b.status.value in filter_status
        ]

        if filtered:
            bonus_data = []
            for bonus in filtered:
                user = aff_service.get_user(bonus.user_id)
                username = user.username if user else "Unknown"

                wr_progress = ""
                if bonus.wagering_requirement:
                    wr_progress = f"{bonus.wagering_progress:,.0f}/{bonus.wagering_requirement:,.0f}"

                bonus_data.append({
                    "ID": bonus.bonus_id[:8] + "...",
                    "User": username,
                    "Type": bonus.bonus_type.value.title(),
                    "Amount": f"${bonus.amount:,.2f}",
                    "Status": bonus.status.value.title(),
                    "Wagering": wr_progress or "-",
                    "Expiry": bonus.expiry_date.strftime("%Y-%m-%d") if bonus.expiry_date else "-",
                    "Claimable": "Yes" if bonus.is_claimable else "No",
                })

            df = pd.DataFrame(bonus_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Summary
            total_amount = sum(b.amount for b in filtered)
            st.metric("Total Amount (Filtered)", f"${total_amount:,.2f}")
        else:
            st.info("No bonuses match the selected filters.")

        # Actions
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Process Expired Bonuses", use_container_width=True):
                expired = bonus_service.process_expired_bonuses()
                st.success(f"Processed {len(expired)} expired bonuses")
                st.rerun()
