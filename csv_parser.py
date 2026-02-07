"""
CSV Parser module for Transaction X-Ray
Handles parsing of different bank CSV formats and normalizes them
"""
import csv
import re
from datetime import datetime
from typing import List, Dict
from pathlib import Path


class CSVParser:
    """Parses CSV files from different banks and normalizes the data"""

    def __init__(self, db=None):
        self.db = db
        self.parsers = {
            'amex': self._parse_amex,
            'apple': self._parse_apple_card,
            'checking': self._parse_checking
        }
        self._load_category_mappings()

    def _load_category_mappings(self):
        """Load learned category mappings from database"""
        self.learned_mappings = {}
        if self.db:
            try:
                mappings = self.db.get_all_category_mappings()
                for mapping in mappings:
                    pattern = mapping['merchant_pattern'].upper()
                    category = mapping['category']
                    self.learned_mappings[pattern] = category
            except Exception:
                # Database might not be initialized yet or table doesn't exist
                pass

    def detect_format(self, file_path: str) -> str:
        """Detect which bank format the CSV is"""
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline().strip()

        if 'Card Member' in header and 'Account #' in header:
            return 'amex'
        elif 'Transaction Date' in header and 'Clearing Date' in header:
            return 'apple'
        elif 'Withdrawal' in header and 'Deposit' in header:
            return 'checking'
        else:
            raise ValueError(f"Unknown CSV format. Header: {header}")

    def parse_file(self, file_path: str, account_type: str = None) -> List[Dict]:
        """Parse a CSV file and return normalized transactions"""
        if account_type is None:
            account_type = self.detect_format(file_path)

        parser_func = self.parsers.get(account_type)
        if not parser_func:
            raise ValueError(f"Unknown account type: {account_type}")

        return parser_func(file_path)

    def _parse_amex(self, file_path: str) -> List[Dict]:
        """Parse American Express CSV format"""
        transactions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Amex uses negative amounts for charges, positive for credits
                # We'll normalize to positive for expenses, negative for credits/refunds
                amount = float(row['Amount'])

                # Clean up description
                description = row['Description'].strip()

                # Try to extract merchant name (usually first part before location)
                merchant = self._extract_merchant(description)

                transactions.append({
                    'date': self._normalize_date(row['Date']),
                    'description': description,
                    'merchant': merchant,
                    'category': self._categorize_transaction(description),
                    'amount': abs(amount),  # Store as positive for expenses
                    'account_type': 'Amex',
                    'account_name': row.get('Card Member', ''),
                    'transaction_type': 'credit' if amount > 0 else 'debit',
                    'raw_data': dict(row)
                })

        return transactions

    def _parse_apple_card(self, file_path: str) -> List[Dict]:
        """Parse Apple Card CSV format"""
        transactions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Apple Card uses positive for charges, negative for payments
                amount = float(row['Amount (USD)'])

                # Skip if this is a payment (negative amount)
                transaction_type = row['Type']

                # Get Apple's category and normalize it to our categories
                apple_category = row.get('Category', 'Uncategorized')
                normalized_category = self._normalize_apple_category(apple_category)

                transactions.append({
                    'date': self._normalize_date(row['Transaction Date']),
                    'description': row['Description'].strip(),
                    'merchant': row.get('Merchant', '').strip(),
                    'category': normalized_category,
                    'amount': abs(amount),
                    'account_type': 'Apple Card',
                    'account_name': row.get('Purchased By', ''),
                    'transaction_type': 'payment' if amount < 0 else 'purchase',
                    'raw_data': dict(row)
                })

        return transactions

    def _parse_checking(self, file_path: str) -> List[Dict]:
        """Parse checking account CSV format"""
        transactions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Checking has separate Withdrawal and Deposit columns
                withdrawal = self._parse_amount(row['Withdrawal'])
                deposit = self._parse_amount(row['Deposit'])

                # Determine amount and type
                if withdrawal > 0:
                    amount = withdrawal
                    trans_type = 'withdrawal'
                elif deposit > 0:
                    amount = -deposit  # Store deposits as negative (income)
                    trans_type = 'deposit'
                else:
                    continue  # Skip zero amount transactions

                description = row['Description'].strip()

                transactions.append({
                    'date': self._normalize_date(row['Date']),
                    'description': description,
                    'merchant': self._extract_merchant(description),
                    'category': self._categorize_transaction(description),
                    'amount': amount,
                    'account_type': 'Checking',
                    'account_name': 'Checking Account',
                    'transaction_type': trans_type,
                    'raw_data': dict(row)
                })

        return transactions

    def _normalize_date(self, date_str: str) -> str:
        """Convert various date formats to YYYY-MM-DD"""
        # Handle MM/DD/YYYY format
        try:
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass

        # Handle other common formats
        for fmt in ['%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If all else fails, return as-is
        return date_str

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string, handling $ and , characters"""
        if not amount_str or amount_str.strip() == '':
            return 0.0

        # Remove $, commas, and quotes
        clean = amount_str.replace('$', '').replace(',', '').replace('"', '').strip()

        try:
            return float(clean)
        except ValueError:
            return 0.0

    def _extract_merchant(self, description: str) -> str:
        """Extract merchant name from description"""
        # Remove common patterns and clean up
        # This is a simple implementation - can be enhanced
        merchant = description.split('  ')[0]  # Take first part before double space
        merchant = re.sub(r'\s+\d{5,}.*', '', merchant)  # Remove phone numbers and after
        return merchant.strip()[:100]  # Limit length

    def _normalize_apple_category(self, apple_category: str) -> str:
        """Normalize Apple Card category names to our standard categories"""
        # Map Apple's category names to our categories
        category_mapping = {
            'Restaurants': 'Dining',
            'Food and Drink': 'Dining',
            'Groceries': 'Grocery',
            'Gas Stations': 'Gas',
            'Entertainment': 'Entertainment',
            'Shopping': 'Shopping',
            'Travel': 'Travel',
            'Transportation': 'Transportation',
            'Health and Fitness': 'Healthcare',
            'Services': 'Other',
        }

        return category_mapping.get(apple_category, apple_category)

    def _load_category_mappings(self):
        """Load learned category mappings from database"""
        self.learned_mappings = {}
        if self.db:
            try:
                mappings = self.db.get_all_category_mappings()
                for mapping in mappings:
                    pattern = mapping['merchant_pattern'].upper()
                    category = mapping['category']
                    self.learned_mappings[pattern] = category
            except Exception:
                # Database might not be initialized yet or table doesn't exist
                pass

    def _categorize_transaction(self, description: str) -> str:
        """Auto-categorize transactions based on description keywords"""
        desc_upper = description.upper()
        desc_lower = description.lower()

        # First, check learned category mappings
        for pattern, category in self.learned_mappings.items():
            if pattern in desc_upper:
                return category

        # Category keywords mapping
        # NOTE: Order matters! More specific categories should come first
        categories = {
            'Income': ['payroll', 'salary', 'interest paid', 'platinum lululemon credit',
                      'platinum amex credit', 'cashback', 'refund', 'reimbursement'],
            'Travel': ['amex fine hotels', 'hotel collectn', 'amextravel', 'airbnb', 'vrbo', 'booking.com'],
            'Airlines': ['american airlines', 'delta', 'united airlines', 'southwest', 'jetblue', 'airline'],
            'Software/Tech': ['anthropic', 'supabase', 'claude.ai', 'github', 'aws', 'google cloud', 'vercel', 'openai'],
            'Subscriptions': ['membership fee', 'spotify', 'netflix', 'hulu', 'apple music', 'youtube premium',
                            'apple.com/bill', 'apple services', 'nytimes', 'aplpay nytimes'],
            'Insurance': ['geico', 'state farm', 'progressive', 'bcbs', 'blue cross', 'insurance', 'ethos'],
            'Grocery': ['grocery', 'burbage', 'food lion', 'kroger', 'whole foods', 'trader joe',
                       'publix', 'safeway', 'harris teeter', 'wegmans'],
            'Dining': ['restaurant', 'sugar', 'malagon', 'southbound', 'tippling', 'by the way', 'merci',
                      'cafe', 'coffee', 'one trick pony', 'starbucks', 'pizza', 'burger',
                      'grill', 'bar', 'bistro', 'diner', 'tst*', 'fsp*blue'],
            'Shopping': ['amazon', 'aplpay amazon', 'amazon mktpl', 'mktpl', 'target', 'walmart', 'retail', 'store', 'shop',
                        'mall', 'lululemon', 'j crew'],
            'Gas': ['circle k', 'shell', 'exxonmobil', 'bp', 'chevron', 'gas station', 'fuel', 'citgo', 'marathon',
                   'sunoco', 'wawa', 'buc-ee', 'qt ', 'refuel', 'parkers'],
            'Sports/Exercise': ['gym', 'fitness', 'yoga', 'crossfit', 'peloton', 'strava', 'marathon', 'race',
                               'running', 'cycling', 'swim', 'athletic', 'sports', 'workout'],
            'Transportation': ['uber', 'lyft', 'transit', 'airport parking', 'chs airport', 'toll', 'ultrasignup'],
            'Utilities': ['dominion', 'comcast', 'xfinity', 'electric', 'power', 'water', 'gas company', 'internet',
                         'phone', 'cellular', 'verizon', 'at&t'],
            'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'medical', 'doctor', 'hospital'],
            'Entertainment': ['movie', 'theater', 'concert', 'show', 'tickets'],
            # Transfer should be last to avoid false matches - only match specific patterns
            'Transfer': ['check paid', 'check number', 'check deposit', 'mobile payment', 'autopay payment',
                        'applecard gsbank', 'amex epayment', 'amex dps',
                        'venmo', 'zelle', 'transfer to', 'transfer from',
                        'funds transfer', 'overdraft transfer', 'payment received',
                        'capital one', 'pmt*charleston'],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return category

        return 'Other'

    def get_supported_formats(self) -> List[str]:
        """Return list of supported CSV formats"""
        return list(self.parsers.keys())
