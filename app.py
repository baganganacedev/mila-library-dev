"""
MILA - Upgraded with HuggingFace AI + FREE Fallback
MCNP-ISAP Library Virtual Assistant
Facebook Page: Library Dev (1303250132873567)
"""
import os
import re
from flask import Flask, request
import requests

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mila_verify_2024")
HF_TOKEN = os.environ.get("HF_TOKEN") # <-- ADD THIS IN RENDER

# Optional HF - only loaded if token exists
hf_client = None
if HF_TOKEN:
    try:
        from huggingface_hub import InferenceClient
        hf_client = InferenceClient(api_key=HF_TOKEN)
        print("✅ HF Client ready")
    except Exception as e:
        print(f"HF init failed: {e}")

# KNOWLEDGE BASE - same as yours
FAQS = [
    {
        "keywords": ["hours", "open", "operating", "schedule", "what time open", "anong oras bukas"],
        "answer": "📚 Hello! I am MILA, your MCNP-ISAP Library Virtual Assistant!\n\nThe library is open from Monday to Friday, 7:00 AM to 6:00 PM, and Saturday, 8:00 AM to 12:00 PM.\n\nAnything else you need? 😊"
    },
    {
        "keywords": ["borrow", "hiram", "borrowing time", "return", "sauli", "due date", "overdue", "fine", "penalty", "what time can i borrow"],
        "answer": "📚 Borrowing starts at 3:00 PM, and borrowed materials must be returned no later than 10:00 AM on the due date.\n\nAn overdue fine of ₱1.00 per hour or ₱10.00 per day per book will be charged for late returns.\n\nNeed help with anything else?"
    },
    {
        "keywords": ["library card", "requirements", "how to get card", "apply", "id", "photocopy", "passport size", "alphabetical list", "class president"],
        "answer": "📚 To apply for a library card, students must prepare:\n• Photocopy of School ID\n• One passport-size picture\n• List of names with ID numbers (alphabetical)\n\nThe class president will submit the soft copy of the list through MCNP-ISAP Library Facebook page. Photocopy of ID and picture must be submitted to the library.\n\nWant to know how to claim it?"
    },
    {
        "keywords": ["lost", "nawala", "lost card", "replacement", "second issuance", "50 pesos"],
        "answer": "📚 If your library card is lost, please report it immediately to the library.\n\nYou may apply for a second issuance and pay the ₱50 replacement fee.\n\nNeed help reporting it?"
    },
    {
        "keywords": ["how many books", "ilang libro", "max books", "borrow how many", "fiction"],
        "answer": "📚 Each student may borrow a maximum of 3 books at a time: 2 professional books with different titles and 1 fiction book.\n\nFiction books may be borrowed for a maximum of 1 week only.\n\nAnything else?"
    },
    {
        "keywords": ["cannot borrow", "not allowed", "bawal hiramin", "thesis", "periodicals", "newspaper", "library use only"],
        "answer": "📚 The following are for library use only and cannot be borrowed:\n• Theses\n• Periodicals\n• Newspapers\n\nYou can read them inside the library though! 😊"
    },
    {
        "keywords": ["claim", "claiming", "ready", "when ready", "notification", "kailan makukuha"],
        "answer": "📚 The assigned library staff will message you once your library card is ready for claiming. Please wait for the notification before going to the library.\n\nWill message you once ready! 📚"
    },
]

DEFAULT_ANSWER = """📚 Hello! I am MILA, your MCNP-ISAP Library Virtual Assistant!

Welcome to MCNP-ISAP Library! I can help you with:
• Library hours
• Borrowing & returning
• Library card requirements
• Lost card
• How many books you can borrow
• What materials cannot be borrowed
• Claiming your card

Just ask me like: "What are library hours?" or "How to get library card?" 😊

For other concerns, please leave your full name, course/year, and concern — I'll forward it to admin!"""

def find_best_faq(user_message):
    msg = user_message.lower()
    best_match = None
    best_score = 0
    for faq in FAQS:
        score = sum(1 for kw in faq["keywords"] if kw in msg)
        if score > best_score:
            best_score = score
            best_match = faq
    return best_match, best_score

def ask_huggingface(user_message, faq_context=""):
    if not hf_client:
        return None

    # RAG: Give HF the FAQ as context so it doesn't hallucinate
    system_prompt = f"""You are MILA, the MCNP-ISAP Library Virtual Assistant.
Answer based ONLY on this library info. Be friendly, short, and use emojis.
If question is outside library info, say you will forward to admin and ask for name/course/year.

LIBRARY KNOWLEDGE:
{faq_context}

If no relevant knowledge, use this general info:
- Hours: Mon-Fri 7AM-6PM, Sat 8AM-12PM
- Borrow starts 3PM, return by 10AM due date
- Fine: P1/hour or P10/day per book
- Max 3 books (2 prof + 1 fiction, fiction 1 week only)
- Cannot borrow: thesis, periodicals, newspaper
- Card requirements: photocopy ID, passport pic, alphabetical list via class president
- Lost card: report + P50 replacement
- Claiming: wait for staff message
"""
    try:
        completion = hf_client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct", # Free, fast, good for Tagalog/English
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=350,
            temperature=0.6
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"HF Error: {e}")
        return None

def find_answer(user_message):
    best_match, score = find_best_faq(user_message)
    faq_context = best_match["answer"] if best_match else DEFAULT_ANSWER

    # 1. Try Hugging Face AI first (if token set)
    if hf_client:
        ai_reply = ask_huggingface(user_message, faq_context)
        if ai_reply:
            return ai_reply

    # 2. Fallback to keyword matching (100% free, always works)
    if best_match and score > 0:
        return best_match["answer"]
    else:
        return DEFAULT_ANSWER

def send_message(recipient_id, text):
    if not PAGE_ACCESS_TOKEN:
        print("No PAGE_ACCESS_TOKEN set!")
        return
    url = f"https://graph.facebook.com/v19.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text[:1900]}
    }
    r = requests.post(url, params=params, json=payload)
    print(f"Sent to {recipient_id}: {r.status_code}")

@app.route("/", methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    return "MILA Bot for Library Dev (1303250132873567) is running 📚 - HF AI + FAQ Fallback", 200

@app.route("/", methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Webhook: {data}")
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            for messaging in entry.get('messaging', []):
                if 'message' in messaging and 'text' in messaging['message']:
                    if messaging['message'].get('is_echo'):
                        continue
                    sender_id = messaging['sender']['id']
                    user_text = messaging['message']['text']
                    print(f"User {sender_id}: {user_text}")
                    reply = find_answer(user_text)
                    send_message(sender_id, reply)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
