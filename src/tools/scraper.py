from bs4 import BeautifulSoup, Comment

# based on https://github.com/trancethehuman/entities-extraction-web-scraper/blob/main/scrape.py

def remove_tags(html_content, unwanted_tags: list[str], remove_comments: bool = True):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    if remove_comments:
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

    return str(soup)


def extract_tags(html_content, tags: list[str]):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ')


def strip_lines(content):
    lines = content.replace("\xa0", "").split("\n")

    stripped_lines = list(filter(lambda x: x and len(x) >0, map(lambda x: x.strip(), lines)))

    return "\n".join(stripped_lines)


def scrape(html: str, exclude_tags: list[str] = ["script", "style", "cdata", "footer"],
           include_tags: list[str] = ["p", "h1", "h2", "h3", "h4", "h5", "a", "span", "div", "table", "ul", "li", "ol", "pre"]):
    results = remove_tags(html, exclude_tags)
    results = extract_tags(results, include_tags)
    results_formatted = strip_lines(results)

    return results_formatted
