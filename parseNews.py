from pygooglenews import GoogleNews


class GoogleParser:
    def __init__(self, lang = 'en', country = 'US'):
        self.lang = lang.lower()
        self.country = country.upper()
        self.gn = GoogleNews(lang=self.lang, country=self.country)

    def parse(self, keyword, when='180d'):
        if self.lang == 'ko':
            query = f'{keyword} 회사 산업'
        else:
            query = f'{keyword} company industry'

        search = self.gn.search(query, when=when)
        list = []
        for entry in search['entries']:
            text = entry['title'].split(' - ')[0]
            list.append(text)

        result = '\n '.join(list)
        return result
