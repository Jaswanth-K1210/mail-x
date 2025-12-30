import os
import json
import requests
import datetime
import smtplib
from email.mime.text import MIMEText
from imap_tools import MailBox, AND
from typing import Dict, Any, List

# Core Logic extracted from previous email_agent.py
# Now stateless function calls, getting config passed in

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "mistralai/mistral-7b-instruct"
MAX_EMAIL_PREVIEW = 600

def get_timestamp():
    return datetime.datetime.now().isoformat()

def call_openrouter(messages: list, api_key: str) -> Dict[str, Any]:
    if not api_key:
        return {}
        
    headers = {
        "Authorization": f"Bearer {api_key}",
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
    except Exception as e:
        print(f"LLM API Error: {e}")
        return {}

def classify_intent_rules(text: str, sender: str) -> Dict[str, Any]:
    text_lower = text.lower()
    sender_lower = sender.lower()
    
    promo_keywords = [
        "unsubscribe", "newsletter", "offer", "discount", "sale", "welcome", 
        "verify", "alert", "security", "code", "login", "update", "marketing",
        "noreply", "no-reply", "notification", "statement"
    ]
    if any(k in text_lower for k in promo_keywords) or \
       any(k in sender_lower for k in promo_keywords):
        return {"intent": "Promotional/Notification", "confidence": 1.0}

    meeting_keywords = ["meeting", "zoom", "teams", "calendly", "schedule", "availability", "meet"]
    if any(k in text_lower for k in meeting_keywords):
        return {"intent": "Meeting Request", "confidence": 0.9}

    support_keywords = ["help", "issue", "problem", "error", "fail", "broken", "bug", "support"]
    if any(k in text_lower for k in support_keywords):
        return {"intent": "Support Query", "confidence": 0.9}

    return {"intent": "General", "confidence": 0.5}

def decide_strategy(intent: str) -> str:
    strategies = {
        "Meeting Request": "Propose a meeting time and ask for confirmation.",
        "Support Query": "Acknowledge the issue and promise support investigation.",
        "General": "Acknowledge receipt and ask how we can help."
    }
    return strategies.get(intent, strategies["General"])

def generate_reply_llm(email_text: str, intent: str, strategy: str, sender_name: str, api_key: str) -> str:
    system_prompt = (
        "You are a professional email assistant. "
        f"The email intent is '{intent}'. "
        f"Strategy: {strategy}. "
        "INSTRUCTIONS:\n"
        f"1. Address the recipient as '{sender_name}' (or 'there' if unknown).\n"
        "2. Draft a response that addresses the points in the body.\n"
        "3. DO NOT invent dates/times. Ask for availability.\n"
        "Tone: formal, concise, neutral. Do NOT include Subject lines. Sign off as 'AI Agent'."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Incoming Email Body:\n{email_text[:MAX_EMAIL_PREVIEW]}\n\nDraft a reply:"}
    ]
    data = call_openrouter(messages, api_key)
    try:
        content = data['choices'][0]['message']['content'].strip()
        content = content.replace("<s>", "").replace("</s>", "").strip()
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        return content if content else "Thank you for your email."
    except:
        return "Thank you for your email. We will get back to you shortly."

def send_email(to_email: str, subject: str, body: str, user_email: str, app_pass: str):
    msg = MIMEText(body)
    msg['Subject'] = f"Re: {subject}"
    msg['From'] = user_email
    msg['To'] = to_email

    try:
        # Assuming Gmail for MVP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(user_email, app_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

def run_agent_cycle(user_email: str, app_pass: str, api_key: str):
    """
    Runs one cycle of: Fetch -> Classify -> Reply
    Returns a list of actions taken for logging.
    """
    logs = []
    try:
        # 1. Connect
        with MailBox("imap.gmail.com").login(user_email, app_pass) as mailbox:
            # Fetch latest 10 unread
            msgs = mailbox.fetch(AND(seen=False), limit=10, reverse=True, mark_seen=True)
            
            for msg in msgs:
                log_entry = {
                    "subject": msg.subject,
                    "sender": msg.from_,
                    "timestamp": get_timestamp(),
                    "action": "Skipped"
                }
                
                # Check Noreply
                if "noreply" in msg.from_.lower() or "no-reply" in msg.from_.lower():
                    log_entry["action"] = "Ignored (No-Reply)"
                    logs.append(log_entry)
                    continue
                
                body = (msg.text or msg.html or "").strip()
                if not body:
                    continue

                # Classify
                cls = classify_intent_rules(body, msg.from_)
                intent = cls["intent"]
                log_entry["intent"] = intent

                if intent == "Promotional/Notification":
                    log_entry["action"] = "Ignored (Promotional)"
                    logs.append(log_entry)
                    continue
                
                # Reply
                strategy = decide_strategy(intent)
                sender_name = msg.from_values.name if msg.from_values.name else "there"
                reply = generate_reply_llm(body, intent, strategy, sender_name, api_key)
                
                # Send
                sent = send_email(msg.from_, msg.subject, reply, user_email, app_pass)
                if sent:
                    log_entry["action"] = "Replied"
                    log_entry["reply_preview"] = reply[:50] + "..."
                else:
                    log_entry["action"] = "Failed to Send"
                
                logs.append(log_entry)

    except Exception as e:
        logs.append({"error": str(e)})
    
    return logs, get_timestamp()
