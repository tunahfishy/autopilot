from agent import Agent
from dotenv import load_dotenv
import os 
import glob
from openai import OpenAI

load_dotenv()

if __name__ == "__main__":
    user_prompt = input("Please enter a prompt: ")
    # sample prompt: Help me buy an apple fruit

    # clear the elements and screenshots folders
    fileList = glob.glob('./elements/*')
    fileList += glob.glob('./screenshots/*')
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)

    agent = Agent(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
    try: 
        agent.complete_task(user_prompt)
    except KeyboardInterrupt:
        print("Keyboard Interrupt, exiting gracefully...")
        # agent.close()

 

