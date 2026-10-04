#!/usr/bin/env python3
"""
Grow Model Quiz Agent - Termux SMS Automation
Reads SMS from a shortcode, asks Groq for the answer, sends it back.
"""

import json
import time
import subprocess
import sys
from pathlib import Path
import requests

# --- Load Configuration ---
CONFIG_PATH = Path(__file__).parent / "config.json"
if not CONFIG_PATH.exists():
    print("[!] config.json not found. Create it first.")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    config = json.load(f)

GROQ_API_KEY = config["groq_api_key"]
SHORTCODE = config["shortcode"]
POLL_INTERVAL = config.get("poll_interval", 5)
MAX_QUESTIONS = config.get("max_questions", 5)

# --- Termux SMS Helpers ---
def get_sms_list(limit=20):
    """Fetch recent SMS messages using termux-sms-list."""
    try:
        output = subprocess.check_output(
            ["termux-sms-list", "-l", str(limit)],
            text=True,
            stderr=subprocess.DEVNULL
        )
        return json.loads(output)
    except Exception as e:
        print(f"[!] Failed to read SMS: {e}")
        return []

def send_sms(number, message):
    """Send an SMS using termux-sms-send."""
    try:
        subprocess.run(
            ["termux-sms-send", "-n", number, message],
            check=True,
            stderr=subprocess.DEVNULL
        )
        print(f"[*] Sent SMS to {number}: {message}")
        return True
    except Exception as e:
        print(f"[!] Failed to send SMS: {e}")
        return False

def get_latest_question(last_timestamp=None):
    """Return the latest SMS from SHORTCODE that looks like a question."""
    messages = get_sms_list(30)
    # Filter by shortcode and inbox type
    relevant = [
        m for m in messages
        if m.get("number") == SHORTCODE and m.get("type") == "inbox"
    ]
    if not relevant:
        return None, None
    # Sort by received time (descending)
    relevant.sort(key=lambda m: m.get("received", 0), reverse=True)
    latest = relevant[0]
    received = latest.get("received", 0)
    body = latest.get("body", "").strip()
    # If we already saw this message, return None
    if last_timestamp is not None and received <= last_timestamp:
        return None, None
    # Heuristic: question contains '?' and options A, B, C, D
    if "?" in body and any(opt in body for opt in ["A.", "B.", "C.", "D.", "A)", "B)", "C)", "D)"]):
        return body, received
    return None, None

# --- Groq API ---
def get_answer_from_groq(question_text):
    """Send question to Groq and extract the answer letter."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are a quiz answer assistant. Read the following SMS quiz question and its options.
Reply with ONLY the letter of the correct answer (A, B, C, or D). Do not include any other text.

Question:
{question_text}
"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You answer multiple-choice questions concisely."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 10
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip().upper()
        for ch in answer:
            if ch in "ABCD":
                return ch
        return "A"  # fallback
    except Exception as e:
        print(f"[!] Groq API error: {e}")
        return "A"

# --- Main Loop ---
def main():
    print("=== Grow Model Quiz Agent (Termux SMS) ===")
    print(f"[*] Listening for SMS from {SHORTCODE}...")
    print(f"[*] Will answer {MAX_QUESTIONS} questions.")

    last_timestamp = None
    answered = 0

    while answered < MAX_QUESTIONS:
        question, timestamp = get_latest_question(last_timestamp)
        if question:
            print(f"\n--- Question {answered + 1}/{MAX_QUESTIONS} ---")
            print(f"[*] Received: {question[:200]}...")
            answer = get_answer_from_groq(question)
            print(f"[*] Groq answer: {answer}")
            if send_sms(SHORTCODE, answer):
                answered += 1
                last_timestamp = timestamp
            else:
                print("[!] Failed to send answer. Retrying...")
            # Wait a bit for the next question
            time.sleep(8)
        else:
            # No new question, wait and poll again
            time.sleep(POLL_INTERVAL)

    print("\n[+] All questions answered. Done.")

if __name__ == "__main__":
    main()
