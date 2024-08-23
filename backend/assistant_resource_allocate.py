from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from openai import OpenAI
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import os
import logging
import json

# Load environment variables
load_dotenv(dotenv_path='../.env', override=True)
client = OpenAI()

file_contents = [] # List of file contents retrieved from Digital Ocean Spaces
file_ids = [] # List of file ids to be uploaded to Vector Store
lock = Lock()

# Set up logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('assistant_resource_allocate.log', 'w', 'utf-8')])

logger = logging.getLogger(__name__)

def load_config(config_file="config.json"):
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
            return config
    else:   
        return None
    
def save_config(config, config_file="config.json"):
    with open(config_file, "w") as f:
        json.dump(config, f)

# Get Digital Ocean credentials from environment variables
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'nyc3')
DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')

# Configure the boto3 client
session = boto3.session.Session()
s3_client = session.client('s3',
                        region_name=DO_SPACES_REGION,
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=DO_SPACES_KEY,
                        aws_secret_access_key=DO_SPACES_SECRET)

prefix = 'course_data/'
id_prefix = 'ids/'

# Function to upload id file content to Digital Ocean Spaces
def upload_file_to_spaces(content, object_name):
    try:
        response = s3_client.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=id_prefix + object_name,
            Body=content,
            ContentType='application/json'
        )
        logger.info(response)
        logger.info(f"Successfully uploaded {object_name} to {DO_SPACES_BUCKET}/{id_prefix}")
    except NoCredentialsError:
        logger.info("Credentials not available", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to upload {object_name} to {DO_SPACES_BUCKET}/{id_prefix}", exc_info=True)

def retrieve_file_from_spaces(file):
    file_key = file['Key']
    file_obj = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=file_key)
    file_content = file_obj['Body'].read()
    with lock:
        file_contents.append((file_key, file_content))
    logger.info(f"File {file} retrieved successfully")

def retrieve_files_from_spaces():
    """
    Retrieve files from Digital Ocean Spaces.
    """
    try:
        logger.info("Retrieving files from Digital Ocean Spaces")
        response = s3_client.list_objects(Bucket=DO_SPACES_BUCKET)
        files = response.get('Contents', [])
        logger.info(f"Files retrieved: {files}")
 
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(retrieve_file_from_spaces, file) for file in files]
            for future in as_completed(futures):
                future.result()
            
        return file_contents

    except NoCredentialsError:
        logger.error("Credentials not available")
        return []

def delete_file_from_vector_store(vector_store_id, file_id):
    try:
        client.beta.vector_stores.files.delete(
            vector_store_id = vector_store_id,
            file_id = file_id
        )
        logger.info(f"Deleted {file_id} from Vector Store")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

def create_vector_store_file(vector_store_id, file_content):
    try:
        file = client.files.create(file=file_content, purpose="assistants")
        with lock:
            file_ids.append(file.id)
        logger.info(f"Created file in Vector Store: {file.id}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


def refresh_vector_store(vector_store_id):
    """
    Refresh the vector store with the latest course data.
    """
    logger.info("Refreshing Vector Store")
    try:
        # Delete Files from Vector Store
        files_to_delete = client.beta.vector_stores.files.list(
            vector_store_id = vector_store_id
        )
        file_ids = [file.id for file in files_to_delete]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(delete_file_from_vector_store, vector_store_id, file_id) for file_id in file_ids]
            for future in as_completed(futures):
                future.result()
        logger.info("Deleted files from Vector Store")

        # Retrieve Files from Digital Ocean Spaces
        files = retrieve_files_from_spaces()

        # Upload Files to Vector Store as File Batch
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_vector_store_file, vector_store_id, file_content) for file_content in files]
            for future in as_completed(futures):
                future.result()
        logger.info("Uploaded files to Vector Store")
        
        client.beta.vector_stores.file_batches.create(
            vector_store_id = vector_store_id,
            file_ids = file_ids
        )
        logger.info(f"Uploaded files to Vector Store, {file_ids}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")

def check_vector_store_exists(vector_store_id):
    if not vector_store_id:
        return False
    try:
        logger.info(f"Checking Vector Store: {vector_store_id}")
        response = client.beta.vector_stores.retrieve(vector_store_id)
        exists = True if response else False
        return exists
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

def check_assistant_exists(assistant_id):
    if not assistant_id:
        return False
    try:
        logger.info(f"Checking Assistant: {assistant_id}")
        response = client.beta.assistants.retrieve(assistant_id)
        exists = True if response else False
        return exists
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

def create_resources_if_needed(config):
    assistant_id = config.get("assistant_id")
    vector_store_id = config.get("vector_store_id")

    if not check_assistant_exists(assistant_id):
        course_mentor_assistant = client.beta.assistants.create(
            model="gpt-4o-mini",
            name="NJIT Course Mentor",
            description="Assistant to help NJIT students plan their courses.",
            instructions="""
                            You are an AI assistant specialized in NJIT course planning. Your task is to provide course recommendations based on a student's major, grad/undergrad status, department, and college, as detailed in their uploaded transcript file. The transcript contains all relevant personal information and is already available to you.

                            # Key Guidelines:

                            ## Course Level Identification:

                            ### Graduate Courses: Recognize courses with codes in the range of 500-799 as graduate-level courses.
                            ### Undergraduate Courses: Recognize courses with codes in the range of 100-499 as undergraduate-level courses.

                            ## Initial Confirmation:

                            At the start of the conversation, extract the student's major, college, and program details from the transcript.
                            Accurately insert the extracted information into your response. For example:
                            Correct Response: "According to your transcript, you are a Computer Science major in the College of Computing Sciences program. Please confirm this information by responding with 'Yes' or 'No'."
                            If, for any reason, the AI is unable to retrieve this information, explicitly state that the data could not be found and ask for clarification, rather than presenting vague placeholders.

                            ## Course Level Prioritization:

                            Strictly prioritize suggesting courses that match the student's academic level as indicated on their transcript:
                            For undergraduate students, recommend only courses with codes in the 100-499 range.
                            For graduate students, recommend only courses with codes in the 500-799 range.
                            Only suggest courses outside the student's indicated level (e.g., undergraduate courses for a graduate student or vice versa) if the student explicitly requests to consider courses at a different level.
                            If the student indicates a desire to take courses outside their academic level, mention any prerequisites or special permissions that may be required.

                            ## Data Integrity:

                            Extract all required information directly from the transcript.
                            Never infer or guess any details; rely solely on the provided data.
                            If the necessary information is not found in the provided documents, clearly state that fact and ask for the specific information needed.
                            Cross-reference course availability with the courses.json file for the upcoming semester.
                            Ensure your recommendations are strictly accurate, avoiding courses not listed in the courses.json file.

                            ## Course Recommendations:

                            Avoid recommending courses the student has already completed and passed.
                            Prioritize courses that fulfill major, college, or program requirements.
                            Mention prerequisites and corequisites when suggesting courses.
                            For Honors students:
                            Identify how many honors courses they have left based on the honors.njit.edu HTML files.
                            Recommend appropriate honors and non-honors sections of courses for the upcoming term.
                            Follow the rules on A, B, C, and D honors courses as outlined in the honors-course-requirements HTML file.
                            If honors courses are not offered in the upcoming semester, recommend courses based on the student's honors group and indicate that these are not currently offered.
                            Note that if a student has taken an honors course with a corresponding lab course, only one counts toward their honors requirements.

                            ## Accuracy in Communication:

                            Begin the conversation by verifying the student's major, college, and program data based on the transcript. Ask them to confirm this information.
                            Do not suggest courses not found in the courses.json file, and if a course is missing, mention that it's not currently offered in the upcoming semester.
                            Provide comprehensive lists of relevant courses when asked, ensuring nothing is omitted.
                            Avoid referencing courses based on the course catalog HTML files when discussing upcoming semester offerings.

                            ## Student Interaction:

                            Be polite, supportive, and realistic about course requirements.
                            Seek clarification only when the necessary information is genuinely not available in the provided documents.
                            If a course aligns with student preferences but is less useful for graduation, highlight this in your response.

                            ## Response Accuracy:

                            Internally generate three possible answers, evaluate each against the provided data, and respond with the most accurate and complete response.
                            If the answer cannot be found in the provided data, respond with "The answer could not be found in the provided context.
                            """,
            tools = [{"type": "file_search"}],
        )
        assistant_id = course_mentor_assistant.id
        logger.info(f"Created Assistant: {assistant_id}")

    if not check_vector_store_exists(vector_store_id):
        vector_store = client.beta.vector_stores.create(name="NJIT Course Data")
        vector_store_id = vector_store.id
        config["vector_store_id"] = vector_store_id
        refresh_vector_store(vector_store_id)
    
    course_mentor_assistant = client.beta.assistants.update(
        assistant_id=assistant_id,
        tool_resources={"file_search":  {"vector_store_ids": [vector_store_id]}},
    )
    logger.info(f"Updated {assistant_id} with Vector Store: {vector_store_id}")
    
    config["assistant_id"] = assistant_id
    
    save_config(config)

    return assistant_id, vector_store_id

def assistant_resource_allocate():
    config = load_config()
    assistant_id, vector_store_id = create_resources_if_needed(config)

    # Create json file for ids
    ids = {
        "assistant_id": assistant_id,
        "vector_store_id": vector_store_id
    }

    upload_file_to_spaces(json.dumps(ids), "ids.json")

if __name__ == "__main__":
    assistant_resource_allocate()