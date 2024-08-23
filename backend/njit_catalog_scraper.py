import logging
import cProfile
import pstats
import os
import requests
import hashlib
import pickle
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re
import boto3
from botocore.exceptions import NoCredentialsError
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables    
load_dotenv(dotenv_path='../.env')

# Get Digital Ocean credentials from environment variables
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'nyc3')
DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')

# Configure the boto3 client
session = boto3.session.Session()
client = session.client('s3',
                        region_name=DO_SPACES_REGION,
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=DO_SPACES_KEY,
                        aws_secret_access_key=DO_SPACES_SECRET)

prefix = 'course_data/'

# Directory to save HTML files
save_dir = "downloaded_html_files"
os.makedirs(save_dir, exist_ok=True)

all_courses = [] # List to store all courses
lock = Lock() # Lock to ensure thread safety when writing to the shared all_courses list

# Set up logging configuration
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('multithreaded_njit_catalog_scraper.log', 'w', 'utf-8')])

logger = logging.getLogger(__name__)

# Function to profile
def profile(func):
    def wrapper(*args, **kwargs):
        profile = cProfile.Profile()
        profile.enable()
        result = func(*args, **kwargs)
        profile.disable()
        stats = pstats.Stats(profile).sort_stats('cumulative')
        stats.print_stats()
        return result
    return wrapper

# Function to upload HTML content to Digital Ocean Spaces
def upload_html_to_spaces(content, object_name):
    try:
        client.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=prefix + object_name,
            Body=content,
            ContentType='text/html'
        )
        logger.info(f"Successfully uploaded {object_name} to {DO_SPACES_BUCKET}/{prefix}")
    except NoCredentialsError:
        logger.info("Credentials not available", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to upload {object_name} to {DO_SPACES_BUCKET}/{prefix}", exc_info=True)

# Cache directory
cache_dir = "cache"
os.makedirs(cache_dir, exist_ok=True)

# Function to get the HTML content from a URL
def get_html(url):
    logger.debug(f"Fetching content from {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Successfully fetched content from {url}")
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch content from {url}", exc_info=True)
        raise

# Function to load HTML content from a file
def load_html_file(file_path):
    logger.debug(f"Loading content from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        logger.info(f"Successfully loaded content from {file_path}")
        return content
    except Exception as e:
        logger.error(f"Failed to load content from {file_path}", exc_info=True)
        raise

# Function to hash content
def hash_content(content):
    logger.debug("Hashing content")
    return hashlib.md5(content.encode()).hexdigest()

# Function to cache results
def cache_results(file_path, results):
    logger.debug(f"Caching results to {file_path}")
    try:
        with open(file_path, 'wb') as f:
            pickle.dump(results, f)
        logger.info(f"Successfully cached results to {file_path}")
    except Exception as e:
        logger.error(f"Failed to cache results to {file_path}", exc_info=True)

# Function to load cached results
def load_cached_results(file_path):
    logger.debug(f"Loading cached results from {file_path}")
    try:        
        with open(file_path, 'rb') as f:
            return pickle.load(f)
        logger.info(f"Successfully loaded cached results from {file_path}")
        return results
    except Exception as e:
        logger.error(f"Failed to load cached results from {file_path}", exc_info=True)
        raise

# Function to extract course information manually with improved parsing to handle full sentences for prerequisites, corequisites, and restrictions
def extract_course_info_with_cleaned_sentences(course_blocks):
    logger.debug("Extracting course information with cleaned sentences")
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
    logger.info("Successfully extracted course information with cleaned sentences")
    return courses

# Function to process HTML with caching
def process_html_with_cache(html_content):
    logger.debug("Processing HTML with caching")
    cache_file = os.path.join(cache_dir, f"cache_{hash_content(html_content)}.pkl")
    if os.path.exists(cache_file):
        logger.info(f"Loading cached results from {cache_file}")
        return load_cached_results(cache_file)
    else:
        soup = BeautifulSoup(html_content, 'html.parser')
        course_blocks = soup.find_all('div', class_='courseblock')
        if course_blocks:
            logger.info(f"Extracting course information from {len(course_blocks)} course blocks")
            courses = extract_course_info_with_cleaned_sentences(course_blocks)
            cache_results(cache_file, courses)
            return courses
        else:
            logger.error("No course blocks found in HTML content")
            return []

# Function to scrape and save HTML from a URL to Digital Ocean Spaces
def scrape_and_save_html(url, filename):
    logger.debug(f"Scraping and saving HTML from {url} to {filename} on Digital Ocean Spaces")    
    try:
        content = get_html(url) 
        upload_html_to_spaces(content, filename)
        logger.info(f"Successfully scraped and saved HTML from {url} to {filename} on Digital Ocean Spaces")
    except Exception as e:
        logger.error(f"Failed to scrape and save HTML from {url} to {filename} on Digital Ocean Spaces", exc_info=True)

def scrape_link(url):
    filename = os.path.join(save_dir, url.replace('https://', '').replace('/', '_') + '.html')
    try:
        logger.debug(f"Scraping main page: {url}")
        main_html_content = get_html(url).decode('utf-8')
        upload_html_to_spaces(main_html_content, filename)
        logger.info(f"Saved main page: {filename}")
        
        soup = BeautifulSoup(main_html_content, 'html.parser')
        sub_links = soup.select('a[href]')
        base_url = url
        
        # Process and cache course information if available
        if soup.find('div', id='coursestextcontainer'):
            processed_courses = process_html_with_cache(main_html_content)
            with lock: # Ensure only one thread is writing to the shared all_courses list at a time
                all_courses.extend(processed_courses)
        else:
            logger.warning(f"No course content found on {url}")
        
        # Scrape sub-links
        for link in sub_links:
            sub_url = link.get('href')
            full_url = urljoin(base_url, sub_url)
            if full_url.startswith('http'):
                sub_filename = os.path.join(save_dir, full_url.replace('https://', '').replace('/', '_') + '.html')
                try:
                    logger.debug(f"Scraping sub-page: {full_url}")
                    sub_html_content = get_html(full_url).decode('utf-8')
                    upload_html_to_spaces(sub_html_content, sub_filename)
                    logger.info(f"Saved sub-page: {sub_filename}")
                    
                    sub_soup = BeautifulSoup(sub_html_content, 'html.parser')
                    if sub_soup.find('div', id='coursestextcontainer'):
                        processed_sub_courses = process_html_with_cache(sub_html_content)
                        with lock:
                            all_courses.extend(processed_sub_courses)

                except Exception as e:
                    logger.error(f"Failed to scrape sub-link {full_url}: {e}")
    
    except Exception as e:
        logger.error(f"Failed to scrape main page {url}: {e}")

# Main function to scrape courses
def njit_catalog_scraper():
    logger.info("Starting course scraping process")
    try:
        # Read URLs to scrape from file
        with open('links_to_scrape.txt', 'r') as file:
            urls = [line.strip() for line in file.readlines()]
        logger.info(f"Read {len(urls)} URLs to scrape")

        # Scrape main pages and their sub-links with multithreading
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(scrape_link, url) for url in urls]
            for future in as_completed(futures):
                future.result()      
        
        # Save all courses to a single JSON file
        logger.debug("Saving all courses to JSON file")
        df_courses = pd.DataFrame(all_courses)
        upload_html_to_spaces(df_courses.to_json(), "all_courses.json")
        logger.info("Successfully saved all courses to DigitalOcean Space")
    except Exception as e:
        logger.error("An error occurred during the course scraping process", exc_info=True)

# To ensure compatibility with the backend runner
if __name__ == "__main__":
    njit_catalog_scraper()
