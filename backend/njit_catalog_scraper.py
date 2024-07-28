import os
import requests
from bs4 import BeautifulSoup

# URLs to scrape
urls = [
    "https://catalog.njit.edu/undergraduate/",
    "https://catalog.njit.edu/graduate/",
    "https://catalog.njit.edu/programs/"
]

# Directory to save HTML files
save_dir = "downloaded_html_files"
os.makedirs(save_dir, exist_ok=True)

# Extensions to filter
extensions = [
    "/architecture-design/",
    "/computing-sciences/",
    "/science-liberal-arts/",
    "/newark-college-engineering/",
    "/management/"
]

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

# Function to check if a link should be processed
def should_process_link(href):
    for ext in extensions:
        if href.endswith(ext):
            return True
    return False

# Function to scrape and save all sub-links HTML for undergraduate and graduate pages
def scrape_and_save_html(url, filter_links=False):
    print(f"Fetching main page: {url}")
    main_html_content = get_html(url)
    main_soup = BeautifulSoup(main_html_content, 'html.parser')
    
    nav_links = main_soup.select("ul.nav a")
    if not nav_links:
        print(f"No nav links found on {url}")
        return

    for link in nav_links:
        sub_url = link.get('href')
        if not sub_url.startswith('http'):
            sub_url = 'https://catalog.njit.edu' + sub_url
        
        if filter_links and not should_process_link(sub_url):
            continue
        
        print(f"Fetching sub-page: {sub_url}")

        sub_html_content = get_html(sub_url).decode('utf-8')
        filename = os.path.join(save_dir, sub_url.replace('https://', '').replace('/', '_') + '.html')
        save_html(sub_html_content, filename)
        print(f"Saved: {filename}")

# Function to scrape and save HTML for all hrefs within the table on the programs page
def scrape_and_save_programs_table_html(url):
    print(f"Fetching programs page: {url}")
    main_html_content = get_html(url)
    main_soup = BeautifulSoup(main_html_content, 'html.parser')
    
    table_links = main_soup.select("table a")
    if not table_links:
        print(f"No table links found on {url}")
        return

    for link in table_links:
        sub_url = link.get('href')
        if not sub_url.startswith('http'):
            sub_url = 'https://catalog.njit.edu' + sub_url
        
        print(f"Fetching table sub-page: {sub_url}")

        sub_html_content = get_html(sub_url).decode('utf-8')
        filename = os.path.join(save_dir, sub_url.replace('https://', '').replace('/', '_') + '.html')
        save_html(sub_html_content, filename)
        print(f"Saved: {filename}")

# Scrape and save HTML for undergraduate and graduate catalogs
for url in urls[:2]:  # First two URLs are for undergraduate and graduate
    scrape_and_save_html(url, filter_links=True)

# Scrape and save HTML for programs table
scrape_and_save_programs_table_html(urls[2])  # Last URL is for programs page

print("HTML files downloaded and saved.")
