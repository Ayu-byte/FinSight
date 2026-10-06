from pathlib import Path

import pandas as pd

from analytics.anomalies import detect_spending_anomalies
from analytics.benchmarking import benchmark_insights, calculate_peer_benchmarks

ROOT = Path(__file__).resolve().parents[2]
USERS_PATH = ROOT / 'data' / 'generated' / 'users.csv'
TRANSACTIONS_PATH = ROOT / 'data' / 'generated' / 'transactions.csv'
BUDGETS_PATH = ROOT / 'data' / 'generated' / 'budgets.csv'
DISCRETIONARY_CATEGORIES = {'Food & Dining', 'Shopping', 'Entertainment', 'Friends & Family', 'Miscellaneous'}
ESSENTIAL_CATEGORIES = {'Grocery', 'Recharge & Utilities', 'Education', 'Healthcare', 'Transportation'}


def load_data(users_path: Path = USERS_PATH, transactions_path: Path = TRANSACTIONS_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not users_path.exists() or not transactions_path.exists():
        raise FileNotFoundError('Generated CSV files were not found. Run the generator scripts first.')

    users = pd.read_csv(users_path)
    transactions = pd.read_csv(transactions_path, parse_dates=['date'])
    transactions['amount'] = pd.to_numeric(transactions['amount'])
    transactions['month'] = transactions['date'].dt.month
    transactions['year'] = transactions['date'].dt.year
    transactions['month_name'] = transactions['date'].dt.strftime('%b')
    transactions['day_of_week'] = transactions['date'].dt.day_name()
    return users, transactions


def load_budgets(budgets_path: Path = BUDGETS_PATH) -> pd.DataFrame:
    if not budgets_path.exists():
        return pd.DataFrame(columns=['budget_id', 'user_id', 'category', 'month', 'year', 'budget_amount'])
    budgets = pd.read_csv(budgets_path)
    budgets['budget_amount'] = pd.to_numeric(budgets['budget_amount'])
    return budgets


def enrich_transactions(users: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    profile_columns = ['user_id', 'name', 'persona', 'spending_habit', 'payment_preference', 'monthly_income']
    merged = transactions.merge(users[profile_columns], on='user_id', how='left')
    merged['spend_group'] = merged['category'].map(
        lambda category: 'Discretionary' if category in DISCRETIONARY_CATEGORIES else 'Essential' if category in ESSENTIAL_CATEGORIES else 'Income'
    )
    return merged


def filter_transactions(data: pd.DataFrame, personas: list[str] | None = None, users: list[int] | None = None, categories: list[str] | None = None, types: list[str] | None = None, month_range: tuple[int, int] | None = None) -> pd.DataFrame:
    filtered = data.copy()
    if personas:
        filtered = filtered[filtered['persona'].isin(personas)]
    if users:
        filtered = filtered[filtered['user_id'].isin(users)]
    if categories:
        filtered = filtered[filtered['category'].isin(categories)]
    if types:
        filtered = filtered[filtered['type'].isin(types)]
    if month_range:
        filtered = filtered[filtered['month'].between(month_range[0], month_range[1])]
    return filtered


def kpis(data: pd.DataFrame) -> dict[str, float | str]:
    income = data.loc[data['type'] == 'Income', 'amount'].sum()
    expenses = data.loc[data['type'] == 'Expense', 'amount'].sum()
    net_savings = income - expenses
    savings_rate = (net_savings / income * 100) if income else 0
    expense_rows = data[data['type'] == 'Expense']
    highest_category = expense_rows.groupby('category')['amount'].sum().idxmax() if not expense_rows.empty else 'N/A'
    highest_month = expense_rows.groupby('month_name')['amount'].sum().idxmax() if not expense_rows.empty else 'N/A'
    return {'total_income': float(income), 'total_expenses': float(expenses), 'net_savings': float(net_savings), 'savings_rate': float(savings_rate), 'average_transaction_value': float(data['amount'].mean()) if not data.empty else 0, 'highest_spending_category': highest_category, 'highest_spending_month': highest_month}


def monthly_trend(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=['month', 'month_name', 'type', 'amount'])
    trend = data.groupby(['month', 'month_name', 'type'], as_index=False)['amount'].sum()
    return trend.sort_values('month')


def spending_by_category(data: pd.DataFrame) -> pd.DataFrame:
    expenses = data[data['type'] == 'Expense']
    if expenses.empty:
        return pd.DataFrame(columns=['category', 'amount'])
    return expenses.groupby('category', as_index=False)['amount'].sum().sort_values('amount', ascending=False)


def top_merchants(data: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    expenses = data[data['type'] == 'Expense']
    if expenses.empty:
        return pd.DataFrame(columns=['merchant', 'amount', 'transactions'])
    return expenses.groupby('merchant', as_index=False).agg(amount=('amount', 'sum'), transactions=('transaction_id', 'count')).sort_values('amount', ascending=False).head(limit)


def persona_category_matrix(data: pd.DataFrame) -> pd.DataFrame:
    expenses = data[data['type'] == 'Expense']
    if expenses.empty:
        return pd.DataFrame()
    return expenses.pivot_table(index='persona', columns='category', values='amount', aggfunc='sum', fill_value=0)


def behavioral_summary(data: pd.DataFrame) -> pd.DataFrame:
    expenses = data[data['type'] == 'Expense'].copy()
    if expenses.empty:
        return pd.DataFrame(columns=['persona', 'week_part', 'amount', 'transactions'])
    expenses['week_part'] = expenses['date'].dt.weekday.map(lambda day: 'Weekend' if day >= 5 else 'Weekday')
    return expenses.groupby(['persona', 'week_part'], as_index=False).agg(amount=('amount', 'sum'), transactions=('transaction_id', 'count'))


def budget_vs_actual(transactions: pd.DataFrame, budgets: pd.DataFrame, user_id: int, month: int, year: int = 2025, categories: list[str] | None = None) -> pd.DataFrame:
    budget_rows = budgets[(budgets['user_id'] == user_id) & (budgets['month'] == month) & (budgets['year'] == year)]
    if categories:
        budget_rows = budget_rows[budget_rows['category'].isin(categories)]
    actual_rows = transactions[(transactions['user_id'] == user_id) & (transactions['type'] == 'Expense') & (transactions['month'] == month) & (transactions['year'] == year)]
    if categories:
        actual_rows = actual_rows[actual_rows['category'].isin(categories)]

    actual = actual_rows.groupby('category', as_index=False)['amount'].sum().rename(columns={'amount': 'actual_amount'})
    result = budget_rows[['category', 'budget_amount']].merge(actual, on='category', how='left')
    result['actual_amount'] = result['actual_amount'].fillna(0.0)
    result['variance'] = result['actual_amount'] - result['budget_amount']
    result['variance_pct'] = result.apply(lambda row: (row['variance'] / row['budget_amount'] * 100) if row['budget_amount'] else pd.NA, axis=1)
    result['budget_utilization_pct'] = result.apply(lambda row: (row['actual_amount'] / row['budget_amount'] * 100) if row['budget_amount'] else pd.NA, axis=1)
    result['status'] = result['budget_utilization_pct'].map(lambda pct: 'No Budget' if pd.isna(pct) else 'Within Budget' if pct < 80 else 'Near Limit' if pct <= 100 else 'Over Budget')
    return result.sort_values('actual_amount', ascending=False)


def budget_summary(budget_analysis: pd.DataFrame) -> dict[str, float]:
    budget = float(budget_analysis['budget_amount'].sum()) if not budget_analysis.empty else 0.0
    actual = float(budget_analysis['actual_amount'].sum()) if not budget_analysis.empty else 0.0
    variance = actual - budget
    utilization = (actual / budget * 100) if budget else 0.0
    return {'total_budget': budget, 'actual_spending': actual, 'variance': variance, 'utilization_pct': utilization}


def previous_month(month: int, year: int) -> tuple[int, int]:
    return (12, year - 1) if month == 1 else (month - 1, year)


def month_over_month(transactions: pd.DataFrame, user_id: int, month: int, year: int = 2025, categories: list[str] | None = None) -> dict[str, object]:
    prev_month, prev_year = previous_month(month, year)
    expenses = transactions[(transactions['user_id'] == user_id) & (transactions['type'] == 'Expense')]
    if categories:
        expenses = expenses[expenses['category'].isin(categories)]

    current_rows = expenses[(expenses['month'] == month) & (expenses['year'] == year)]
    previous_rows = expenses[(expenses['month'] == prev_month) & (expenses['year'] == prev_year)]
    current_total = float(current_rows['amount'].sum())
    previous_total = float(previous_rows['amount'].sum())
    change = current_total - previous_total
    pct_change = (change / previous_total * 100) if previous_total else None

    current = current_rows.groupby('category')['amount'].sum()
    previous = previous_rows.groupby('category')['amount'].sum()
    table = pd.concat([previous.rename('previous_amount'), current.rename('current_amount')], axis=1).fillna(0).reset_index()
    if table.empty:
        table = pd.DataFrame(columns=['category', 'previous_amount', 'current_amount'])
    table['change'] = table['current_amount'] - table['previous_amount']
    table['change_pct'] = table.apply(lambda row: (row['change'] / row['previous_amount'] * 100) if row['previous_amount'] else pd.NA, axis=1)
    table['change_label'] = table.apply(lambda row: 'New spending this month' if row['previous_amount'] == 0 and row['current_amount'] > 0 else 'No prior spending' if row['previous_amount'] == 0 else f"{row['change_pct']:.1f}%", axis=1)

    increases = table[table['change'] > 0].sort_values('change', ascending=False)
    decreases = table[table['change'] < 0].sort_values('change')
    return {'current_total': current_total, 'previous_total': previous_total, 'change': change, 'pct_change': pct_change, 'previous_month': prev_month, 'previous_year': prev_year, 'category_comparison': table.sort_values('current_amount', ascending=False), 'largest_increase': increases.iloc[0].to_dict() if not increases.empty else None, 'largest_decrease': decreases.iloc[0].to_dict() if not decreases.empty else None}


def _month_label(month: int, year: int) -> str:
    return pd.Timestamp(year=year, month=month, day=1).strftime('%B')


def _diversify_insights(insights: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    type_counts: dict[str, int] = {}
    used_categories: set[str] = set()

    for insight in sorted(insights, key=lambda item: item['priority'], reverse=True):
        insight_type = str(insight['type'])
        category = str(insight.get('category', ''))
        if type_counts.get(insight_type, 0) >= 2:
            continue
        if category and category in used_categories:
            continue
        selected.append(insight)
        type_counts[insight_type] = type_counts.get(insight_type, 0) + 1
        if category:
            used_categories.add(category)
        if len(selected) == limit:
            return selected

    for insight in sorted(insights, key=lambda item: item['priority'], reverse=True):
        insight_type = str(insight['type'])
        if insight not in selected and type_counts.get(insight_type, 0) < 2:
            selected.append(insight)
            type_counts[insight_type] = type_counts.get(insight_type, 0) + 1
        if len(selected) == limit:
            break
    return selected


def generate_insights(transactions: pd.DataFrame, budgets: pd.DataFrame, users: pd.DataFrame, user_id: int, month: int, year: int = 2025, categories: list[str] | None = None, limit: int = 5) -> list[dict[str, object]]:
    budget_df = budget_vs_actual(transactions, budgets, user_id, month, year, categories)
    mom = month_over_month(transactions, user_id, month, year, categories)
    month_rows = transactions[(transactions['user_id'] == user_id) & (transactions['month'] == month) & (transactions['year'] == year)]
    if categories:
        month_rows = month_rows[month_rows['category'].isin(categories)]
    expenses = month_rows[month_rows['type'] == 'Expense']
    insights = []

    for row in budget_df.assign(abs_variance=lambda df: df['variance'].abs()).sort_values('abs_variance', ascending=False).head(5).itertuples():
        if row.budget_amount <= 0:
            continue
        variance_pct = row.variance / row.budget_amount * 100
        impact = abs(float(row.variance))
        if row.variance > 750 and row.budget_utilization_pct >= 115:
            priority = 80 + min(35, impact / 250) + min(20, abs(variance_pct) / 4)
            insights.append({'type': 'Budget', 'priority': priority, 'severity': 'high', 'title': 'Budget overrun', 'category': row.category, 'message': f'{row.category} exceeded its {_month_label(month, year)} budget by ₹{row.variance:,.0f} ({variance_pct:.1f}%).'})
        elif row.variance < -750 and row.budget_utilization_pct <= 70:
            priority = 48 + min(22, impact / 350) + min(12, abs(variance_pct) / 8)
            insights.append({'type': 'Budget', 'priority': priority, 'severity': 'normal', 'title': 'Below budget', 'category': row.category, 'message': f'{row.category} remained ₹{abs(row.variance):,.0f} below budget this month.'})

    for row in mom['category_comparison'].itertuples():
        impact = abs(float(row.change))
        if row.previous_amount > 0 and impact >= 750 and abs(row.change_pct) >= 20:
            direction = 'increased' if row.change > 0 else 'decreased'
            priority = 68 + min(35, impact / 300) + min(18, abs(row.change_pct) / 6)
            insights.append({'type': 'MoM', 'priority': priority, 'severity': 'high' if row.change > 0 else 'normal', 'title': 'Month-over-month change', 'category': row.category, 'message': f'{row.category} spending {direction} {abs(row.change_pct):.1f}% compared with last month (₹{impact:,.0f} change).'})
        elif row.previous_amount == 0 and row.current_amount >= 1000:
            insights.append({'type': 'MoM', 'priority': 58 + min(20, row.current_amount / 300), 'severity': 'normal', 'title': 'New category spend', 'category': row.category, 'message': f'{row.category} had new spending this month at ₹{row.current_amount:,.0f}.'})

    income = float(month_rows.loc[month_rows['type'] == 'Income', 'amount'].sum())
    expense_total = float(expenses['amount'].sum())
    if income:
        savings = income - expense_total
        savings_rate = savings / income * 100
        if savings < 0:
            insights.append({'type': 'Savings', 'priority': 86 + min(25, abs(savings) / 500), 'severity': 'high', 'title': 'Negative savings', 'message': f'Expenses exceeded income by ₹{abs(savings):,.0f} this month.'})
        else:
            prev_rows = transactions[(transactions['user_id'] == user_id) & (transactions['month'] == mom['previous_month']) & (transactions['year'] == mom['previous_year'])]
            prev_income = float(prev_rows.loc[prev_rows['type'] == 'Income', 'amount'].sum())
            prev_expense = float(prev_rows.loc[prev_rows['type'] == 'Expense', 'amount'].sum())
            if prev_income:
                prev_rate = (prev_income - prev_expense) / prev_income * 100
                diff = savings_rate - prev_rate
                income_base = max(income, prev_income)
                impact = abs((savings_rate - prev_rate) / 100 * income_base)
                if abs(diff) >= 5 and impact >= 750:
                    verb = 'improved' if diff > 0 else 'fell'
                    insights.append({'type': 'Savings', 'priority': 72 + min(20, impact / 400) + min(12, abs(diff)), 'severity': 'normal' if diff > 0 else 'high', 'title': 'Savings rate shift', 'message': f'Your savings rate {verb} from {prev_rate:.1f}% to {savings_rate:.1f}%.'})

    recurring = detect_recurring_expenses(transactions, user_id)
    if recurring['monthly_total'] >= 500:
        insights.append({'type': 'Recurring', 'priority': 54 + min(20, recurring['monthly_total'] / 250), 'severity': 'normal', 'title': 'Recurring cost', 'message': f'Likely recurring expenses account for about ₹{recurring["monthly_total"]:,.0f} per month.'})

    if expense_total > 0 and not expenses.empty:
        category_totals = expenses.groupby('category')['amount'].sum().sort_values(ascending=False)
        top_category = category_totals.index[0]
        share = category_totals.iloc[0] / expense_total * 100
        if share >= 28 and category_totals.iloc[0] >= 1000:
            insights.append({'type': 'Category', 'priority': 50 + min(20, share / 2) + min(15, category_totals.iloc[0] / 500), 'severity': 'normal', 'title': 'Largest category', 'category': top_category, 'message': f'{top_category} was your largest expense category, accounting for {share:.1f}% of monthly spending.'})

        merchant_spend = expenses.groupby('merchant')['amount'].sum().sort_values(ascending=False)
        merchant_count = expenses.groupby('merchant')['transaction_id'].count().sort_values(ascending=False)
        if not merchant_spend.empty and merchant_spend.iloc[0] >= 1000:
            insights.append({'type': 'Merchant', 'priority': 45 + min(18, merchant_spend.iloc[0] / 500), 'severity': 'normal', 'title': 'Top merchant', 'message': f'{merchant_spend.index[0]} was your highest-spend merchant this month at ₹{merchant_spend.iloc[0]:,.0f}.'})
        if not merchant_count.empty and merchant_count.iloc[0] >= 5:
            insights.append({'type': 'Merchant', 'priority': 38 + min(10, merchant_count.iloc[0]), 'severity': 'normal', 'title': 'Frequent merchant', 'message': f'{merchant_count.index[0]} was your most frequent merchant with {int(merchant_count.iloc[0])} transactions.'})

    anomalies = detect_spending_anomalies(transactions, user_id)
    month_anomalies = anomalies[
        (pd.to_datetime(anomalies['date']).dt.month == month)
        & (pd.to_datetime(anomalies['date']).dt.year == year)
    ] if not anomalies.empty else anomalies
    if categories and not month_anomalies.empty:
        month_anomalies = month_anomalies[month_anomalies['category'].isin(categories)]
    if not month_anomalies.empty:
        anomaly = month_anomalies.sort_values('amount_above_threshold', ascending=False).iloc[0]
        insights.append({'type': 'Anomaly', 'priority': 74 + min(20, anomaly['amount_above_threshold'] / 500), 'severity': 'high' if anomaly['severity'] == 'High' else 'normal', 'title': 'Unusual spending', 'category': anomaly['category'], 'message': f'An unusually large {anomaly["category"]} transaction of ₹{anomaly["amount"]:,.0f} was detected this month.'})

    benchmark = calculate_peer_benchmarks(transactions, users, user_id)
    peer_messages = benchmark_insights(benchmark, limit=1)
    if peer_messages:
        insights.append({'type': 'Benchmark', 'priority': 52, 'severity': 'normal', 'title': 'Peer comparison', 'message': peer_messages[0]})

    return _diversify_insights(insights, limit)


def derived_insights(data: pd.DataFrame) -> list[str]:
    expenses = data[data['type'] == 'Expense']
    insights = []
    if expenses.empty:
        return insights

    persona_category = expenses.groupby(['persona', 'category'])['amount'].sum()
    persona_totals = expenses.groupby('persona')['amount'].sum()
    shares = (persona_category / persona_totals).reset_index(name='share')

    for persona, category in [('Shopaholic', 'Shopping'), ('Traveler', 'Transportation'), ('Hostel Student', 'Food & Dining'), ('Budget Student', 'Shopping')]:
        row = shares[(shares['persona'] == persona) & (shares['category'] == category)]
        if not row.empty:
            share = row.iloc[0]['share']
            insights.append(f'{persona}: {category} accounts for {share:.1%} of expense value.')

    week = expenses.assign(week_part=expenses['date'].dt.weekday.map(lambda day: 'Weekend' if day >= 5 else 'Weekday'))
    avg_daily = week.groupby('week_part')['amount'].mean()
    if {'Weekend', 'Weekday'}.issubset(avg_daily.index):
        weekend = avg_daily['Weekend']
        weekday = avg_daily['Weekday']
        insights.append(f'Average weekend expense transaction value is ₹{weekend:,.0f} versus ₹{weekday:,.0f} on weekdays.')

    habit = expenses.groupby('spending_habit')['amount'].mean().sort_values(ascending=False)
    if not habit.empty:
        insights.append(f'{habit.index[0]} students have the highest average expense transaction value at ₹{habit.iloc[0]:,.0f}.')

    return insights


# Recurring detection thresholds are deliberately conservative:
# at least four active months, mostly one transaction per month, low amount variability,
# and either monthly-like date intervals or long month coverage.
def detect_recurring_expenses(transactions: pd.DataFrame, user_id: int, min_distinct_months: int = 5) -> dict[str, object]:
    expenses = transactions[(transactions['user_id'] == user_id) & (transactions['type'] == 'Expense')].copy()
    empty_columns = ['merchant', 'category', 'estimated_frequency', 'average_amount', 'median_amount', 'amount_cv', 'max_median_deviation_pct', 'estimated_monthly_cost', 'estimated_annual_cost', 'transactions', 'distinct_months', 'first_occurrence', 'last_occurrence', 'monthly_interval_share', 'single_transaction_month_share', 'confidence', 'confidence_score']
    if expenses.empty:
        return {'items': pd.DataFrame(columns=empty_columns), 'monthly_total': 0.0, 'annual_total': 0.0}

    rows = []
    for merchant, group in expenses.groupby('merchant'):
        group = group.sort_values('date')
        transaction_count = len(group)
        distinct_months = int(group['month'].nunique())
        if distinct_months < min_distinct_months or transaction_count < min_distinct_months:
            continue

        monthly_counts = group.groupby(['year', 'month'])['transaction_id'].count()
        active_month_share = distinct_months / 12
        single_transaction_month_share = float((monthly_counts == 1).mean())
        transactions_per_active_month = transaction_count / distinct_months
        multi_txn_months = int((monthly_counts > 1).sum())
        avg_amount = float(group['amount'].mean())
        median_amount = float(group['amount'].median())
        std_amount = float(group['amount'].std(ddof=0)) if transaction_count > 1 else 0.0
        amount_cv = (std_amount / avg_amount) if avg_amount else 0.0
        max_median_deviation = float((group['amount'].sub(median_amount).abs() / median_amount).max()) if median_amount else 0.0
        intervals = group['date'].diff().dt.days.dropna()
        monthly_interval_share = float(intervals.between(25, 35).mean()) if len(intervals) else 0.0
        median_interval = float(intervals.median()) if len(intervals) else 0.0

        amount_consistent = amount_cv <= 0.22 and max_median_deviation <= 0.45
        one_per_month_pattern = transactions_per_active_month <= 1.15 and single_transaction_month_share >= 0.85 and multi_txn_months == 0
        timing_consistent = monthly_interval_share >= 0.45 or (active_month_share >= 0.65 and 24 <= median_interval <= 38)
        enough_coverage = distinct_months >= 5 and active_month_share >= 0.40
        if not (amount_consistent and one_per_month_pattern and timing_consistent and enough_coverage):
            continue
        if median_amount < 100:
            continue

        score = 0
        score += 35 if amount_cv <= 0.12 else 25
        score += 20 if max_median_deviation <= 0.20 else 12
        score += min(20, distinct_months * 3)
        score += 15 if monthly_interval_share >= 0.60 else 10
        score += 10 if single_transaction_month_share == 1 else 6
        confidence = 'High' if score >= 80 else 'Medium'
        category = group['category'].mode().iat[0]
        estimated_monthly_cost = median_amount

        rows.append({'merchant': merchant, 'category': category, 'estimated_frequency': 'Monthly', 'average_amount': avg_amount, 'median_amount': median_amount, 'amount_cv': amount_cv, 'max_median_deviation_pct': max_median_deviation * 100, 'estimated_monthly_cost': estimated_monthly_cost, 'estimated_annual_cost': estimated_monthly_cost * 12, 'transactions': transaction_count, 'distinct_months': distinct_months, 'first_occurrence': group['date'].min(), 'last_occurrence': group['date'].max(), 'monthly_interval_share': monthly_interval_share, 'single_transaction_month_share': single_transaction_month_share, 'confidence': confidence, 'confidence_score': score})

    items = pd.DataFrame(rows)
    if items.empty:
        return {'items': pd.DataFrame(columns=empty_columns), 'monthly_total': 0.0, 'annual_total': 0.0}

    items = items.sort_values(['confidence_score', 'estimated_monthly_cost'], ascending=False).reset_index(drop=True)
    return {'items': items, 'monthly_total': float(items['estimated_monthly_cost'].sum()), 'annual_total': float(items['estimated_annual_cost'].sum())}


def historical_monthly_profile(transactions: pd.DataFrame, user_id: int) -> dict[str, object]:
    user_rows = transactions[transactions['user_id'] == user_id].copy()
    if user_rows.empty:
        empty_categories = pd.DataFrame(columns=['category', 'avg_monthly_spend', 'total_spend', 'share_of_expenses'])
        return {'months_observed': 0, 'avg_income': 0.0, 'avg_expenses': 0.0, 'avg_savings': 0.0, 'category_profile': empty_categories}

    months = user_rows[['year', 'month']].drop_duplicates()
    months_observed = max(1, len(months))
    income = float(user_rows.loc[user_rows['type'] == 'Income', 'amount'].sum())
    expenses = float(user_rows.loc[user_rows['type'] == 'Expense', 'amount'].sum())
    expense_rows = user_rows[user_rows['type'] == 'Expense']
    category_totals = expense_rows.groupby('category', as_index=False)['amount'].sum().rename(columns={'amount': 'total_spend'})
    if not category_totals.empty:
        category_totals['avg_monthly_spend'] = category_totals['total_spend'] / months_observed
        category_totals['share_of_expenses'] = category_totals['total_spend'] / expenses * 100 if expenses else 0.0
        category_totals = category_totals.sort_values('avg_monthly_spend', ascending=False)
    else:
        category_totals = pd.DataFrame(columns=['category', 'total_spend', 'avg_monthly_spend', 'share_of_expenses'])

    return {'months_observed': months_observed, 'avg_income': income / months_observed, 'avg_expenses': expenses / months_observed, 'avg_savings': (income - expenses) / months_observed, 'category_profile': category_totals}


def generate_savings_recommendations(transactions: pd.DataFrame, budgets: pd.DataFrame, user_id: int, monthly_gap: float, reduction_overrides: dict[str, float] | None = None) -> pd.DataFrame:
    profile = historical_monthly_profile(transactions, user_id)
    category_profile = profile['category_profile']
    if category_profile.empty:
        return pd.DataFrame(columns=['category', 'avg_monthly_spend', 'suggested_reduction_pct', 'estimated_monthly_saving', 'reason'])

    base_reductions = {'Shopping': 15.0, 'Entertainment': 12.0, 'Food & Dining': 10.0, 'Miscellaneous': 8.0, 'Transportation': 5.0}
    caps = {'Shopping': 25.0, 'Entertainment': 20.0, 'Food & Dining': 18.0, 'Miscellaneous': 12.0, 'Transportation': 8.0}
    overrides = reduction_overrides or {}
    rows = []

    budget_rows = budgets[budgets['user_id'] == user_id] if not budgets.empty else pd.DataFrame()
    actual_expenses = transactions[(transactions['user_id'] == user_id) & (transactions['type'] == 'Expense')]
    over_budget_categories: set[str] = set()
    if not budget_rows.empty and not actual_expenses.empty:
        actual_monthly = actual_expenses.groupby(['category', 'year', 'month'], as_index=False)['amount'].sum()
        merged = budget_rows.merge(actual_monthly, on=['category', 'year', 'month'], how='left')
        merged['amount'] = merged['amount'].fillna(0)
        merged['over_budget'] = merged['amount'] > merged['budget_amount'] * 1.05
        over_budget_categories = set(merged.groupby('category')['over_budget'].mean().loc[lambda s: s >= 0.35].index)

    for row in category_profile.itertuples():
        category = row.category
        if category not in base_reductions or row.avg_monthly_spend <= 0:
            continue
        suggested_pct = overrides.get(category, base_reductions[category])
        reason_parts = ['controllable category']
        if category in over_budget_categories:
            suggested_pct += 3.0
            reason_parts.append('often over budget')
        if row.share_of_expenses >= 25:
            suggested_pct += 2.0
            reason_parts.append('large share of expenses')
        suggested_pct = max(0.0, min(caps[category], suggested_pct))
        estimated = row.avg_monthly_spend * suggested_pct / 100
        rows.append({'category': category, 'avg_monthly_spend': float(row.avg_monthly_spend), 'suggested_reduction_pct': suggested_pct, 'estimated_monthly_saving': estimated, 'reason': ', '.join(reason_parts)})

    recommendations = pd.DataFrame(rows)
    if recommendations.empty:
        return pd.DataFrame(columns=['category', 'avg_monthly_spend', 'suggested_reduction_pct', 'estimated_monthly_saving', 'reason'])

    return recommendations.sort_values('estimated_monthly_saving', ascending=False).reset_index(drop=True)


def calculate_savings_goal(transactions: pd.DataFrame, budgets: pd.DataFrame, user_id: int, goal_amount: float, target_months: int, reduction_overrides: dict[str, float] | None = None) -> dict[str, object]:
    if goal_amount <= 0 or target_months <= 0:
        raise ValueError('Goal amount and target months must be positive.')

    profile = historical_monthly_profile(transactions, user_id)
    required_monthly_savings = goal_amount / target_months
    current_average_savings = float(profile['avg_savings'])
    monthly_gap = max(0.0, required_monthly_savings - current_average_savings)
    recommendations = generate_savings_recommendations(transactions, budgets, user_id, monthly_gap, reduction_overrides)
    potential_monthly_savings = float(recommendations['estimated_monthly_saving'].sum()) if not recommendations.empty else 0.0
    projected_monthly_savings = current_average_savings + potential_monthly_savings
    remaining_gap = max(0.0, required_monthly_savings - projected_monthly_savings)
    expected_months_current = (goal_amount / current_average_savings) if current_average_savings > 0 else None
    expected_months_projected = (goal_amount / projected_monthly_savings) if projected_monthly_savings > 0 else None
    recurring = detect_recurring_expenses(transactions, user_id)

    if current_average_savings >= required_monthly_savings:
        status = 'Already on pace based on historical averages.'
    elif remaining_gap <= 0:
        status = 'Appears achievable under the simulated reductions.'
    elif current_average_savings <= 0 and potential_monthly_savings <= 0:
        status = 'Historical spending leaves no positive average monthly savings.'
    else:
        status = 'The simulation leaves a remaining monthly gap.'

    return {'goal_amount': goal_amount, 'target_months': target_months, 'required_monthly_savings': required_monthly_savings, 'avg_monthly_income': float(profile['avg_income']), 'avg_monthly_expenses': float(profile['avg_expenses']), 'current_average_savings': current_average_savings, 'monthly_gap': monthly_gap, 'recommendations': recommendations, 'potential_monthly_savings': potential_monthly_savings, 'projected_monthly_savings': projected_monthly_savings, 'remaining_gap': remaining_gap, 'expected_months_current': expected_months_current, 'expected_months_projected': expected_months_projected, 'category_profile': profile['category_profile'], 'recurring': recurring, 'status': status}

