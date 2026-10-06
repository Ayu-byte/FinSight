"""Beginner-level regression tests for FinSight's core calculations.

Each test pins one formula to a hand-checked answer so future edits
can't silently break the dashboard. Run with: pytest
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from analytics.insights import (  # noqa: E402
    budget_summary,
    budget_vs_actual,
    calculate_savings_goal,
    filter_transactions,
    kpis,
    month_over_month,
    previous_month,
)
from analytics.anomalies import detect_spending_anomalies  # noqa: E402
from analytics.benchmarking import calculate_peer_benchmarks  # noqa: E402
from dashboard.app import ordinal  # noqa: E402


def make_transactions():
    return pd.DataFrame([
        {'transaction_id': 1, 'user_id': 1, 'date': pd.Timestamp('2025-10-05'),
         'type': 'Expense', 'category': 'Shopping', 'merchant': 'Myntra',
         'amount': 1200.0, 'month': 10, 'year': 2025, 'month_name': 'Oct'},
        {'transaction_id': 2, 'user_id': 1, 'date': pd.Timestamp('2025-10-06'),
         'type': 'Expense', 'category': 'Grocery', 'merchant': 'DMart',
         'amount': 800.0, 'month': 10, 'year': 2025, 'month_name': 'Oct'},
        {'transaction_id': 3, 'user_id': 1, 'date': pd.Timestamp('2025-10-01'),
         'type': 'Income', 'category': 'Income', 'merchant': 'Monthly Allowance',
         'amount': 5000.0, 'month': 10, 'year': 2025, 'month_name': 'Oct'},
        {'transaction_id': 4, 'user_id': 1, 'date': pd.Timestamp('2025-09-10'),
         'type': 'Expense', 'category': 'Shopping', 'merchant': 'Myntra',
         'amount': 400.0, 'month': 9, 'year': 2025, 'month_name': 'Sep'},
    ])


def make_budgets():
    return pd.DataFrame([
        {'budget_id': 1, 'user_id': 1, 'category': 'Shopping',
         'month': 10, 'year': 2025, 'budget_amount': 1000.0},
        {'budget_id': 2, 'user_id': 1, 'category': 'Grocery',
         'month': 10, 'year': 2025, 'budget_amount': 1000.0},
    ])


def test_variance_is_actual_minus_budget():
    result = budget_vs_actual(make_transactions(), make_budgets(), 1, 10, 2025)
    shopping = result[result['category'] == 'Shopping'].iloc[0]
    assert shopping['actual_amount'] == 1200.0
    assert shopping['variance'] == 200.0  # overspend is positive
    assert shopping['status'] == 'Over Budget'


def test_underspend_is_negative_variance():
    result = budget_vs_actual(make_transactions(), make_budgets(), 1, 10, 2025)
    grocery = result[result['category'] == 'Grocery'].iloc[0]
    assert grocery['variance'] == -200.0
    assert grocery['status'] == 'Near Limit'  # exactly 80% -> not Within


def test_budget_summary_totals():
    result = budget_vs_actual(make_transactions(), make_budgets(), 1, 10, 2025)
    summary = budget_summary(result)
    assert summary['total_budget'] == 2000.0
    assert summary['actual_spending'] == 2000.0
    assert summary['variance'] == 0.0


def test_january_looks_at_prior_december():
    assert previous_month(1, 2025) == (12, 2024)
    assert previous_month(10, 2025) == (9, 2025)


def test_mom_compares_adjacent_months():
    mom = month_over_month(make_transactions(), 1, 10, 2025)
    assert mom['previous_month'] == 9
    assert mom['current_total'] == 2000.0
    assert mom['previous_total'] == 400.0
    assert mom['change'] == 1600.0


def test_mom_new_spending_label_not_infinity():
    txns = make_transactions()
    first = txns[txns['month'] == 10].copy()  # no September history
    mom = month_over_month(first, 1, 10, 2025)
    assert mom['previous_total'] == 0.0
    assert mom['pct_change'] is None  # must not divide by zero
    labels = dict(zip(mom['category_comparison']['category'],
                      mom['category_comparison']['change_label']))
    assert labels['Shopping'] == 'New spending this month'


def test_kpis_exclude_income_from_expenses():
    metrics = kpis(make_transactions())
    assert metrics['total_income'] == 5000.0
    assert metrics['total_expenses'] == 2400.0
    assert metrics['net_savings'] == 2600.0
    assert metrics['savings_rate'] == 52.0


def test_filter_by_persona_and_users():
    data = make_transactions().merge(
        pd.DataFrame([{'user_id': 1, 'persona': 'Hostel Student'}]),
        on='user_id', how='left')
    assert len(filter_transactions(data, personas=['Hostel Student'],
                                   users=[1])) == 4
    assert filter_transactions(data, personas=['Shopaholic']).empty
    assert filter_transactions(data, users=[999]).empty


def test_anomaly_flags_clear_outlier():
    rows = [{'transaction_id': i, 'user_id': 7, 'date': '2025-03-01',
             'type': 'Expense', 'category': 'Grocery', 'merchant': 'DMart',
             'amount': float(80 + (i * 7) % 60)} for i in range(12)]
    rows.append({'transaction_id': 99, 'user_id': 7, 'date': '2025-03-02',
                 'type': 'Expense', 'category': 'Grocery', 'merchant': 'DMart',
                 'amount': 5000.0})
    anomalies = detect_spending_anomalies(pd.DataFrame(rows), 7)
    assert not anomalies.empty
    assert 99 in set(anomalies['transaction_id'])


def test_anomaly_skips_tiny_history():
    rows = [{'transaction_id': i, 'user_id': 8, 'date': '2025-03-01',
             'type': 'Expense', 'category': 'Grocery', 'merchant': 'DMart',
             'amount': 100.0 + i} for i in range(3)]
    assert detect_spending_anomalies(pd.DataFrame(rows), 8).empty


def test_benchmark_self_excluded_and_percentile_range():
    txns = pd.DataFrame([
        {'user_id': 1, 'date': '2025-01-05', 'type': 'Expense',
         'category': 'Shopping', 'amount': 1000.0},
        {'user_id': 2, 'date': '2025-01-05', 'type': 'Expense',
         'category': 'Shopping', 'amount': 2000.0},
        {'user_id': 3, 'date': '2025-01-05', 'type': 'Expense',
         'category': 'Shopping', 'amount': 3000.0},
        {'user_id': 4, 'date': '2025-01-05', 'type': 'Expense',
         'category': 'Shopping', 'amount': 4000.0},
        {'user_id': 5, 'date': '2025-01-05', 'type': 'Expense',
         'category': 'Shopping', 'amount': 5000.0},
    ])
    users = pd.DataFrame([
        {'user_id': i, 'persona': 'Hostel Student'} for i in range(1, 6)
    ])
    bench = calculate_peer_benchmarks(txns, users, 1)
    assert bench['available'] is True
    assert bench['peer_count'] == 4  # self excluded
    assert bench['table']['percentile'].between(0, 100).all()


def test_ordinal_suffixes():
    assert ordinal(1) == '1st'
    assert ordinal(2) == '2nd'
    assert ordinal(3) == '3rd'
    assert ordinal(11) == '11th'
    assert ordinal(12) == '12th'
    assert ordinal(13) == '13th'
    assert ordinal(53) == '53rd'
    assert ordinal(42) == '42nd'


def test_savings_goal_rejects_bad_input():
    import pytest
    with pytest.raises(ValueError):
        calculate_savings_goal(make_transactions(), make_budgets(),
                               1, 0, 6)
    with pytest.raises(ValueError):
        calculate_savings_goal(make_transactions(), make_budgets(),
                               1, 25000, 0)
