import streamlit as st
import time
from openai import OpenAI
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import os
import json
import logging
import cProfile
import pstats
from html_templates import bot_template, user_template, css

# Load environment variables
load_dotenv()
client = OpenAI()

# Global variables for vector store and assistant
assistant_id = None
vector_store_id = None

# Set up logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('app.log', 'w', 'utf-8')])

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

# Get Digital Ocean credentials from environment variables
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'nyc3')
#DO_SPACES_ENDPOINT = os.getenv('DO_SPACES_ENDPOINT', 'https://nyc3.digitaloceanspaces.com')
DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')

# Configure the boto3 client
session = boto3.session.Session()
s3_client = session.client('s3',
                        region_name=DO_SPACES_REGION,
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=DO_SPACES_KEY,
                        aws_secret_access_key=DO_SPACES_SECRET)

prefix = 'ids/'

def retrieve_ids_from_spaces():
    try:
        logger.info("Retrieving Assistant ID and Vector Store ID from Spaces")
        response = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=prefix + 'ids.json')
        ids = json.loads(response['Body'].read().decode('utf-8'))
        assistant_id = ids['assistant_id']
        vector_store_id = ids['vector_store_id']
        logger.info(f"Retrieved Assistant ID: {assistant_id} and Vector Store ID: {vector_store_id} from Spaces")
        return assistant_id, vector_store_id
    except NoCredentialsError:
        logger.error("Credentials not available")
        return None, None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise None, None

def start_assistant_thread(uploaded_file, prompt):
    logger.info(f"Starting Assistant Thread with Transcript attached")
    file = client.files.create(file=uploaded_file, purpose="assistants")
    updated_prompt = "You have been provided with my transcript. Based on its information, answer the following question: " + prompt
    tools = [{"type": "file_search"}]

    # Create the message with the content and the file attached using the tools array
    updated_prompt = "You have been provided with my transcript. Based on its information, answer the following question: " + prompt
    messages = [{
        "role": "user",
        "content": updated_prompt,
        "attachments": [{"file_id": file.id, "tools": tools}]
    }] 
    try:
        logger.info("Creating Assistant Thread")
        thread = client.beta.threads.create(messages=messages)
        return thread.id
    except Exception as e: 
        logger.error(f"An error occurred: {e}")
        raise e
    
def retrieve_thread(thread_id):
    try:
        logger.info(f"Retrieving Thread: {thread_id}")
        thread_messages = client.beta.threads.messages.list(thread_id)
        list_messages = thread_messages.data
        thread_messages = []
        for message in list_messages:
            obj = {}
            obj["role"] = message.role
            obj["content"] = message.content[0].text.value
            thread_messages.append(obj)
        return thread_messages[::-1]
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise e

def add_message_to_thread(thread_id, message):
    logger.info(f"Adding message to Thread: {thread_id}")
    client.beta.threads.messages.create(thread_id, role="user", content=message)

def run_assistant(thread_id, assistant_id):
    try:
        logger.info(f"Running Assistant: {assistant_id}")
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        return run.id
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise e

def check_run_status(thread_id, run_id):
    try:
        logger.info(f"Checking Run Status: {run_id}")
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return run.status
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise e

def main():
    
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Page Configuration
    st.set_page_config(
        page_title="NJIT Course Planning Tool",
        page_icon=":mortar_board:",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    logger.info("Configured Streamlit Page")

    if not openai_api_key:
        st.error("OpenAI API key is not set. Please add it to the .env file.")
        logger.error("OpenAI API key is not set.")
        return
    
    assistant_id, vector_store_id = retrieve_ids_from_spaces()

    # Title and Description
    st.title("NJIT Course Planning Tool")
    st.write("""
        Welcome to the NJIT Course Planning Tool! This application will help you plan your courses for the upcoming semester 
        based on your major, grad/undergrad status, and department/college. Please upload 
        your unofficial transcript for accurate course suggestions.
    """)

    # Upload Unofficial Transcript
    st.sidebar.header("Upload Unofficial Transcript")
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["pdf"])

    # Display uploaded file name
    if uploaded_file is not None:
        st.sidebar.write("Uploaded file:", uploaded_file.name)

    #Query Assistant
    if uploaded_file is not None:
        thread_id = st.session_state.get("thread_id", None)
        query = st.text_area("Ask a question to receive course mentorship.")
        if query:
            with st.spinner('Processing query...'):
                # Call your assistant to process the uploaded file and get course suggestions
                try:
                    if thread_id == None:
                        # Start a new thread
                        thread_id = start_assistant_thread(uploaded_file, query)
                        st.session_state.thread_id = thread_id
                    else:
                        add_message_to_thread(thread_id, query)
                    # Run the assistant
                    run_id = run_assistant(thread_id, assistant_id)
                    st.session_state.run_id = run_id

                    # Check the status of the run
                    status = check_run_status(thread_id, run_id)
                    st.session_state.status = status

                    while st.session_state.status != "completed":
                        with st.spinner('Generating answer...'):
                            backoff_time = 1  # Start with 1 second delay
                            max_backoff_time = 30  # Maximum delay time
                            max_retries = 10  # Maximum number of retries before timing out
    
                            retries = 0

                            while st.session_state.status != "completed" and retries < max_retries:
                                with st.spinner('Generating answer...'):
                                    time.sleep(backoff_time)
                                    st.session_state.status = check_run_status(thread_id, run_id)

                                    # If status is still not completed, increase the delay with backoff
                                    if st.session_state.status != "completed":
                                        backoff_time = min(backoff_time * 2, max_backoff_time)  # Exponential backoff
                                        retries += 1

                            if st.session_state.status != "completed":
                                st.error("Request timed out. Please try again.")
                            st.session_state.status = check_run_status(thread_id, run_id)

                    # Store conversation
                    if 'chat_history' not in st.session_state:
                        st.session_state.chat_history = []
                    chat_history = retrieve_thread(st.session_state.thread_id)
                    for message in chat_history:
                        if message["role"] == "user":
                            st.session_state.chat_history.append(f"USER: {message['content']}")
                        else:
                            st.session_state.chat_history.append(f"AI: {message['content']}")

                    # Display conversation in reverse order
                    for i, message in enumerate(reversed(st.session_state.chat_history)):
                        if i % 2 == 0: st.markdown(bot_template.replace("{{MSG}}", message), unsafe_allow_html=True)
                        else: st.markdown(user_template.replace("{{MSG}}", message), unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logger.error(f"An error occurred: {e}")

    else:
        st.warning("Please upload your unofficial transcript to generate course suggestions.")

    # Footer
    st.write("""
        ---
        This tool uses OpenAI's GPT to provide course suggestions based on the data you provide. 
        Your data is kept confidential and secure.
    """)

if __name__ == "__main__":
    main()