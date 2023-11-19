from openai import OpenAI
import base64
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os 
from nav_tools import scroll_up, scroll_down, click_element, type, type_and_submit

load_dotenv()

def get_page_info(url, save_path='screenshot.png'):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # page.screenshot(path=save_path)
        # elements = ['button', 'a', 'input', 'select', 'textarea', 'div[onclick]', 'span[onclick]']; 

        element_info = page.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll("a, button, input"));
            return elements.map((element, index) => {{
                const rect = element.getBoundingClientRect();
                const isVisible = element.offsetWidth > 0 && element.offsetHeight > 0;

                const inViewport = (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );

                if (inViewport && isVisible) {{
                    element.style.border = "1px solid red";

                    const label = document.createElement("span");
                    label.textContent = index + 1;
                    label.style.position = "absolute";
                    label.style.top = rect.top + "px";
                    label.style.left = rect.left + "px";
                    label.style.color = "red";
                    label.style.zIndex = 10000;
                    document.body.appendChild(label);
                }}

                let attributes = {{}};
                for (let attr of element.attributes) {{
                    attributes[attr.name] = attr.value;
                }}
                return {{tagName: element.tagName, attributes: attributes}};
            }});
        }}''')
        page.screenshot(path=save_path)

        page.wait_for_timeout(5000)
 
        # element_parents = [element.evaluate('node => node.parentElement.outerHTML') for element in elements]
        browser.close()
        return element_info
    

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_gpt_action(client, base64_image, prompt, elements):
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

                1. CLICK_ATTRIBUTE_X - click on a link, button, or input with the attribute key "ATTRIBUTE" and the value "X"
                2. TYPE_AND_SUBMIT - type text into an input and press enter
                3. SCROLL_UP - 
                4. SCROLL_DOWN
                5. GO_BACK
                6. END

                You are given the following elements on the page: {elements}
                # You will reason about what actions to perform first, and only return the name of the first action that you want to do. 
                Based on these, return the dictionary of the element that you want to click on first.
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
    # user_prompt = input("Please enter a prompt: ")

    elements = get_page_info("https://amazon.com/")
    # print(len(elements))

    import json
    print(len(elements), json.dumps(elements, indent=4))
    # base64_image = encode_image("screenshot.png")

    # get_gpt_action(client, base64_image, user_prompt, elements)

