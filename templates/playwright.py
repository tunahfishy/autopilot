ANNOTATE_PAGE_TEMPLATE = f'''() => {{
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
            for (const attr of ['aria-label', 'alt', 'placeholder', 'value']) {{
                if (element.hasAttribute(attr)) {{
                    let attrValue = element.getAttribute(attr);
                    simplified_html += ` ${{attr}}="${{attrValue}}"`;
                }}
            }}
            const textContent = element.textContent.replace(/\\\\n/g, ' ')
            simplified_html = simplified_html + '>' + textContent + '</' + element.tagName.toLowerCase() + '>'                              
            simplified_html = simplified_html.replace(/\s+/g, ' ').trim();                                 
            for (const attr of element.attributes) {{
                if (attr.name !== "style" && attr.name !== "class") {{
                    if (!attr.value.includes('"') && !attr.value.includes(';')) {{
                        selector += `[${{attr.name}}="${{attr.value}}"]`;
                    }}
                }} 
            }}
            label_selectors[index] = selector;
            label_simplified_htmls[index] = simplified_html;
            const rect = element.getBoundingClientRect();
            const newElement = document.createElement('div');
            newElement.className = 'autopilot-generated-rect';
            newElement.style.border = '2px solid brown';
            newElement.style.position = 'absolute';
            newElement.style.top = `${{rect.top}}px`;
            newElement.style.left = `${{rect.left}}px`;
            newElement.style.width = `${{rect.width}}px`;
            newElement.style.height = `${{rect.height}}px`;
            newElement.style.zIndex = 10000;  // Ensure the new element is on top
            newElement.style.pointerEvents = 'none';  // Make the new element unclickable so it doesn't interfere with interactions
            document.body.appendChild(newElement);
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
}}'''


CLEAR_PAGE_TEMPLATE = f'''() => {{
    const removeElementsByClass = (className) => {{
        const elements = Array.from(document.querySelectorAll(className));
        elements.forEach((element, index) => {{
            element.remove();
        }});
    }};
    removeElementsByClass(".autopilot-generated-rect");
    removeElementsByClass(".autopilot-generated-label");
}}'''