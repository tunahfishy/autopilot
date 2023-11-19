from openai import OpenAI
import base64
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os 

load_dotenv()

def take_screenshot(url, save_path='screenshot.png'):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        page.screenshot(path=save_path)
        elements = page.query_selector_all("a, button, input")
        element_info = [(element.get_attribute("tagName"), element.get_attribute("value") if element.get_attribute("tagName") and element.get_attribute("tagName").lower() == "input" else element.inner_text()) for element in elements]
        
        browser.close()
        return element_info
    
def get_dom(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        
        body_html = page.evaluate('() => document.body.innerHTML')
        browser.close()
        return body_html

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_gpt_action(client, base64_image, prompt):
    response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
        "role": "user",
        "content": [
            {
                "type": "text", 
                "text": f"""You are an agent controlling a browser. 
                You are on the page shown in this image. You will be provided with a task that will require you to interact with the browser and navigate to different pages. 
                For each step, you will think about which actions you should preform to complete the task. You have the following actions available to you:

                1. Click on a link
                2. Click on a button
                3. Enter text into a text field
                ... etc

                You will reason about what actions to perform first, and only return the name of the first action that you want to do.
                Here is your task: {prompt}
                """
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "auto"
            },
            },
        ],
        }
    ],
    max_tokens=300,
    )

    print(response.choices[0])
    return response.choices[0]


if __name__ == "__main__":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_prompt = input("Please enter a prompt: ")


    take_screenshot("https://www.amazon.com/")
    base64_image = encode_image("screenshot.png")

    get_gpt_action(client, base64_image, user_prompt)
