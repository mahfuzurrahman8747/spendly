"""Seed <count> realistic Indian expenses for a user across the past <months> months."""

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Force UTF-8 on stdout so the rupee sign (₹) prints cleanly on Windows (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:  # pragma: no cover — older Pythons
    pass

# Reuse the project's DB connection helper so the path/foreign-key pragmas stay consistent.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from database.db import get_db  # noqa: E402


# Category weights — Food dominates, Health/Entertainment are rare. Index aligned with CATEGORIES.
CATEGORY_WEIGHTS = {
    "Food":          30,
    "Transport":     18,
    "Shopping":      14,
    "Bills":         12,
    "Other":         10,
    "Entertainment": 8,
    "Health":        8,
}

# Realistic Indian-context descriptions and amount ranges (in INR, ₹).
CATEGORIES = {
    "Food": {
        "range": (50, 800),
        "descriptions": [
            "Chai and samosa",
            "Lunch at office canteen",
            "Dinner at a dhaba",
            "Swiggy order — biryani",
            "Zomato — butter chicken",
            "Groceries from BigBasket",
            "Street food — pav bhaji",
            "Breakfast — idli sambar",
            "Dinner — thali",
            "Sabzi mandi vegetables",
            "Dairy — milk and curd",
            "Dominos pizza",
        ],
    },
    "Transport": {
        "range": (20, 500),
        "descriptions": [
            "Uber auto to office",
            "Ola cab ride",
            "Delhi Metro recharge",
            "Local train ticket",
            "Rapido bike ride",
            "Petrol refill",
            "State transport bus",
            "Auto rickshaw",
            "Parking fees",
            "Cab to airport",
        ],
    },
    "Bills": {
        "range": (200, 3000),
        "descriptions": [
            "Electricity bill — BSES",
            "Mobile recharge — Jio",
            "Broadband — Airtel Xstream",
            "Gas cylinder refil",
            "Water bill — municipal",
            "DTH recharge — Tata Play",
            "Maintenance — society",
            "Broadband — Jio Fiber",
        ],
    },
    "Health": {
        "range": (100, 2000),
        "descriptions": [
            "Pharmacy — Apollo",
            "Doctor consultation",
            "Lab tests — path lab",
            "Health supplements",
            "Dental checkup",
            "Eye checkup",
            "Gym monthly membership",
            "Yoga class",
        ],
    },
    "Entertainment": {
        "range": (100, 1500),
        "descriptions": [
            "Movie — PVR Inox",
            "OTT — Netflix subscription",
            "OTT — Hotstar",
            "Concert tickets",
            "Weekend outing",
            "Bookstore — Crossword",
            "Video game on Steam",
        ],
    },
    "Shopping": {
        "range": (200, 5000),
        "descriptions": [
            "Amazon — headphones",
            "Flipkart — t-shirt",
            "Myntra — kurta",
            "Decathlon — running shoes",
            "Croma — phone charger",
            "Lifestyle — jeans",
            "Meesho — household item",
            "Ajio — sneakers",
            "Local kirana — monthly",
            "BigBasket — grocery haul",
        ],
    },
    "Other": {
        "range": (50, 1000),
        "descriptions": [
            "Haircut at salon",
            "Newspaper — Times of India",
            "Birthday gift",
            "Temple donation",
            "Courier — DTDC",
            "Stationery",
            "Laundry — dhobi",
            "Tailoring — alterations",
            "Repairs — electrician",
            "Misc cash expense",
        ],
    },
}


def weighted_category() -> str:
    """Pick a category using the rough-proportional weights above."""
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    return random.choices(categories, weights=weights, k=1)[0]


def random_date_within_past_months(months: int) -> date:
    """Return a random date in the past `months` months (today included)."""
    today = date.today()
    # Look back `months` calendar months, then sample a random day in that window.
    start_month = today.month - months
    start_year = today.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start = date(start_year, start_month, 1)
    span_days = (today - start).days
    if span_days <= 0:
        return today
    return start + timedelta(days=random.randint(0, span_days))


def seed_expenses(user_id: int, count: int, months: int) -> None:
    conn = get_db()
    try:
        # Build the insert list up front so we can commit atomically.
        rows = []
        for _ in range(count):
            category = weighted_category()
            meta = CATEGORIES[category]
            low, high = meta["range"]
            # Round to 2 decimal places and a whole-rupee for cash-like categories.
            amount = round(random.uniform(low, high), 2)
            description = random.choice(meta["descriptions"])
            d = random_date_within_past_months(months)
            rows.append((user_id, amount, category, d.isoformat(), description))

        # Single transaction: either all rows insert or none do.
        try:
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise RuntimeError(f"Insert failed, rolled back: {exc}") from exc

        # Fetch a date range + sample rows for the confirmation summary.
        stats = conn.execute(
            "SELECT MIN(date) AS min_date, MAX(date) AS max_date, COUNT(*) AS n "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        sample_rows = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC LIMIT 5",
            (user_id,),
        ).fetchall()

    finally:
        conn.close()

    print(f"Inserted {stats['n']} expenses for user_id={user_id}")
    print(f"Date range: {stats['min_date']} to {stats['max_date']}")
    print("Sample of 5 most recent:")
    for row in sample_rows:
        print(f"  id={row['id']}  {row['date']}  ₹{row['amount']:>7.2f}  "
              f"{row['category']:<13} {row['description']}")


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        return 1
    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        return 1

    if count <= 0 or months <= 0:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        return 1

    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        print(f"No user found with id {user_id}.")
        return 1

    seed_expenses(user_id, count, months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
