from nav_tools import scroll_up, scroll_down, click_element, type, type_and_submit
from playwright.sync_api import sync_playwright
import json
import base64

class Agent:
    def __init__(self, client):
        self.name = "Bot"
        self.prompt = ""
        self.client = client
        self.url = "https://amazon.com/"
        self.base64_image = None
        self.elements = {}

    def set_image(self, base64_image):
        self.base64_image = base64_image

    def set_prompt(self, prompt):
        self.prompt = prompt

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            image = base64.b64encode(image_file.read()).decode('utf-8')
            self.base64_image = image
            return image 
        
    def get_page_info(self, save_path='screenshot.png'):
        print("Annotating", self.url, "...")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(self.url)

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
    
            browser.close()
            self.elements = element_info
            return element_info

    def get_gpt_action(self):
        print("Generating action...")
        response = self.client.chat.completions.create(
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
                    Here is your task: {self.prompt}
                    """
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{self.base64_image}",
                    "detail": "auto"
                },
                },
            ],
            }
        ],
        max_tokens=300,
        )

        responseData = response.choices[0].message.content
        if responseData!= "{":
            responseData = responseData[responseData.index("{"):responseData.rindex("}")+1]
        print(responseData)
        return json.loads(response.choices[0].message.content)

    def select_action(self, actions):
        # Select an action from the list of actions
        pass

    # click for now
    def perform_action(self, action, selector):
        print("Performing action...", action)
        with sync_playwright() as playwright:
            chromium = playwright.chromium
            browser = chromium.launch(headless=False)
            page = browser.new_page()
            page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
            page.goto("https://www.amazon.com/")

            page.wait_for_timeout(2000)
            try: 
                click_element(page, selector)
            except:
                print("Error: could not click element")
            page.wait_for_timeout(5000)
            page.close()


    def complete_task(self, prompt):
        self.set_prompt(prompt)
        self.get_page_info()
        self.encode_image("screenshot.png")
        response = self.get_gpt_action()
        selector_id = response["id"]
        selector = self.elements[str(selector_id)]
        print(selector_id, selector)
        self.perform_action(response, selector)


        