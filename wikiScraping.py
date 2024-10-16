import tiktoken
import wikipediaapi as wkapi

class scrapWiki():
    def __init__(self, lang='ko'):
        self.wiki = wkapi.Wikipedia(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                               "(KHTML, like Gecko) Chrome/118.0.0.0 Whale/3.23.214.10 Safari/537.36"
                       , language=lang)

    def get_page(self, keyword):
        page = self.wiki.page(keyword)

        return page

if __name__ == "__main__":
    wiki = scrapWiki()
    page = wiki.get_page('2차전지산업')
    print(page.text)
    print(page.summary)
    print(page.fullurl)
    print(page.exists())