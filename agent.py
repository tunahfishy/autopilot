from nav_tools import scroll_up, scroll_down, click_element, type, type_and_submit, go_back, end
from playwright.sync_api import sync_playwright
import json
import base64

class Agent:
    def __init__(self, client):
        self.name = "Bot"
        self.prompt = ""
        self.client = client
        self.starting_url = "https://amazon.com/"
        self.page = None
        self.base64_image = None
        self.base64_image_annotated = None
        self.elements = {}
        self.iterations = 0
        self.past_commands = ["START"]

    def set_image(self, base64_image):
        self.base64_image = base64_image

    def set_prompt(self, prompt: str):
        self.prompt = prompt

    def encode_images(self, image_path: str):
        with open(image_path, "rb") as image_file:
            image = base64.b64encode(image_file.read()).decode('utf-8')
            self.base64_image = image
        with open(image_path + ".annotated.png", "rb") as image_file:
            annotated_image = base64.b64encode(image_file.read()).decode('utf-8')
            self.base64_image_annotated = annotated_image
        
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
        page.wait_for_timeout(2000)
        
    def get_page_info(self, page, save_path: str):
        print("Annotating", self.page.url, "...")
        page.screenshot(path=save_path)
        element_info = page.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll("a, button, input"));
            let result = {{}};
            function isHiddenByAncestors(element) {{
                while (element) {{
                    const style = window.getComputedStyle(element);
                    if (style.display === 'none' || style.visibility === 'hidden') {{
                        return true;
                    }}
                    element = element.parentElement;
                }}
                return false;
            }}
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

                if (inViewport && isVisible && !isHiddenByAncestors(element)) {{
                    let label = element.tagName.toLowerCase();
                    for (const attr of element.attributes) {{
                        if (attr.name !== "style" && attr.name !== "class") {{
                            label += `[${{attr.name}}="${{attr.value}}"]`;
                        }} 
                    }}
                    result[index] = label;
                    element.style.border = "1px solid blue";
                    const label = document.createElement("span");
                    label.className = "autopilot-generated-label";
                    label.textContent = index;
                    label.style.position = "absolute";
                    label.style.padding = "1px";
                    label.style.top = (window.scrollY + rect.top) + "px";
                    label.style.left = (window.scrollX + rect.left) + "px"; 
                    label.style.color = "white";
                    label.style.fontWeight = "bold";
                    label.style.backgroundColor = "blue";
                    label.style.zIndex = 10000;
                    document.body.appendChild(label);
                }}
            }});
            return result;
        }}''')
        page.wait_for_timeout(2000)
        page.screenshot(path=save_path + ".annotated.png")

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
                    "text": f"""You are an intelligent agent controlling a browser with the following end goal: {self.prompt}.
                    You are on the page shown in these images. The first image is the page and the second is an annotated version that will help you select elements on the page. You will be provided with a task that will require you to interact with the browser and navigate to different pages. 
                    For each step, you will first try to understand the current page that you are on. What on this page might be able to help you achieve the end goal? Are there any helpful elements that should be on this page but might only be visible if you scroll? Which of the seven actions you can take to help you achieve this goal? and which element will help you perform this immediate action? You will then return this output in the format of one of the following JSON commands:

                    1. {{"action": "CLICK", "goal": "This image of an apple will allow me to navigate to its purchase page", "label": "label number to click"}} - click on a link, button, or input that has the associated blue label number in the image
                    2. {{"action": "TYPE", "goal": "I must type my username in this input to login to put the apple in the cart", "label": "label number to click", "value": "apple"}} - type text 'apple' into an input that has the associated blue label number. Use this only if you don't want to submit right after typing.
                    3. {{"action": "TYPE_AND_SUBMIT", "goal": "typing 'apple' into the searchbar will allow me to find the apple selection", "label": "label number to click", value: "apple"}} - type text 'apple' into an input with the associated blue label number and press enter
                    4. {{"action": "GO_BACK", "goal": "I've clicked the same button multiple times and it looks like this page doesn't have what I'm looking for. I should backtrack"}} - go back to the previous page
                    5. {{"action": "SCROLL_DOWN", "goal": "I'm on the apple product page but I don't see the checkout button, I assume it is further down the page."}} - scroll down the 3/4ths of the page
                    6. {{"action": "SCROLL_UP", "goal": "I have scrolled down but now must press the cart button at the top of the page"}} - scroll up the 3/4ths of the page
                    7. {{"action": "END", "goal": "I have succesfully added the apple to the cart and enteblue payment information"}} - indicate you've successfully completed the task

                    Based on the following task, return ONLY THE JSON in the exact provided format above. Do not return anything beyond JSON. Do not return an action that is not "CLICK", "TYPE", "TYPE_AND_SUBMIT", "GO_BACK", "SCROLL_UP", "SCROLL_DOWN", or "END". Any deviation will cause the system to fail.

                    For guidance, here is the history of your past goals for the actions you have already tried. This should prevent you from repeating actions that don't work: {self.past_commands}
                    """
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{self.base64_image}",
                        "detail": "auto"
                    },
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{self.base64_image_annotated}",
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
        return json.loads(responseData)

    # can use match case if python3.10
    def select_action(self, command: str, label: str, value:str):
        if label: 
            label = self.elements[label]

        if command == "CLICK":
            print("Clicking on element with label", label)
            return click_element(self.page, label)
        elif command == "TYPE":
            print("Typing...", value, label)
            return type(self.page, label, value)
        elif command == "TYPE_AND_SUBMIT":
            print("Typing and submitting...", value, label)
            return type_and_submit(self.page, label, value)
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

    def perform_action(self, action: str, label: str, value: str):
        try: 
            self.select_action(action, label, value)
        except Exception as e:
            print("Error: could not perform action. Error details:", str(e), ". Trying again.")

    def update_commands_and_narrate(self, response):
        command, label, value, goal = response["action"], response.get("label", ""), str(response.get("value", "")), response.get("goal", "")
        action_details = "taking action with command: " + command
        if label:
            action_details += ", label: " + label
        if value:
            action_details += ", value: " + value
        action_details += ", and goal: " + goal

        self.past_commands.append(action_details)
        print(action_details)
        return command, label, value

    def complete_task(self, prompt: str):
        self.set_prompt(prompt)
        # sample prompt: Help me buy an apple fruit
        with sync_playwright() as playwright:
            chromium = playwright.chromium
            browser = chromium.launch(headless=False)
            page = browser.new_page()
            page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
            page.goto(self.starting_url)
            self.page = page

            while True:
                print("🤖", self.name, "is on iteration", self.iterations)
                screenshot_path = f'screenshots/{self.iterations}.png'
                self.get_page_info(page, screenshot_path)
                self.encode_images(screenshot_path)
                response = self.get_gpt_command()
                command, label, value = self.update_commands_and_narrate(response)
                self.clear_page_info(page)
                self.perform_action(command, label, value)
                if command == "END":
                    print("Task completed after", self.iterations, "iterations!")
                    break
                self.iterations += 1
                print()       