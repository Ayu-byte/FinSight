import random
from datetime import date, datetime, timedelta


def random_date(start_date: date | datetime, end_date: date | datetime) -> date | datetime:
    '''Return a random date or datetime between two boundaries.'''
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def random_time(category: str | None = None) -> str:
    '''Return a realistic transaction time with category-specific clustering.'''
    if category == 'Food & Dining':
        hours = [8, 9, 12, 13, 14, 18, 19, 20, 21, 22]
        weights = [4, 3, 12, 12, 5, 10, 18, 18, 12, 6]
    elif category == 'Entertainment':
        hours = [12, 13, 16, 17, 18, 19, 20, 21, 22, 23]
        weights = [3, 3, 6, 8, 12, 16, 18, 18, 12, 4]
    elif category == 'Transportation':
        hours = [7, 8, 9, 10, 16, 17, 18, 19, 20, 21]
        weights = [10, 16, 16, 8, 7, 12, 16, 8, 5, 2]
    elif category == 'Income':
        hours = [9, 10, 11, 12, 13, 14, 15, 16]
        weights = [8, 14, 16, 14, 12, 12, 14, 10]
    else:
        hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
        weights = [2, 3, 4, 4, 5, 5, 4, 4, 5, 6, 8, 10, 12, 10, 6]

    hour = random.choices(hours, weights=weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f'{hour:02}:{minute:02}:{second:02}'


def payment_method(preferred: str) -> str:
    '''Return a payment method with the user's preference dominant.'''
    methods = ['UPI', 'Debit Card', 'Cash']

    if preferred == 'UPI':
        weights = [80, 15, 5]
    elif preferred == 'Debit Card':
        weights = [30, 65, 5]
    else:
        weights = [25, 15, 60]

    return random.choices(methods, weights=weights, k=1)[0]


def end_of_month(year: int, month: int) -> date:
    '''Return the last date for a month.'''
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def weighted_choice(weights: dict[str, float]) -> str:
    '''Choose one key from a weighted dictionary.'''
    return random.choices(list(weights), weights=list(weights.values()), k=1)[0]
