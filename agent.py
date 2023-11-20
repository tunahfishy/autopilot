from nav_tools import scroll_up, scroll_down, click_element, type, type_and_submit, go_back, end
from playwright.sync_api import sync_playwright
import json
import base64

class Agent:
    def __init__(self, client):
        self.name = "Bot"
        self.prompt = ""
        self.client = client
        self.url = "https://amazon.com/"
        self.page = None
        self.base64_image = None
        self.elements = {}
        self.iterations = 0
        self.past_commands = ["START"]

    def set_image(self, base64_image):
        self.base64_image = base64_image

    def set_prompt(self, prompt: str):
        self.prompt = prompt

    def encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            image = base64.b64encode(image_file.read()).decode('utf-8')
            self.base64_image = image
            return image 
        
    def clear_page_info(self, page):
        print("Clearing page info...")
        page.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll("a, button, input"));
            elements.forEach((element, index) => {{
                element.style.border = "none";
            }});
            const labels = Array.from(document.querySelectorAll(".autopilot-generated-label"));
            labels.forEach((label, index) => {{
                label.remove();
            }});
        }}''')
        
    def get_page_info(self, page, save_path: str):
        print("Annotating", self.url, "...")
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
                    label.className = "autopilot-generated-label";
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
        page.wait_for_timeout(2000)
        page.screenshot(path=save_path)

        self.elements = element_info
        
        # Save to JSON file
        with open(f'elements/{self.iterations}.json', 'w') as f:
            json.dump(self.elements, f, indent=4)
            
        return element_info

    def get_gpt_command(self):
        print("Generating command...")
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
                    For each step, you will think about which actions you should preform to complete the task. You will give a short rationalization for the immediate action to perform. You will then return one of the following JSON commands:

                    1. {{"action": "CLICK", "selector": "label number to click", "rationale": "this button will allow me to navigate to the apple product page"}} - click on a link, button, or input that has the associated red label number
                    2. {{"action": "TYPE", "selector": "label number to click", "value": "apple", "rationale": "i must type my username in this input to login to put the apple in the cart"}} - type text 'apple' into an input that has the associated red label number. Use this only if you don't want to submit right after typing.
                    3. {{"action": "TYPE_AND_SUBMIT", "selector": "label number to click", value: "apple", "rationale": "typing 'apple' into the searchbar will allow me to find the apple selection"}} - type text 'apple' into an input with the associated red label number and press enter
                    4. {{"action": "GO_BACK", value: "", "rationale": "it looks like this page doesn't have what I'm looking for. I should backtrack"}} - go back to the previous page
                    5. {{"action": "SCROLL_UP", "rationale": "I see an apple near the bottom of the page but can't select it yet"}} - scroll down the 3/4ths of the page
                    6. {{"action": "SCROLL_DOWN", "rationale": "I have scrolled down but now must press the cart button at the top of the page"}} - scroll up the 3/4ths of the page
                    7. {{"action": "END", "value": "", "rationale": "I have succesfully added the apple to the cart and entered payment information"}} - indicate you've successfully completed the task

                    Based on the following task, return ONLY THE JSON in the exact provided format above. Do not return anything beyond JSON. Do not return an action that is not "CLICK", "TYPE", "TYPE_AND_SUBMIT", "GO_BACK", "SCROLL_UP", "SCROLL_DOWN", or "END". Any deviation will cause the system to fail.

                    Here is your task: {self.prompt}

                    Here is the history of your past rationale for the actions you have already tried: {self.past_commands}
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
        if responseData[0] != "{":
            responseData = responseData[responseData.index("{"):responseData.rindex("}")+1]
        print("returned", responseData)
        return json.loads(responseData)

    # can use match case if python3.10
    def select_action(self, command: str, selector: str, value:str):
        if selector: 
            print("Selector key:", selector)
            selector = self.elements[selector]
            print("Selector:", selector)

        if command == "CLICK":
            print("Clicking on element with selector", selector)
            return click_element(self.page, selector)
        elif command == "TYPE":
            print("Typing...", value, selector)
            return type(self.page, selector, value)
        elif command == "TYPE_AND_SUBMIT":
            print("Typing and submitting...", value, selector)
            return type_and_submit(self.page, selector, value)
        elif command == "GO_BACK":
            print("Going back...")
            return go_back(self.page)
        elif command == "SCROLL_UP":
            print("Scrolling up...")
            return scroll_up(self.page)
        elif command == "SCROLL_DOWN":
            print("Scrolling down...")
            return scroll_down(self.page)
        elif command == "END":
            print("Ending task...")
            return end(self.page)
        else:
            print("Invalid command")
            return None

    # click for now
    def perform_action(self, action: str, selector: str, value: str):
        print("Performing action...", action)
        try: 
            self.select_action(action, selector, value)
        except Exception as e:
            print("Error: could not perform action. Error details:", str(e))


    def complete_task(self, prompt: str):
        self.set_prompt(prompt)
        # sample prompt: Help me buy an apple fruit
        with sync_playwright() as playwright:
            chromium = playwright.chromium
            browser = chromium.launch(headless=False)
            page = browser.new_page()
            page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
            page.goto(self.url)
            self.page = page

            while True:
                print(self.name, "is on iteration", self.iterations)
                screenshot_path = f'screenshots/{self.iterations}.png'
                self.get_page_info(page, screenshot_path)
                self.encode_image(screenshot_path)
                response = self.get_gpt_command()
                command, selector, value, rationale = response["action"], response.get("selector", ""), str(response.get("value", "")), response.get("rationale", "")
                self.past_commands.append("command: " + command + ", selector: " + selector + ", value: " + value + ", rationale: " + rationale)
                print("taking action with command:", command + ", selector:", selector + ", and value:", value + ", rationale:", rationale)
                self.clear_page_info(page)
                self.perform_action(command, selector, value)
                if command == "END":
                    print("Task completed after", self.iterations, "iterations!")
                    break
                self.iterations += 1
                print()


        