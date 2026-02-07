#!/usr/bin/env python3
"""
Command-line tool for importing CSV files into Transaction X-Ray
"""
import sys
import argparse
from pathlib import Path
from database import TransactionDatabase
from csv_parser import CSVParser


def main():
    parser = argparse.ArgumentParser(description='Import CSV files into Transaction X-Ray')
    parser.add_argument('files', nargs='*', help='CSV files to import')
    parser.add_argument('-d', '--directory', help='Import all CSV files from directory')
    parser.add_argument('--clear', action='store_true', help='Clear all existing data first')
    parser.add_argument('--stats', action='store_true', help='Show statistics after import')

    args = parser.parse_args()

    db = TransactionDatabase()
    csv_parser = CSVParser()

    # Clear data if requested
    if args.clear:
        confirm = input('⚠️  Are you sure you want to clear all data? (yes/no): ')
        if confirm.lower() == 'yes':
            db.clear_all_transactions()
            print('✅ All data cleared')
        else:
            print('❌ Clear operation cancelled')
            return

    # Collect files to import
    files_to_import = []

    if args.directory:
        dir_path = Path(args.directory)
        if not dir_path.is_dir():
            print(f'❌ Error: {args.directory} is not a valid directory')
            sys.exit(1)
        files_to_import.extend(dir_path.glob('*.csv'))
        print(f'📂 Found {len(files_to_import)} CSV files in {args.directory}')

    if args.files:
        for file_path in args.files:
            path = Path(file_path)
            if path.exists():
                files_to_import.append(path)
            else:
                print(f'⚠️  Warning: {file_path} does not exist, skipping')

    if not files_to_import:
        print('❌ No CSV files to import')
        parser.print_help()
        sys.exit(1)

    # Import files
    total_imported = 0
    successful_files = 0
    errors = []

    for file_path in files_to_import:
        try:
            print(f'📄 Processing {file_path.name}...', end=' ')
            transactions = csv_parser.parse_file(str(file_path))
            count = db.insert_bulk(transactions)
            total_imported += count
            successful_files += 1
            print(f'✅ {count} transactions')
        except Exception as e:
            print(f'❌ Error: {e}')
            errors.append((file_path.name, str(e)))

    # Summary
    print('\n' + '='*60)
    print(f'✅ Successfully imported {total_imported} transactions from {successful_files} file(s)')

    if errors:
        print(f'\n⚠️  Errors encountered:')
        for filename, error in errors:
            print(f'  - {filename}: {error}')

    # Show stats if requested
    if args.stats:
        print('\n' + '='*60)
        print('📊 DATABASE STATISTICS')
        print('='*60)

        total = db.get_total_count()
        print(f'Total transactions: {total}')

        if total > 0:
            transactions = db.get_all_transactions()
            total_spent = sum(t['amount'] for t in transactions if t['amount'] > 0)
            total_income = sum(abs(t['amount']) for t in transactions if t['amount'] < 0)

            print(f'Total spent: ${total_spent:,.2f}')
            print(f'Total income: ${total_income:,.2f}')
            print(f'Net: ${(total_income - total_spent):,.2f}')

            print('\n📂 By Account:')
            for account in db.get_account_summary():
                print(f"  {account['account_type']}: {account['transaction_count']} transactions, ${account['total_spent']:,.2f} spent")

            print('\n📊 Top Categories:')
            for cat in db.get_spending_by_category()[:5]:
                print(f"  {cat['category']}: ${cat['total_spent']:,.2f}")


if __name__ == '__main__':
    main()
