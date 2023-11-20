from agent import Agent
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os 
from openai import OpenAI

load_dotenv()

if __name__ == "__main__":
    user_prompt = input("Please enter a prompt: ")
    # sample prompt: Help me buy an apple
    agent = Agent(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    agent.complete_task(user_prompt)

   

