import streamlit as st
from dotenv import load_dotenv
import os

def main():
    load_dotenv()

    # openai_api_key = os.getenv("OPENAI_API_KEY")
    # if not openai_api_key:
    #     st.error("OpenAI API key is not set. Please add it to the .env file.")
    #     return

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
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

    # Display uploaded file name
    if uploaded_file is not None:
        st.sidebar.write("Uploaded file:", uploaded_file.name)

    #Query Assistant
    if uploaded_file is not None:
        query = st.text_area("Ask a question to receive course mentorship.")
        with st.spinner('Generating answer...'):
            # Call your assistant to process the uploaded file and get course suggestions
            pass
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