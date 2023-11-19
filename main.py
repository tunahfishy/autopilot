from openai import OpenAI
import base64
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os 
from nav_tools import scroll_up, scroll_down, click_element, type, type_and_submit
import json

load_dotenv()

def get_page_info(url, save_path='screenshot.png'):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        element_info = page.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll("a, button, input"));
            let result = {{}};
            elements.forEach((element, index) => {{
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                const isVisible = element.offsetWidth > 0 && element.offsetHeight > 0 && style.visibility !== 'hidden' && style.opacity !== '0' && style.display !== 'none';

                const inViewport = (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );

                if (inViewport && isVisible) {{
                    let selector = element.tagName.toLowerCase();
                    for (const attr of element.attributes) {{
                        if (attr.name !== "style") {{
                            selector += `[${{attr.name}}="${{attr.value}}"]`;
                        }} 
                    }}
                    result[index] = selector;
                    element.style.border = "1px solid red";
                    const label = document.createElement("span");
                    label.textContent = index;
                    label.style.position = "absolute";
                    label.style.top = rect.top + "px";
                    label.style.left = rect.left + "px";
                    label.style.color = "red";
                    label.style.zIndex = 10000;
                    document.body.appendChild(label);
                }}
            }});
            return result;
        }}''')
        page.screenshot(path=save_path)

        page.wait_for_timeout(3000)
 
        # element_parents = [element.evaluate('node => node.parentElement.outerHTML') for element in elements]
        browser.close()
        return element_info
    

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

                # 2. TYPE_AND_SUBMIT - type text into an input and press enter
                # 3. SCROLL_UP - 
                # 4. SCROLL_DOWN
                # 5. GO_BACK
                # 6. END
                # You will reason about what actions to perform first, and only return the name of the first action that you want to do. 

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

                1. CLICK_X - click on a link, button, or input that has the label X

                Based on the following task, return only a json of the format {{"id": number}} with the number label of the element in the page that you want to click on first. Do not return anything beyond JSON. any deviation will cause the system to fail.
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

    responseData = response.choices[0].message.content
    print(responseData)
    if responseData!= "{":
        responseData = responseData[responseData.index("{"):responseData.rindex("}")+1]
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_prompt = input("Please enter a prompt: ")
    # sample prompt: Help me buy a pair of women's medium gray sweatpants

    elements = get_page_info("https://amazon.com/")
    print(len(elements), json.dumps(elements, indent=4))
    # print(elements["4"])
    base64_image = encode_image("screenshot.png")

    response = get_gpt_action(client, base64_image, user_prompt)
    selector_id = response["id"]
    selector = elements[str(selector_id)]
    print(selector_id, selector)

    with sync_playwright() as playwright:
        chromium = playwright.chromium
        browser = chromium.launch(headless=False) # Set headless to False to visualize the actions
        page = browser.new_page()
        page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
        page.goto("https://www.amazon.com/")

        page.wait_for_timeout(2000)
        click_element(page, selector)
        page.wait_for_timeout(20000)
        page.close()


