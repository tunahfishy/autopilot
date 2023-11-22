from agent import Agent
from dotenv import load_dotenv
import os 
import glob
from openai import OpenAI

load_dotenv()

def clear_files():
    fileList = glob.glob('./element_htmls/*')
    fileList += glob.glob('./element_selectors/*')
    fileList += glob.glob('./screenshots/*')
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)


if __name__ == "__main__":
    user_prompt = input("🤖 Bot: What would you like me to do? ")
    print()

    # clear the elements and screenshots folders
    clear_files()

    agent = Agent(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    
    try: 
        agent.complete_task(user_prompt)
    except KeyboardInterrupt:
        print()
        print("Keyboard Interrupt, exiting gracefully...")

 

