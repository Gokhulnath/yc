import os
import re
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database connection parameters from environment variables
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = os.environ.get("DB_PORT", "5432")


def clean_domain(url):
    """
    Clean a URL by removing http, https, www and unnecessary characters
    """
    if not url:
        return None

    # Add http:// prefix if not present (required for urlparse)
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    # Parse the URL
    parsed_url = urlparse(url)

    # Get the netloc (domain with subdomain)
    domain = parsed_url.netloc

    # Remove www. if present
    domain = re.sub(r'^www\.', '', domain)

    # Remove any trailing special characters
    special_chars = ['\'', '"', '@', '#', '\\', '/']
    while domain and domain[-1] in special_chars:
        domain = domain[:-1]

    return domain


def update_domains():
    """
    Connect to the database, read records, clean domains and update them
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )

        # Create a cursor
        cur = conn.cursor()

        # Get all companies with links
        cur.execute("SELECT id, domain FROM companies WHERE domain IS NOT NULL")
        companies = cur.fetchall()

        print(f"Found {len(companies)} companies with links")

        # Process each company
        updated_count = 0
        for company_id, link in companies:
            # Clean the domain
            clean_domain_value = clean_domain(link)

            if clean_domain_value:
                # Update the domain in the database
                cur.execute(
                    "UPDATE companies SET domain = %s WHERE id = %s",
                    (clean_domain_value, company_id)
                )
                updated_count += 1

        # Commit the changes
        conn.commit()
        print(f"Updated domains for {updated_count} companies")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the cursor and connection
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    update_domains()
