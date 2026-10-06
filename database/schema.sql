CREATE DATABASE IF NOT EXISTS finsight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE finsight;

DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(160) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    persona VARCHAR(40) NOT NULL,
    monthly_income DECIMAL(10,2) NOT NULL,
    spending_habit VARCHAR(20) NOT NULL,
    payment_preference VARCHAR(20) NOT NULL,
    monthly_transactions INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_persona (persona),
    INDEX idx_users_spending_habit (spending_habit)
);

CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_time TIME NOT NULL,
    transaction_type ENUM('Income', 'Expense') NOT NULL,
    category VARCHAR(40) NOT NULL,
    merchant VARCHAR(100) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    day_of_week VARCHAR(12),
    transaction_month TINYINT,
    CONSTRAINT fk_transactions_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT chk_transactions_amount CHECK (amount > 0),
    INDEX idx_transactions_user_date (user_id, transaction_date),
    INDEX idx_transactions_category (category),
    INDEX idx_transactions_type (transaction_type),
    INDEX idx_transactions_month (transaction_month),
    INDEX idx_transactions_merchant (merchant)
);

CREATE TABLE budgets (
    budget_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    category VARCHAR(40) NOT NULL,
    budget_month TINYINT NOT NULL,
    budget_year SMALLINT NOT NULL,
    budget_amount DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT chk_budgets_month CHECK (budget_month BETWEEN 1 AND 12),
    CONSTRAINT chk_budgets_year CHECK (budget_year >= 2000),
    CONSTRAINT chk_budgets_amount CHECK (budget_amount > 0),
    CONSTRAINT uq_budget_user_category_month_year UNIQUE (user_id, category, budget_month, budget_year),
    INDEX idx_budgets_user_month (user_id, budget_year, budget_month),
    INDEX idx_budgets_category (category)
);
