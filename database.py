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
