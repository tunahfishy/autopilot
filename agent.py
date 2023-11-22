import base64
import json
import time
import re
import openai
from templates.playwright import ANNOTATE_PAGE_TEMPLATE, CLEAR_PAGE_TEMPLATE
from playwright.sync_api import sync_playwright

from nav_tools import (click_element, end, go_back, scroll_down, scroll_up,
                       type, type_and_submit)
from utils import get_base_url


class Agent:
    def __init__(self, client):
        self.name = "Bot"
        self.prompt = ""
        self.client = client
        self.starting_url = "https://www.amazon.com/Apple-2023-MacBook-Laptop-chip/dp/B0C75ZRQLB/ref=sr_1_3?crid=2N4KGFW2ATRK0&keywords=macbook&qid=1700628543&sprefix=macbook%2Caps%2C122&sr=8-3"
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
        page.evaluate(CLEAR_PAGE_TEMPLATE)
        page.wait_for_timeout(2000)
        
    # get's initial and annotated sreenshots, finds html of all interactable elemtns 
    def get_page_info(self, page, save_path: str):
        print("Annotating", self.page.url, "...")
        page.screenshot(path=save_path + ".png")
        label_selectors, label_simplified_htmls = page.evaluate(ANNOTATE_PAGE_TEMPLATE)
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
        for _ in range(3):
            try:
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

                            You are currently on a specific page of {get_base_url(self.page.url)}, which shown in the image. The image is an annotated version of your current page, with bounding boxes drawn around each element that you can interact with. At the top left of the bounding box is a number that corresponds to the label of the element. If an element doesn't have a bounding box around it, you cannot interact with it. Each label is associated with the simplified html of the element.

                            Here are the following actions you can take on a page:
                            - CLICK: click a specific element on the page
                            - SCROLL_DOWN: scroll down on the page
                            - SCROLL_UP: scroll up on the page
                            - TYPE: type text into a text input or textarea
                            - TYPE_AND_SUBMIT: type text into a text input or textarea and press enter
                            - GO_BACK: go back to the previous page
                            - END: declare that you have completed the task
                            

                            TASK:
                            Complete steps 1-7, showing your work for each step. Be detailed in your reasoning and answer all questions. Completing these steps will help you achieve your end goal.

                            TASK STEPS:
                            1. Have you achieved your end goal? 
                                - If not, what is the next step you might need to take to get closer to your end goal? 
                                - If you have achieved your end goal, skip to step 6 and output {{"action": "END"}}.
                            2. Look at the mapping of each label value to its simplified HTML. Using the HTML and its associated labeled area on the image to help understand what it does: {self.label_simplified_htmls}. Do not infer what else may be on rest of the page. 
                                - What on this image could be helpful in getting closer to the end goal?
                                - What do you predict would happen if you interacted with these elements?
                            3. Based on prior knowledge of websites with this structure and function, what might be on the page that is not currently showing but could appear via scrolling? For example, maybe pricing is found in a footer or a 'buy now' button may be lower down the page. How would these be helpful in getting closer to the end goal?
                            4. Which of the elements you described in step 1 or 2 would be the best to interact with to help you achieve your goal? Based on this, determine whether to scroll up, down, or not.
                            5. Is this action similar to one that you took in the past? If so, are you further along now than you were when you did the previous action? Would taking this action again be helpful in getting closer to the end goal? If it wouldn't, try not to take it. Here was the thought process for the last action that you succesfully took. Remember that the label numbers may be different than the last step: {self.past_commands[-1]}
                            6. If you don't need to scroll, visually describe the element you will interact with to help you achieve your goal. Then, identify the label number of this element in the image. What action will you take on this element?
                            7. Output your final action on the current page. Begin your response with "RESPONSE: ".
                                - If you are scrolling or going back, output a JSON command in the following format: {{"action": ACTION}}
                                - If you are clicking, output a JSON command in the following format: {{"action": ACTION, "label": LABEL_NUMBER}}
                                - If you are typing, output a JSON command in the following format: {{"action": ACTION, "label": LABEL_NUMBER, "value": "TEXT_TO_TYPE"}}

                            REMEMBER:
                            Complete all the steps 1-7, showing your work for each step.
                            """
                        },
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
                break  # If the request was successful, break the loop
            except openai.RateLimitError:
                print("Rate limit exceeded. Waiting 60 seconds before retrying.")
                time.sleep(60)
        else:
            raise Exception("Rate limit exceeded. Please try again later.")
            
        responseData = response.choices[0].message.content
        print("CoT:", responseData)
        responseData = responseData.split("RESPONSE:")
        self.update_last_command(responseData[0])
        answer = responseData[-1]
        if answer[0] != "{":
            answer = answer[answer.index("{"):answer.rindex("}")+1]
        return json.loads(answer)

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

    def update_last_command(self, response):
        pattern = r"6\.[^.]*\.(?: Then, identify the label number of this element in the image.)?(?: What action will you take on this element\?)? (.*?)7\."
        match = re.search(pattern, response, re.DOTALL)        
        # If a match is found, the matched text is in group 1
        if match:
            item_6_text = match.group(1).strip().strip()
            item_6_text = item_6_text.replace('\n', ' ')
        else:
            item_6_text = "No match found"
        print()
        print("PAST COMMAND GIVEN:", item_6_text)
        self.past_commands.append(item_6_text)

    def update_history_and_narrate(self, response):
        command, label, value = response["action"], str(response.get("label", "")), str(response.get("value", ""))
        action_details = "taking action with command: " + command
        if label:
            action_details += ", label: " + label
        if value:
            action_details += ", value: " + value

        if self.past_commands[-1] == "No match found":
            self.past_commands[-1] = action_details
        print(action_details)
        return command, label, value

    def complete_task(self, prompt: str):
        self.set_prompt(prompt)
        # sample prompt: Buy a Macbook Pro
        with sync_playwright() as playwright:
            chromium = playwright.chromium
            browser = chromium.launch(headless=False)
            context = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
            page = context.new_page()
            page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
            page.goto(self.starting_url)
            self.page = page

            while True:
                print("🤖", self.name, "is on iteration", self.iterations)
                screenshot_path = f'screenshots/{self.iterations}'
                self.get_page_info(page, screenshot_path)
                self.encode_images(screenshot_path)
                response = self.get_gpt_command()
                command, label, value = self.update_history_and_narrate(response)
                self.clear_page_info(page)
                self.perform_action(command, label, value)
                if command == "END":
                    print("Task completed after", self.iterations, "iterations!")
                    break
                self.iterations += 1
                print()    