"""Explainable, category-relative spending anomaly analytics."""

from __future__ import annotations

import pandas as pd


ANOMALY_COLUMNS = [
    'transaction_id', 'date', 'merchant', 'category', 'amount', 'category_median',
    'q1', 'q3', 'iqr', 'upper_bound', 'amount_above_typical',
    'amount_above_threshold', 'deviation_pct', 'severity', 'sample_size',
]


def detect_spending_anomalies(
    transactions: pd.DataFrame,
    user_id: int,
    *,
    iqr_multiplier: float = 2.0,
    min_samples: int = 10,
) -> pd.DataFrame:
    """Return unusually large expenses using per-user, per-category IQR fences.

    Categories with fewer than ``min_samples`` observations or zero IQR are
    deliberately skipped; no statistically weak user-level fallback is used.
    """
    expenses = transactions[
        (transactions['user_id'] == user_id) & (transactions['type'] == 'Expense')
    ].copy()
    if expenses.empty:
        return pd.DataFrame(columns=ANOMALY_COLUMNS)

    stats = expenses.groupby('category')['amount'].agg(
        sample_size='size',
        category_median='median',
        q1=lambda values: values.quantile(0.25),
        q3=lambda values: values.quantile(0.75),
    )
    stats['iqr'] = stats['q3'] - stats['q1']
    stats['upper_bound'] = stats['q3'] + iqr_multiplier * stats['iqr']
    eligible = stats[(stats['sample_size'] >= min_samples) & (stats['iqr'] > 0)]
    if eligible.empty:
        return pd.DataFrame(columns=ANOMALY_COLUMNS)

    candidates = expenses.merge(eligible.reset_index(), on='category', how='inner')
    anomalies = candidates[candidates['amount'] > candidates['upper_bound']].copy()
    if anomalies.empty:
        return pd.DataFrame(columns=ANOMALY_COLUMNS)

    anomalies['amount_above_typical'] = anomalies['amount'] - anomalies['category_median']
    anomalies['amount_above_threshold'] = anomalies['amount'] - anomalies['upper_bound']
    anomalies['deviation_pct'] = anomalies.apply(
        lambda row: row['amount_above_typical'] / row['category_median'] * 100
        if row['category_median'] > 0 else pd.NA,
        axis=1,
    )
    # High requires meaningful relative and monetary impact; percentage alone is
    # intentionally insufficient for small-value transactions.
    anomalies['severity'] = anomalies.apply(
        lambda row: 'High'
        if row['amount_above_threshold'] >= 1000
        and row['amount'] >= row['category_median'] * 3
        else 'Moderate',
        axis=1,
    )
    return anomalies[ANOMALY_COLUMNS].sort_values(
        ['severity', 'amount_above_threshold'], ascending=[True, False]
    ).reset_index(drop=True)


def anomaly_summary(transactions: pd.DataFrame, anomalies: pd.DataFrame, user_id: int) -> dict[str, object]:
    expenses = transactions[
        (transactions['user_id'] == user_id) & (transactions['type'] == 'Expense')
    ]
    anomalous_spend = float(anomalies['amount'].sum()) if not anomalies.empty else 0.0
    total_expenses = float(expenses['amount'].sum())
    category = (
        anomalies['category'].value_counts().index[0] if not anomalies.empty else 'N/A'
    )
    return {
        'count': len(anomalies),
        'anomalous_spend': anomalous_spend,
        'expense_share_pct': anomalous_spend / total_expenses * 100 if total_expenses else 0.0,
        'most_affected_category': category,
    }
