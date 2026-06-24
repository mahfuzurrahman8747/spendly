"""Seed a single random Indian user into the Spendly DB."""

import random
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

# Reuse the project's get_db() helper so the connection pattern stays consistent.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from database.db import get_db  # noqa: E402

# Realistic Indian first + last names covering different regions and languages.
FIRST_NAMES = [
    "Aarav", "Vihaan", "Aditya", "Arjun", "Rohan", "Rahul", "Karan", "Ishaan",
    "Sai", "Krishna", "Ravi", "Amit", "Sandeep", "Vikram", "Manish", "Suresh",
    "Priyanka", "Anjali", "Pooja", "Neha", "Sneha", "Aishwarya", "Divya",
    "Kavya", "Meera", "Nandini", "Riya", "Shruti", "Tanvi", "Vidya",
    "Arijit", "Debanjan", "Rohit", "Siddharth", "Tushar", "Yash",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Iyer", "Reddy", "Nair", "Menon",
    "Banerjee", "Mukherjee", "Chatterjee", "Das", "Bose", "Sen", "Ghosh",
    "Khan", "Ahmed", "Sheikh", "Ansari", "Siddiqui",
    "Rao", "Pillai", "Krishnan", "Subramanian", "Bhat", "Hegde",
    "Singh", "Kaur", "Gill", "Dhillon",
    "Joshi", "Mehta", "Shah", "Desai", "Trivedi",
    "Kapoor", "Kumar", "Jain", "Agarwal", "Mittal",
]


def generate_email(name: str) -> str:
    """Build `firstname.lastname<2-3 digit number>@gmail.com`."""
    parts = name.lower().split()
    digits = random.randint(10, 999)
    return f"{parts[0]}.{parts[1]}{digits}@gmail.com"


def main() -> int:
    conn = get_db()

    # Generate a unique email; regenerate the name/email pair on collision.
    while True:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = generate_email(name)

        existing = conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing is None:
            break

    password_hash = generate_password_hash("password123")
    created_at = datetime.now().isoformat(sep=" ", timespec="seconds")

    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) "
        "VALUES (?, ?, ?, ?)",
        (name, email, password_hash, created_at),
    )
    conn.commit()

    user_id = cur.lastrowid
    print(f"id: {user_id}")
    print(f"name: {name}")
    print(f"email: {email}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
