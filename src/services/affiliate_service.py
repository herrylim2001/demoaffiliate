"""
Affiliate Service - handles affiliate tree management and operations
"""
from typing import Dict, List, Optional
from decimal import Decimal
from ..models.affiliate import Affiliate, CommissionPlan
from ..models.user import User
from ..utils.enums import AffiliateStatus


class AffiliateService:
    """Service for managing affiliates and their relationships"""

    def __init__(self):
        self._affiliates: Dict[str, Affiliate] = {}
        self._users: Dict[str, User] = {}

    def register_affiliate(self, affiliate: Affiliate) -> Affiliate:
        """Register a new affiliate in the system"""
        self._affiliates[affiliate.affiliate_id] = affiliate

        # Update parent's child list if parent exists
        if affiliate.parent_affiliate_id:
            parent = self._affiliates.get(affiliate.parent_affiliate_id)
            if parent and affiliate.affiliate_id not in parent.child_affiliates:
                parent.child_affiliates.append(affiliate.affiliate_id)

        return affiliate

    def get_affiliate(self, affiliate_id: str) -> Optional[Affiliate]:
        """Get an affiliate by ID"""
        return self._affiliates.get(affiliate_id)

    def register_user(self, user: User) -> User:
        """Register a user in the system"""
        self._users[user.user_id] = user

        # Add to affiliate's coded users if applicable
        if user.affiliate_id:
            affiliate = self._affiliates.get(user.affiliate_id)
            if affiliate and user.user_id not in affiliate.coded_users:
                affiliate.coded_users.append(user.user_id)

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self._users.get(user_id)

    def get_affiliate_users(self, affiliate_id: str) -> List[User]:
        """Get all users coded under an affiliate"""
        affiliate = self._affiliates.get(affiliate_id)
        if not affiliate:
            return []
        return [self._users[uid] for uid in affiliate.coded_users if uid in self._users]

    def get_upline_chain(self, affiliate_id: str) -> List[Affiliate]:
        """Get the complete upline chain for an affiliate (parent, grandparent, etc.)"""
        chain = []
        current = self._affiliates.get(affiliate_id)

        while current and current.parent_affiliate_id:
            parent = self._affiliates.get(current.parent_affiliate_id)
            if parent:
                chain.append(parent)
                current = parent
            else:
                break

        return chain

    def get_downline_tree(self, affiliate_id: str, max_depth: Optional[int] = None) -> Dict:
        """
        Get the complete downline tree for an affiliate.
        Returns a nested dictionary structure.
        """
        def build_tree(aff_id: str, current_depth: int = 0) -> Optional[Dict]:
            if max_depth is not None and current_depth >= max_depth:
                return None

            affiliate = self._affiliates.get(aff_id)
            if not affiliate:
                return None

            children = []
            for child_id in affiliate.child_affiliates:
                child_tree = build_tree(child_id, current_depth + 1)
                if child_tree:
                    children.append(child_tree)

            return {
                "affiliate_id": affiliate.affiliate_id,
                "name": affiliate.name,
                "level": current_depth,
                "coded_users_count": len(affiliate.coded_users),
                "children": children,
            }

        return build_tree(affiliate_id, 0) or {}

    def get_all_downline_affiliates(self, affiliate_id: str) -> List[Affiliate]:
        """Get all affiliates in the downline (flattened)"""
        result = []

        def collect(aff_id: str):
            affiliate = self._affiliates.get(aff_id)
            if affiliate:
                for child_id in affiliate.child_affiliates:
                    child = self._affiliates.get(child_id)
                    if child:
                        result.append(child)
                        collect(child_id)

        collect(affiliate_id)
        return result

    def update_affiliate_status(self, affiliate_id: str, status: AffiliateStatus) -> bool:
        """Update an affiliate's status"""
        affiliate = self._affiliates.get(affiliate_id)
        if affiliate:
            affiliate.status = status
            return True
        return False

    def set_manual_adjustment(self, affiliate_id: str, amount: Decimal) -> bool:
        """Set manual adjustment for an affiliate"""
        affiliate = self._affiliates.get(affiliate_id)
        if affiliate:
            affiliate.manual_adjustment = amount
            return True
        return False

    def get_affiliate_metrics(self, affiliate_id: str) -> Dict:
        """Get aggregated metrics for an affiliate's users"""
        users = self.get_affiliate_users(affiliate_id)

        total_bets = Decimal("0.00")
        total_payouts = Decimal("0.00")
        total_deposits = Decimal("0.00")
        total_withdrawals = Decimal("0.00")
        total_bonus = Decimal("0.00")
        active_count = 0
        new_signups = 0
        first_deposits = 0

        for user in users:
            total_bets += user.total_bets
            total_payouts += user.total_payouts
            total_deposits += user.total_deposits
            total_withdrawals += user.total_withdrawals
            total_bonus += user.total_bonus_used

            if user.is_active:
                active_count += 1
            if user.first_deposit_date:
                first_deposits += 1

        ggr = total_bets - total_payouts
        ngr = ggr - total_bonus

        return {
            "total_users": len(users),
            "active_users": active_count,
            "new_signups": new_signups,
            "first_deposits": first_deposits,
            "total_bets": total_bets,
            "total_payouts": total_payouts,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_bonus_cost": total_bonus,
            "ggr": ggr,
            "ngr": ngr,
        }

    def print_affiliate_tree(self, affiliate_id: str, indent: int = 0) -> str:
        """Print affiliate tree structure as a string"""
        result = []
        affiliate = self._affiliates.get(affiliate_id)

        if not affiliate:
            return ""

        prefix = "  " * indent + ("└── " if indent > 0 else "")
        result.append(f"{prefix}{affiliate.name} (ID: {affiliate.affiliate_id[:8]}..., Users: {len(affiliate.coded_users)})")

        for child_id in affiliate.child_affiliates:
            result.append(self.print_affiliate_tree(child_id, indent + 1))

        return "\n".join(result)
