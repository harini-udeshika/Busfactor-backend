# Bus Factor Backend

This project is the backend application for the Bus Factor analysis tool. It is built using Python and handles the data processing and graph generation for the frontend application.

## Prerequisites

Before running this project, ensure you have the following installed on your machine:

- **Python** (v3.8 or later) - [Download Python](https://www.python.org/downloads/)
- **pip** (comes with Python for package management)

## Getting Started

Follow these steps to set up and run the project on your local machine:

### 1. Clone the Repository
```bash
git clone https://github.com/harini-udeshika/Busfactor-backend.git
cd harini-udeshika-busfactor-backend
```

### 2. Set Up Environment Variables
Create a `.env` file in the root directory of the project with the following content:
```
GITHUB_TOKEN=<Add your token here>
```
Replace `<Add your token here>` with your personal GitHub token. This is required for accessing GitHub's API.

### 3. Install Dependencies

#### With a Virtual Environment (Recommended)
1. Create and activate a virtual environment to isolate the project dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
2. Install the required Python packages listed in the `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```

#### Without a Virtual Environment
1. Install the required Python packages directly:
   ```bash
   pip install Flask flask-cors python-dotenv flask-socketio requests rapidfuzz GitPython networkx python-louvain numpy PyGithub
   ```
2. Optionally, generate a `requirements.txt` file for future use:
   ```bash
   pip freeze > requirements.txt
   ```

### 4. Run the Application
Start the backend server using the following command:
```bash
python app.py
```
The application will start, and you can access its endpoints locally (default: `http://127.0.0.1:5000`).

### 5. Place the `requirements.txt` File
Ensure the `requirements.txt` file is placed in the root directory of the project (same level as `app.py`). This file contains all the dependencies required for the project:

```plaintext
Flask
flask-cors
python-dotenv
flask-socketio
requests
rapidfuzz
GitPython
networkx
python-louvain
numpy
PyGithub
```

## Project Structure
The project is organized into the following files:

- **`app.py`**: Main entry point of the backend server.
- **`generate_graphs.py`**: Script for generating graphs based on data.
- **`graph_to_json.py`**: Script for converting graph data to JSON format for frontend consumption.

## Additional Notes
- **Environment Variables**: Ensure your `.env` file is properly configured to avoid API rate limits or unauthorized access.
- **Development Tools**: Use an IDE or text editor with Python support for the best development experience.

## Troubleshooting
If you encounter issues:
1. Ensure Python and pip are installed correctly.
2. Verify the `.env` file is set up and contains a valid GitHub token.
3. Check for missing dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```
4. Review the terminal or log output for error messages.


