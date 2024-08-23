from fetch_and_parse_php_to_dataframe import fetch_and_parse_php
from njit_catalog_scraper import njit_catalog_scraper
from assistant_resource_allocate import assistant_resource_allocate

def run_all_backends():
    # Fetch and upload NJIT PHP data to Digital Ocean Spaces
    fetch_and_parse_php()

    # Scrape and upload NJIT Course Data to Digital Ocean Spaces
    njit_catalog_scraper()

    # Allocate resources to the Assistant
    assistant_resource_allocate()

if __name__ == "__main__":
    run_all_backends()
