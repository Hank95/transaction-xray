# Transaction X-Ray - Claude Project Context

## Project Overview
A personal finance web application that parses CSV files from multiple banks (Amex, Apple Card, Checking) and provides intelligent categorization and visualization of spending patterns.

**Tech Stack:** Python 3.11+, Flask, SQLite, Plotly.js, Vanilla JavaScript  
**Port:** 8000 (avoiding macOS AirPlay on 5000)  
**Database:** SQLite (`transactions.db`)

## Architecture

### Backend (Python/Flask)
- `app.py` - Flask web server with REST API endpoints
- `database.py` - SQLite operations and transaction storage
- `csv_parser.py` - CSV parsing logic for different bank formats
- `import_csv.py` - CLI tool for batch importing

### Frontend (HTML/JS)
- `templates/index.html` - Single-page dashboard with embedded CSS/JS
- Uses Plotly.js for interactive charts (loaded from CDN)
- Client-side filtering for Transfer/Payment exclusion toggle

### Data Storage
- `transactions.db` - SQLite database with normalized transaction schema
- All data stored locally, no cloud dependencies
- Indexed on: date, category, account_type

## Key Concepts

### Double-Counting Problem
When tracking both credit cards AND checking accounts:
- Credit card purchase: $100 → recorded
- Checking account payment to credit card: $1000 → recorded again
- **Solution:** "Exclude Transfers & Payments" toggle filters out Transfer/Payment categories

### Transaction Normalization
Each bank has different CSV formats:
- **Amex**: Negative amounts = charges, positive = credits
- **Apple Card**: Positive = charges, negative = payments, has built-in categories
- **Checking**: Separate Withdrawal/Deposit columns

All normalized to: `{date, description, merchant, category, amount, account_type, ...}`

### Categorization System
Keyword-based matching in `csv_parser.py` line 191:
- Order matters! More specific categories first
- Categories: Dining, Grocery, Gas, Shopping, Airlines, Insurance, Software/Tech, etc.
- "Transfer" and "Payment" categories for account movements
- Falls back to Apple Card's built-in category if no keyword match

## Common Tasks

### Adding a New Category
Edit `csv_parser.py` line 191:
```python
categories = {
    'New Category': ['keyword1', 'keyword2', 'merchant name'],
}
```
Then reimport: `python3 import_csv.py -d /path --clear --stats`

### Supporting a New Bank
1. Add parser method in `csv_parser.py`: `_parse_new_bank()`
2. Register in `self.parsers` dict
3. Update `detect_format()` to identify CSV headers
4. Test with sample CSV

### Modifying the Dashboard
- **UI Changes**: Edit `templates/index.html` (CSS in `<style>`, JS in `<script>`)
- **API Changes**: Edit `app.py` routes (all prefixed with `/api/`)
- **Database Queries**: Edit `database.py` methods

## Important File Locations

- **Category keywords**: `csv_parser.py:191`
- **Database schema**: `database.py:19`
- **Transfer toggle**: `templates/index.html:440`
- **Flask port**: `app.py:195`
- **CSV parsing**: `csv_parser.py:40-140`
- **API endpoints**: `app.py:26-195`

## Coding Conventions

### Python
- Type hints for function signatures
- Docstrings for classes and public methods
- Date format: YYYY-MM-DD (ISO 8601)
- Amount: positive = expense, negative = income

### Database
- Never store unmasked account numbers
- Keep raw_data as JSON for debugging
- Use parameterized queries
- Index frequently queried columns

### Frontend
- Vanilla JS (no frameworks)
- Plotly for all charts
- Client-side filtering for instant response

## Known Issues & Design Decisions

**Port 5000 → 8000:** macOS reserves 5000 for AirPlay Receiver

**Category Order Matters:** More specific before generic
- ✅ "Airlines" before "Transportation"
- ✅ "Software/Tech" before "Other"

**Client-Side Filtering:** Transfer toggle works in JavaScript, not API
- Pro: Instant response
- Con: May be slow with 10K+ transactions
- Decision: Acceptable for personal use

## Quick Commands

```bash
# Start the app
./start.sh

# Import CSVs
python3 import_csv.py -d /path/to/csvs --stats

# Clear and reimport
python3 import_csv.py -d /path/to/csvs --clear --stats

# Access dashboard
open http://localhost:8000
```

## Project Status

✅ Multi-bank CSV parsing (Amex, Apple Card, Checking)  
✅ SQLite database with normalized schema  
✅ Web dashboard with interactive visualizations  
✅ Smart categorization (15+ categories)  
✅ Transfer/Payment exclusion toggle  
✅ CLI import tool  
✅ Comprehensive README  
✅ Claude context file  

**Ready for production use!** 🎉
