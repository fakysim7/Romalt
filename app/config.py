import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AI21_API_KEY = os.getenv("AI21_API_KEY")

# URL AI21 API (Jurassic-2, Jamba и т.д.)
AI21_URL = "https://api.ai21.com/studio/v1/jamba-instruct"

