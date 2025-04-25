import requests
import json
import re
import os
import psycopg2
from psycopg2.extras import execute_values
from bs4 import BeautifulSoup
from lxml import html
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("company_updater.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection parameters from .env file
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def _get_db_connection():
    """Create a database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def _get_connection_pool(min_conn=1, max_conn=10):
    """Create a connection pool for database connections"""
    try:
        from psycopg2 import pool

        connection_pool = pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        logger.info(f"Created database connection pool with {min_conn}-{max_conn} connections")
        return connection_pool
    except Exception as e:
        logger.error(f"Error creating connection pool: {e}")
        raise


def _extract_content_to_json(url, extraction_list, timeout=30):
    """
    Extract content from a webpage based on a unified extraction list.
    Args:
        url (str): The URL to scrape
        extraction_list (list): List of dictionaries with extraction specifications
        timeout (int): Request timeout in seconds
    Returns:
        dict: Extracted content
    """
    try:
        # Send HTTP request to the URL
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse using BeautifulSoup for class-based extraction
        soup = BeautifulSoup(response.text, 'html.parser')

        # Parse using lxml for xpath extraction
        tree = html.fromstring(response.text)

        # Dictionary to store results
        results = {}

        # Default extraction for mailto links to collect email addresses
        results["emails"] = _extract_emails_from_content(soup)

        # Initialize all keys with null values
        for item in extraction_list:
            if 'array_name' in item:
                # Initialize array keys
                results[item['array_name']] = []
            elif 'children' in item:
                # Initialize regular card keys
                for child in item['children']:
                    results[child['key_name']] = None
            else:
                # Initialize basic keys
                results[item['key_name']] = None

        # Process each item in the extraction list
        for item in extraction_list:
            # Special handling for array of cards
            if 'array_name' in item and 'children' in item:
                array_items = _extract_array_from_cards(soup, item)
                results[item['array_name']] = array_items
                continue

            # Special handling for single card with links
            if 'children' in item:
                card_links = _extract_links_from_card(soup, item)
                results.update(card_links)
                continue

            key_name = item['key_name']

            # Handle XPath-based extraction
            if 'xpath' in item and item['xpath']:
                xpath = item['xpath']
                elements = tree.xpath(xpath)
                if elements:  # Only update if elements are found
                    text_content = elements[0].text_content().strip() if hasattr(elements[0], 'text_content') else None
                    results[key_name] = text_content

            # Handle class-based extraction
            elif 'class_name' in item and 'tag_type' in item:
                class_name = item['class_name']
                tag_type = item['tag_type']
                elements = soup.find_all(tag_type, class_=class_name)
                if elements:  # Only update if elements are found
                    if len(elements) > 1:
                        content_list = []
                        for element in elements:
                            content_list.append(element.get_text(strip=True))
                        results[key_name] = content_list
                    else:
                        results[key_name] = elements[0].get_text(strip=True)

        return results
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return {}


def _extract_emails_from_content(soup):
    """
    Extract all email addresses from mailto links in the content area.
    Ignores navigation, header, and footer sections.
    Args:
        soup (BeautifulSoup): The parsed HTML
    Returns:
        list: List of unique email addresses
    """
    # Create a list to store unique email addresses
    emails = []

    # Find all mailto links in the document
    mailto_links = soup.select('a[href^="mailto:"]')

    # Elements to ignore (typically navigation, header, footer)
    ignore_selectors = ['nav', 'header', 'footer', '.navigation', '.nav', '.header', '.footer',
                        '#nav', '#header', '#footer', '.navbar', '.site-header', '.site-footer']

    # Build a list of elements to ignore
    elements_to_ignore = []
    for selector in ignore_selectors:
        elements_to_ignore.extend(soup.select(selector))

    # Function to check if an element is within any of the elements to ignore
    def is_within_ignored_element(element):
        for ignored in elements_to_ignore:
            if ignored.find(element) is not None:
                return True
        return False

    # Process each mailto link
    for link in mailto_links:
        # Skip if link is within ignored elements
        if is_within_ignored_element(link):
            continue

        # Extract email from href attribute
        href = link.get('href', '')
        if href.startswith('mailto:'):
            # Extract the email address, handle URL encoding
            email = unquote(href[7:])  # Remove 'mailto:' prefix

            # Remove any additional parameters (like ?subject=)
            if '?' in email:
                email = email.split('?')[0]

            # Validate the email format using a simple regex
            if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                # Add to the list if not already present
                if email not in emails:
                    emails.append(email)

    return emails


def _extract_links_from_card(soup, card_config):
    """
    Extract links from cards based on specified configuration.
    Args:
        soup (BeautifulSoup): The parsed HTML
        card_config (dict): Configuration for card extraction with class_name, tag_type, and children specs
    Returns:
        dict: Extracted links mapped to their key_names
    """
    results = {}

    # Initialize all child keys with null values
    for child in card_config.get('children', []):
        results[child['key_name']] = None

    # Find all cards with the specified class name
    cards = soup.find_all(card_config['tag_type'], class_=card_config['class_name'])

    if not cards:
        return results

    # For each card, look for links matching the criteria
    for card in cards:
        for child_config in card_config.get('children', []):
            # Skip if we've already found this item
            if results[child_config['key_name']] is not None:
                continue

            # Find all matching tags within this card
            links = card.find_all(child_config['tag_type'])

            # Check each link for the specified substring
            for link in links:
                href = link.get('href', '')
                if child_config['sub_word'] in href.lower():
                    # Store the full URL
                    results[child_config['key_name']] = href
                    break

    return results


def _extract_array_from_cards(soup, card_config):
    """
    Extract an array of items from multiple cards.
    Args:
        soup (BeautifulSoup): The parsed HTML
        card_config (dict): Configuration with class_name, tag_type, array_name, and children specs
    Returns:
        list: List of dictionaries, each representing a card's data
    """
    results = []

    # Find all cards with the specified class name
    cards = soup.find_all(card_config['tag_type'], class_=card_config['class_name'])

    if not cards:
        return results

    # Process each card
    for card in cards:
        card_data = {}

        # Initialize all keys with null values
        for child in card_config.get('children', []):
            card_data[child['key_name']] = None

        # Extract data for each child configuration
        for child_config in card_config.get('children', []):
            # Handle link-based extraction with sub_word
            if 'sub_word' in child_config:
                links = card.find_all(child_config['tag_type'])
                for link in links:
                    href = link.get('href', '')
                    if child_config['sub_word'] in href.lower():
                        card_data[child_config['key_name']] = href
                        break
            # Handle class-based extraction
            elif 'class_name' in child_config:
                elements = card.find_all(child_config['tag_type'], class_=child_config['class_name'])
                if elements:
                    card_data[child_config['key_name']] = elements[0].get_text(strip=True)

        # Only add cards with at least one non-null value
        if any(value is not None for value in card_data.values()):
            results.append(card_data)

    return results


def _update_company_data(conn, company_id, company_data):
    """Update company data in the database"""
    try:
        cursor = conn.cursor()

        # Convert tags from Python list to PostgreSQL array format
        tags = company_data.get('tags')
        if tags and isinstance(tags, list):
            # Format as PostgreSQL array with curly braces
            formatted_tags = "{" + ",".join(f'"{tag}"' for tag in tags) + "}"
        else:
            formatted_tags = None

        # Convert emails from Python list to PostgreSQL array format
        emails = company_data.get('emails')
        if emails and isinstance(emails, list):
            # Format as PostgreSQL array with curly braces
            formatted_emails = "{" + ",".join(f'"{email}"' for email in emails) + "}"
        else:
            formatted_emails = None

        # Update companies table
        update_query = """
        UPDATE companies
        SET
            short_description = %s,
            tags = %s,
            job_count = %s,
            domain = %s,
            description = %s,
            team_size = %s,
            primary_partner = %s,
            linkedin = %s,
            x = %s,
            twitter = %s,
            facebook = %s,
            github = %s,
            crunchbase = %s,
            emails = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """

        cursor.execute(update_query, (
            company_data.get('short_description'),
            formatted_tags,  # Use the properly formatted tags
            company_data.get('job_count'),
            company_data.get('domain'),
            company_data.get('description'),
            company_data.get('team_size'),
            company_data.get('primary_partner'),
            company_data.get('linkedIn'),
            company_data.get('x'),
            company_data.get('twitter'),
            company_data.get('facebook'),
            company_data.get('github'),
            company_data.get('crunchbase'),
            formatted_emails,  # Use the properly formatted emails
            company_id
        ))

        # Delete existing people for this company
        cursor.execute("DELETE FROM people WHERE company_id = %s", (company_id,))

        # Insert people data if available
        if company_data.get('people'):
            people_data = []
            for person in company_data.get('people', []):
                people_data.append((
                    company_id,
                    person.get('name'),
                    person.get('designation'),
                    person.get('linkedIn'),
                    person.get('x'),
                    person.get('twitter')
                ))

            if people_data:
                insert_people_query = """
                INSERT INTO people (company_id, name, designation, linkedin, x, twitter)
                VALUES %s
                """
                execute_values(cursor, insert_people_query, people_data)

        conn.commit()
        logger.info(f"Updated company data for ID: {company_id}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating company data for ID {company_id}: {e}")
        return False


def _process_retry_queue(retry_queue, extraction_list, max_retries=3):
    """Process companies that failed in the initial run with multiple retry attempts"""
    conn = None
    try:
        conn = _get_db_connection()

        total_retries = len(retry_queue)
        retry_success = 0

        logger.info(f"Starting retry processing for {total_retries} companies")

        # Process each failed company with retries
        for retry_attempt in range(1, max_retries + 1):
            if not retry_queue:
                break

            logger.info(f"Retry attempt {retry_attempt}/{max_retries} for {len(retry_queue)} companies")
            still_failing = []

            for company_id, company_link in retry_queue:
                try:
                    logger.info(f"Retry {retry_attempt} for company ID: {company_id}")

                    # Extract data with increased timeout
                    company_data = _extract_content_to_json(company_link, extraction_list, timeout=60 * retry_attempt)

                    if company_data:
                        # Update company in database
                        success = _update_company_data(conn, company_id, company_data)
                        if success:
                            retry_success += 1
                            print(
                                f"Retry success: {company_id} - Total retry successes: {retry_success}/{total_retries}")
                        else:
                            still_failing.append((company_id, company_link))
                    else:
                        logger.warning(f"Retry {retry_attempt} failed for company ID: {company_id} - No data extracted")
                        still_failing.append((company_id, company_link))

                except Exception as e:
                    logger.error(f"Retry {retry_attempt} failed for company ID {company_id}: {e}")
                    still_failing.append((company_id, company_link))
                    continue

            # Update retry queue for next attempt
            retry_queue = still_failing

            # Commit after each retry attempt
            conn.commit()

            logger.info(
                f"Retry attempt {retry_attempt} results: {retry_success} total successes, {len(still_failing)} still failing")

        # Log final retry results
        if retry_queue:
            logger.warning(f"Failed to process {len(retry_queue)} companies after {max_retries} retry attempts")
            # Save failed companies to a file for manual review
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            failed_file = f"failed_companies_{timestamp}.txt"
            with open(failed_file, "w") as f:
                for company_id, company_link in retry_queue:
                    f.write(f"{company_id},{company_link}\n")
            logger.info(f"Failed companies saved to {failed_file}")

    except Exception as e:
        logger.error(f"Error in process_retry_queue: {e}")
    finally:
        if conn:
            conn.close()


def _process_companies(batch_size=50, max_retries=3, start_from=0, limit=None, company_id=None):
    """Process all companies in the database with batch processing and progress tracking"""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Get total count of companies with links
        cursor.execute("SELECT COUNT(*) FROM companies WHERE link IS NOT NULL")
        total_companies = cursor.fetchone()[0]

        # Modify the query to support start_from and limit
        if company_id:
            query = f"SELECT id, link FROM companies WHERE link IS NOT NULL AND id = '{company_id}' ORDER BY id"
        else:
            query = "SELECT id, link FROM companies WHERE link IS NOT NULL ORDER BY id"
        if limit:
            query += f" LIMIT {limit}"
        if start_from:
            query += f" OFFSET {start_from}"

        cursor.execute(query)
        companies = cursor.fetchall()

        # If we're using start_from or limit, adjust the total for progress calculation
        if start_from or limit:
            processing_count = len(companies)
            logger.info(
                f"Processing {processing_count} companies (with offset={start_from}, limit={limit}) out of {total_companies} total")
        else:
            processing_count = total_companies
            logger.info(f"Processing all {total_companies} companies")

        # Define extraction configuration
        extraction_list = [
            {
                "class_name": "text-3xl font-bold",
                "tag_type": "h1",
                "key_name": "company_name",
            },
            {
                "xpath": '/html/body/div[1]/div[2]/section/div[2]/div[1]/div[1]/div[2]/div[2]/div',
                "key_name": "short_description"
            },
            {
                "class_name": 'yc-tw-Pill rounded-sm bg-[#E6E4DC] uppercase tracking-widest px-3 py-[3px] text-[12px] font-thin',
                "tag_type": "div",
                "key_name": "tags"
            },
            {
                "class_name": "ycdc-badge ml-0 px-1.5 font-bold no-underline",
                "tag_type": "span",
                "key_name": "job_count"
            },
            {
                "class_name": "inline-block group-hover:underline",
                "tag_type": "div",
                "key_name": "domain"
            },
            {
                "class_name": "prose max-w-full whitespace-pre-line",
                "tag_type": "div",
                "key_name": "description"
            },
            {
                "xpath": '/html/body/div[1]/div[2]/section/div[2]/div[2]/div/div[3]/div[3]/span[2]',
                "key_name": "team_size"
            },
            {
                "xpath": '/html/body/div[1]/div[2]/section/div[2]/div[2]/div/div[3]/div[5]/span[2]',
                "key_name": "location"
            },
            {
                'class_name': 'ycdc-card-new space-y-1.5 sm:w-[300px]',
                "tag_type": "div",
                'children': [
                    {
                        "tag_type": "a",
                        "sub_word": '/people/',
                        "key_name": "primary_partner"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'linkedin',
                        "key_name": "linkedIn"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'x.com',
                        "key_name": "x"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'twitter',
                        "key_name": "twitter"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'facebook',
                        "key_name": "facebook"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'github',
                        "key_name": "github"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'crunchbase',
                        "key_name": "crunchbase"
                    },
                ]
            },
            {
                'class_name': 'ycdc-card-new w-full space-y-1.5',
                "tag_type": "div",
                "array_name": 'people',
                'children': [
                    {
                        "class_name": 'text-xl font-bold',
                        "tag_type": "div",
                        "key_name": "name"
                    },
                    {
                        "class_name": 'pt-1 text-[15px] text-gray-600',
                        "tag_type": "div",
                        "key_name": "designation"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'linkedin',
                        "key_name": "linkedIn"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'x.com',
                        "key_name": "x"
                    },
                    {
                        "tag_type": "a",
                        "sub_word": 'twitter',
                        "key_name": "twitter"
                    },
                ]
            }
        ]

        # Track progress
        processed_count = 0
        success_count = 0
        failed_count = 0
        retry_queue = []

        # Process in batches
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            batch_results = {"success": 0, "failed": 0}

            logger.info(
                f"Processing batch {i // batch_size + 1}/{(processing_count + batch_size - 1) // batch_size} (companies {i + 1}-{min(i + batch_size, processing_count)})")

            # Process each company in the batch
            for company_id, company_link in batch:
                try:
                    logger.info(f"Processing company ID: {company_id}, Link: {company_link}")

                    # Extract data from company page
                    company_data = _extract_content_to_json(company_link, extraction_list)

                    if company_data:
                        # Update company in database
                        success = _update_company_data(conn, company_id, company_data)
                        if success:
                            batch_results["success"] += 1
                            success_count += 1
                        else:
                            logger.warning(f"Failed to update company ID: {company_id}")
                            retry_queue.append((company_id, company_link))
                            batch_results["failed"] += 1
                            failed_count += 1
                    else:
                        logger.warning(f"No data extracted for company ID: {company_id}")
                        retry_queue.append((company_id, company_link))
                        batch_results["failed"] += 1
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Error processing company ID {company_id}: {e}")
                    retry_queue.append((company_id, company_link))
                    batch_results["failed"] += 1
                    failed_count += 1
                    continue

                processed_count += 1

                # Print progress after each company
                progress_percentage = (processed_count / processing_count) * 100
                print(
                    f"Progress: {processed_count}/{processing_count} companies processed ({progress_percentage:.2f}%) - Success: {success_count}, Failed: {failed_count}")

            # Log batch results
            logger.info(f"Batch results: {batch_results['success']} successful, {batch_results['failed']} failed")

            # Commit after each batch
            conn.commit()

        # Process retry queue with fallback
        if retry_queue:
            logger.info(f"Attempting to process {len(retry_queue)} failed companies")
            _process_retry_queue(retry_queue, extraction_list, max_retries)

        logger.info(
            f"Final results: {success_count}/{processing_count} companies processed successfully, {failed_count} failed")

    except Exception as e:
        logger.error(f"Error in process_companies: {e}")
    finally:
        if conn:
            conn.close()


def parse_company_info(company_id=None):
    """Main function with command-line arguments"""
    parser = argparse.ArgumentParser(description='Process company data from websites and update database.')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of companies to process in each batch')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Maximum number of retry attempts for failed companies')
    parser.add_argument('--start-from', type=int, default=0, help='Start processing from this company index')
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of companies to process')

    args = parser.parse_args()

    logger.info("Starting company data update process")
    logger.info(
        f"Configuration: batch_size={args.batch_size}, max_retries={args.max_retries}, start_from={args.start_from}, limit={args.limit}")

    _process_companies(batch_size=args.batch_size, max_retries=args.max_retries, start_from=args.start_from,
                       limit=args.limit, company_id=company_id)

    logger.info("Company data update process completed")
