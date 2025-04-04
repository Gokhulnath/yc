import requests
import os
import psycopg2
import re
from urllib.parse import urlparse
import time


def sanitize_filename(url):
    """Convert a URL into a valid filename"""
    # Get domain name as base of filename
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove invalid filename characters and replace with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", domain)

    return f"{sanitized}.html"


def download_and_save_html(url, output_dir="downloaded_html"):
    """Download HTML from URL and save to file"""
    try:
        # Add http:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        # Make request with timeout and user-agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)

        # Check if request was successful
        if response.status_code == 200:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Generate filename from URL
            filename = sanitize_filename(url)
            filepath = os.path.join(output_dir, filename)

            # Save HTML content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"Successfully downloaded {url} to {filepath}")
            return True

        else:
            print(f"Failed to download {url}, status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False


def process_companies_table(db_params, table_name="companies"):
    """Process all URLs in the companies table"""
    conn = None

    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Get all links from the table
        cursor.execute(f"SELECT id, link FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            print(f"No links found in table '{table_name}'")
            return

        print(f"Found {len(rows)} links to process")

        # Track statistics
        success_count = 0
        error_count = 0

        # Process each link
        for row_id, link in rows:
            if link and isinstance(link, str) and link.strip():
                print(f"Processing company ID {row_id}, URL: {link}")

                # Add delay to avoid rate limiting
                time.sleep(1)

                if download_and_save_html(link):
                    success_count += 1
                else:
                    error_count += 1
            else:
                print(f"Skipping empty or invalid link for company ID {row_id}")

        print(f"\nDownload Summary:")
        print(f"- Successfully downloaded: {success_count}")
        print(f"- Failed to download: {error_count}")
        print(f"- Total processed: {len(rows)}")

    except Exception as e:
        print(f"Database error: {str(e)}")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    # PostgreSQL connection parameters - adjust these for your environment
    db_params = {
        'host': 'localhost',
        'database': 'company_database',
        'user': 'postgres',
        'password': 'your_password',
        'port': '5432'
    }

    companies_table = "companies"

    print(f"Starting to download HTML from links in {companies_table} table")
    process_companies_table(db_params, companies_table)
    print("Processing complete")