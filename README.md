#AI Email Agent (Submission)

## Project Overview
This project is an **Autonomous AI Email Agent** capable of managing your inbox intelligently. It automatically detects crucial emails (Meeting Requests, Support Queries) and ignores promotional spam. It then uses LLMs (Mistral-7B via OpenRouter) to draft professional replies in your tone.

The system is built as a **Chrome Extension** powered by a local **FastAPI Backend**, offering a secure, privacy-first architecture where credentials stay on your device/local server.

## Features
*   **Inbox Triage**: Instantly separates "Urgent/Actionable" from "Promotional/Spam" using smart rule-based and LLM classification.
*   **Auto-Drafting**: Generates context-aware replies for identified meetings or support tickets.
*   **Scheduler**: Runs completely autonomously in the background at user-defined intervals (1 min, 30 mins, etc.).
*   **Chrome Extension UI**: A clean, modern popup to manage the agent, view status, and configure settings.
*   **Privacy First**: Emails are processed via your own OpenRouter key; App Passwords are stored locally encrypted.

## Project Structure
*   `/backend`: Python FastAPI server.
    *   `main.py`: API endpoints and Scheduler.
    *   `agent_logic.py`: Core IMAP/SMTP and LLM processing logic.
*   `/extension`: Chrome Extension source code.
    *   `manifest.json`: V3 Manifest.
    *   `popup.html/js`: UI Logic.

## Installation & Setup

### 1. Prerequisites
*   Python 3.9+
*   Google Chrome (or Brave/Edge)

### 2. Start the Backend Server
The extension needs the Python "brain" to run.
```bash
# install dependencies
pip install -r requirements.txt

# run the server
cd backend
uvicorn main:app --reload --port 8000
```
Keep this terminal window running.

### 3. Install the Extension
1.  Open Chrome and go to `chrome://extensions`.
2.  Enable **Developer Mode** (top right).
3.  Click **Load Unpacked**.
4.  Select the `extension` folder from this project.
5.  Pin the **IBM AI Email Agent** icon to your toolbar.

### 4. Usage
1.  Click the extension icon.
2.  Enter your **Gmail** address and **App Password**.
    *   *(Note: You must generate an App Password from your Google Account > Security > 2-Step Verification)*.
3.  Enter your **OpenRouter API Key**.
4.  Click **Connect Agent**.
5.  Set your desired check interval (e.g., 30 mins) and click **Save**.

The agent is now running! It will check your email in the background and process actionable items automatically.
