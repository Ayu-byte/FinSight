"""Median-based peer benchmarking for synthetic student cohorts."""

from __future__ import annotations

import pandas as pd


MONEY_METRICS = [
    'Average Monthly Expenses', 'Average Monthly Income', 'Average Monthly Net Savings',
    'Food & Dining', 'Shopping', 'Transportation', 'Entertainment',
]
METRIC_ORDER = MONEY_METRICS + ['Savings Rate', 'Transaction Frequency']


def _student_monthly_metrics(transactions: pd.DataFrame) -> pd.DataFrame:
    rows = transactions.copy()
    rows['period'] = pd.to_datetime(rows['date']).dt.to_period('M')
    observed = rows.groupby('user_id')['period'].nunique().clip(lower=1)
    income = rows[rows['type'] == 'Income'].groupby('user_id')['amount'].sum()
    expenses = rows[rows['type'] == 'Expense'].groupby('user_id')['amount'].sum()
    counts = rows.groupby('user_id').size()
    users = pd.Index(rows['user_id'].unique(), name='user_id')
    metrics = pd.DataFrame(index=users)
    metrics['months'] = observed.reindex(users).fillna(1)
    metrics['Average Monthly Income'] = income.reindex(users, fill_value=0) / metrics['months']
    metrics['Average Monthly Expenses'] = expenses.reindex(users, fill_value=0) / metrics['months']
    metrics['Average Monthly Net Savings'] = metrics['Average Monthly Income'] - metrics['Average Monthly Expenses']
    metrics['Savings Rate'] = metrics.apply(
        lambda row: row['Average Monthly Net Savings'] / row['Average Monthly Income'] * 100
        if row['Average Monthly Income'] else 0.0,
        axis=1,
    )
    metrics['Transaction Frequency'] = counts.reindex(users, fill_value=0) / metrics['months']
    expense_rows = rows[rows['type'] == 'Expense']
    category_totals = expense_rows.groupby(['user_id', 'category'])['amount'].sum().unstack(fill_value=0)
    for category in ['Food & Dining', 'Shopping', 'Transportation', 'Entertainment']:
        metrics[category] = category_totals.get(category, pd.Series(dtype=float)).reindex(users, fill_value=0) / metrics['months']
    return metrics


def calculate_peer_benchmarks(
    transactions: pd.DataFrame,
    users: pd.DataFrame,
    user_id: int,
    *,
    peer_scope: str = 'Same Persona',
    min_peers: int = 3,
) -> dict[str, object]:
    selected = users[users['user_id'] == user_id]
    if selected.empty:
        return {'available': False, 'reason': 'Student not found.', 'table': pd.DataFrame()}
    persona = str(selected.iloc[0]['persona'])
    peers = users[users['user_id'] != user_id]
    if peer_scope == 'Same Persona':
        peers = peers[peers['persona'] == persona]
    metrics = _student_monthly_metrics(transactions)
    peer_ids = peers.loc[peers['user_id'].isin(metrics.index), 'user_id'].tolist()
    if user_id not in metrics.index or len(peer_ids) < min_peers:
        return {'available': False, 'reason': 'Insufficient peer data for this comparison.', 'persona': persona, 'peer_count': len(peer_ids), 'table': pd.DataFrame()}

    student = metrics.loc[user_id]
    cohort = metrics.loc[peer_ids]
    result_rows = []
    for metric in METRIC_ORDER:
        value = float(student[metric])
        peer_median = float(cohort[metric].median())
        difference = value - peer_median
        difference_pct = difference / peer_median * 100 if peer_median != 0 else None
        # Midrank percentile treats ties fairly and describes position, not quality.
        below = int((cohort[metric] < value).sum())
        equal = int((cohort[metric] == value).sum())
        percentile = (below + 0.5 * equal) / len(cohort) * 100
        result_rows.append({
            'metric': metric, 'student_value': value, 'peer_median': peer_median,
            'difference': difference, 'difference_pct': difference_pct,
            'percentile': percentile, 'unit': 'percent' if metric == 'Savings Rate' else 'count' if metric == 'Transaction Frequency' else 'currency',
        })
    return {
        'available': True, 'persona': persona, 'peer_scope': peer_scope,
        'peer_count': len(peer_ids), 'table': pd.DataFrame(result_rows),
    }


def benchmark_insights(benchmark: dict[str, object], limit: int = 3) -> list[str]:
    if not benchmark.get('available'):
        return []
    candidates = []
    for row in benchmark['table'].itertuples():
        if row.metric == 'Savings Rate':
            if abs(row.difference) >= 5:
                direction = 'above' if row.difference > 0 else 'below'
                candidates.append((abs(row.difference), f'Your savings rate is {abs(row.difference):.1f} percentage points {direction} the median for your peer group.'))
        elif row.unit == 'currency' and row.difference_pct is not None:
            if abs(row.difference_pct) >= 15 and abs(row.difference) >= 500:
                direction = 'above' if row.difference > 0 else 'below'
                candidates.append((abs(row.difference_pct), f'Your {row.metric.lower()} is {abs(row.difference_pct):.1f}% {direction} the median for similar students.'))
    return [message for _, message in sorted(candidates, reverse=True)[:limit]]
