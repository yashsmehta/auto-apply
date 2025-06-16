#!/usr/bin/env python3
"""Command Line Interface for auto-apply"""
import argparse
import csv
import os
import sys
from typing import List, Dict

from core.processor import process_application, save_results
from core.claude import ClaudeMCP
from core.scraper import WebScraper
from core.utils import sanitize_filename


def read_csv(file_path: str) -> List[Dict[str, str]]:
    """Read CSV file and return list of applications"""
    applications = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'app_name' in row and 'info_url' in row and 'application_url' in row:
                applications.append({
                    'app_name': row['app_name'].strip(),
                    'info_url': row['info_url'].strip(),
                    'application_url': row['application_url'].strip(),
                    'context': row.get('context', '').strip()  # Optional context field
                })
    return applications


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='Auto-Apply: Automated application form processor'
    )
    parser.add_argument(
        'input',
        nargs='?',
        default='applications.csv',
        help='Input CSV file (default: applications.csv)'
    )
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching for scraping and Claude responses'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found!", file=sys.stderr)
        print("\nPlease create a CSV file with the following columns:")
        print("app_name,info_url,application_url[,context]")
        print("\nExample:")
        print('Company A,https://example.com/info,https://example.com/apply,"Additional context"')
        return 1
    
    # Read applications from CSV
    applications = read_csv(args.input)
    if not applications:
        print("No valid applications found in CSV!", file=sys.stderr)
        return 1
    
    print(f"Found {len(applications)} applications to process")
    
    # Initialize Claude MCP
    claude = ClaudeMCP(use_cache=not args.no_cache)
    
    # Process each application
    successful = 0
    failed = 0
    
    with WebScraper(use_cache=not args.no_cache) as scraper:
        for i, app in enumerate(applications, 1):
            print(f"\n[{i}/{len(applications)}] Processing: {app['app_name']}")
            
            try:
                results = process_application(app, scraper, claude)
                
                if results.get('status') == 'success':
                    save_results(app['app_name'], results)
                    safe_name = sanitize_filename(app['app_name'])
                    print(f"  ✓ Saved results to: {args.output}/{safe_name}/")
                    successful += 1
                else:
                    print(f"  ✗ Failed: {results.get('error', 'Unknown error')}")
                    failed += 1
                    
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                failed += 1
                if args.verbose:
                    import traceback
                    traceback.print_exc()
    
    # Summary
    print(f"\nProcessing complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())