import base64
import json

from playwright.sync_api import sync_playwright

from nav_tools import (click_element, end, go_back, scroll_down, scroll_up,
                       type, type_and_submit)
from utils import get_base_url


class Agent:
    def __init__(self, client):
        self.name = "Bot"
        self.prompt = ""
        self.client = client
        self.starting_url = "https://amazon.com/"
        self.page = None
        self.base64_image = None
        self.base64_image_annotated = None
        self.label_selectors = {}
        self.label_simplified_htmls = {}
        self.iterations = 0
        self.past_commands = ["START"]

    def set_image(self, base64_image):
        self.base64_image = base64_image

    def set_prompt(self, prompt: str):
        self.prompt = prompt

    def encode_images(self, image_path: str):
        with open(image_path + ".png", "rb") as image_file:
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
        
    # get's initial and annotated sreenshots, finds html of all interactable elemtns 
    def get_page_info(self, page, save_path: str):
        print("Annotating", self.page.url, "...")
        page.screenshot(path=save_path + ".png")
        label_selectors, label_simplified_htmls = page.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll("a, button, input, textarea, select"));
            let label_selectors = {{}};
            let label_simplified_htmls = {{}};
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
                    let selector = element.tagName.toLowerCase();
                    let simplified_html = '<' + element.tagName.toLowerCase();
                    for (const attr of ['id', 'class', 'name', 'type', 'value', 'src', 'alt']) {{
                        if (element.hasAttribute(attr)) {{
                            let attrValue = element.getAttribute(attr);
                            if (attr === 'class') {{
                                let classList = attrValue.split(' ');
                                if (classList.length > 3) {{
                                    attrValue = classList.slice(0, 3).join(' ');
                                }}
                            }}
                            if (attr === 'href') {{
                                let parts = attrValue.split('/');
                                if (parts.length > 3) {{
                                    // If the URL starts with http:// or https://, include the first 5 parts (protocol, empty, domain, and two path segments)
                                    // Otherwise, include the first 3 parts (domain and one path segment)
                                    let limit = parts[0].startsWith('http') ? 5 : 3;
                                    attrValue = parts.slice(0, limit).join('/');
                                }}
                            }}
                            simplified_html += ` ${{attr}}="${{attrValue}}"`;
                        }}
                    }}
                    simplified_html = simplified_html + '>' + element.textContent + '</' + element.tagName.toLowerCase() + '>'                              
                    simplified_html = simplified_html.replace(/\s+/g, ' ').trim();                                 
                    for (const attr of element.attributes) {{
                        if (attr.name !== "style" && attr.name !== "class") {{
                            selector += `[${{attr.name}}="${{attr.value}}"]`;
                        }} 
                    }}
                    label_selectors[index] = selector;
                    label_simplified_htmls[index] = simplified_html;
                    element.style.border = "2px solid brown";
                    const label = document.createElement("span");
                    label.className = "autopilot-generated-label";
                    label.textContent = index;
                    label.style.position = "absolute";
                    label.style.lineHeight = "16px";
                    label.style.padding = "1px";
                    label.style.top = (window.scrollY + rect.top) + "px";
                    label.style.left = (window.scrollX + rect.left) + "px"; 
                    label.style.color = "white";
                    label.style.fontWeight = "bold";
                    label.style.fontSize = "16px";
                    label.style.backgroundColor = "brown";
                    label.style.zIndex = 10000;
                    document.body.appendChild(label);
                }}
            }});
            return [label_selectors, label_simplified_htmls];
        }}''')
        page.wait_for_timeout(2000)
        page.screenshot(path=save_path + ".annotated.png")

        self.label_selectors = label_selectors
        self.label_simplified_htmls = label_simplified_htmls

        # Save to JSON file
        with open(f'element_selectors/{self.iterations}.json', 'w') as f:
            json.dump(self.label_selectors, f, indent=4)
        with open(f'element_htmls/{self.iterations}.json', 'w') as f:
            json.dump(self.label_simplified_htmls, f, indent=4)

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
                    "text": f"""
                    BACKGROUND:
                    Your end goal is the following: {self.prompt}

                    You are currently on a specific page of {get_base_url(self.page.url)}, which shown in the image. The image is an annotated version of your current page, with bounding boxes drawn around each element that you can interact with. At the top left of the bounding box is a number that corresponds to the label of the element. If an element doesn't have a bounding box around it, you cannot interact with it. You will also be provided the simplified html of each of these elements.

                    Here are the following actions you can take on a page:
                    - CLICK: click a specific element on the page
                    - SCROLL_DOWN: scroll down on the page
                    - SCROLL_UP: scroll up on the page
                    - TYPE: type text into a text input or textarea
                    - TYPE_AND_SUBMIT: type text into a text input or textarea and press enter
                    - GO_BACK: go back to the previous page
                    - END: declare that you have completed the task
                    

                    TASK:
                    Complete steps 1-8, showing your work for each step. Be detailed in your reasoning and answer all questions. Completing these steps will help you achieve your end goal.

                    TASK STEPS:
                    1. Have you achieved your end goal? 
                        - If not, what is the next step you might need to take to get closer to your end goal? 
                        - If you have achieved your end goal, skip to step 8 and output {{"action": "END"}}.
                    2. Describe the elements you see in the image. Look at the simplified HTML associated with each page to ensure you are correctly interpreting the labeled elements: {self.label_simplified_htmls} Do not infer what else may be on rest of the page. 
                        - What on this image could be helpful in getting closer to the end goal?
                        - What do you predict would happen if you interacted with these elements?
                    3. What might be on the page that is not currently showing but could appear via scrolling? How would these be helpful in getting closer to the end goal?
                    4. Which of the elements you described in step 1 or 2 would be the best to interact with to help you achieve your goal? Is this element currently labeled and visible on the page?
                    5. Based on the elements you described in step 3, determine whether to scroll or not.
                    6. If you need to scroll, determine whether to scroll up or down. 
                    7. If you don't need to scroll, visually describe the element you will interact with to help you achieve your goal. Then, identify the label number of this element in the image. What action will you take on this element?
                    8. Output your final action on the current page. Begin your response with "RESPONSE: ".
                        - If you are scrolling or going back, output a JSON command in the following format: {{"action": ACTION}}
                        - If you are clicking, output a JSON command in the following format: {{"action": ACTION, "label": LABEL_NUMBER}}
                        - If you are typing, output a JSON command in the following format: {{"action": ACTION, "label": LABEL_NUMBER, "value": "TEXT_TO_TYPE"}}

                    REMEMBER:
                    Complete all the steps 1-8, showing your work for each step.
                    """
                },
                # {
                #     "type": "image_url",
                #     "image_url": {
                #         "url": f"data:image/jpeg;base64,{self.base64_image}",
                #         "detail": "high"
                #     },
                # },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{self.base64_image_annotated}",
                        "detail": "high"
                    },
                },
            ],
            }
        ],
        max_tokens=4096,
        temperature=0.0,
        )

        responseData = response.choices[0].message.content
        print("CoT:", responseData)
        responseData = responseData.split("RESPONSE:")[-1]
        if responseData[0] != "{":
            responseData = responseData[responseData.index("{"):responseData.rindex("}")+1]
        return json.loads(responseData)

    # can use match case if python3.10
    def select_action(self, command: str, label: int, value:str):
        if label: 
            label = str(label)
            label = self.label_selectors[label]

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
            print("Error: could not perform action. Error details:", str(e) + ". Trying again.")

    def update_commands_and_narrate(self, response):
        command, label, value = response["action"], str(response.get("label", "")), str(response.get("value", ""))
        action_details = "taking action with command: " + command
        if label:
            action_details += ", label: " + label
        if value:
            action_details += ", value: " + value

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
                screenshot_path = f'screenshots/{self.iterations}'
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