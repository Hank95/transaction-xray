"""
Flask web application for Transaction X-Ray
Provides web interface and API endpoints
"""
from flask import Flask, render_template, request, jsonify
import os
from pathlib import Path
from database import TransactionDatabase
from csv_parser import CSVParser
from datetime import datetime
import json

app = Flask(__name__)
db = TransactionDatabase()
parser = CSVParser(db)


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


@app.route('/api/charts/category-trends')
def category_trends_chart():
    """Generate category spending trends over time"""
    trends = db.get_category_trends()
    return jsonify(trends)


@app.route('/api/import', methods=['POST'])
def import_csv():
    """Import CSV file(s) into database"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    total_imported = 0
    total_duplicates = 0
    errors = []

    for file in files:
        try:
            # Save temporarily
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)

            # Parse and import
            transactions = parser.parse_file(temp_path)
            result = db.insert_bulk(transactions)
            total_imported += result['inserted']
            total_duplicates += result['duplicates']

            # Clean up
            os.remove(temp_path)

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    response = {
        'imported': total_imported,
        'duplicates': total_duplicates,
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
    total_imported = 0
    total_duplicates = 0
    errors = []

    for csv_file in csv_files:
        try:
            transactions = parser.parse_file(str(csv_file))
            result = db.insert_bulk(transactions)
            total_imported += result['inserted']
            total_duplicates += result['duplicates']
        except Exception as e:
            errors.append(f"{csv_file.name}: {str(e)}")

    response = {
        'imported': total_imported,
        'duplicates': total_duplicates,
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


# Budget API Endpoints

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    """Get all budgets"""
    budgets = db.get_all_budgets()
    return jsonify(budgets)


@app.route('/api/budgets/<category>', methods=['GET'])
def get_budget(category):
    """Get budget for a specific category"""
    budget = db.get_budget(category)
    if budget:
        return jsonify(budget)
    return jsonify({'error': 'Budget not found'}), 404


@app.route('/api/budgets', methods=['POST'])
def set_budget():
    """Set or update a budget"""
    data = request.get_json()
    category = data.get('category')
    monthly_limit = data.get('monthly_limit')

    if not category or monthly_limit is None:
        return jsonify({'error': 'Category and monthly_limit required'}), 400

    try:
        monthly_limit = float(monthly_limit)
        if monthly_limit < 0:
            return jsonify({'error': 'Budget must be non-negative'}), 400

        db.set_budget(category, monthly_limit)
        return jsonify({'message': 'Budget set successfully', 'category': category, 'monthly_limit': monthly_limit})
    except ValueError:
        return jsonify({'error': 'Invalid budget amount'}), 400


@app.route('/api/budgets/<category>', methods=['DELETE'])
def delete_budget(category):
    """Delete a budget"""
    db.delete_budget(category)
    return jsonify({'message': 'Budget deleted successfully'})


@app.route('/api/budget-status')
def get_budget_status():
    """Get budget status for current or specified month"""
    year_month = request.args.get('month')  # Optional YYYY-MM parameter
    status = db.get_budget_status(year_month)
    return jsonify(status)


# Category Mapping API Endpoints

@app.route('/api/category-mappings', methods=['GET'])
def get_category_mappings():
    """Get all learned category mappings with statistics"""
    include_stats = request.args.get('stats', 'false').lower() == 'true'

    if include_stats:
        mappings = db.get_category_mappings_with_stats()
    else:
        mappings = db.get_all_category_mappings()

    return jsonify(mappings)


@app.route('/api/category-mappings', methods=['POST'])
def save_category_mapping():
    """Save a new category mapping and update matching transactions"""
    data = request.get_json()
    merchant_pattern = data.get('merchant_pattern')
    category = data.get('category')
    transaction_id = data.get('transaction_id')

    print(f"[DEBUG] Saving mapping: '{merchant_pattern}' → '{category}'")

    if not merchant_pattern or not category:
        print(f"[ERROR] Missing required fields: pattern={merchant_pattern}, category={category}")
        return jsonify({'error': 'merchant_pattern and category required'}), 400

    if not merchant_pattern.strip():
        print(f"[ERROR] Empty merchant pattern after stripping")
        return jsonify({'error': 'merchant_pattern cannot be empty'}), 400

    try:
        # Save the mapping
        db.save_category_mapping(merchant_pattern, category)
        print(f"[DEBUG] Mapping saved to database")

        # Update all matching transactions
        updated_count = db.update_transactions_by_pattern(merchant_pattern, category)
        print(f"[DEBUG] Updated {updated_count} transactions")

        return jsonify({
            'message': 'Mapping saved successfully',
            'merchant_pattern': merchant_pattern,
            'category': category,
            'updated_count': updated_count
        })
    except Exception as e:
        print(f"[ERROR] Exception in save_category_mapping: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/category-mappings/<int:mapping_id>', methods=['PUT'])
def update_category_mapping(mapping_id):
    """Update a category mapping and reapply to transactions"""
    data = request.get_json()
    new_category = data.get('category')

    if not new_category:
        return jsonify({'error': 'Category required'}), 400

    try:
        affected_count = db.update_category_mapping(mapping_id, new_category)
        return jsonify({
            'message': 'Mapping updated successfully',
            'affected_transactions': affected_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/category-mappings/<int:mapping_id>', methods=['DELETE'])
def delete_category_mapping(mapping_id):
    """Delete a category mapping"""
    db.delete_category_mapping(mapping_id)
    return jsonify({'message': 'Mapping deleted successfully'})


@app.route('/api/category-mappings/<int:mapping_id>/transactions', methods=['GET'])
def get_pattern_transactions(mapping_id):
    """Get all transactions matching a specific pattern"""
    transactions = db.get_transactions_by_pattern(mapping_id)
    return jsonify(transactions)


# Recurring Transaction API Endpoints

@app.route('/api/recurring/detect', methods=['POST'])
def detect_recurring():
    """Detect recurring transactions and save patterns"""
    try:
        count = db.detect_recurring_transactions()
        return jsonify({
            'message': f'Detected {count} recurring transaction patterns',
            'count': count
        })
    except Exception as e:
        print(f"[ERROR] Exception in detect_recurring: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/recurring', methods=['GET'])
def get_recurring():
    """Get all detected recurring transactions"""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    recurring = db.get_recurring_transactions(active_only=active_only)
    return jsonify(recurring)


@app.route('/api/recurring/<int:recurring_id>', methods=['PUT'])
def update_recurring(recurring_id):
    """Update a recurring transaction"""
    data = request.get_json()
    try:
        db.update_recurring_transaction(recurring_id, data)
        return jsonify({'message': 'Updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recurring/<int:recurring_id>', methods=['DELETE'])
def delete_recurring(recurring_id):
    """Delete a recurring transaction"""
    db.delete_recurring_transaction(recurring_id)
    return jsonify({'message': 'Deleted successfully'})


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    app.run(debug=True, port=8000)
