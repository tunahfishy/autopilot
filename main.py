from openai import OpenAI
import base64
from playwright.sync_api import sync_playwright

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

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def make_vision_gpt_call(client, base64_image):
    response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": "What’s in this image?"},
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
    client = OpenAI(api_key="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")

    take_screenshot("https://google.com")
    base64_image = encode_image("screenshot.png")

    make_vision_gpt_call(client, base64_image)
