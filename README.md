# 💰 Transaction X-Ray

A powerful Python + HTML web application for analyzing your financial transactions from multiple bank accounts. Break free from Excel and get deep insights into your spending, income, and budgeting with intelligent categorization and interactive visualizations.

![Version](https://img.shields.io/badge/version-2.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

### 🏦 Multi-Bank Support
Automatically parses and normalizes CSV files from:
- **American Express** (Amex)
- **Apple Card** (with built-in categories)
- **Checking Accounts** (with separate withdrawal/deposit columns)
- Easy to extend for other banks by adding custom parsers

### 📊 Smart Financial Analysis
- **Intelligent Categorization**: Auto-categorizes transactions into 17+ categories
  - Dining, Grocery, Gas, Shopping, Sports/Exercise, Airlines, Healthcare, Insurance, Travel
  - Software/Tech, Subscriptions, Utilities, Entertainment, Transportation
- **Learning Categorizer**: Interactive modal to categorize "Other" transactions
  - Click, categorize, and the system learns merchant patterns automatically
  - Learned patterns take priority over keyword rules
  - Retroactively updates ALL matching transactions
  - Applies to future imports automatically
- **Category Normalization**: Automatically maps Apple Card categories to standard categories
  - Prevents duplicate categories (e.g., "Restaurants" → "Dining")
- **Transfer Detection**: Automatically identifies account transfers to avoid double-counting
- **Persistent Toggle**: Transfer/Payment filter at top of page (state saved in localStorage)
- **Customizable Categories**: Easy keyword-based system you can extend

### 💰 Monthly Budget Tracking
- **Set Budget Limits**: Define monthly spending limits per category
- **Visual Progress Bars**: Color-coded indicators show budget status
  - 🟢 Green: Under 80% (on track)
  - 🟡 Orange: 80-100% (approaching limit)
  - 🔴 Red: Over 100% (over budget!)
- **Historical View**: Check budget performance for previous months
- **Smart Exclusions**: Automatically excludes transfers and payments
- **Collapsible Section**: Minimize to save screen space (state persists)

### 📈 Visual Dashboard
- **Interactive Pie Chart**: See spending breakdown by category
- **Monthly Trend Chart**: Track spending vs income over time
- **Category Trends Over Time**: Multi-line chart showing spending patterns across all categories
  - See which categories are increasing or decreasing month-over-month
  - Interactive legend to toggle categories on/off
  - Hover to see exact amounts for each category per month
- **Budget Progress Bars**: Visual tracking of spending vs budget limits
- **Summary Cards**: Total transactions, spending, income, and net balance with date ranges
- **Transaction Table**: Searchable, filterable list with 100 most recent transactions
- **Collapsible Sections**: Minimize budget tracker to focus on what matters

### 🔄 Recurring Transaction Detection
- **Intelligent Pattern Recognition**: Automatically detects recurring charges
  - Weekly, monthly, quarterly, and annual patterns
  - Requires minimum 3 occurrences with consistent intervals
- **Subscription Identification**: Flags likely subscriptions
  - Low amount variance (<10%)
  - Monthly or annual frequency
  - Common subscription categories
- **Amount Change Alerts**: Notifies when recurring payments change
  - Compares last payment to average
  - Visual warnings for significant changes (>20%)
- **Detailed Tracking**: Shows frequency, occurrences, last payment date

### 🔧 Data Management
- **Drag-and-drop CSV import** in web interface
- **Batch directory import** for processing multiple files at once
- **SQLite database** for fast queries and portability
- **Privacy-first**: All data stays on your local machine
- **No cloud**: Zero external dependencies or tracking

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd Transaction_Xray
pip install -r requirements.txt
```

**Required packages:**
- Flask 3.0.0 (web framework)
- Pandas 2.1.4 (CSV parsing and data processing)
- python-dateutil 2.8.2 (date parsing)

**Note:** Charts use Plotly.js via CDN (no Python plotly package needed)

### 2. Import Your Transaction Data

**Option A: Using the Web Interface** (Recommended)
```bash
./start.sh
# Or: python3 app.py
```

1. Open http://localhost:8000 in your browser
2. Click "📂 Load All Parent Directory CSVs" to import all files
3. Or drag & drop individual CSV files using "📁 Import CSV Files"

**Option B: Using the Command Line**
```bash
# Import all CSVs from a directory
python3 import_csv.py -d /path/to/csv/files --stats

# Import specific files
python3 import_csv.py file1.csv file2.csv file3.csv

# Clear old data and import fresh
python3 import_csv.py -d /path/to/csv/files --clear --stats
```

### 3. Analyze Your Finances

Navigate to **http://localhost:8000** and explore:
- Toggle "Exclude Transfers & Payments" to see actual spending
- Click "🏷️ Categorize 'Other' Transactions" to teach the system new patterns
- Click on pie chart sections to drill down
- Scroll down to view recent transactions
- Use the monthly trend to spot patterns
- Set budgets and track your spending goals

## 💡 Understanding Double-Counting

### The Problem
If you track both credit cards AND checking accounts, you'll count the same money twice:
1. **Purchase on credit card**: $100 grocery charge → counted once
2. **Payment from checking**: $1000 to Amex → counted again

This inflates your "total spent" by including both the purchases AND the payments.

### The Solution: Transfer Toggle
Use the **"💡 Exclude Transfers & Payments"** checkbox to:
- ✅ See only actual spending on goods/services
- ✅ Remove account transfers and credit card payments
- ✅ Get accurate spending totals (~50% reduction in most cases)

**Example from this dataset:**
- With transfers included: $239,355 total
- With transfers excluded: $120,834 actual spending

## 🎓 Teaching the System: Smart Categorization

Transaction X-Ray learns from you! When transactions are categorized as "Other", you can teach the system to recognize them automatically.

### How It Works

1. **Click** "🏷️ Categorize 'Other' Transactions" at the top of the dashboard
2. **Review** uncategorized transactions in the modal
3. **Select** the correct category from the dropdown
4. **Click ✓** to save

### What Happens Next

The system:
- 🧠 **Extracts the merchant pattern** (e.g., "TWO BLOKES BREWI" from "FSP*TWO BLOKES BREWIMOUNT PLEASAN SC")
- 💾 **Saves it to the database** for future use
- 🔄 **Updates ALL matching transactions** retroactively
- ✨ **Applies to future imports** automatically

### Smart Pattern Extraction

The categorizer intelligently removes:
- Common prefixes (FSP*, TST*, CTLP*, SQ *)
- State abbreviations and ZIP codes
- Extra whitespace and transaction IDs

This ensures accurate matching without being too specific or too generic.

### Example

**Transaction:** `FSP*TWO BLOKES BREWIMOUNT PLEASAN       SC`
**Pattern extracted:** `TWO BLOKES BREWIMOUNT PLEASAN`
**Result:** All future "TWO BLOKES BREWI" transactions → automatically categorized as Dining

The more you teach it, the smarter it gets! Learned patterns take priority over keyword rules.

## 🔄 Managing Recurring Transactions

Track your subscriptions and recurring bills automatically with intelligent pattern detection.

### How Detection Works

The system analyzes all transactions to find patterns based on:
1. **Merchant consistency** - Same merchant appearing multiple times
2. **Interval regularity** - Payments occurring at consistent intervals
3. **Amount stability** - Similar amounts each time (with variance tolerance)

### Running Detection

1. **Scroll to** "🔄 Recurring Transactions & Subscriptions" section
2. **Click** "🔍 Detect Recurring" button
3. **Review** detected patterns and subscriptions

### What Gets Detected

**Frequency Types:**
- **Weekly** - Charges every 7 days (±2 days variance allowed)
- **Monthly** - Charges every 30 days (±5 days variance allowed)
- **Quarterly** - Charges every 90 days (±5 days variance allowed)
- **Annual** - Charges every 365 days (±15 days variance allowed)

**Qualification Criteria:**
- Minimum 3 occurrences required
- Consistent intervals within variance tolerance
- Active transactions (not one-time purchases)

### Subscription Identification

Transactions are marked as subscriptions when:
- Frequency is monthly or annual
- Amount variance is less than 10%
- Category is Subscriptions, Software/Tech, or Entertainment

### Amount Change Alerts

Get notified when recurring amounts change:
- Compares last payment to historical average
- Shows percentage change (e.g., "+15%" or "-8%")
- Visual warning for changes >20%

**Example Alert:**
```
⚠️ Amount changed by 25% from average
Average: $20.00 → Last Payment: $25.00 (+25%)
```

### Typical Results

From a 2-year dataset, you might see:
- Netflix: Monthly subscription, $15.99, 24 payments
- Spotify: Monthly subscription, $9.99, 24 payments
- Car Insurance: Quarterly, $450.00, 8 payments
- Amazon Prime: Annual, $139.00, 2 payments

## 📁 Project Structure

```
Transaction_Xray/
├── app.py                  # Flask web application & API endpoints
├── database.py             # SQLite database manager & queries
├── csv_parser.py           # CSV parsers for different bank formats
├── import_csv.py           # Command-line import tool
├── start.sh                # Easy launcher script
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Web dashboard UI
├── transactions.db        # SQLite database (created on first run)
└── README.md              # This file
```

## 🎯 Usage Examples

### Viewing Your Data

**Start the web app:**
```bash
./start.sh
```

**Access dashboard:** http://localhost:8000

**Stop the server:** Press `Ctrl+C`

### Importing New Transactions

```bash
# Import new month's CSV files
python3 import_csv.py -d ~/Downloads/bank-statements

# See statistics after import
python3 import_csv.py ~/Downloads/amex-feb-2026.csv --stats
```

### Analyzing Spending

1. **Check the box** to exclude transfers and payments (avoid double-counting)
2. **Teach the system** by clicking "🏷️ Categorize 'Other' Transactions" to improve accuracy
3. **Look at pie chart** to see where money goes
4. **Review monthly trends** to spot increases
5. **Analyze category trends** to see which categories are growing or shrinking over time
6. **Detect recurring charges** by clicking "🔍 Detect Recurring" to find subscriptions
7. **Set budgets** by clicking "⚙️ Set Budgets" in the budget section
8. **Track progress** with color-coded progress bars
9. **View history** using the month dropdown to see past performance
10. **Scroll through transactions** to find unexpected charges

## 🔧 Customization

### Adding New Categories

**Option A: Use the UI Categorizer (Recommended)**

Simply click "🏷️ Categorize 'Other' Transactions" and teach the system by categorizing transactions. The system learns and applies patterns automatically!

**Option B: Edit Keyword Rules**

For broader keyword-based rules, edit `csv_parser.py` at line ~250:

```python
categories = {
    'Your New Category': ['keyword1', 'keyword2', 'merchant name'],
    # Add more categories here
}
```

**Tips:**
- More specific keywords should come first
- Use lowercase (matching is case-insensitive)
- Include merchant names you recognize from transactions

### Supporting New Bank Formats

1. **Add a parser method** in `csv_parser.py`:
```python
def _parse_new_bank(self, file_path: str) -> List[Dict]:
    transactions = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append({
                'date': self._normalize_date(row['Date']),
                'description': row['Description'],
                'amount': float(row['Amount']),
                'account_type': 'New Bank',
                # ... etc
            })
    return transactions
```

2. **Register it** in `__init__`:
```python
self.parsers = {
    'amex': self._parse_amex,
    'apple': self._parse_apple_card,
    'checking': self._parse_checking,
    'newbank': self._parse_new_bank  # Add here
}
```

3. **Update detection** in `detect_format`:
```python
if 'Unique Column Name' in header:
    return 'newbank'
```

## 📊 Data Storage

All data is stored in `transactions.db` (SQLite) with four main tables:

### Transactions Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-incrementing primary key |
| date | TEXT | Transaction date (YYYY-MM-DD) |
| description | TEXT | Full transaction description |
| merchant | TEXT | Extracted merchant name |
| category | TEXT | Auto-assigned category |
| amount | REAL | Amount (positive=expense, negative=income) |
| account_type | TEXT | Amex, Apple Card, or Checking |
| account_name | TEXT | Account holder name |
| transaction_type | TEXT | debit, credit, purchase, payment, etc. |
| raw_data | TEXT | Original CSV row as JSON |
| created_at | TIMESTAMP | When imported |

**Indexes:** date, category, account_type for fast queries

### Budgets Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-incrementing primary key |
| category | TEXT | Category name (unique) |
| monthly_limit | REAL | Monthly spending limit |
| created_at | TIMESTAMP | When budget was created |
| updated_at | TIMESTAMP | When budget was last updated |

### Category Mappings Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-incrementing primary key |
| merchant_pattern | TEXT | Merchant name pattern (unique) |
| category | TEXT | Assigned category |
| created_at | TIMESTAMP | When pattern was learned |

**Purpose:** Stores learned merchant patterns from the categorizer. These patterns take priority over keyword-based rules during import and recategorization.

### Recurring Transactions Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-incrementing primary key |
| merchant_pattern | TEXT | Merchant identifier (unique) |
| category | TEXT | Transaction category |
| frequency | TEXT | weekly, monthly, quarterly, or annual |
| average_amount | REAL | Historical average payment amount |
| last_amount | REAL | Most recent payment amount |
| last_date | TEXT | Date of last payment (YYYY-MM-DD) |
| occurrence_count | INTEGER | Number of detected occurrences |
| amount_variance | REAL | Difference between max and min amounts |
| is_active | INTEGER | 1 if currently active, 0 if inactive |
| is_subscription | INTEGER | 1 if identified as subscription |
| notes | TEXT | Optional user notes |
| created_at | TIMESTAMP | When pattern was first detected |
| updated_at | TIMESTAMP | When pattern was last updated |

**Purpose:** Tracks recurring transactions and subscriptions. Automatically populated by detection algorithm and used for monitoring subscription costs and alerting on amount changes.

## 🔒 Privacy & Security

- ✅ **100% Local**: All data stays on your machine
- ✅ **No Cloud**: No external services or APIs
- ✅ **No Tracking**: No analytics or telemetry
- ✅ **You Own It**: SQLite database you can backup/export
- ✅ **Open Source**: Full code transparency

## 🐛 Troubleshooting

### "Port 5000 already in use"
**Solution:** The app now uses port 8000 (macOS reserves 5000 for AirPlay)

### "No transactions found"
**Check:**
- Have you imported CSV files?
- Are they in a supported format?
- Try command-line import with `--stats` to see errors

### Charts not displaying
**Fix:**
- Clear browser cache
- Check browser console for JavaScript errors
- Ensure internet connection (Plotly loads from CDN)

### Import errors
**Verify:**
- CSV file format matches Amex, Apple Card, or Checking
- Date columns are in MM/DD/YYYY format
- Amount columns have numeric values
- Files aren't password-protected Excel files

### Categories seem wrong
**Customize:**
- Edit `csv_parser.py` line 191 to add merchant keywords
- Clear database and re-import: `python3 import_csv.py -d /path --clear`

## 🎉 Recently Added

### v2.2 (Latest)
- [x] **Category Trends Chart** - Multi-line visualization of spending patterns over time
- [x] **Recurring Transaction Detection** - Automatically identify subscriptions and bills
- [x] **Subscription Identification** - Smart detection of subscription services
- [x] **Amount Change Alerts** - Notifications when recurring payments vary
- [x] **Date Ranges in Summary Cards** - See time period for all financial data

### v2.1
- [x] **Learning Categorizer** - Interactive modal to teach transaction patterns
- [x] **Smart Pattern Extraction** - Removes noise, keeps core merchant names
- [x] **Retroactive Updates** - All matching transactions recategorized automatically
- [x] **Sports/Exercise Category** - Gym, fitness, yoga, running, etc.
- [x] **Improved Error Handling** - Visible warnings and debug logging
- [x] **Persistent Toggle State** - Transfer filter saves to localStorage
- [x] **Amazon Marketplace Fix** - MKTPL transactions now categorize as Shopping

### v2.0
- [x] **Monthly budget tracking** with visual progress bars
- [x] **Budget alerts** (color-coded warnings)
- [x] **Category normalization** (merged duplicate categories)
- [x] **Collapsible sections** for cleaner UI
- [x] **Transfer/Payment toggle** to avoid double-counting

## 🚀 Future Enhancement Ideas

- [ ] Export to Excel/PDF reports
- [ ] Year-over-year comparisons
- [ ] Spending predictions with ML
- [ ] Bill payment reminders based on recurring patterns
- [ ] Search and advanced filtering in transaction table
- [ ] Multi-currency support
- [ ] Mobile-responsive design improvements
- [ ] Savings goals tracker with visual progress
- [ ] Bulk edit/merge categories
- [ ] Custom category creation from UI
- [ ] Merchant management dashboard
- [ ] Email/SMS alerts for budget overruns
- [ ] Tax category tagging for deductions

## 📝 Technical Details

**Architecture:**
- **Frontend**: Vanilla JavaScript with Plotly.js for charts
- **Backend**: Flask (Python) REST API
- **Database**: SQLite with indexed queries
- **Parsing**: Pandas for CSV processing
- **Filtering**: Client-side for instant toggle response

**Why these choices:**
- **Flask**: Lightweight, easy to extend
- **SQLite**: Portable, no server needed, perfect for local apps
- **Plotly**: Interactive, professional charts
- **No framework**: Fast loading, no build step required

## 📄 License

MIT License - Feel free to use, modify, and distribute for personal or commercial use.

## 🤝 Contributing

This is a personal finance tool, but improvements are welcome! If you add support for a new bank format or useful feature, consider sharing it.

## 💬 Support

For questions or issues:
1. Check the Troubleshooting section above
2. Review the code comments in `csv_parser.py` and `database.py`
3. Test with the command-line tool: `python3 import_csv.py --stats`

---

**Built with ❤️ for better financial insights**

*Stop using Excel. Start using Transaction X-Ray.*
