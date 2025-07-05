import os
import telebot
import openai
import fitz
import qrcode
import threading
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from fpdf import FPDF
from flask import Flask

# === API Keys from environment variables ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
UPI_ID = os.environ.get("UPI_ID")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

user_usage = {}
paid_users = {}
app = Flask(__name__)

@app.route('/')
def index():
    return "PDF Summary Bot Running"

def generate_qr():
    qr = qrcode.make(f"upi://pay?pa={UPI_ID}&pn=Kamal&am=49")
    qr_path = "upi_qr.png"
    qr.save(qr_path)
    return qr_path

upi_qr_path = generate_qr()

def make_summary_pdf(text, username):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    filename = f"summary_{username}.pdf"
    pdf.output(filename)
    return filename

menu = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("💰 Buy Premium", "📄 Help")
menu.row("📬 Contact Admin")

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"""
👋 Hello {message.from_user.first_name}!

📄 Send me a PDF and I’ll summarize it using ChatGPT.
🆓 First summary is free.
💰 To unlock unlimited summaries:

1. Pay ₹49 to UPI ID: `{UPI_ID}`
2. Or scan the QR code below
3. Send /verify {message.from_user.id} after payment
""", parse_mode="Markdown", reply_markup=menu)
    with open(upi_qr_path, 'rb') as qr:
        bot.send_photo(message.chat.id, qr, caption="📸 Scan this UPI QR to pay ₹49")

@bot.message_handler(commands=['verify'])
def verify(message):
    parts = message.text.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        uid = int(parts[1])
        paid_users[uid] = datetime.now() + timedelta(days=30)
        bot.send_message(uid, "✅ You're now a Premium User for 30 days! Send a PDF to continue.")
        bot.send_message(message.chat.id, "✅ User verified.")
    else:
        bot.reply_to(message, "❌ Invalid. Use: /verify <user_id>")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = len(user_usage)
    paid = len(paid_users)
    msg = f"📊 Bot Usage Stats:\n\n👤 Total Users: {total_users}\n💰 Paid Users: {paid}\n📄 Usage:\n"
    for uid, count in user_usage.items():
        status = "✅" if uid in paid_users else "❌"
        msg += f" - {uid}: {count} file(s) | Paid: {status}\n"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "💰 Buy Premium")
def buy_premium(message):
    bot.send_message(message.chat.id,
        f"💳 To unlock premium access, pay ₹49 to:\n\nUPI ID: `{UPI_ID}`\nThen send /verify {message.from_user.id}",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📄 Help")
def help_text(message):
    bot.send_message(message.chat.id,
        "📚 *How to use this bot:*\n\n1. Send any PDF file\n2. Get a ChatGPT-powered summary\n3. First summary is free\n4. For unlimited use, pay ₹49 and verify",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📬 Contact Admin")
def contact(message):
    bot.send_message(message.chat.id, "📩 Contact: @yourusername (Telegram)")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    user_id = message.from_user.id
    now = datetime.now()
    if user_id in paid_users and paid_users[user_id] < now:
        del paid_users[user_id]
    if user_id not in paid_users and user_usage.get(user_id, 0) >= 1:
        bot.reply_to(message, f"🔒 You’ve used your 1 free summary.\nPay ₹49 to `{UPI_ID}` and send /verify {user_id} to continue.", parse_mode="Markdown")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(downloaded)
        pdf_path = tmp.name

    try:
        text = extract_text(pdf_path)
        if len(text.strip()) < 100:
            bot.send_message(message.chat.id, "❌ Couldn't extract enough text.")
            return

        bot.send_message(message.chat.id, "🧠 Summarizing...")
        summary = summarize_text(text)
        summary_pdf_path = make_summary_pdf(summary, message.from_user.username or str(user_id))
        bot.send_document(message.chat.id, open(summary_pdf_path, 'rb'), caption="✅ Summary PDF")
        bot.send_document(message.chat.id, open(pdf_path, 'rb'), caption="📄 Original File")
        if user_id not in paid_users:
            user_usage[user_id] = user_usage.get(user_id, 0) + 1
        os.remove(summary_pdf_path)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")
    finally:
        os.remove(pdf_path)

def extract_text(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text[:6000]

def summarize_text(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Summarize this in bullet points:\n\n{text}"}],
        temperature=0.5,
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=8080)
