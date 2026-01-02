# 📄 IBM AI Email Agent: Detailed Project Report

## 1. Executive Summary
The **IBM AI Email Agent** is an autonomous inbox management system designed to reclaim user productivity by automating email processing. Unlike standard auto-responders, this agent uses **Large Language Models (LLMs)** to intelligently "read" emails, understand context, and take appropriate actions—whether that's flagging an urgent meeting request, drafting a polite decline, or ignoring a promotional newsletter.

The solution is delivered as a user-friendly **Chrome Extension** backed by a robust **Python API**, ensuring seamless integration into the user's daily workflow.

---

## 2. Problem Statement
Modern professionals spend approximately **28% of their work week** managing email. The cognitive load of filtering through spam, notifications, and low-priority messages distracts from deep work. Existing tools are either too simple (keyword filters) or too intrusive (requiring full access to data on third-party servers).

## 3. Solution Architecture
The project follows a **Client-Server Architecture** designed for security and scalability.

### A. Frontend: Chrome Extension
*   **Technology**: HTML5, CSS3, Vanilla JavaScript (ES6+), Manifest V3.
*   **Role**: Serves as the control panel. It manages user authentication, displays real-time agent status (Running/Stopped), allows configuration of check intervals (e.g., every 30 mins), and securely stores session tokens.
*   **Key Components**:
    *   `popup.html/js`: The UI logic.
    *   `manifest.json`: Defines permissions (`storage`, `host_permissions`).

### B. Backend: Python API Server
*   **Technology**: Python 3.9+, FastAPI, Uvicorn, APScheduler.
*   **Role**: The "Brain" of the operation. It runs locally (or on a cloud server like Colab/Render) to handle the heavy lifting.
*   **Key Components**:
    *   `main.py`: REST API endpoints (`/login`, `/toggle`, `/status`) and the Scheduler entry point.
    *   `agent_logic.py`: Contains the core `run_agent_cycle` function.
    *   **IMAP/SMTP**: Uses standard protocols to fetch/send emails without proprietary APIs.

### C. AI Intelligence Layer
*   **Provider**: OpenRouter API.
*   **Model**: Mistral-7B (configurable).
*   **Tasks**:
    1.  **Classification**: Analyzes email body to tag it as `Urgent`, `Meeting Request`, `Support`, or `Promotional`.
    2.  **Generation**: Drafts warm, professional, context-aware replies based on the sender's content.

---

## 4. Key Features
1.  **Smart Filtering**: automatically skips "No-Reply", "Newsletter", and "Promotional" emails to save API costs and avoid spamming.
2.  **Autonomous Scheduling**: Users can set the agent to run every 1, 15, 30, or 60 minutes. The backend handles this schedule via background threads.
3.  **Secure Authentication**: Uses **Gmail App Passwords** (not your main password) and **OpenRouter API Keys**. Credentials can be stored locally, minimizing data leak risks.
4.  **Real-Time Status**: The extension UI updates live to show when the last check occurred and when the next one is due.

---

## 5. Technical Workflow
1.  **User Login**: User enters credentials in the Chrome Extension.
2.  **Validation**: The backend attempts a test IMAP login to verify credentials.
3.  **Scheduling**: On success, the backend's `APScheduler` creates a recurring job for that user.
4.  **Execution Cycle**:
    *   Fetch unread emails (limit 10).
    *   **Rule Check**: Is it a generic `no-reply` address? -> *Skip*.
    *   **AI Classify**: Send email body to LLM -> *Get Intent*.
    *   **Action**: If Actionable, *Generate Reply* -> *Send Email* -> *Mark as Read*.
5.  **Feedback**: The cycle timestamp is logged, and the Front-end updates the "Last Run" display.

---

## 6. How to Deploy on Google Colab
To run the backend on Google Cloud (Colab) instead of your local laptop, follow these steps:

**Step 1: Open Google Colab**
Create a new notebook.

**Step 2: Copy-Paste this Script**
Run this block to set up the server and get a public URL.

```python
# 1. Install Dependencies
!pip install fastapi uvicorn pyngrok nest-asyncio apscheduler imap-tools requests python-multipart pydantic

# 2. Setup Ngrok (Public URL)
from pyngrok import ngrok
import nest_asyncio
import uvicorn
import os

# SET YOUR NGROK TOKEN HERE (Get from dashboard.ngrok.com)
NGROK_TOKEN = "YOUR_NGROK_AUTH_TOKEN" 
ngrok.set_auth_token(NGROK_TOKEN)

# 3. Create the Backend Code (main.py + agent_logic.py)
# We will pull the latest code directly from your GitHub repo
!git clone https://github.com/Jaswanth-K1210/mail-x.git
%cd mail-x/backend

# 4. Run the Server
# Start Ngrok tunnel on port 8000
public_url = ngrok.connect(8000).public_url
print(f"\n🚀 PUBLIC SERVER URL: {public_url}\n")
print("COPY this URL and paste it into your Chrome Extension!\n")

# Patch asyncio to allow nested loops in Colab
nest_asyncio.apply()

# Run the app
from main import app
uvicorn.run(app, port=8000)
```

**Step 3: Connect Extension**
1.  Copy the **Public URL** printed by the script (e.g., `https://a1b2-34-56.ngrok-free.app`).
2.  Open your Chrome Extension.
3.  Paste it into the **Server URL** box.
4.  Login normally.

---

## 7. Future Roadmap
*   **Database Migration**: Move from `users.json` to Firebase/Supabase for persistent cloud storage.
*   **RAG Integration**: Allow the agent to search your Google Drive/Calendar to verify availability before accepting meetings.
*   **Multi-Agent System**: Separate "Triage Agent" and "Drafting Agent" for higher accuracy.
