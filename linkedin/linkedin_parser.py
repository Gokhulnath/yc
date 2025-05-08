from bs4 import BeautifulSoup
import json

# Load your offline HTML file
file_path = 'yc-hiring.html'  # Replace with your actual file path

with open(file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, 'html.parser')

# Find all li elements
li_elements = soup.find_all('li')

# Create a list to store data from each li
extracted_data_list = []

for li in li_elements:
    # Extract link from a tag
    link_tag = li.find('a', class_='CSjrqhxOAEorzMiBTefPjPDZCYXKeHCeTqUI scale-down')
    link = link_tag['href'] if link_tag else None

    # Extract name from nested span tags
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

    # Extract bio text
    bio_div = li.find('div', class_='GWquMHbrFcETAFDIcQCAbUMKMyZvxtAk t-14 t-black t-normal')
    bio = bio_div.get_text(strip=True) if bio_div else None

    # Extract location text
    location_div = li.find('div', class_='snNWPeIDfOhqTorIyswvGLCxIRNebUk t-14 t-normal')
    location = location_div.get_text(strip=True) if location_div else None

    # Extract other info text
    other_info_p = li.find('p', class_='dCbLbtTtyBxoIDsINdLalRhQRRmzfivkEiujo entity-result__summary--2-lines t-12 t-black--light mb1')
    other_info = other_info_p.get_text(strip=True) if other_info_p else None

    # Add this item's data to our list
    extracted_data_list.append({
        'link': link,
        'name': name,
        'bio': bio,
        'location': location,
        'other_info': other_info
    })

# Save the data to a JSON file
json_file_path = 'extracted_list_data.json'
with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json.dump(extracted_data_list, json_file, ensure_ascii=False, indent=4)

print(f"Data successfully extracted and saved to {json_file_path}")