import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
USERS_PATH = ROOT / 'data' / 'generated' / 'users.csv'
TRANSACTIONS_PATH = ROOT / 'data' / 'generated' / 'transactions.csv'
BUDGETS_PATH = ROOT / 'data' / 'generated' / 'budgets.csv'
SCHEMA_PATH = ROOT / 'database' / 'schema.sql'


def connection_config(include_database: bool = True) -> dict[str, str | int]:
    load_dotenv(ROOT / '.env')
    config: dict[str, str | int] = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
    }
    if include_database:
        config['database'] = os.getenv('MYSQL_DATABASE', 'finsight')
    return config


def execute_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding='utf-8')
    connection = mysql.connector.connect(**connection_config(include_database=False))
    cursor = connection.cursor()
    for statement in [part.strip() for part in sql.split(';') if part.strip()]:
        cursor.execute(statement)
    connection.commit()
    cursor.close()
    connection.close()


def load_users(cursor, users: pd.DataFrame) -> None:
    rows = users[
        ['user_id', 'name', 'username', 'email', 'password', 'persona', 'monthly_income', 'spending_habit', 'payment_preference', 'monthly_transactions']
    ].itertuples(index=False, name=None)
    cursor.executemany(
        '''
        INSERT INTO users
        (user_id, name, username, email, password, persona, monthly_income, spending_habit, payment_preference, monthly_transactions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''',
        list(rows),
    )


def load_transactions(cursor, transactions: pd.DataFrame) -> None:
    rows = transactions[
        ['transaction_id', 'user_id', 'date', 'time', 'type', 'category', 'merchant', 'amount', 'payment_method', 'day_of_week', 'month']
    ].itertuples(index=False, name=None)
    cursor.executemany(
        '''
        INSERT INTO transactions
        (transaction_id, user_id, transaction_date, transaction_time, transaction_type, category, merchant, amount, payment_method, day_of_week, transaction_month)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''',
        list(rows),
    )


def load_budgets(cursor, budgets: pd.DataFrame) -> None:
    rows = budgets[['budget_id', 'user_id', 'category', 'month', 'year', 'budget_amount']].itertuples(index=False, name=None)
    cursor.executemany(
        '''
        INSERT INTO budgets
        (budget_id, user_id, category, budget_month, budget_year, budget_amount)
        VALUES (%s, %s, %s, %s, %s, %s)
        ''',
        list(rows),
    )


def main() -> None:
    if not USERS_PATH.exists() or not TRANSACTIONS_PATH.exists() or not BUDGETS_PATH.exists():
        raise FileNotFoundError('Generated CSV files are missing. Run the user, transaction, and budget generator scripts before loading MySQL.')

    execute_schema()
    users = pd.read_csv(USERS_PATH)
    transactions = pd.read_csv(TRANSACTIONS_PATH)
    budgets = pd.read_csv(BUDGETS_PATH)

    connection = mysql.connector.connect(**connection_config(include_database=True))
    cursor = connection.cursor()
    load_users(cursor, users)
    load_transactions(cursor, transactions)
    load_budgets(cursor, budgets)
    connection.commit()
    cursor.close()
    connection.close()

    print(f'Loaded {len(users)} users, {len(transactions)} transactions, and {len(budgets)} budgets into MySQL.')


if __name__ == '__main__':
    main()
