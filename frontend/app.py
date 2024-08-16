import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from html_templates import bot_template, user_template, css

# Load environment variables
load_dotenv()
client = OpenAI()

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

def check_assistant_exists(assistant_id):
    try:
        response = client.beta.assistants.retrieve(assistant_id)
        exists = True if response.status_code == 200 else False
        return exists
    except Exception as e:
        return False

def create_assistant_if_needed(config):
    assistant_id = config.get("assistant_id")

    if not check_assistant_exists(assistant_id):
        course_mentor_assistant = client.beta.assistants.create(
            model="gpt-4o-mini",
            name="NJIT Course Mentor",
            description="Assistant to help NJIT students plan their courses.",
            instructions="""
                            You are an AI assistant specialized in NJIT course planning. Your task is to provide course recommendations based on a student's major, grad/undergrad status, department, and college, as detailed in their uploaded transcript file. The transcript contains all relevant personal information and is already available to you.

                            Key Guidelines:

                            Course Level Identification:

                            Graduate Courses: Recognize courses with codes in the range of 500-799 as graduate-level courses.
                            Undergraduate Courses: Recognize courses with codes in the range of 100-499 as undergraduate-level courses.

                            Initial Confirmation:

                            At the start of the conversation, extract the student's major, college, and program details from the transcript.
                            Accurately insert the extracted information into your response. For example:
                            Correct Response: "According to your transcript, you are a Computer Science major in the College of Computing Sciences program. Please confirm this information by responding with 'Yes' or 'No'."
                            If, for any reason, the AI is unable to retrieve this information, explicitly state that the data could not be found and ask for clarification, rather than presenting vague placeholders.

                            Course Level Prioritization:

                            Strictly prioritize suggesting courses that match the student's academic level as indicated on their transcript:
                            For undergraduate students, recommend only courses with codes in the 100-499 range.
                            For graduate students, recommend only courses with codes in the 500-799 range.
                            Only suggest courses outside the student's indicated level (e.g., undergraduate courses for a graduate student or vice versa) if the student explicitly requests to consider courses at a different level.
                            If the student indicates a desire to take courses outside their academic level, mention any prerequisites or special permissions that may be required.

                            Data Integrity:

                            Extract all required information directly from the transcript.
                            Never infer or guess any details; rely solely on the provided data.
                            If the necessary information is not found in the provided documents, clearly state that fact and ask for the specific information needed.
                            Cross-reference course availability with the courses.json file for the upcoming semester.
                            Ensure your recommendations are strictly accurate, avoiding courses not listed in the courses.json file.

                            Course Recommendations:

                            Avoid recommending courses the student has already completed and passed.
                            Prioritize courses that fulfill major, college, or program requirements.
                            Mention prerequisites and corequisites when suggesting courses.
                            For Honors students:
                            Identify how many honors courses they have left based on the honors.njit.edu HTML files.
                            Recommend appropriate honors and non-honors sections of courses for the upcoming term.
                            Follow the rules on A, B, C, and D honors courses as outlined in the honors-course-requirements HTML file.
                            If honors courses are not offered in the upcoming semester, recommend courses based on the student's honors group and indicate that these are not currently offered.
                            Note that if a student has taken an honors course with a corresponding lab course, only one counts toward their honors requirements.

                            Accuracy in Communication:

                            Begin the conversation by verifying the student's major, college, and program data based on the transcript. Ask them to confirm this information.
                            Do not suggest courses not found in the courses.json file, and if a course is missing, mention that it's not currently offered in the upcoming semester.
                            Provide comprehensive lists of relevant courses when asked, ensuring nothing is omitted.
                            Avoid referencing courses based on the course catalog HTML files when discussing upcoming semester offerings.

                            Student Interaction:

                            Be polite, supportive, and realistic about course requirements.
                            Seek clarification only when the necessary information is genuinely not available in the provided documents.
                            If a course aligns with student preferences but is less useful for graduation, highlight this in your response.

                            Response Accuracy:

                            Internally generate three possible answers, evaluate each against the provided data, and respond with the most accurate and complete response.
                            If the answer cannot be found in the provided data, respond with "The answer could not be found in the provided context.
                            """,
            tools = [{"type": "file_search"}],
        )
        assistant_id = course_mentor_assistant.id
        config["assistant_id"] = assistant_id
        save_config(config)

    return assistant_id

def attach_file_to_assistant(uploaded_file, assistant_id):
    """
    Attach the uploaded file to the assistant for processing.
    """
    file = client.files.create(file=uploaded_file)
    client.assistants.update(
        assistant_id = assistant_id,
        tool_resources = {"type": "file_search", "file_ids": [file.id]}
    )

def start_assistant_thread(prompt):
    messages = [{"role": "user", "content": prompt}]
    try:
        thread = client.beta.threads.create(messages=messages)
        return thread.id
    except Exception as e: 
        raise e
    
def retrieve_thread(thread_id):
    try:
        thread_messages = client.beta.threads.messages.list(thread_id)
        list_messages = thread_messages.data
        thread_messages = {}
        for message in list_messages:
            obj = {}
            obj["role"] = message.role
            obj["content"] = message.content[0].text.value
            thread_messages.append(obj)
        return thread_messages[::-1]
    except Exception as e:
        raise e

def add_message_to_thread(thread_id, message):
    client.beta.threads.messages.create(thread_id, role="user", content=message)

def run_assistant(thread_id, assistant_id):
    try:
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        return run.id
    except Exception as e:
        raise e

def check_run_status(thread_id, run_id):
    try:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return run.status
    except Exception as e:
        raise e

def main():
    
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        st.error("OpenAI API key is not set. Please add it to the .env file.")
        return
    
    config = load_config()
    assistant_id = create_assistant_if_needed(config)

    # Page Configuration
    st.set_page_config(
        page_title="NJIT Course Planning Tool",
        page_icon=":mortar_board:",
        layout="centered",
        initial_sidebar_state="expanded",
    )

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
        attach_file_to_assistant(uploaded_file, assistant_id)

        query = st.text_area("Ask a question to receive course mentorship.")
        if query and st.button("Ask"):
            with st.spinner('Generating answer...'):
                # Call your assistant to process the uploaded file and get course suggestions
                try:
                    # Start a new thread
                    thread_id = start_assistant_thread(query)
                    st.session_state.thread_id = thread_id

                    # Run the assistant
                    run_id = run_assistant(thread_id, assistant_id)
                    st.session_state.run_id = run_id

                    # Check the status of the run
                    status = check_run_status(thread_id, run_id)
                    st.session_state.status = status

                    while st.session_state.status != "complete":
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