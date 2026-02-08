"""
Database module for Transaction X-Ray
Handles SQLite database operations and transaction storage
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json


class TransactionDatabase:
    """Manages the SQLite database for storing normalized transactions"""

    def __init__(self, db_path: str = "transactions.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main transactions table with normalized structure
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                merchant TEXT,
                category TEXT,
                amount REAL NOT NULL,
                account_type TEXT NOT NULL,
                account_name TEXT,
                transaction_type TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON transactions(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_account_type ON transactions(account_type)
        """)

        # Budgets table for monthly budget tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category)
            )
        """)

        # Category mappings table for learned categorization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_pattern TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Recurring transactions table for subscription/bill detection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_pattern TEXT NOT NULL UNIQUE,
                category TEXT,
                frequency TEXT NOT NULL,
                average_amount REAL NOT NULL,
                last_amount REAL,
                last_date TEXT,
                occurrence_count INTEGER DEFAULT 0,
                amount_variance REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_subscription INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def insert_transaction(self, transaction: Dict) -> int:
        """Insert a single transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transactions
            (date, description, merchant, category, amount, account_type,
             account_name, transaction_type, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction['date'],
            transaction['description'],
            transaction.get('merchant'),
            transaction.get('category'),
            transaction['amount'],
            transaction['account_type'],
            transaction.get('account_name'),
            transaction.get('transaction_type'),
            json.dumps(transaction.get('raw_data', {}))
        ))

        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return transaction_id

    def insert_bulk(self, transactions: List[Dict]) -> int:
        """Insert multiple transactions efficiently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        data = [
            (
                t['date'],
                t['description'],
                t.get('merchant'),
                t.get('category'),
                t['amount'],
                t['account_type'],
                t.get('account_name'),
                t.get('transaction_type'),
                json.dumps(t.get('raw_data', {}))
            )
            for t in transactions
        ]

        cursor.executemany("""
            INSERT INTO transactions
            (date, description, merchant, category, amount, account_type,
             account_name, transaction_type, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)

        count = cursor.rowcount
        conn.commit()
        conn.close()

        return count

    def get_all_transactions(self, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve all transactions, optionally limited"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM transactions ORDER BY date DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get transactions within a date range"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM transactions
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (start_date, end_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_spending_by_category(self, start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> List[Dict]:
        """Get total spending grouped by category"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT
                COALESCE(category, 'Uncategorized') as category,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_spent,
                COUNT(*) as transaction_count
            FROM transactions
        """

        params = []
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]

        query += " GROUP BY category ORDER BY total_spent DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_monthly_summary(self) -> List[Dict]:
        """Get spending summary by month"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_spent,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_income,
                COUNT(*) as transaction_count
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_category_trends(self) -> Dict:
        """Get spending trends by category over time"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                strftime('%Y-%m', date) as month,
                COALESCE(category, 'Uncategorized') as category,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_spent
            FROM transactions
            WHERE category NOT IN ('Transfer', 'Payment', 'Income')
            GROUP BY month, category
            ORDER BY month, category
        """)

        rows = cursor.fetchall()
        conn.close()

        # Reorganize data by category
        trends_by_category = {}
        all_months = set()

        for row in rows:
            month = row['month']
            category = row['category']
            amount = row['total_spent']

            all_months.add(month)

            if category not in trends_by_category:
                trends_by_category[category] = {}

            trends_by_category[category][month] = amount

        # Convert to list format for Plotly
        months = sorted(list(all_months))
        category_data = []

        for category, month_data in trends_by_category.items():
            values = [month_data.get(month, 0) for month in months]
            category_data.append({
                'category': category,
                'months': months,
                'values': values
            })

        return {
            'months': months,
            'categories': category_data
        }

    def get_account_summary(self) -> List[Dict]:
        """Get spending summary by account"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                account_type,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_spent,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_credits,
                COUNT(*) as transaction_count
            FROM transactions
            GROUP BY account_type
            ORDER BY total_spent DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def clear_all_transactions(self):
        """Clear all transactions from database (use with caution!)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions")
        conn.commit()
        conn.close()

    def get_total_count(self) -> int:
        """Get total number of transactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # Budget Management Methods

    def set_budget(self, category: str, monthly_limit: float) -> None:
        """Set or update monthly budget for a category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO budgets (category, monthly_limit, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(category)
            DO UPDATE SET monthly_limit = ?, updated_at = CURRENT_TIMESTAMP
        """, (category, monthly_limit, monthly_limit))

        conn.commit()
        conn.close()

    def get_budget(self, category: str) -> Optional[Dict]:
        """Get budget for a specific category"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM budgets WHERE category = ?
        """, (category,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_all_budgets(self) -> List[Dict]:
        """Get all budgets"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM budgets ORDER BY category")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_budget(self, category: str) -> None:
        """Delete budget for a category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE category = ?", (category,))
        conn.commit()
        conn.close()

    def get_budget_status(self, year_month: Optional[str] = None) -> List[Dict]:
        """
        Get budget status showing actual spending vs budget for each category
        year_month format: 'YYYY-MM' (e.g., '2026-02')
        If not provided, uses current month
        """
        import datetime

        if not year_month:
            year_month = datetime.datetime.now().strftime('%Y-%m')

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get actual spending for the month, excluding Transfer and Payment
        cursor.execute("""
            SELECT
                b.category,
                b.monthly_limit as budget,
                COALESCE(SUM(CASE
                    WHEN t.amount > 0
                    AND t.category NOT IN ('Transfer', 'Payment', 'Income')
                    THEN t.amount
                    ELSE 0
                END), 0) as actual,
                b.monthly_limit - COALESCE(SUM(CASE
                    WHEN t.amount > 0
                    AND t.category NOT IN ('Transfer', 'Payment', 'Income')
                    THEN t.amount
                    ELSE 0
                END), 0) as remaining
            FROM budgets b
            LEFT JOIN transactions t ON b.category = t.category
                AND strftime('%Y-%m', t.date) = ?
            GROUP BY b.category, b.monthly_limit
            ORDER BY b.category
        """, (year_month,))

        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            data = dict(row)
            data['percent_used'] = (data['actual'] / data['budget'] * 100) if data['budget'] > 0 else 0
            data['over_budget'] = data['actual'] > data['budget']
            result.append(data)

        return result

    # Category Mapping Methods

    def save_category_mapping(self, merchant_pattern: str, category: str) -> None:
        """Save or update a merchant pattern to category mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO category_mappings (merchant_pattern, category)
            VALUES (?, ?)
            ON CONFLICT(merchant_pattern)
            DO UPDATE SET category = ?, created_at = CURRENT_TIMESTAMP
        """, (merchant_pattern, category, category))

        conn.commit()
        conn.close()

    def get_all_category_mappings(self) -> List[Dict]:
        """Get all learned category mappings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM category_mappings
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_category_mapping(self, merchant_pattern: str) -> Optional[str]:
        """Get category for a merchant pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category FROM category_mappings
            WHERE merchant_pattern = ?
        """, (merchant_pattern,))

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    def update_transactions_by_pattern(self, merchant_pattern: str, category: str) -> int:
        """Update all transactions matching a merchant pattern to a new category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use LIKE to match the pattern anywhere in the description
        cursor.execute("""
            UPDATE transactions
            SET category = ?
            WHERE UPPER(description) LIKE '%' || ? || '%'
            AND (category = 'Other' OR category = 'Uncategorized' OR category IS NULL)
        """, (category, merchant_pattern.upper()))

        count = cursor.rowcount
        conn.commit()
        conn.close()

        return count

    def delete_category_mapping(self, mapping_id: int) -> None:
        """Delete a category mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM category_mappings WHERE id = ?", (mapping_id,))
        conn.commit()
        conn.close()

    # Recurring Transaction Detection Methods

    def detect_recurring_transactions(self) -> int:
        """Analyze transactions to detect recurring patterns"""
        from datetime import datetime
        from collections import defaultdict

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all transactions with positive amounts (expenses), sorted by merchant and date
        cursor.execute("""
            SELECT id, date, description, merchant, category, amount
            FROM transactions
            WHERE amount > 0
            ORDER BY merchant, date
        """)

        transactions = cursor.fetchall()

        # Group transactions by merchant
        merchant_groups = defaultdict(list)
        for t in transactions:
            merchant = t['merchant'] or t['description'][:30]  # Use first 30 chars if no merchant
            merchant_groups[merchant].append({
                'date': t['date'],
                'amount': t['amount'],
                'category': t['category']
            })

        detected_count = 0

        # Analyze each merchant group
        for merchant, txns in merchant_groups.items():
            if len(txns) < 3:  # Need at least 3 occurrences
                continue

            # Calculate intervals between transactions
            dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in txns]
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates) - 1)]

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            # Determine if it's recurring based on interval consistency
            # Allow 20% variance in interval
            is_recurring = False
            frequency = None

            if 6 <= avg_interval <= 9:  # Weekly (7 days ± 2)
                is_recurring = all(5 <= i <= 10 for i in intervals)
                frequency = 'weekly'
            elif 25 <= avg_interval <= 35:  # Monthly (30 days ± 5)
                is_recurring = all(20 <= i <= 40 for i in intervals)
                frequency = 'monthly'
            elif 85 <= avg_interval <= 95:  # Quarterly (90 days ± 5)
                is_recurring = all(80 <= i <= 100 for i in intervals)
                frequency = 'quarterly'
            elif 350 <= avg_interval <= 380:  # Annual (365 days ± 15)
                is_recurring = all(340 <= i <= 390 for i in intervals)
                frequency = 'annual'

            if is_recurring and frequency:
                amounts = [t['amount'] for t in txns]
                avg_amount = sum(amounts) / len(amounts)
                last_amount = amounts[-1]
                last_date = txns[-1]['date']
                category = txns[0]['category']

                # Calculate amount variance
                amount_variance = max(amounts) - min(amounts)

                # Determine if it's likely a subscription
                is_subscription = (
                    frequency in ['monthly', 'annual'] and
                    amount_variance < avg_amount * 0.1 and  # Less than 10% variance
                    category in ['Subscriptions', 'Software/Tech', 'Entertainment']
                )

                # Save to recurring_transactions table
                cursor.execute("""
                    INSERT INTO recurring_transactions
                    (merchant_pattern, category, frequency, average_amount, last_amount,
                     last_date, occurrence_count, amount_variance, is_subscription)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(merchant_pattern)
                    DO UPDATE SET
                        category = ?,
                        frequency = ?,
                        average_amount = ?,
                        last_amount = ?,
                        last_date = ?,
                        occurrence_count = ?,
                        amount_variance = ?,
                        is_subscription = ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (merchant, category, frequency, avg_amount, last_amount, last_date,
                      len(txns), amount_variance, int(is_subscription),
                      category, frequency, avg_amount, last_amount, last_date,
                      len(txns), amount_variance, int(is_subscription)))

                detected_count += 1

        conn.commit()
        conn.close()

        return detected_count

    def get_recurring_transactions(self, active_only: bool = True) -> List[Dict]:
        """Get all detected recurring transactions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM recurring_transactions"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY frequency, average_amount DESC"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_recurring_transaction(self, recurring_id: int, updates: Dict) -> None:
        """Update a recurring transaction record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(recurring_id)

            query = f"UPDATE recurring_transactions SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

        conn.close()

    def delete_recurring_transaction(self, recurring_id: int) -> None:
        """Delete a recurring transaction record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recurring_transactions WHERE id = ?", (recurring_id,))
        conn.commit()
        conn.close()
