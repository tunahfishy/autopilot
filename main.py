from agent import Agent
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os 
from openai import OpenAI

load_dotenv()
    # 2. TYPE_AND_SUBMIT - type text into an input and press enter
    # 3. SCROLL_UP - 
    # 4. SCROLL_DOWN
    # 5. GO_BACK
    # 6. END
    # You will reason about what actions to perform first, and only return the name of the first action that you want to do. 


if __name__ == "__main__":
    user_prompt = input("Please enter a prompt: ")
    agent = Agent(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    agent.complete_task(user_prompt)

   

