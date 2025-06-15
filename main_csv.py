"""Legacy CSV processing module for auto-apply
This provides the original CSV batch processing functionality.
For the web interface, run main.py instead.
"""
import csv
import os
from typing import List, Dict, Any
from core import ClaudeMCP, WebScraper, process_application, save_results, sanitize_filename


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
                    'application_url': row['application_url'].strip()
                })
    return applications


def main():
    """Main function - maintains original CLI functionality"""
    # Check if CSV file exists
    csv_file = 'applications.csv'
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        print("\nPlease create a CSV file with the following columns:")
        print("app_name,info_url,application_url")
        return
    
    # Read applications from CSV
    applications = read_csv(csv_file)
    if not applications:
        print("No valid applications found in CSV!")
        return
    
    print(f"Found {len(applications)} applications to process")
    
    # Initialize Claude MCP
    claude = ClaudeMCP()
    
    # Process each application
    with WebScraper() as scraper:
        for app in applications:
            results = process_application(app, scraper, claude)
            save_results(app['app_name'], results)
            safe_name = sanitize_filename(app['app_name'])
            print(f"  Saved results to: output/{safe_name}/")
    
    print("\nProcessing complete!")


if __name__ == "__main__":
    main()