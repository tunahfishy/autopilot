def scroll_up(page):
    page.evaluate(
        "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop - (window.innerHeight * 0.75);"
    )
    page.wait_for_timeout(2000)

def scroll_down(page):
    page.evaluate(
        "(document.scrollingElement || document.body).scrollTop = (document.scrollingElement || document.body).scrollTop + (window.innerHeight * 0.75);"
    )
    page.wait_for_timeout(2000)

def click_element(page, selector):
    page.eval_on_selector(selector, 'element => element.style.border = "3px solid red"')
    page.click(selector)
    page.wait_for_timeout(2000)

def type(page, selector, text):
    page.fill(selector, text)
    page.wait_for_timeout(2000)

def type_and_submit(page, selector, text):
    page.fill(selector, text)
    page.press(selector, 'Enter')
    page.wait_for_timeout(2000)

def go_back(page):
    page.go_back()
    page.wait_for_timeout(2000)

def end(page):
    # Celebrate with a confetti animation before closing the page
    page.evaluate("""
        let confettiElement = document.createElement('div');
        confettiElement.innerHTML = '<div class="confetti"></div>';
        document.body.appendChild(confettiElement);
        setTimeout(() => {
            document.body.removeChild(confettiElement);
        }, 2000);
    """)
    page.wait_for_timeout(2000)
    page.close()