# Telegram PDF Summarizer Bot

Upload a PDF to the Telegram bot and get an AI-generated summary (1 free use, ₹49 for 30-day premium).

## Features
- 1 free PDF summary per user
- ₹49 UPI payment unlocks 30-day premium
- Summarizes PDF using OpenAI ChatGPT
- Sends downloadable summary PDF + original file
- QR code for payment and admin tools

## Setup

1. Clone this repo
2. Add your `.env` file with:
    - `TELEGRAM_BOT_TOKEN`
    - `OPENAI_API_KEY`
    - `UPI_ID`
    - `ADMIN_ID`
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Run the bot:
```bash
python main.py
```
