"""
Bonus Service - handles all bonus operations
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from ..models.bonus import Bonus, BonusConfig
from ..models.user import User
from ..utils.enums import BonusType, BonusStatus


class BonusService:
    """
    Service for managing bonuses:
    - Deposit Bonus
    - Rakeback Bonus
    - Cashback Bonus
    - Special Bonus

    Handles bonus lifecycle: issue, track, claim, expire
    """

    def __init__(self):
        self._bonus_configs: Dict[str, BonusConfig] = {}
        self._bonuses: Dict[str, Bonus] = {}
        self._user_bonuses: Dict[str, List[str]] = {}  # user_id -> list of bonus_ids

    # ==================== Configuration Management ====================

    def register_bonus_config(self, config: BonusConfig) -> BonusConfig:
        """Register a new bonus configuration"""
        self._bonus_configs[config.config_id] = config
        return config

    def get_bonus_config(self, config_id: str) -> Optional[BonusConfig]:
        """Get a bonus configuration by ID"""
        return self._bonus_configs.get(config_id)

    def get_configs_by_type(self, bonus_type: BonusType) -> List[BonusConfig]:
        """Get all active configurations for a bonus type"""
        return [
            config
            for config in self._bonus_configs.values()
            if config.bonus_type == bonus_type and config.is_active
        ]

    # ==================== Deposit Bonus ====================

    def issue_deposit_bonus(
        self,
        user: User,
        deposit_amount: Decimal,
        config: Optional[BonusConfig] = None,
    ) -> Optional[Bonus]:
        """
        Issue deposit bonus to user.
        Formula: Bonus = min(Deposit × Rate, Max Bonus)
        """
        if config is None:
            configs = self.get_configs_by_type(BonusType.DEPOSIT)
            if not configs:
                return None
            config = configs[0]

        bonus_amount = config.calculate_bonus(deposit_amount)
        if bonus_amount <= 0:
            return None

        expiry = datetime.now() + timedelta(days=config.expiry_days)

        # Calculate wagering requirement
        wagering_req = None
        if config.wagering_requirement:
            wagering_req = bonus_amount * config.wagering_requirement

        bonus = Bonus(
            user_id=user.user_id,
            bonus_type=BonusType.DEPOSIT,
            config_id=config.config_id,
            amount=bonus_amount,
            wagering_requirement=wagering_req,
            status=BonusStatus.ACTIVE if wagering_req else BonusStatus.CLAIMABLE,
            expiry_date=expiry,
        )

        return self._register_bonus(bonus)

    # ==================== Rakeback Bonus ====================

    def calculate_rakeback(
        self,
        user: User,
        total_bet: Decimal,
        config: Optional[BonusConfig] = None,
    ) -> Decimal:
        """
        Calculate rakeback bonus amount.
        Formula: Rakeback = Total Bet × Rakeback Rate
        """
        if config is None:
            configs = self.get_configs_by_type(BonusType.RAKEBACK)
            if not configs:
                return Decimal("0.00")
            config = configs[0]

        return total_bet * config.rate

    def accumulate_rakeback(
        self,
        user: User,
        bet_amount: Decimal,
        config: Optional[BonusConfig] = None,
    ) -> Bonus:
        """
        Accumulate rakeback for a user (continuous accumulation).
        Returns the updated or new rakeback bonus.
        """
        if config is None:
            configs = self.get_configs_by_type(BonusType.RAKEBACK)
            if not configs:
                # Create default config if none exists
                config = BonusConfig(
                    bonus_type=BonusType.RAKEBACK,
                    name="Default Rakeback",
                    rate=Decimal("0.005"),  # 0.5% rakeback
                )
                self.register_bonus_config(config)
            else:
                config = configs[0]

        # Find existing active rakeback bonus for user
        existing_bonus = self._find_active_rakeback(user.user_id)

        rakeback_amount = bet_amount * config.rate

        if existing_bonus:
            existing_bonus.amount += rakeback_amount
            return existing_bonus
        else:
            # Create new rakeback bonus (claimable immediately, no wagering)
            bonus = Bonus(
                user_id=user.user_id,
                bonus_type=BonusType.RAKEBACK,
                config_id=config.config_id,
                amount=rakeback_amount,
                status=BonusStatus.CLAIMABLE,
                expiry_date=datetime.now() + timedelta(days=config.expiry_days),
            )
            return self._register_bonus(bonus)

    def _find_active_rakeback(self, user_id: str) -> Optional[Bonus]:
        """Find active/claimable rakeback bonus for user"""
        user_bonus_ids = self._user_bonuses.get(user_id, [])
        for bonus_id in user_bonus_ids:
            bonus = self._bonuses.get(bonus_id)
            if (
                bonus
                and bonus.bonus_type == BonusType.RAKEBACK
                and bonus.status in [BonusStatus.ACTIVE, BonusStatus.CLAIMABLE]
            ):
                return bonus
        return None

    # ==================== Cashback Bonus ====================

    def calculate_cashback(
        self,
        user: User,
        config: Optional[BonusConfig] = None,
    ) -> Decimal:
        """
        Calculate cashback bonus.
        Formula: Cashback = max(0, Bet - Payout) × Cashback Rate
        """
        if config is None:
            configs = self.get_configs_by_type(BonusType.CASHBACK)
            if not configs:
                return Decimal("0.00")
            config = configs[0]

        net_loss = user.net_loss
        return net_loss * config.rate

    def issue_cashback_bonus(
        self,
        user: User,
        config: Optional[BonusConfig] = None,
    ) -> Optional[Bonus]:
        """Issue cashback bonus based on user's net loss"""
        cashback_amount = self.calculate_cashback(user, config)
        if cashback_amount <= 0:
            return None

        if config is None:
            configs = self.get_configs_by_type(BonusType.CASHBACK)
            config = configs[0] if configs else None

        expiry_days = config.expiry_days if config else 30

        bonus = Bonus(
            user_id=user.user_id,
            bonus_type=BonusType.CASHBACK,
            config_id=config.config_id if config else None,
            amount=cashback_amount,
            status=BonusStatus.CLAIMABLE,
            expiry_date=datetime.now() + timedelta(days=expiry_days),
        )

        return self._register_bonus(bonus)

    # ==================== Special Bonus ====================

    def issue_special_bonus(
        self,
        user: User,
        amount: Decimal,
        admin_id: str,
        admin_note: str,
        wagering_requirement: Optional[Decimal] = None,
        expiry_days: int = 30,
    ) -> Bonus:
        """
        Issue special/manual bonus by admin.
        Requires admin note for audit log.
        """
        expiry = datetime.now() + timedelta(days=expiry_days)

        wagering_req = None
        if wagering_requirement:
            wagering_req = amount * wagering_requirement

        bonus = Bonus(
            user_id=user.user_id,
            bonus_type=BonusType.SPECIAL,
            amount=amount,
            wagering_requirement=wagering_req,
            status=BonusStatus.ACTIVE if wagering_req else BonusStatus.CLAIMABLE,
            expiry_date=expiry,
            admin_note=admin_note,
            issued_by=admin_id,
        )

        return self._register_bonus(bonus)

    # ==================== Bonus Lifecycle ====================

    def _register_bonus(self, bonus: Bonus) -> Bonus:
        """Register a bonus in the system"""
        self._bonuses[bonus.bonus_id] = bonus

        if bonus.user_id not in self._user_bonuses:
            self._user_bonuses[bonus.user_id] = []
        self._user_bonuses[bonus.user_id].append(bonus.bonus_id)

        return bonus

    def get_bonus(self, bonus_id: str) -> Optional[Bonus]:
        """Get a bonus by ID"""
        return self._bonuses.get(bonus_id)

    def get_user_bonuses(
        self,
        user_id: str,
        status: Optional[BonusStatus] = None,
    ) -> List[Bonus]:
        """Get all bonuses for a user, optionally filtered by status"""
        bonus_ids = self._user_bonuses.get(user_id, [])
        bonuses = [self._bonuses[bid] for bid in bonus_ids if bid in self._bonuses]

        if status:
            bonuses = [b for b in bonuses if b.status == status]

        return bonuses

    def update_wagering_progress(
        self,
        user_id: str,
        bet_amount: Decimal,
    ) -> List[Bonus]:
        """
        Update wagering progress for all active bonuses of a user.
        Returns list of bonuses that became claimable.
        """
        now_claimable = []
        bonuses = self.get_user_bonuses(user_id, status=BonusStatus.ACTIVE)

        for bonus in bonuses:
            if bonus.wagering_requirement:
                was_claimable = bonus.is_claimable
                bonus.update_wagering_progress(bet_amount)
                if not was_claimable and bonus.is_claimable:
                    now_claimable.append(bonus)

        return now_claimable

    def claim_bonus(self, bonus_id: str, user_id: str) -> bool:
        """Attempt to claim a bonus"""
        bonus = self._bonuses.get(bonus_id)
        if not bonus or bonus.user_id != user_id:
            return False

        # Check and update expiry first
        bonus.check_and_update_expiry()

        return bonus.claim()

    def process_expired_bonuses(self) -> List[Bonus]:
        """Process and expire all expired bonuses. Returns list of expired bonuses."""
        expired = []
        for bonus in self._bonuses.values():
            if bonus.check_and_update_expiry():
                expired.append(bonus)
        return expired

    # ==================== Reporting ====================

    def get_bonus_statistics(self, user_id: Optional[str] = None) -> Dict:
        """Get bonus statistics, optionally for a specific user"""
        if user_id:
            bonuses = self.get_user_bonuses(user_id)
        else:
            bonuses = list(self._bonuses.values())

        total_issued = Decimal("0.00")
        total_claimed = Decimal("0.00")
        total_expired = Decimal("0.00")
        total_pending = Decimal("0.00")

        by_type = {
            BonusType.DEPOSIT: Decimal("0.00"),
            BonusType.RAKEBACK: Decimal("0.00"),
            BonusType.CASHBACK: Decimal("0.00"),
            BonusType.SPECIAL: Decimal("0.00"),
        }

        for bonus in bonuses:
            total_issued += bonus.amount
            by_type[bonus.bonus_type] += bonus.amount

            if bonus.status == BonusStatus.CLAIMED:
                total_claimed += bonus.amount
            elif bonus.status == BonusStatus.EXPIRED:
                total_expired += bonus.amount
            elif bonus.status in [BonusStatus.ACTIVE, BonusStatus.CLAIMABLE]:
                total_pending += bonus.amount

        return {
            "total_issued": total_issued,
            "total_claimed": total_claimed,
            "total_expired": total_expired,
            "total_pending": total_pending,
            "count": len(bonuses),
            "by_type": {k.value: float(v) for k, v in by_type.items()},
        }

    def get_bonus_report(self) -> List[Dict]:
        """Get detailed bonus report"""
        return [
            {
                "bonus_id": bonus.bonus_id[:8],
                "user_id": bonus.user_id[:8],
                "type": bonus.bonus_type.value,
                "amount": float(bonus.amount),
                "status": bonus.status.value,
                "wagering_progress": float(bonus.wagering_progress),
                "wagering_required": float(bonus.wagering_requirement) if bonus.wagering_requirement else None,
                "expiry_date": bonus.expiry_date.isoformat() if bonus.expiry_date else None,
                "is_claimable": bonus.is_claimable,
            }
            for bonus in self._bonuses.values()
        ]
