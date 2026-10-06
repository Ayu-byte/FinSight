import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from merchant_library import MERCHANTS
from personas import PERSONAS
from utils import end_of_month, payment_method, random_time, weighted_choice

SEED = 202502
YEAR = 2025
USERS_PATH = Path('data/generated/users.csv')
OUTPUT_PATH = Path('data/generated/transactions.csv')
VALID_CATEGORIES = set(MERCHANTS)
EXPENSE_CATEGORIES = VALID_CATEGORIES - {'Income'}
VALID_TYPES = {'Income', 'Expense'}
TARGET_RANGE = (40000, 50000)

SPENDING_LIMITS = {
    'Frugal': (0.45, 0.65),
    'Balanced': (0.58, 0.78),
    'Impulsive': (0.78, 1.05),
}

ESSENTIAL_CATEGORIES = {
    'Grocery',
    'Recharge & Utilities',
    'Education',
    'Healthcare',
    'Transportation',
}
RECURRING_PLANS = [
    {'category': 'Entertainment', 'merchant': 'Spotify', 'amount': 149, 'personas': {'Hostel Student', 'Tech Enthusiast', 'Shopaholic', 'Working Student'}},
    {'category': 'Entertainment', 'merchant': 'Netflix', 'amount': 199, 'personas': {'Tech Enthusiast', 'Shopaholic', 'Working Student'}},
    {'category': 'Recharge & Utilities', 'merchant': 'Jio', 'amount': 239, 'personas': {'Budget Student', 'Day Scholar', 'Hostel Student'}},
    {'category': 'Recharge & Utilities', 'merchant': 'Airtel', 'amount': 299, 'personas': {'Traveler', 'Fitness Enthusiast', 'Working Student'}},
]
def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)


def month_days(month: int) -> list[date]:
    current = date(YEAR, month, 1)
    last = end_of_month(YEAR, month)
    days = []
    while current <= last:
        days.append(current)
        current += timedelta(days=1)
    return days


def choose_transaction_date(month: int, category: str) -> date:
    days = month_days(month)
    weights = []

    for day in days:
        weight = 1.0
        is_weekend = day.weekday() >= 5

        if is_weekend and category in {'Food & Dining', 'Entertainment', 'Shopping'}:
            weight *= 1.55
        if not is_weekend and category in {'Transportation', 'Education'}:
            weight *= 1.25
        if month in {10, 11} and category in {'Shopping', 'Food & Dining', 'Entertainment'}:
            weight *= 1.45
        if month in {5, 6, 12} and category == 'Transportation':
            weight *= 1.35
        if month in {1, 7, 8} and category == 'Education':
            weight *= 1.5

        weights.append(weight)

    return random.choices(days, weights=weights, k=1)[0]


def adjusted_category_weights(persona: str, month: int) -> dict[str, float]:
    weights = {category: float(weight) for category, weight in PERSONAS[persona]['category_weights'].items()}
    weights.setdefault('Miscellaneous', 2.0)

    if month in {10, 11}:
        weights['Shopping'] *= 1.75
        weights['Food & Dining'] *= 1.2
        weights['Entertainment'] *= 1.2
    if month in {1, 7, 8}:
        weights['Education'] *= 1.7
    if month in {5, 6, 12}:
        weights['Transportation'] *= 1.45

    return weights


def choose_merchant(category: str, month: int) -> dict[str, int | str]:
    merchants = MERCHANTS[category]
    if category == 'Education':
        regular = [merchant for merchant in merchants if merchant['name'] != 'College Fees']
        return random.choice(regular)
    if category == 'Transportation' and month in {5, 6, 12} and random.random() < 0.22:
        return next(merchant for merchant in merchants if merchant['name'] == 'IRCTC')
    return random.choice(merchants)


def scale_amount(base_amount: int, category: str, spending_habit: str, month: int) -> int:
    multiplier = 1.0
    if spending_habit == 'Frugal':
        multiplier *= random.uniform(0.72, 0.92)
        if category not in ESSENTIAL_CATEGORIES:
            multiplier *= random.uniform(0.72, 0.9)
    elif spending_habit == 'Impulsive':
        multiplier *= random.uniform(1.0, 1.28)
        if category in {'Shopping', 'Entertainment', 'Food & Dining'}:
            multiplier *= random.uniform(1.05, 1.32)
    else:
        multiplier *= random.uniform(0.88, 1.08)

    if month in {10, 11} and category in {'Shopping', 'Food & Dining', 'Entertainment'}:
        multiplier *= random.uniform(1.08, 1.32)
    if month in {1, 7, 8} and category == 'Education':
        multiplier *= random.uniform(1.08, 1.25)

    return max(20, int(round(base_amount * multiplier)))


def recurring_plan_for_user(user: pd.Series) -> dict[str, int | str] | None:
    user_id = int(user['user_id'])
    persona = str(user['persona'])
    if user_id % 5 != 0:
        return None
    eligible = [plan for plan in RECURRING_PLANS if persona in plan['personas']]
    if not eligible:
        return None
    return eligible[user_id % len(eligible)]


def add_recurring_expense(transactions: list[dict], transaction_id: int, user: pd.Series, month: int) -> int:
    plan = recurring_plan_for_user(user)
    if plan is None:
        return transaction_id

    rng = random.Random(SEED + int(user['user_id']) * 1000 + month)
    txn_date = date(YEAR, month, min(26, 5 + (int(user['user_id']) % 4) + rng.choice([-1, 0, 1])))
    base_amount = int(plan['amount'])
    amount = max(20, int(round(base_amount * rng.uniform(0.97, 1.03))))
    transactions.append(
        {
            'transaction_id': transaction_id,
            'user_id': int(user['user_id']),
            'date': txn_date.isoformat(),
            'time': random_time(str(plan['category'])),
            'type': 'Expense',
            'category': str(plan['category']),
            'merchant': str(plan['merchant']),
            'amount': amount,
            'payment_method': payment_method(str(user['payment_preference'])),
        }
    )
    return transaction_id + 1
def income_events(user: pd.Series) -> list[dict[str, int | str]]:
    persona = str(user['persona'])
    monthly_income = int(user['monthly_income'])
    events: list[dict[str, int | str]] = []

    if random.random() < 0.97:
        allowance = random.randint(int(monthly_income * 0.9), int(monthly_income * 1.08))
        events.append({'merchant': 'Monthly Allowance', 'amount': allowance})

    scholarship_probability = 0.07 if persona in {'Budget Student', 'Day Scholar'} else 0.035
    if random.random() < scholarship_probability:
        events.append({'merchant': 'Scholarship', 'amount': random.randint(5000, 25000)})

    if persona == 'Working Student':
        if random.random() < 0.82:
            events.append({'merchant': 'Internship Stipend', 'amount': random.randint(9000, 26000)})
        if random.random() < 0.45:
            events.append({'merchant': 'Freelance Payment', 'amount': random.randint(1500, 12000)})
    elif persona == 'Tech Enthusiast' and random.random() < 0.14:
        events.append({'merchant': 'Freelance Payment', 'amount': random.randint(800, 9000)})
    elif random.random() < 0.035:
        events.append({'merchant': 'Freelance Payment', 'amount': random.randint(500, 6000)})

    return events


def add_income_transactions(transactions: list[dict], transaction_id: int, user: pd.Series, month: int) -> int:
    for event in income_events(user):
        income_day = date(YEAR, month, random.randint(1, 6))
        transactions.append(
            {
                'transaction_id': transaction_id,
                'user_id': int(user['user_id']),
                'date': income_day.isoformat(),
                'time': random_time('Income'),
                'type': 'Income',
                'category': 'Income',
                'merchant': event['merchant'],
                'amount': int(event['amount']),
                'payment_method': 'Bank Transfer',
            }
        )
        transaction_id += 1
    return transaction_id


def add_college_fee(transactions: list[dict], transaction_id: int, user: pd.Series, month: int) -> int:
    if month not in {1, 7} or random.random() > 0.10:
        return transaction_id

    merchant = next(item for item in MERCHANTS['Education'] if item['name'] == 'College Fees')
    amount = random.randint(merchant['min'], min(merchant['max'], 18000))
    if str(user['spending_habit']) == 'Frugal':
        amount = int(amount * random.uniform(0.7, 0.9))

    txn_date = date(YEAR, month, random.randint(3, 18))
    transactions.append(
        {
            'transaction_id': transaction_id,
            'user_id': int(user['user_id']),
            'date': txn_date.isoformat(),
            'time': random_time('Education'),
            'type': 'Expense',
            'category': 'Education',
            'merchant': 'College Fees',
            'amount': amount,
            'payment_method': payment_method(str(user['payment_preference'])),
        }
    )
    return transaction_id + 1


def monthly_expense_budget(user: pd.Series) -> int:
    low, high = SPENDING_LIMITS[str(user['spending_habit'])]
    return int(int(user['monthly_income']) * random.uniform(low, high))


def add_expense_transactions(transactions: list[dict], transaction_id: int, user: pd.Series, month: int) -> int:
    persona = str(user['persona'])
    spending_habit = str(user['spending_habit'])
    target_count = max(12, int(round(np.random.normal(int(user['monthly_transactions']), 4))))
    target_count = int(target_count * random.uniform(0.78, 0.98))
    budget = monthly_expense_budget(user)
    spent = 0

    for index in range(target_count):
        weights = adjusted_category_weights(persona, month)
        category = weighted_choice(weights)
        merchant = choose_merchant(category, month)
        amount = scale_amount(random.randint(merchant['min'], merchant['max']), category, spending_habit, month)

        if spent > budget and category not in ESSENTIAL_CATEGORIES and random.random() < 0.72:
            essential_weights = {item: weights[item] for item in ['Grocery', 'Education', 'Healthcare', 'Transportation'] if item in weights}
            category = weighted_choice(essential_weights)
            merchant = choose_merchant(category, month)
            amount = scale_amount(random.randint(merchant['min'], merchant['max']), category, spending_habit, month)

        monthly_cap = budget * (1.18 if spending_habit == 'Impulsive' else 0.98)
        remaining_transactions = max(1, target_count - index)
        if spent + amount > monthly_cap:
            remaining_budget = max(350, monthly_cap - spent)
            amount = max(50, int((remaining_budget / remaining_transactions) * random.uniform(0.75, 1.45)))

        txn_date = choose_transaction_date(month, category)
        transactions.append(
            {
                'transaction_id': transaction_id,
                'user_id': int(user['user_id']),
                'date': txn_date.isoformat(),
                'time': random_time(category),
                'type': 'Expense',
                'category': category,
                'merchant': merchant['name'],
                'amount': amount,
                'payment_method': payment_method(str(user['payment_preference'])),
            }
        )
        transaction_id += 1
        spent += amount

    return add_college_fee(transactions, transaction_id, user, month)


def generate_transactions(users: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    seed_everything(seed)
    transactions: list[dict] = []
    transaction_id = 1

    for _, user in users.iterrows():
        for month in range(1, 13):
            transaction_id = add_income_transactions(transactions, transaction_id, user, month)
            transaction_id = add_recurring_expense(transactions, transaction_id, user, month)
            transaction_id = add_expense_transactions(transactions, transaction_id, user, month)

    transactions_df = pd.DataFrame(transactions)
    transactions_df['date'] = pd.to_datetime(transactions_df['date'])
    transactions_df['day_of_week'] = transactions_df['date'].dt.day_name()
    transactions_df['month'] = transactions_df['date'].dt.month
    transactions_df = transactions_df.sort_values(['date', 'time', 'transaction_id']).reset_index(drop=True)
    transactions_df['date'] = transactions_df['date'].dt.strftime('%Y-%m-%d')
    return transactions_df


def validate_dataset(users: pd.DataFrame, transactions: pd.DataFrame) -> dict[str, pd.Series | int | float]:
    errors = []
    critical_fields = ['transaction_id', 'user_id', 'date', 'time', 'type', 'category', 'merchant', 'amount', 'payment_method']

    if len(users) != 100:
        errors.append(f'Expected 100 users, found {len(users)}')
    if users['user_id'].duplicated().any():
        errors.append('Duplicate user_id values found')
    if transactions['transaction_id'].duplicated().any():
        errors.append('Duplicate transaction_id values found')
    if transactions[critical_fields].isna().any().any():
        errors.append('Missing critical transaction fields found')
    if not set(transactions['type']).issubset(VALID_TYPES):
        errors.append('Invalid transaction type found')
    if (transactions['amount'] <= 0).any():
        errors.append('Non-positive transaction amounts found')
    if not set(transactions['user_id']).issubset(set(users['user_id'])):
        errors.append('Transaction user_id without matching user found')

    dates = pd.to_datetime(transactions['date'])
    if dates.min().date() < date(YEAR, 1, 1) or dates.max().date() > date(YEAR, 12, 31):
        errors.append('Transaction dates outside 2025 found')

    expense_categories = set(transactions.loc[transactions['type'] == 'Expense', 'category'])
    if not expense_categories.issubset(EXPENSE_CATEGORIES):
        errors.append(f'Invalid expense categories found: {expense_categories - EXPENSE_CATEGORIES}')
    if (transactions.loc[transactions['type'] == 'Income', 'category'] != 'Income').any():
        errors.append('Income records with non-Income category found')

    persona_counts = users['persona'].value_counts().to_dict()
    expected_counts = {persona: details['count'] for persona, details in PERSONAS.items()}
    if persona_counts != expected_counts:
        errors.append(f'Persona counts mismatch: {persona_counts}')

    if not TARGET_RANGE[0] <= len(transactions) <= TARGET_RANGE[1]:
        errors.append(f'Transaction count {len(transactions)} outside target range {TARGET_RANGE}')

    forbidden_categories = {'Investments', 'Investment', 'Refunds', 'Refund'}
    if set(transactions['category']).intersection(forbidden_categories) or set(transactions['merchant']).intersection(forbidden_categories):
        errors.append('Forbidden investment/refund records found')

    if errors:
        raise ValueError('Dataset validation failed:\n- ' + '\n- '.join(errors))

    merged = transactions.merge(users[['user_id', 'persona']], on='user_id', how='left')
    expenses = merged[merged['type'] == 'Expense']
    return {
        'total_transactions': len(transactions),
        'income_count': int((transactions['type'] == 'Income').sum()),
        'expense_count': int((transactions['type'] == 'Expense').sum()),
        'transactions_per_month': transactions['month'].value_counts().sort_index(),
        'transactions_per_persona': merged['persona'].value_counts(),
        'spending_by_category': expenses.groupby('category')['amount'].sum().sort_values(ascending=False),
        'average_transaction_amount': float(transactions['amount'].mean()),
        'payment_method_distribution': transactions['payment_method'].value_counts(normalize=True).mul(100).round(2),
    }


def print_statistics(stats: dict[str, pd.Series | int | float]) -> None:
    print('=' * 58)
    print('Validation Summary')
    print('=' * 58)
    for key in ('total_transactions', 'income_count', 'expense_count', 'average_transaction_amount'):
        print('{}: {}'.format(key.replace('_' , ' ').title(), stats[key]))
    print('\nTransactions Per Month:')
    print(stats['transactions_per_month'].to_string())
    print('\nTransactions Per Persona:')
    print(stats['transactions_per_persona'].to_string())
    print('\nSpending By Category:')
    print(stats['spending_by_category'].to_string())
    print('\nPayment Method Distribution (%):')
    print(stats['payment_method_distribution'].to_string())


def main() -> None:
    if not USERS_PATH.exists():
        raise FileNotFoundError(f'{USERS_PATH} not found. Run python src/generator/generate_students.py first.')

    users = pd.read_csv(USERS_PATH)
    transactions = generate_transactions(users)
    stats = validate_dataset(users, transactions)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(OUTPUT_PATH, index=False)

    print('=' * 58)
    print('Transaction Generation Complete')
    print('=' * 58)
    print(f'Saved to {OUTPUT_PATH}')
    print_statistics(stats)


if __name__ == '__main__':
    main()



