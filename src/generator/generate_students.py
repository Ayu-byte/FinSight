import random
from pathlib import Path

import pandas as pd

from personas import PERSONAS

SEED = 202501
OUTPUT_PATH = Path('data/generated/users.csv')

FIRST_NAMES = [
    'Aarav', 'Aditi', 'Advait', 'Aisha', 'Akash', 'Ananya', 'Anika', 'Arjun', 'Avni', 'Dev',
    'Diya', 'Esha', 'Ishaan', 'Kabir', 'Kavya', 'Krish', 'Meera', 'Naina', 'Neha', 'Nikhil',
    'Pranav', 'Priya', 'Rahul', 'Riya', 'Rohan', 'Saanvi', 'Sahil', 'Simran', 'Tanvi', 'Vihaan',
    'Yash', 'Zara', 'Ahan', 'Ira', 'Kunal', 'Mihir', 'Navya', 'Parth', 'Rudra', 'Sanya',
]

LAST_NAMES = [
    'Sharma', 'Iyer', 'Nair', 'Menon', 'Reddy', 'Kapoor', 'Mehta', 'Patel', 'Rao', 'Das',
    'Chatterjee', 'Banerjee', 'Kulkarni', 'Joshi', 'Pillai', 'Malhotra', 'Bose', 'Gupta', 'Singh', 'Verma',
    'Khan', 'Shetty', 'Agarwal', 'Mishra', 'Saxena', 'Bhat', 'Ghosh', 'Desai', 'Naidu', 'Jain',
]


def student_name(user_id: int) -> str:
    first = FIRST_NAMES[(user_id - 1) % len(FIRST_NAMES)]
    last = LAST_NAMES[((user_id - 1) * 7) % len(LAST_NAMES)]
    return f'{first} {last}'


def username_from_name(name: str, suffix: int) -> str:
    return name.lower().replace(' ', '').replace('.', '') + str(suffix)


def generate_students(seed: int = SEED) -> pd.DataFrame:
    '''Generate the 100 synthetic student profiles used by FinSight.'''
    random.seed(seed)

    students = []
    user_id = 1

    for persona, details in PERSONAS.items():
        for _ in range(details['count']):
            name = 'Ayushi Agarwal' if user_id == 1 else student_name(user_id)
            username = username_from_name(name, random.randint(10, 999))

            students.append(
                {
                    'user_id': user_id,
                    'name': name,
                    'username': username,
                    'email': f'{username}@gmail.com',
                    'password': 'password123',
                    'persona': persona,
                    'monthly_income': random.randint(*details['income_range']),
                    'spending_habit': random.choice(details['spending_habits']),
                    'payment_preference': random.choice(details['payment_methods']),
                    'monthly_transactions': random.randint(*details['monthly_transactions']),
                }
            )
            user_id += 1


    return pd.DataFrame(students)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    students_df = generate_students()
    students_df.to_csv(OUTPUT_PATH, index=False)

    print('===================================')
    print('Users Generated Successfully!')
    print('===================================')
    print(f'Total Students : {len(students_df)}')
    print(f'Saved to {OUTPUT_PATH}')


if __name__ == '__main__':
    main()




