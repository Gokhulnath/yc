import requests
import json
import re
from bs4 import BeautifulSoup
from lxml import html
from urllib.parse import urlparse, unquote


def extract_content_to_json(url, extraction_list):
    """
    Extract content from a webpage based on a unified extraction list.

    Args:
        url (str): The URL to scrape
        extraction_list (list): List of dictionaries with extraction specifications

    Returns:
        dict: Extracted content
    """
    # Send HTTP request to the URL
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for bad status codes

    # Parse using BeautifulSoup for class-based extraction
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse using lxml for xpath extraction
    tree = html.fromstring(response.text)

    # Dictionary to store results
    results = {}

    # Default extraction for mailto links to collect email addresses
    results["emails"] = extract_emails_from_content(soup)

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
            array_items = extract_array_from_cards(soup, item)
            results[item['array_name']] = array_items
            continue

        # Special handling for single card with links
        if 'children' in item:
            card_links = extract_links_from_card(soup, item)
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


def extract_emails_from_content(soup):
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


def extract_links_from_card(soup, card_config):
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


def extract_array_from_cards(soup, card_config):
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


def extract_domain_from_url(url):
    """
    Extract domain name from a URL.

    Args:
        url (str): The URL to extract domain from

    Returns:
        str: Domain name
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        return domain
    except:
        return None


def main():
    # Hardcoded URL - replace with your target URL
    url = "https://www.ycombinator.com/companies/optifye-ai"

    # Unified extraction list with both regular items and card extraction configs
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
                    "sub_word": 'people',
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
        # Array-based extraction configuration
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
        },
    ]

    # Extract content with unified extraction list
    results = extract_content_to_json(url, extraction_list)
    print(results)

    # Save results to a JSON file
    output_file = "extracted_content.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Content has been extracted and saved to {output_file}")


if __name__ == "__main__":
    main()