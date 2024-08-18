import pandas as pd
import re
import os
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

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

prefix = 'course_data/'

# URL of the PHP file
url = 'https://myhub.njit.edu/scbldr/include/datasvc.php?p=/'

def upload_to_digital_ocean_space(file_content, object_name, content_type):
    try:
        client.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=prefix + object_name,
            Body=file_content,
            ContentType=content_type
        )
        print(f"Successfully uploaded {object_name} to {DO_SPACES_BUCKET}/{prefix}")
    except NoCredentialsError:
        print("Credentials not available")

# Define a function to fetch and parse the PHP file content into structured data
def fetch_and_parse_php_file(url):
    response = requests.get(url)
    content = response.text
    
    # Remove PHP tags and clean up the content
    content = content.replace('<?php', '').replace('?>', '').strip()
    
    # Extract the data section using regular expressions
    data_match = re.search(r'data:\s*(\[\[.*\]\]),', content, re.DOTALL)
    term_match = re.search(r'term:\s*"(.*)"', content)
    update_match = re.search(r'update:\s*"(.*)"', content)
    
    if data_match and term_match and update_match:
        data_str = data_match.group(1)
        data_str = data_str.replace('null', 'None')
        data = eval(data_str)
        term = term_match.group(1)
        update = update_match.group(1)
        return data, term, update
    else:
        raise ValueError("The PHP file format is incorrect or has changed.")

# Function to convert seconds into HH:MM format
def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02}:{minutes:02}"

# Function to convert day integer to day string
def convert_day_to_string(day):
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    return days[day-1]

# Define function to convert parsed data to DataFrame
def convert_to_dataframe(parsed_data, term, update):
    columns = [
        'Course Code', 'Course Name', 'Credits', 'Section Code', 'Section Number', 'CRN',
        'Enrollment', 'Professor', 'Notes', 'Schedule'
    ]
    df_data = []
    for course in parsed_data:
        course_code = course[0]
        course_name = course[1]
        credits = course[2]
        sections = course[3:]
        for section in sections:
            section_code = section[0]
            section_number = section[1]
            crn = section[2]
            enrollment = section[3]
            professor = section[4]
            notes = section[7]
            schedule_list = section[9]
            schedule = []
            for sched in schedule_list:
                day_str = convert_day_to_string(sched[0])
                start_time = convert_seconds_to_time(sched[1])
                end_time = convert_seconds_to_time(sched[2])
                location = sched[3]
                schedule.append(f"{day_str} {start_time}-{end_time} at {location}")
            
            df_data.append([
                course_code, course_name, credits, section_code, section_number, crn,
                enrollment, professor, notes, "; ".join(schedule)
            ])
    
    df = pd.DataFrame(df_data, columns=columns)
    object_name = f'courses_{term}.json' 
    upload_to_digital_ocean_space(df.to_json(), object_name, 'application/json')

# Main function to fetch, parse, and save the course data
def fetch_and_parse_php():
    # Fetch and parse the file content
    parsed_data, term, update = fetch_and_parse_php_file(url)
    
    # Convert parsed data to DataFrame and upload to Digital Ocean Spaces
    convert_to_dataframe(parsed_data, term, update)

# To ensure compatibility with the backend runner
if __name__ == "__main__":
    df_courses, term, update = fetch_and_parse_php()
    print(f"Term: {term}")
    print(f"Update: {update}")
    print(df_courses.head())
