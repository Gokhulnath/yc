import requests
import os
import psycopg2
import time
from dotenv import load_dotenv
from helper.database_connector import get_db_params_from_env


def download_and_save_html(url, company_id, output_dir="downloaded_html"):
    """Download HTML from URL and save to file using company ID as filename"""
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

            # Use company ID as filename
            filename = f"{company_id}.html"
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

def process_companies_table(table_name="companies"):
    """Process all URLs in the companies table"""
    conn = None

    try:
        # Get database parameters from environment variables
        db_params = get_db_params_from_env()

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

                if download_and_save_html(link, row_id):
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


def get_all_companies_html():
    # PostgreSQL connection parameters - adjust these for your environment
    load_dotenv()
    db_params = get_db_params_from_env()

    # Get table name and output directory from environment or use defaults
    companies_table = "companies"
    output_directory = "downloaded_html"

    print(f"Starting to download HTML from links in {companies_table} table")
    process_companies_table(companies_table)
    print("Processing complete")
