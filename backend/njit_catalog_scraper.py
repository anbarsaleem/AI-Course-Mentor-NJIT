import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Directory to save HTML files
save_dir = "data/scraped_data"
os.makedirs(save_dir, exist_ok=True)

# Function to get the HTML content from a URL
def get_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to retrieve content from {url}")

# Function to save HTML content to a file
def save_html(content, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

# Function to scrape and save HTML from a URL
def scrape_and_save_html(url, filename):
    print(f"Fetching page: {url}")
    content = get_html(url)
    save_html(content.decode('utf-8'), filename)
    print(f"Saved: {filename}")

# Function to scrape all sub-links within the main content of a page
def scrape_sub_links(url, soup, base_url=None):
    links = soup.select('a[href]')
    if not links:
        print(f"No sub-links found on {url}")
        return
    
    for link in links:
        sub_url = link.get('href')
        full_url = urljoin(base_url, sub_url) if base_url else sub_url
        if full_url.startswith('http'):
            try:
                sub_html_content = get_html(full_url).decode('utf-8')
                filename = os.path.join(save_dir, full_url.replace('https://', '').replace('/', '_') + '.html')
                save_html(sub_html_content, filename)
                print(f"Saved sub-page: {filename}")
            except Exception as e:
                print(f"Failed to scrape sub-link {full_url}: {e}")

def main():
    # Read URLs to scrape from file
    with open('data/links_to_scrape.txt', 'r') as file:
        urls = [line.strip() for line in file.readlines()]

    # Scrape main pages and their sub-links
    for url in urls:
        filename = os.path.join(save_dir, url.replace('https://', '').replace('/', '_') + '.html')
        try:
            main_html_content = get_html(url).decode('utf-8')
            save_html(main_html_content, filename)
            print(f"Saved main page: {filename}")
            soup = BeautifulSoup(main_html_content, 'html.parser')
            scrape_sub_links(url, soup, base_url=url)
        except Exception as e:
            print(f"Failed to scrape main page {url}: {e}")

    # Scrape sub-links for specific pages
    scrape_sub_links("https://honors.njit.edu/currentstudents/requirements", BeautifulSoup(get_html("https://honors.njit.edu/currentstudents/requirements"), 'html.parser'), "https://honors.njit.edu")
    scrape_sub_links("https://catalog.njit.edu/undergraduate/academic-policies-procedures/", BeautifulSoup(get_html("https://catalog.njit.edu/undergraduate/academic-policies-procedures/"), 'html.parser'), "https://catalog.njit.edu")

if __name__ == "__main__":
    main()
