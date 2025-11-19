from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

print(f"API Key : {os.getenv('OPENAI_API_KEY')}")