# AI Course Mentor NJIT

An OpenAI GPT-powered assistant that provides curated course advice for NJIT students. This app helps students by analyzing their transcripts and suggesting relevant courses from NJIT's course catalog and upcoming semester data.

## Features

- **GPT-powered recommendations**: Get course advice based on your academic history.
- **Data Integration**: Retrieves NJIT's course data from their API and catalog.
- **Cloud Storage**: Uses DigitalOcean for storing course and transcript data.
- **Containerized**: Built with Docker for easy deployment.
- **Scalable**: Backend and frontend run in separate containers.

## Tech Stack

- **Frontend**: Streamlit, Python
- **Backend**: Python, OpenAI API
- **Cloud Storage**: DigitalOcean Spaces
- **Containerization**: Docker

## Setup and Installation

### Prerequisites

- Docker & Docker Compose installed
- DigitalOcean Space and API keys
- OpenAI API key

### Clone the Repository

````bash
git clone https://github.com/anbarsaleem/AI-Course-Mentor-NJIT.git
cd AI-Course-Mentor-NJIT

### Setup Environment Variables
1. Copy the .env.example file to .env in the project root:
```bash
cp .env.example .env
````

2. Edit .env to include your OpenAI and DigitalOcean credentials.

### Build and Run the Project

```bash
docker-compose up --build
```

This will start both the frontend and backend services. The frontend should be accessible at http://localhost:8501.

## Deployment

- For production deployment, you can push the Docker containers to your desired hosting platform, such as DigitalOcean's App Platform.

## Contributing

Feel free to submit issues and pull requests to improve this project.
