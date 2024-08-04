
import pdfplumber
import json
import re

def extract_full_transcript_info(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    
    transcript_data = {}

    # Extracting student information
    student_info_pattern = re.compile(r'Name\s*(.*)\n\s*Birth Date\s*(.*)\n.*Program\s*(.*)\n.*College\s*(.*)\n.*Major and Department\s*(.*)\n')
    match = student_info_pattern.search(text)
    if match:
        transcript_data['student_info'] = {
            'name': match.group(1).strip(),
            'birth_date': match.group(2).strip(),
            'program': match.group(3).strip(),
            'college': match.group(4).strip(),
            'major_and_department': match.group(5).strip()
        }

    # Extracting degree information
    degree_info_pattern = re.compile(r'DEGREE AWARDED\s*\n.*\nProgram\s*(.*?)\n.*\n.*\n.*\nMajor\s*(.*?)\n')
    match = degree_info_pattern.search(text)
    if match:
        transcript_data['degree_info'] = {
            'program': match.group(1).strip(),
            'major': match.group(2).strip()
        }

    # Extracting transfer credit information
    transfer_credit_pattern = re.compile(r'TRANSFER CREDIT ACCEPTED BY INSTITUTION\n(.*?)\n\nAttempt Hours Passed Hours Earned Hours GPA Hours Quality Points GPA', re.DOTALL)
    match = transfer_credit_pattern.search(text)
    if match:
        transfer_credits = []
        transfer_entries = re.findall(r'([A-Z]+\s\d+)\s+(.*?)\s+([A-Z])\s+([\d.]+)\s+([\d.]+)', match.group(1))
        for entry in transfer_entries:
            credit = {
                'course_code': entry[0].strip(),
                'course_title': entry[1].strip(),
                'grade': entry[2].strip(),
                'credit_hours': float(entry[3].strip()),
                'quality_points': float(entry[4].strip())
            }
            transfer_credits.append(credit)
        transcript_data['transfer_credits'] = transfer_credits

    # Extracting course information
    courses_pattern = re.compile(r'Term\s*:\s*(.*?)\n.*?\n(.*?)\nTerm Totals.*?\n.*?\n', re.DOTALL)
    transcript_data['courses'] = []
    for term, course_text in courses_pattern.findall(text):
        course_entries = re.findall(r'([A-Z]+ \d+)\s+U\s+(.*?)\s+([A-F][+-]?)\s+([\d.]+)\s+([\d.]+)', course_text)
        for entry in course_entries:
            course = {
                'term': term.strip(),
                'course_code': entry[0].strip(),
                'course_title': entry[1].strip(),
                'grade': entry[2].strip(),
                'credit_hours': float(entry[3].strip()),
                'quality_points': float(entry[4].strip())
            }
            transcript_data['courses'].append(course)

    # Extracting cumulative GPA information
    gpa_pattern = re.compile(r'Transcript Totals\s*-\s*\(Undergraduate\)\s*Attempt Hours Passed Hours Earned Hours GPA Hours Quality Points GPA\s*Total Institution\s*(.*?)\s*Total Transfer\s*(.*?)\s*Overall\s*(.*?)\s*\n', re.DOTALL)
    match = gpa_pattern.search(text)
    if match:
        total_institution = match.group(1).split()
        total_transfer = match.group(2).split()
        overall = match.group(3).split()
        
        transcript_data['gpa_totals'] = {
            'total_institution': {
                'attempt_hours': float(total_institution[0]),
                'passed_hours': float(total_institution[1]),
                'earned_hours': float(total_institution[2]),
                'gpa_hours': float(total_institution[3]),
                'quality_points': float(total_institution[4]),
                'gpa': float(total_institution[5])
            },
            'total_transfer': {
                'attempt_hours': float(total_transfer[0]),
                'passed_hours': float(total_transfer[1]),
                'earned_hours': float(total_transfer[2]),
                'gpa_hours': float(total_transfer[3]),
                'quality_points': float(total_transfer[4]),
                'gpa': float(total_transfer[5])
            },
            'overall': {
                'attempt_hours': float(overall[0]),
                'passed_hours': float(overall[1]),
                'earned_hours': float(overall[2]),
                'gpa_hours': float(overall[3]),
                'quality_points': float(overall[4]),
                'gpa': float(overall[5])
            }
        }

    # Extracting courses in progress
    in_progress_pattern = re.compile(r'COURSE\(S\) IN PROGRESS\s*Term\s*:\s*(.*?)\s*College\s*(.*?)\s*Major\s*(.*?)\s*Subject Course Level Title Credit Hours\s*(.*?)\s*\n', re.DOTALL)
    match = in_progress_pattern.search(text)
    if match:
        courses_in_progress = []
        course_entries = re.findall(r'([A-Z]+ \d+)\s+U\s+(.*?)\s+([\d.]+)', match.group(4))
        for entry in course_entries:
            course = {
                'term': match.group(1).strip(),
                'course_code': entry[0].strip(),
                'course_title': entry[1].strip(),
                'credit_hours': float(entry[2].strip())
            }
            courses_in_progress.append(course)
        transcript_data['courses_in_progress'] = courses_in_progress

    return transcript_data

def save_as_json(data, output_path):
    with open(output_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Paths to the PDF transcripts
pdf_paths = []
output_files = []

for pdf_path, output_file in zip(pdf_paths, output_files):
    transcript_data = extract_full_transcript_info(pdf_path)
    save_as_json(transcript_data, output_file)
    print(f"Saved {output_file}")
