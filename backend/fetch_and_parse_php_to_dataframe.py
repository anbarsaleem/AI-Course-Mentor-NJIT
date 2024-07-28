
import pandas as pd
import re
import requests

# URL of the PHP file
url = 'https://myhub.njit.edu/scbldr/include/datasvc.php?p=/'

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

# Fetch and parse the file content
parsed_data, term, update = fetch_and_parse_php_file(url)

# Define columns for the DataFrame
columns = [
    'Course Code', 'Course Name', 'Credits', 'Section Code', 'Section Number', 'CRN',
    'Enrollment', 'Professor', 'Notes', 'Schedule'
]

# Define function to convert parsed data to DataFrame
def convert_to_dataframe(parsed_data):
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
    return df

# Convert parsed data to DataFrame
df_courses = convert_to_dataframe(parsed_data)

# Display metadata and DataFrame
print(f"Term: {term}")
print(f"Update: {update}")
print(df_courses.head())

# Save the DataFrame to a CSV file
df_courses.to_csv('courses.csv', index=False)
# Save the DataFrame to a JSON file
df_courses.to_json('courses.json', orient='records', lines=True)