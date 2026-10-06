import random
from pathlib import Path

import pandas as pd

from merchant_library import MERCHANTS
from personas import PERSONAS

SEED = 202503
YEAR = 2025
USERS_PATH = Path('data/generated/users.csv')
OUTPUT_PATH = Path('data/generated/budgets.csv')
EXPENSE_CATEGORIES = sorted(set(MERCHANTS) - {'Income'})

BUDGET_RATIO_BY_HABIT = {
    'Frugal': 0.58,
    'Balanced': 0.72,
    'Impulsive': 0.88,
}

PERSONA_CATEGORY_MULTIPLIERS = {
    'Budget Student': {'Shopping': 0.62, 'Entertainment': 0.68, 'Food & Dining': 0.82, 'Grocery': 1.18, 'Education': 1.12},
    'Shopaholic': {'Shopping': 1.42, 'Entertainment': 1.12, 'Food & Dining': 1.08},
    'Traveler': {'Transportation': 1.45, 'Food & Dining': 1.06},
    'Hostel Student': {'Food & Dining': 1.35, 'Grocery': 1.12, 'Transportation': 0.78},
    'Day Scholar': {'Transportation': 1.28, 'Food & Dining': 0.92},
    'Tech Enthusiast': {'Education': 1.22, 'Entertainment': 1.12, 'Shopping': 1.08},
    'Fitness Enthusiast': {'Grocery': 1.18, 'Healthcare': 1.32, 'Entertainment': 0.82},
    'Working Student': {'Education': 1.18, 'Shopping': 1.08, 'Food & Dining': 1.06},
}


def adjusted_budget_weights(persona: str, month: int) -> dict[str, float]:
    weights = {category: float(weight) for category, weight in PERSONAS[persona]['category_weights'].items()}
    weights.setdefault('Miscellaneous', 2.0)

    for category, multiplier in PERSONA_CATEGORY_MULTIPLIERS.get(persona, {}).items():
        if category in weights:
            weights[category] *= multiplier

    if month in {10, 11}:
        weights['Shopping'] *= 1.22
        weights['Food & Dining'] *= 1.08
        weights['Entertainment'] *= 1.08
    if month in {5, 6, 12}:
        weights['Transportation'] *= 1.18
    if month in {1, 7, 8}:
        weights['Education'] *= 1.2

    return {category: weights.get(category, 1.0) for category in EXPENSE_CATEGORIES}


def planned_monthly_total(user: pd.Series, month: int) -> float:
    income = float(user['monthly_income'])
    habit_ratio = BUDGET_RATIO_BY_HABIT[str(user['spending_habit'])]
    persona = str(user['persona'])
    rng = random.Random(SEED + int(user['user_id']) * 100 + month)
    persona_adjustment = {'Budget Student': 0.9, 'Shopaholic': 1.08, 'Traveler': 1.04, 'Working Student': 0.96}.get(persona, 1.0)

    seasonal_adjustment = 1.0
    if month in {10, 11}:
        seasonal_adjustment += 0.08
    if month in {1, 7}:
        seasonal_adjustment += 0.06
    if month in {5, 6, 12}:
        seasonal_adjustment += 0.04

    return income * habit_ratio * persona_adjustment * seasonal_adjustment * rng.uniform(0.94, 1.07)


def generate_budgets(users: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    rows = []
    budget_id = 1

    for _, user in users.iterrows():
        for month in range(1, 13):
            weights = adjusted_budget_weights(str(user['persona']), month)
            total_weight = sum(weights.values())
            monthly_total = planned_monthly_total(user, month)

            for category in EXPENSE_CATEGORIES:
                rng = random.Random(seed + int(user['user_id']) * 10000 + month * 100 + sum(ord(char) for char in category))
                variation = rng.uniform(0.9, 1.12)
                amount = round((monthly_total * weights[category] / total_weight) * variation, 2)
                rows.append({'budget_id': budget_id, 'user_id': int(user['user_id']), 'category': category, 'month': month, 'year': YEAR, 'budget_amount': max(100.0, amount)})
                budget_id += 1

    return pd.DataFrame(rows)


def validate_budgets(users: pd.DataFrame, budgets: pd.DataFrame) -> None:
    errors = []
    if not set(budgets['user_id']).issubset(set(users['user_id'])):
        errors.append('Budget user_id without matching user found')
    if not set(budgets['category']).issubset(set(EXPENSE_CATEGORIES)):
        errors.append('Invalid budget category found')
    if not budgets['month'].between(1, 12).all():
        errors.append('Invalid budget month found')
    if (budgets['budget_amount'] <= 0).any():
        errors.append('Non-positive budget amounts found')
    if budgets.duplicated(['user_id', 'category', 'month', 'year']).any():
        errors.append('Duplicate user/category/month/year budget rows found')
    expected_rows = len(users) * 12 * len(EXPENSE_CATEGORIES)
    if len(budgets) != expected_rows:
        errors.append(f'Expected {expected_rows} budget rows, found {len(budgets)}')

    if errors:
        raise ValueError('Budget validation failed:\n- ' + '\n- '.join(errors))


def main() -> None:
    if not USERS_PATH.exists():
        raise FileNotFoundError(f'{USERS_PATH} not found. Run python src/generator/generate_students.py first.')

    users = pd.read_csv(USERS_PATH)
    budgets = generate_budgets(users)
    validate_budgets(users, budgets)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    budgets.to_csv(OUTPUT_PATH, index=False)
    print('=' * 58)
    print('Budget Generation Complete')
    print('=' * 58)
    print(f'Saved to {OUTPUT_PATH}')
    print(f'Budget rows: {len(budgets)}')


if __name__ == '__main__':
    main()
