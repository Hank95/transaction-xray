"""
Flask web application for Transaction X-Ray
Provides web interface and API endpoints
"""
from flask import Flask, render_template, request, jsonify
import os
from pathlib import Path
from database import TransactionDatabase
from csv_parser import CSVParser
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

app = Flask(__name__)
db = TransactionDatabase()
parser = CSVParser()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    transactions = db.get_all_transactions()
    monthly_summary = db.get_monthly_summary()
    category_spending = db.get_spending_by_category()
    account_summary = db.get_account_summary()

    # Calculate totals
    total_spent = sum(t['amount'] for t in transactions if t['amount'] > 0)
    total_income = sum(abs(t['amount']) for t in transactions if t['amount'] < 0)

    # Get date range
    if transactions:
        dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in transactions]
        earliest = min(dates).strftime('%Y-%m-%d')
        latest = max(dates).strftime('%Y-%m-%d')
    else:
        earliest = latest = None

    return jsonify({
        'total_transactions': len(transactions),
        'total_spent': round(total_spent, 2),
        'total_income': round(total_income, 2),
        'net': round(total_income - total_spent, 2),
        'date_range': {
            'earliest': earliest,
            'latest': latest
        },
        'monthly_summary': monthly_summary,
        'category_spending': category_spending,
        'account_summary': account_summary
    })


@app.route('/api/transactions')
def get_transactions():
    """Get transactions with optional filtering"""
    limit = request.args.get('limit', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    account = request.args.get('account')

    if start_date and end_date:
        transactions = db.get_transactions_by_date_range(start_date, end_date)
    else:
        transactions = db.get_all_transactions(limit=limit)

    # Filter by category if specified
    if category:
        transactions = [t for t in transactions if t.get('category') == category]

    # Filter by account if specified
    if account:
        transactions = [t for t in transactions if t.get('account_type') == account]

    return jsonify(transactions)


@app.route('/api/charts/category-spending')
def category_spending_chart():
    """Generate category spending pie chart data"""
    category_data = db.get_spending_by_category()

    # Filter out very small amounts for cleaner chart
    significant_categories = [c for c in category_data if c['total_spent'] > 10]

    labels = [c['category'] for c in significant_categories]
    values = [c['total_spent'] for c in significant_categories]

    return jsonify({
        'labels': labels,
        'values': values
    })


@app.route('/api/charts/monthly-trend')
def monthly_trend_chart():
    """Generate monthly spending trend chart data"""
    monthly_data = db.get_monthly_summary()

    # Sort by month
    monthly_data.sort(key=lambda x: x['month'])

    return jsonify({
        'months': [m['month'] for m in monthly_data],
        'spending': [m['total_spent'] for m in monthly_data],
        'income': [m['total_income'] for m in monthly_data]
    })


@app.route('/api/import', methods=['POST'])
def import_csv():
    """Import CSV file(s) into database"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    imported_count = 0
    errors = []

    for file in files:
        try:
            # Save temporarily
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)

            # Parse and import
            transactions = parser.parse_file(temp_path)
            count = db.insert_bulk(transactions)
            imported_count += count

            # Clean up
            os.remove(temp_path)

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    response = {
        'imported': imported_count,
        'files_processed': len(files) - len(errors)
    }

    if errors:
        response['errors'] = errors

    return jsonify(response)


@app.route('/api/import-directory', methods=['POST'])
def import_directory():
    """Import all CSV files from a directory"""
    data = request.get_json()
    directory = data.get('directory')

    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid directory'}), 400

    csv_files = list(Path(directory).glob('*.csv'))
    imported_count = 0
    errors = []

    for csv_file in csv_files:
        try:
            transactions = parser.parse_file(str(csv_file))
            count = db.insert_bulk(transactions)
            imported_count += count
        except Exception as e:
            errors.append(f"{csv_file.name}: {str(e)}")

    response = {
        'imported': imported_count,
        'files_processed': len(csv_files) - len(errors)
    }

    if errors:
        response['errors'] = errors

    return jsonify(response)


@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    """Clear all transactions (use with caution!)"""
    db.clear_all_transactions()
    return jsonify({'message': 'All transactions cleared'})


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    app.run(debug=True, port=8000)
