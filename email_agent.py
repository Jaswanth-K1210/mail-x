import os
import sys
import json
import time
import requests
import datetime
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, List
from dotenv import load_dotenv
from imap_tools import MailBox, AND

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "mistralai/mistral-7b-instruct"
MEMORY_FILE = "memory.json"
MAX_EMAIL_PREVIEW = 600 # Reduced from 2000 for speed

# Email Configuration
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

def call_openrouter(messages: list) -> Dict[str, Any]:
    """Helper to call OpenRouter API."""
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost", 
        "X-Title": "EmailAgent"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {e}")
        return {}

def classify_intent_llm(email_text: str) -> Dict[str, Any]:
    """Classifies email intent using LLM."""
    system_prompt = (
        "You are an email classifier. Your goal is to filter out spam and automated emails. "
        "Classify the email into exactly one category: "
        "'Meeting Request', 'Support Query', 'Information Request', 'Promotional/Notification', 'General'. "
        "\nRULES:\n"
        "1. Use 'Promotional/Notification' for ALL newsletters, marketing, automated welcome emails, 'Get Started' guides, status updates, and system alerts. If no human action is explicitly requested, it is Promotional.\n"
        "2. Use 'General' ONLY if it appears to be a personal email from a human that requires a reply but fits no other category.\n"
        "3. Output ONLY valid JSON: {\"intent\": \"<Category>\", \"confidence\": <0.0-1.0>}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": email_text[:MAX_EMAIL_PREVIEW]} # Truncate for speed/safety
    ]
    
    response_data = call_openrouter(messages)
    
    try:
        if not response_data:
            raise ValueError("No response from API")
            
        content = response_data['choices'][0]['message']['content']
        # Sanitize markdown code blocks if present
        content_clean = content.replace("```json", "").replace("```", "").strip()
        classification = json.loads(content_clean)
        return classification
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Intent classification failed ({e}). Defaulting to General.")
        return {"intent": "General", "confidence": 0.0}

def decide_strategy(intent: str) -> str:
    """Decides response strategy based on intent."""
    strategies = {
        "Meeting Request": "Propose a meeting time and ask for confirmation.",
        "Support Query": "Acknowledge the issue and promise support investigation.",
        "Information Request": "Provide the requested information clearly.",
        "General": "Acknowledge receipt and ask how we can help."
    }
    return strategies.get(intent, strategies["General"])

def generate_reply_llm(email_text: str, intent: str, strategy: str, sender_name: str) -> str:
    """Generates a professional reply using LLM."""
    system_prompt = (
        "You are a professional email assistant. "
        f"The email intent is '{intent}'. "
        f"Strategy: {strategy}. "
        "INSTRUCTIONS:\n"
        "1. Analyze the email body provided below to understand the specific context.\n"
        f"2. Address the recipient as '{sender_name}' (or 'there' if name is unknown).\n"
        "3. Draft a response that directly addresses the points raised in the body.\n"
        "4. DO NOT invent specific dates, times, or meeting slots. Instead, ask the recipient for their availability or propose 'a convenient time'.\n"
        "5. Keep it short, professional, and enterprise-style.\n"
        "Tone: formal, concise, neutral. "
        "Do NOT include Subject lines. "
        "Sign off as 'AI Agent'. "
        "If the input is very short (like 'yea' or 'ok'), assume it confirms the previous topic and ask for next steps politely."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Incoming Email Body:\n{email_text[:MAX_EMAIL_PREVIEW]}\n\nDraft a reply:"}
    ]
    
    response_data = call_openrouter(messages)
    
    try:
        if not response_data:
            return "Thank you for your response. Please let us know how you would like to proceed. Best regards, AI Agent"
            
        content = response_data['choices'][0]['message']['content'].strip()
        
        # Cleanup artifacts
        content = content.replace("<s>", "").replace("</s>", "").strip()
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
            
        if not content:
             return "Thank you for your update. Best regards, AI Agent"
             
        return content
    except (KeyError, IndexError):
        return "Error: Could not generate reply."

def save_to_memory(record: Dict[str, Any]):
    """Stores interaction in memory.json."""
    data = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
        except (IOError, json.JSONDecodeError):
            data = []
            
    data.append(record)
    
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving to memory: {e}")

def send_email(to_email: str, subject: str, body: str):
    """Sends the reply via SMTP."""
    if not EMAIL_USER or not EMAIL_PASS:
        print("Skipping email send: Credentials not found.")
        return

    msg = MIMEText(body)
    msg['Subject'] = f"Re: {subject}"
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"✅ Reply sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def is_noreply(sender: str) -> bool:
    """Checks if the sender is a no-reply address."""
    sender_lower = sender.lower()
    noreply_patterns = ["noreply", "no-reply", "do-not-reply", "donotreply", "mailer-daemon", "notification"]
    return any(pattern in sender_lower for pattern in noreply_patterns)

def classify_intent_rules(text: str, sender: str, subject: str) -> Dict[str, Any]:
    """Classifies email intent using fast keyword rules (No LLM)."""
    text_lower = text.lower()
    subject_lower = subject.lower()
    sender_lower = sender.lower()
    
    # 1. Promotional / Automated
    promo_keywords = [
        "unsubscribe", "newsletter", "offer", "discount", "sale", "welcome", 
        "verify", "alert", "security", "code", "login", "update", "marketing",
        "noreply", "no-reply", "notification", "statement", "receipt"
    ]
    if any(k in text_lower for k in promo_keywords) or \
       any(k in sender_lower for k in promo_keywords):
        return {"intent": "Promotional/Notification", "confidence": 1.0}

    # 2. Meeting Request
    meeting_keywords = ["meeting", "zoom", "teams", "calendly", "schedule", "availability", "meet"]
    if any(k in text_lower for k in meeting_keywords):
        return {"intent": "Meeting Request", "confidence": 0.9}

    # 3. Support Query
    support_keywords = ["help", "issue", "problem", "error", "fail", "broken", "bug", "support", "ticket"]
    if any(k in text_lower for k in support_keywords):
        return {"intent": "Support Query", "confidence": 0.9}

    # 4. Fallback
    return {"intent": "General", "confidence": 0.5}

def process_emails():
    """Main loop to fetch and process unread emails."""
    global EMAIL_USER, EMAIL_PASS

    # Interactive Login if .env is missing credentials
    if not EMAIL_USER:
        print("\n🔒 Email Credentials Required")
        EMAIL_USER = input("Enter your email address: ").strip()
    
    if not EMAIL_PASS:
        # Use input() instead of getpass for better compatibility with pipes/automation
        print(f"Enter App Password for {EMAIL_USER}: ", end='', flush=True)
        EMAIL_PASS = sys.stdin.readline().strip().replace(" ", "")

    if not EMAIL_USER or not EMAIL_PASS:
        print("Error: Credentials required to proceed.")
        return

    print(f"Connecting to {IMAP_SERVER} as {EMAIL_USER}...")
    
    try:
        with MailBox(IMAP_SERVER).login(EMAIL_USER, EMAIL_PASS) as mailbox:
            # Fetch LATEST UNSEEN messages first (limit to 20 for speed)
            print("Fetching latest 20 unread emails...")
            msgs = mailbox.fetch(AND(seen=False), limit=20, reverse=True)
            
            for msg in msgs:
                print(f"\n📧 Processing: {msg.subject} from {msg.from_}")

                if is_noreply(msg.from_):
                    print(f"🚫 Skipping no-reply sender: {msg.from_}")
                    continue
                
                # 1. Perception
                email_text = msg.text or msg.html
                if not email_text:
                    print("Empty body, skipping.")
                    continue
                
                # Normalize
                email_text_clean = email_text.strip()
                if not email_text_clean:
                    continue
                
                # 2. Reasoning (Rule-based)
                classification = classify_intent_rules(email_text_clean, msg.from_, msg.subject)
                intent = classification.get("intent", "General")
                confidence = classification.get("confidence", 0.0)
                
                # OUTPUT ONLY
                print(f"   🎯 Classification: {intent} ({confidence})")

                # If it is NOT promotional, we should propose a reply
                if intent in ["General", "Meeting Request", "Support Query", "Information Request"]:
                    print("\n   💡 Valuable email detected. Analyzing body and drafting reply...")
                    
                    # 3. Decision
                    strategy = decide_strategy(intent)
                    
                    # Extract name from sender (e.g. "John Doe <john@doe.com>" -> "John Doe")
                    sender_name = msg.from_values.name if msg.from_values and msg.from_values.name else "there"
                    
                    # 4. Action (Drafting)
                    reply_body = generate_reply_llm(email_text_clean, intent, strategy, sender_name)
                    
                    # Approval Step
                    print("\n" + "-"*40)
                    print(f"📝 Proposed Reply to: {msg.from_}")
                    print(f"Subject: Re: {msg.subject}")
                    print(f"Body:\n{reply_body}")
                    print("-" * 40)
                    
                    user_approval = input("❓ Send this reply? (y/N): ").lower().strip()
                    if user_approval == 'y':
                        send_email(msg.from_, msg.subject, reply_body)
                        generated_reply_result = reply_body
                    else:
                        print("❌ Reply skipped by user.")
                        generated_reply_result = "[SKIPPED BY USER] " + reply_body
                else:
                    generated_reply_result = "N/A (Promotional/Ignored)"
                
                # 5. Memory (Log the classification)
                record = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "sender": msg.from_,
                    "subject": msg.subject,
                    "email_text": email_text_clean[:200], 
                    "intent": intent,
                    "confidence": confidence,
                    "generated_reply": generated_reply_result
                }
                save_to_memory(record)
                
    except Exception as e:
        print(f"❌ critical error in email loop: {e}")

def main():
    if not OPENROUTER_API_KEY:
        print("Error: environment variable OPENROUTER_API_KEY is missing.")
        return
        
    process_emails()

if __name__ == "__main__":
    main()
