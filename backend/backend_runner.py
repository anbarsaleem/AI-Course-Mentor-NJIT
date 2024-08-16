# backend_runner.py

from fetch_and_parse_php_to_dataframe import fetch_and_parse_php
from njit_catalog_scraper import scrape_courses
import os
import boto3
from botocore.exceptions import NoCredentialsError
import dotenv

dotenv.load_dotenv()

# Get Digital Ocean credentials from environment variables
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'nyc3')
DO_SPACES_ENDPOINT = os.getenv('DO_SPACES_ENDPOINT', 'https://nyc3.digitaloceanspaces.com')
DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')

# Configure the boto3 client
session = boto3.session.Session()
client = session.client('s3',
                        region_name=DO_SPACES_REGION,
                        endpoint_url=DO_SPACES_ENDPOINT,
                        aws_access_key_id=DO_SPACES_KEY,
                        aws_secret_access_key=DO_SPACES_SECRET)

def run_all_backends():
    # Fetch and upload NJIT PHP data to Digital Ocean Spaces:33,36d
    fetch_and_parse_php()

    # Scrape and upload NJIT Course Data to Digital Ocean Spaces
    scrape_courses()

if __name__ == "__main__":
    run_all_backends()
