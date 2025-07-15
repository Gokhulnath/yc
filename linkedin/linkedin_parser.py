import os

from bs4 import BeautifulSoup
import json
import psycopg2  # Add this for PostgreSQL connection
from dotenv import load_dotenv


# Database connection setup
def get_db_connection():
    load_dotenv()

    # Connect to database using environment variables
    connection = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        user=os.environ.get('DB_USER', 'myuser'),
        password=os.environ.get('DB_PASSWORD', 'mypassword'),
        dbname=os.environ.get('DB_NAME', 'mydb')
    )
    return connection


# Load your offline HTML file
file_path = 'yc-hiring.html'
with open(file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, 'html.parser')

# Connect to database
conn = get_db_connection()
cursor = conn.cursor()

# Find all li elements
li_elements = soup.find_all('li')
extracted_data_list = []

for li in li_elements:
    # Extract data as in your original code
    link_tag = li.find('a', class_='CSjrqhxOAEorzMiBTefPjPDZCYXKeHCeTqUI scale-down')
    link = link_tag['href'].split('?')[0] if link_tag else None

    # Extract name
    name = None
    span_tag = li.find('span', class_='zyAcEsTDwsHSNbxtpUmIadsaRxkAcRNVOujw t-16')
    if span_tag:
        a_tag = span_tag.find('a')
        if a_tag:
            inner_span = a_tag.find('span')
            if inner_span:
                inner_inner_span = inner_span.find('span')
                if inner_inner_span:
                    name = inner_inner_span.get_text(strip=True)

    # Other extractions (bio, location, other_info)
    bio_div = li.find('div', class_='GWquMHbrFcETAFDIcQCAbUMKMyZvxtAk t-14 t-black t-normal')
    bio = bio_div.get_text(strip=True) if bio_div else None

    location_div = li.find('div', class_='snNWPeIDfOhqTorIyswvGLCxIRNebUk t-14 t-normal')
    location = location_div.get_text(strip=True) if location_div else None

    other_info_p = li.find('p',
                           class_='dCbLbtTtyBxoIDsINdLalRhQRRmzfivkEiujo entity-result__summary--2-lines t-12 t-black--light mb1')
    if not other_info_p:
        other_info_p = li.find('p',
                               class_='dCbLbtTtyBxoIDsINdLalRhQRRmzfivkEiujo entity-result__summary--2-lines t-12 t-black--light')
    other_info = other_info_p.get_text(strip=True) if other_info_p else None

    # Check people database for email and company details
    person_data = None
    company_data = None

    if name:
        # Query for person by name
        cursor.execute("SELECT p.*, c.* FROM people p JOIN companies c ON p.company_id = c.id WHERE p.name = %s",
                       (name,))
        result = cursor.fetchone()

        if result:
            # Extract person and company data from result
            # Adjust column indices based on your actual query results
            person_data = {
                "id": result[0],
                "email": result[7] or None,
                "linkedin": result[5] or None
            }

            company_data = {
                "id": result[9],  # Assuming company data starts at index 9
                "company_name": result[11],
                "description": result[15],
                "domain": result[14]
            }

    # Add this item's data to our list
    extracted_data_list.append({
        'link': link,
        'name': name,
        'bio': bio,
        'location': location,
        'other_info': other_info,
        'person_details': person_data,
        'company_details': company_data
    })

# Close database connection
cursor.close()
conn.close()

# Save the data to a JSON file
json_file_path = 'extracted_list_data.json'
with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json.dump(extracted_data_list, json_file, default=str, ensure_ascii=False, indent=4)

print(f"Data successfully extracted and saved to {json_file_path}")
