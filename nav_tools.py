def scroll_up(page):
    page.evaluate(
        "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop - (window.innerHeight * 0.75);"
    )

def scroll_down(page):
    page.evaluate(
        "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop + (window.innerHeight * 0.75);"
    )

def click_element(page, selector):
    page.eval_on_selector(selector, 'element => element.style.border = "3px solid red"')
    page.click(selector)

def type(page, selector, text):
    page.fill(selector, text)

def type_and_submit(page, selector, text):
    page.fill(selector, text)
    page.press(selector, 'Enter')

def go_back(page):
    page.go_back()