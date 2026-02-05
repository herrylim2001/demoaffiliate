# Affiliate & Bonus System Demo

Demo prototype sistem affiliate dan bonus berdasarkan Functional Specification Document v1.0.

## Features

### Affiliate Module
- **Multi-level Affiliate Structure** - Unlimited depth affiliate tree
- **Commission Plan Types**:
  - Revenue Share (NGR/GGR based)
  - Wager/Rakeback
  - Count-based (Signup, First Deposit, Active User)
  - Deposit-Withdrawal
  - Hybrid (multiple plans)
- **DSR (Dynamic Slicing Rule)** - Tier-based commission rates
  - Flat calculation (single rate for entire base)
  - Non-Flat/Marginal calculation (rate per tier segment)
- **Admin Cost & Deductions**
- **Manual Adjustment**
- **Multi-level Commission Distribution**

### Bonus Module
- **Deposit Bonus** - Match bonus with max cap
- **Rakeback Bonus** - Continuous accumulation from wagers
- **Cashback Bonus** - Based on net losses
- **Special Bonus** - Manual admin-issued bonus
- **Wagering Requirements**
- **Bonus Expiry**

## Project Structure

```
demoaffiliate/
├── src/
│   ├── models/
│   │   ├── affiliate.py     # Affiliate, CommissionPlan, DSRTier
│   │   ├── bonus.py         # Bonus, BonusConfig
│   │   ├── commission.py    # CommissionStatement, CommissionPeriod
│   │   ├── transaction.py   # Transaction model
│   │   └── user.py          # User model
│   ├── services/
│   │   ├── affiliate_service.py      # Affiliate tree management
│   │   ├── commission_calculator.py  # Commission calculation engine
│   │   └── bonus_service.py          # Bonus management
│   └── utils/
│       └── enums.py         # All enums and constants
├── demo/
│   └── run_demo.py          # Comprehensive demo runner
├── tests/
│   ├── test_commission.py   # Commission calculation tests
│   └── test_bonus.py        # Bonus system tests
├── requirements.txt
└── README.md
```

## Quick Start

### Run Demo

```bash
cd demoaffiliate
python -m demo.run_demo
```

### Run Tests

```bash
# Using unittest
python -m pytest tests/ -v

# Or directly
python -m unittest discover tests/
```

## Key Formulas

### Revenue Metrics
```
GGR = Total Bet - Total Payout
NGR = GGR - Bonus Cost
```

### Commission Calculation
```
Revenue Share: Base × Rate
Wager/Rakeback: Total Bet × Rate
Count-based: Event Count × Fixed Payout
Deposit-Withdrawal: (Deposit - Withdrawal) × Rate
```

### DSR Flat vs Non-Flat
- **Flat**: Single tier rate applied to entire base
- **Non-Flat**: Marginal rate applied per tier segment

### Deductions
```
AdminCost = NGR × AdminRoyaltyRate
Net_AfterCost = Total_Gross - AdminCost - BonusDeduction - BalanceDeduction
NetCommission = Net_AfterCost + ManualAdjustment
```

### Multi-Level Commission
```
UplineCommission = ChildNetCommission × UplineRate
```

### Bonus Formulas
```
Deposit Bonus = min(Deposit × Rate, MaxBonus)
Rakeback = Total Bet × Rakeback Rate
Cashback = max(0, Bet - Payout) × Cashback Rate
```

## Example Output

```
======================================================================
 AFFILIATE & BONUS SYSTEM DEMO
======================================================================

--- DEMO 1: Multi-Level Affiliate Structure ---

Affiliate Tree Structure:
Master Affiliate Corp (ID: a1b2c3d4..., Users: 3)
└── Sub-Affiliate A (ID: e5f6g7h8..., Users: 5)
    └── Sub-Sub-Affiliate A1 (ID: i9j0k1l2..., Users: 0)
    └── Sub-Sub-Affiliate A2 (ID: m3n4o5p6..., Users: 0)
└── Sub-Affiliate B (ID: q7r8s9t0..., Users: 4)

--- DEMO 2: DSR Commission Calculation ---

DSR Tiers Configuration:
  $0 - $10,000: 25%
  $10,000 - $50,000: 30%
  $50,000 - $100,000: 35%
  $100,000 - ∞: 40%

FLAT Calculation:
  NGR $75,000 → Rate: 35% → Commission: $26,250

NON-FLAT Calculation:
  NGR $75,000 breakdown:
    $0 - $10,000 × 25% = $2,500
    $10,000 - $50,000 × 30% = $12,000
    $50,000 - $75,000 × 35% = $8,750
    Total = $23,250
```

## API Usage

### Create Affiliate with Commission Plan

```python
from src.models.affiliate import Affiliate, CommissionPlan, DSRTier
from src.services.affiliate_service import AffiliateService
from src.utils.enums import CommissionPlanType, BaseType, RateMode

# Initialize service
affiliate_service = AffiliateService()

# Create commission plan
plan = CommissionPlan(
    plan_type=CommissionPlanType.REVENUE_SHARE,
    name="Premium Revenue Share",
    base_type=BaseType.NGR,
    rate_mode=RateMode.FIXED,
    fixed_rate=Decimal("0.35"),  # 35%
)

# Create affiliate
affiliate = Affiliate(
    name="My Affiliate",
    admin_royalty_rate=Decimal("0.05"),
    commission_plans=[plan],
)
affiliate_service.register_affiliate(affiliate)
```

### Calculate Commission

```python
from src.services.commission_calculator import CommissionCalculator
from src.models.commission import CommissionPeriod

calculator = CommissionCalculator(affiliate_service)
period = CommissionPeriod(start_date=datetime(2026, 2, 1), end_date=datetime(2026, 2, 28))

statement = calculator.calculate_commission(affiliate, period)
print(f"Net Commission: ${statement.net_commission}")
```

### Issue Bonus

```python
from src.services.bonus_service import BonusService
from src.models.bonus import BonusConfig
from src.utils.enums import BonusType

bonus_service = BonusService()

config = BonusConfig(
    bonus_type=BonusType.DEPOSIT,
    name="Welcome Bonus",
    rate=Decimal("1.00"),  # 100% match
    max_bonus=Decimal("500.00"),
    wagering_requirement=Decimal("30"),
)
bonus_service.register_bonus_config(config)

bonus = bonus_service.issue_deposit_bonus(user, Decimal("200.00"), config)
```

## License

MIT License - Demo/Prototype Only
