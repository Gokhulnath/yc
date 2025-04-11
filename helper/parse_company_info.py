import requests
import json
from bs4 import BeautifulSoup
from lxml import html

def extract_content_to_json(url, extraction_list):
    # Send HTTP request to the URL
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for bad status codes

    # Parse using BeautifulSoup for class-based extraction
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse using lxml for xpath extraction
    tree = html.fromstring(response.text)

    # Dictionary to store results
    results = {}

    # Initialize all keys with null values
    for item in extraction_list:
        results[item['key_name']] = None
        # For anchor tags, also initialize the link key
        if item.get('tag_type') == 'a' or item.get('is_anchor', False):
            results[item['key_name'] + '_link'] = None

    # Process each item in the extraction list
    for item in extraction_list:
        key_name = item['key_name']

        # Handle XPath-based extraction
        if 'xpath' in item and item['xpath']:
            xpath = item['xpath']
            elements = tree.xpath(xpath)

            if elements:  # Only update if elements are found
                # Check if the element is an anchor tag
                if elements[0].tag == 'a' or item.get('is_anchor', False):
                    # Get href attribute
                    href = elements[0].get('href')
                    if href:
                        results[key_name + '_link'] = href

                    # Get text content
                    text_content = elements[0].text_content().strip() if hasattr(elements[0], 'text_content') else None
                    results[key_name] = text_content
                    if text_content is None or text_content.strip() == '':
                        results[key_name] = None
                        results[key_name + '_link'] = None
                else:
                    # Regular element processing
                    text_content = elements[0].text_content().strip() if hasattr(elements[0], 'text_content') else None
                    results[key_name] = text_content

        # Handle class-based extraction
        elif 'class_name' in item and 'tag_type' in item:
            class_name = item['class_name']
            tag_type = item['tag_type']
            elements = soup.find_all(tag_type, class_=class_name)

            if elements:  # Only update if elements are found
                if tag_type == 'a':  # It's an anchor tag
                    if len(elements) > 1:
                        content_list = []
                        link_list = []
                        for element in elements:
                            content_list.append(element.get_text(strip=True))
                            link_list.append(element.get('href', ''))
                        results[key_name] = content_list
                        results[key_name + '_link'] = link_list
                    else:
                        text_content = elements[0].get_text(strip=True)
                        results[key_name] = text_content
                        results[key_name + '_link'] = elements[0].get('href', '')
                        if text_content is None or text_content.strip() == '':
                            results[key_name] = None
                            results[key_name + '_link'] = None
                else:  # Regular tag
                    if len(elements) > 1:
                        content_list = []
                        for element in elements:
                            content_list.append(element.get_text(strip=True))
                        results[key_name] = content_list
                    else:
                        results[key_name] = elements[0].get_text(strip=True)

    return results


def main():
    # Hardcoded URL - replace with your target URL
    url = "https://www.ycombinator.com/companies/valora"

    # List of items to extract
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
            "xpath": '/html/body/div[1]/div[2]/section/div[2]/div[2]/div/div[3]/div[6]/a',
            "key_name": "primary_partner",
            "is_anchor": True
        },
        # Add more items as needed
    ]

    # Extract content
    results = extract_content_to_json(url, extraction_list)
    print(results)

    # Save results to a JSON file
    output_file = "extracted_content.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Content has been extracted and saved to {output_file}")


if __name__ == "__main__":
    main()
