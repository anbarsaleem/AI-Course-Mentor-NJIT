import os
import requests
import hashlib
import pickle
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re

# Directory to save HTML files
save_dir = "data/scraped_data"
os.makedirs(save_dir, exist_ok=True)

# Cache directory
cache_dir = "data/cache"
os.makedirs(cache_dir, exist_ok=True)

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

# Function to load HTML content from a file
def load_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to hash content
def hash_content(content):
    return hashlib.md5(content.encode()).hexdigest()

# Function to cache results
def cache_results(file_path, results):
    with open(file_path, 'wb') as f:
        pickle.dump(results, f)

# Function to load cached results
def load_cached_results(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)

# Function to extract course information manually with improved parsing to handle full sentences for prerequisites, corequisites, and restrictions
def extract_course_info_with_cleaned_sentences(course_blocks):
    courses = []
    prereq_pattern = re.compile(r'Prerequisites?:\s*(.*?)(?:\.|$)', re.IGNORECASE)
    coreq_pattern = re.compile(r'Corequisites?:\s*(.*?)(?:\.|$)', re.IGNORECASE)
    restrict_pattern = re.compile(r'Restrictions?:\s*(.*?)(?:\.|$)', re.IGNORECASE)

    for block in course_blocks:
        soup = BeautifulSoup(str(block), 'html.parser')
        title_tag = soup.find('p', class_='courseblocktitle')
        desc_tag = soup.find('p', class_='courseblockdesc')
        if title_tag and desc_tag:
            title_text = title_tag.get_text(strip=True).replace('\xa0', ' ')
            description = desc_tag.get_text(strip=True).replace('\xa0', ' ')
            course_id = title_text.split('.')[0]
            title = '.'.join(title_text.split('.')[1:]).strip()

            # Extract prerequisites
            prereq_match = prereq_pattern.search(description)
            prerequisites = prereq_match.group(1).strip() if prereq_match else "None"

            # Extract corequisites
            coreq_match = coreq_pattern.search(description)
            corequisites = coreq_match.group(1).strip() if coreq_match else "None"

            # Extract restrictions
            restrict_match = restrict_pattern.search(description)
            restrictions = restrict_match.group(1).strip() if restrict_match else "None"

            # Remove extracted prerequisites, corequisites, and restrictions from description
            if prereq_match:
                description = description.replace(prereq_match.group(0), '')
            if coreq_match:
                description = description.replace(coreq_match.group(0), '')
            if restrict_match:
                description = description.replace(restrict_match.group(0), '')

            courses.append({
                'course_id': course_id,
                'title': title,
                'description': description.strip(),
                'prerequisites': prerequisites,
                'corequisites': corequisites,
                'restrictions': restrictions
            })
    return courses

# Function to process HTML with caching
def process_html_with_cache(html_content):
    cache_file = os.path.join(cache_dir, f"cache_{hash_content(html_content)}.pkl")
    if os.path.exists(cache_file):
        return load_cached_results(cache_file)
    else:
        soup = BeautifulSoup(html_content, 'html.parser')
        course_blocks = soup.find_all('div', class_='courseblock')
        if course_blocks:
            courses = extract_course_info_with_cleaned_sentences(course_blocks)
            cache_results(cache_file, courses)
            return courses
        else:
            return []

# Function to scrape and save HTML from a URL
def scrape_and_save_html(url, filename):
    print(f"Fetching page: {url}")
    content = get_html(url)
    save_html(content.decode('utf-8'), filename)
    print(f"Saved: {filename}")

def main():
    # Read URLs to scrape from file
    with open('data/links_to_scrape.txt', 'r') as file:
        urls = [line.strip() for line in file.readlines()]

    all_courses = []

    # Scrape main pages and their sub-links
    for url in urls:
        filename = os.path.join(save_dir, url.replace('https://', '').replace('/', '_') + '.html')
        try:
            main_html_content = get_html(url).decode('utf-8')
            save_html(main_html_content, filename)
            print(f"Saved main page: {filename}")
            soup = BeautifulSoup(main_html_content, 'html.parser')
            sub_links = soup.select('a[href]')
            base_url = url
            
            # Process and cache course information if available
            if soup.find('div', id='coursestextcontainer'):
                processed_courses = process_html_with_cache(main_html_content)
                all_courses.extend(processed_courses)
            else:
                print(f"No course content found on {url}")
            
            # Scrape sub-links
            for link in sub_links:
                sub_url = link.get('href')
                full_url = urljoin(base_url, sub_url)
                if full_url.startswith('http'):
                    sub_filename = os.path.join(save_dir, full_url.replace('https://', '').replace('/', '_') + '.html')
                    try:
                        sub_html_content = get_html(full_url).decode('utf-8')
                        save_html(sub_html_content, sub_filename)
                        print(f"Saved sub-page: {sub_filename}")
                        
                        sub_soup = BeautifulSoup(sub_html_content, 'html.parser')
                        if sub_soup.find('div', id='coursestextcontainer'):
                            processed_sub_courses = process_html_with_cache(sub_html_content)
                            all_courses.extend(processed_sub_courses)
                        
                    except Exception as e:
                        print(f"Failed to scrape sub-link {full_url}: {e}")
        
        except Exception as e:
            print(f"Failed to scrape main page {url}: {e}")

    # Save all courses to a single CSV file
    df_courses = pd.DataFrame(all_courses)
    csv_file_path = './course_data/all_courses_cleaned_sentences.csv'
    df_courses.to_csv(csv_file_path, index=False)
    print("All course data saved to", csv_file_path)

if __name__ == "__main__":
    main()