import selenium
from selenium.webdriver.common.by import By
from selenium import webdriver
import time

def _initialize_driver():
    """Initializes the WebDriver for Chrome."""
    driver = webdriver.Chrome()
    return driver

def _scroll_to_end(driver, url):
    """Scrolls the page to the end to load all content."""
    driver.get(url)
    scroll_pause_time = 2  # Adjust the time for scrolling if necessary
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break

        last_height = new_height


def _fetch_a_tags(driver, class_name):
    """Fetches all <a> tags with the specified class name."""
    links = driver.find_elements(By.CSS_SELECTOR, f"a.{class_name}")
    return links


def _extract_company_info(link):
    """Extracts relevant company information from an <a> tag."""
    try:
        img_src = link.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
    except selenium.common.exceptions.NoSuchElementException:
        img_src = 'https://bookface-images.s3.amazonaws.com/small_logos/2db694dd7905db37d037821a2fdaf9fa0708a964.png'
    company_name = link.find_element(By.CSS_SELECTOR, "span._coName_i9oky_470").text
    location = link.find_element(By.CSS_SELECTOR, "span._coLocation_i9oky_486").text or None
    short_description = link.find_element(By.CSS_SELECTOR, "span._coDescription_i9oky_495").text

    # Extract batch link, industry, and industry type from the div _pillWrapper_i9oky_33
    pill_wrapper = link.find_element(By.CSS_SELECTOR, "div._pillWrapper_i9oky_33")
    a_tags = pill_wrapper.find_elements(By.TAG_NAME, 'a')

    industry = []

    for a_tag in a_tags:
        if '?industry=' in a_tag.get_attribute('href'):
            industry_details = {
                'type' : a_tag.find_element(By.TAG_NAME, "span").text,
                'link' : a_tag.get_attribute('href'),
            }
            industry.append(industry_details)

    company_info = {
        "logo": img_src,
        "company_name": company_name,
        "link": link.get_attribute('href'),
        "location": location,
        "short_description": short_description,
        "industry": industry,
    }

    return company_info

def initiate_extraction(url):
    class_name = '_company_i9oky_355'  # The class name for <a> tags

    # Initialize the WebDriver
    driver = _initialize_driver()

    try:
        # Scroll to the end of the page
        _scroll_to_end(driver, url)

        # Fetch all <a> tags with the specified class name
        links = _fetch_a_tags(driver, class_name)

        company_data = []

        # Extract company information from each link
        for link in links:
            company_info = _extract_company_info(link)
            company_data.append(company_info)

        # Output the data as a JSON string
        return company_data

    finally:
        # Close the WebDriver
        driver.quit()