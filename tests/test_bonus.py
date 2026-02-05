"""
Tests for Bonus System
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from decimal import Decimal
from datetime import datetime, timedelta

from src.models.bonus import Bonus, BonusConfig
from src.models.user import User
from src.services.bonus_service import BonusService
from src.utils.enums import BonusType, BonusStatus


class TestDepositBonus(unittest.TestCase):
    """Test Deposit Bonus functionality"""

    def setUp(self):
        self.bonus_service = BonusService()
        self.user = User(username="test_user")

        self.config = BonusConfig(
            bonus_type=BonusType.DEPOSIT,
            name="Welcome Bonus",
            rate=Decimal("1.00"),  # 100% match
            max_bonus=Decimal("500.00"),
            min_trigger_amount=Decimal("50.00"),
            wagering_requirement=Decimal("30"),
            expiry_days=30,
        )
        self.bonus_service.register_bonus_config(self.config)

    def test_deposit_bonus_calculation(self):
        """Test deposit bonus is calculated correctly"""
        bonus = self.bonus_service.issue_deposit_bonus(
            self.user, Decimal("200.00"), self.config
        )

        self.assertIsNotNone(bonus)
        self.assertEqual(bonus.amount, Decimal("200.00"))
        self.assertEqual(bonus.wagering_requirement, Decimal("6000.00"))  # 200 * 30

    def test_deposit_bonus_max_cap(self):
        """Test deposit bonus respects max cap"""
        bonus = self.bonus_service.issue_deposit_bonus(
            self.user, Decimal("1000.00"), self.config
        )

        self.assertIsNotNone(bonus)
        self.assertEqual(bonus.amount, Decimal("500.00"))  # Capped at max

    def test_deposit_bonus_min_trigger(self):
        """Test deposit bonus requires minimum amount"""
        bonus = self.bonus_service.issue_deposit_bonus(
            self.user, Decimal("30.00"), self.config
        )

        self.assertIsNone(bonus)  # Below minimum

    def test_deposit_bonus_status(self):
        """Test deposit bonus has correct initial status"""
        bonus = self.bonus_service.issue_deposit_bonus(
            self.user, Decimal("100.00"), self.config
        )

        self.assertEqual(bonus.status, BonusStatus.ACTIVE)  # Has wagering req


class TestRakebackBonus(unittest.TestCase):
    """Test Rakeback Bonus functionality"""

    def setUp(self):
        self.bonus_service = BonusService()
        self.user = User(username="rakeback_user")

        self.config = BonusConfig(
            bonus_type=BonusType.RAKEBACK,
            name="VIP Rakeback",
            rate=Decimal("0.005"),  # 0.5%
            expiry_days=7,
        )
        self.bonus_service.register_bonus_config(self.config)

    def test_rakeback_calculation(self):
        """Test rakeback is calculated correctly"""
        rakeback = self.bonus_service.calculate_rakeback(
            self.user, Decimal("10000.00"), self.config
        )

        self.assertEqual(rakeback, Decimal("50.00"))  # 10000 * 0.005

    def test_rakeback_accumulation(self):
        """Test rakeback accumulates correctly"""
        # First bet
        bonus = self.bonus_service.accumulate_rakeback(
            self.user, Decimal("5000.00"), self.config
        )
        self.assertEqual(bonus.amount, Decimal("25.00"))

        # Second bet - should accumulate
        bonus = self.bonus_service.accumulate_rakeback(
            self.user, Decimal("5000.00"), self.config
        )
        self.assertEqual(bonus.amount, Decimal("50.00"))

    def test_rakeback_is_claimable(self):
        """Test rakeback is immediately claimable (no wagering)"""
        bonus = self.bonus_service.accumulate_rakeback(
            self.user, Decimal("10000.00"), self.config
        )

        self.assertEqual(bonus.status, BonusStatus.CLAIMABLE)
        self.assertTrue(bonus.is_claimable)


class TestCashbackBonus(unittest.TestCase):
    """Test Cashback Bonus functionality"""

    def setUp(self):
        self.bonus_service = BonusService()

        self.config = BonusConfig(
            bonus_type=BonusType.CASHBACK,
            name="Weekly Cashback",
            rate=Decimal("0.10"),  # 10%
            expiry_days=7,
        )
        self.bonus_service.register_bonus_config(self.config)

    def test_cashback_calculation(self):
        """Test cashback is calculated from net loss"""
        user = User(
            username="cashback_user",
            total_bets=Decimal("10000"),
            total_payouts=Decimal("8000"),
        )

        # Net loss = 10000 - 8000 = 2000
        # Cashback = 2000 * 0.10 = 200

        cashback = self.bonus_service.calculate_cashback(user, self.config)
        self.assertEqual(cashback, Decimal("200.0"))

    def test_cashback_no_loss(self):
        """Test no cashback when player is winning"""
        user = User(
            username="winner_user",
            total_bets=Decimal("10000"),
            total_payouts=Decimal("12000"),  # Winning
        )

        cashback = self.bonus_service.calculate_cashback(user, self.config)
        self.assertEqual(cashback, Decimal("0.00"))

    def test_cashback_bonus_issue(self):
        """Test cashback bonus is issued correctly"""
        user = User(
            username="cashback_user",
            total_bets=Decimal("5000"),
            total_payouts=Decimal("4000"),
        )

        bonus = self.bonus_service.issue_cashback_bonus(user, self.config)

        self.assertIsNotNone(bonus)
        self.assertEqual(bonus.amount, Decimal("100.0"))  # 1000 * 0.10
        self.assertEqual(bonus.status, BonusStatus.CLAIMABLE)


class TestSpecialBonus(unittest.TestCase):
    """Test Special/Manual Bonus functionality"""

    def setUp(self):
        self.bonus_service = BonusService()
        self.user = User(username="special_user")

    def test_special_bonus_instant(self):
        """Test instant special bonus (no wagering)"""
        bonus = self.bonus_service.issue_special_bonus(
            self.user,
            amount=Decimal("100.00"),
            admin_id="admin_001",
            admin_note="VIP reward",
        )

        self.assertEqual(bonus.amount, Decimal("100.00"))
        self.assertEqual(bonus.status, BonusStatus.CLAIMABLE)
        self.assertEqual(bonus.admin_note, "VIP reward")
        self.assertEqual(bonus.issued_by, "admin_001")

    def test_special_bonus_with_wagering(self):
        """Test special bonus with wagering requirement"""
        bonus = self.bonus_service.issue_special_bonus(
            self.user,
            amount=Decimal("50.00"),
            admin_id="admin_001",
            admin_note="Promo bonus",
            wagering_requirement=Decimal("10"),
        )

        self.assertEqual(bonus.status, BonusStatus.ACTIVE)
        self.assertEqual(bonus.wagering_requirement, Decimal("500.00"))  # 50 * 10


class TestBonusLifecycle(unittest.TestCase):
    """Test Bonus lifecycle (wagering, claiming, expiry)"""

    def setUp(self):
        self.bonus_service = BonusService()
        self.user = User(username="lifecycle_user")

    def test_wagering_progress(self):
        """Test wagering progress tracking"""
        bonus = self.bonus_service.issue_special_bonus(
            self.user,
            amount=Decimal("100.00"),
            admin_id="admin",
            admin_note="Test",
            wagering_requirement=Decimal("10"),  # 1000 total wagering
        )

        # Progress 500 in wagers
        self.bonus_service.update_wagering_progress(
            self.user.user_id, Decimal("500.00")
        )

        bonus = self.bonus_service.get_bonus(bonus.bonus_id)
        self.assertEqual(bonus.wagering_progress, Decimal("500.00"))
        self.assertEqual(bonus.wagering_remaining, Decimal("500.00"))
        self.assertFalse(bonus.is_claimable)

    def test_wagering_completion(self):
        """Test bonus becomes claimable when wagering completed"""
        bonus = self.bonus_service.issue_special_bonus(
            self.user,
            amount=Decimal("100.00"),
            admin_id="admin",
            admin_note="Test",
            wagering_requirement=Decimal("10"),
        )

        # Complete wagering
        claimable = self.bonus_service.update_wagering_progress(
            self.user.user_id, Decimal("1000.00")
        )

        self.assertEqual(len(claimable), 1)
        self.assertEqual(claimable[0].bonus_id, bonus.bonus_id)

        bonus = self.bonus_service.get_bonus(bonus.bonus_id)
        self.assertEqual(bonus.status, BonusStatus.CLAIMABLE)
        self.assertTrue(bonus.is_claimable)

    def test_bonus_claim(self):
        """Test bonus claiming"""
        bonus = self.bonus_service.issue_special_bonus(
            self.user,
            amount=Decimal("50.00"),
            admin_id="admin",
            admin_note="Test",
        )

        result = self.bonus_service.claim_bonus(bonus.bonus_id, self.user.user_id)

        self.assertTrue(result)
        bonus = self.bonus_service.get_bonus(bonus.bonus_id)
        self.assertEqual(bonus.status, BonusStatus.CLAIMED)
        self.assertIsNotNone(bonus.claimed_at)

    def test_bonus_expiry(self):
        """Test bonus expiry"""
        bonus = Bonus(
            user_id=self.user.user_id,
            bonus_type=BonusType.DEPOSIT,
            amount=Decimal("100.00"),
            status=BonusStatus.ACTIVE,
            expiry_date=datetime.now() - timedelta(days=1),  # Expired
        )
        self.bonus_service._register_bonus(bonus)

        self.assertTrue(bonus.is_expired)
        self.assertFalse(bonus.is_claimable)

        # Process expired bonuses
        expired = self.bonus_service.process_expired_bonuses()
        self.assertEqual(len(expired), 1)

        bonus = self.bonus_service.get_bonus(bonus.bonus_id)
        self.assertEqual(bonus.status, BonusStatus.EXPIRED)


class TestBonusStatistics(unittest.TestCase):
    """Test bonus statistics and reporting"""

    def setUp(self):
        self.bonus_service = BonusService()
        self.user = User(username="stats_user")

    def test_statistics(self):
        """Test bonus statistics calculation"""
        # Issue various bonuses
        self.bonus_service.issue_special_bonus(
            self.user, Decimal("100.00"), "admin", "Test 1"
        )
        self.bonus_service.issue_special_bonus(
            self.user, Decimal("200.00"), "admin", "Test 2"
        )

        stats = self.bonus_service.get_bonus_statistics(self.user.user_id)

        self.assertEqual(stats["total_issued"], Decimal("300.00"))
        self.assertEqual(stats["count"], 2)


if __name__ == "__main__":
    unittest.main()
