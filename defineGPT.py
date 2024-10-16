import configparser

import pandas as pd
import torch
import unicodedata
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import tiktoken
from tqdm import tqdm

from parseNews import GoogleParser
from reranker import reRanker
from wikiScraping import scrapWiki


class GptAgent:
    def __init__(self
                 , OPENAI_API_KEY: str
                 , type: str
                 , input_lang: str = "ko"
                 , model: str = "gpt-3.5-turbo-1106"
                 , rerankerModel: str = 'Alibaba-NLP/gte-multilingual-reranker-base'
                 , chunk_size: int = 2000
                 , overlap: int = 200
                 ):
        '''
        GPT Agent for analysis of correlation between theme keyword and company
        :param OPENAI_API_KEY: 오픈AI API 키
        :param type: headline or document
        :param input_lang: 'ko' or 'en'
        :param model: OpenAI GPT 모델명
        :param rerankerModel: reranker 모델명
        :param chunk_size: 문서를 나눌 때의 chunk size
        :param overlap: 문서를 나눌 때의 overlap
        '''
        self.API_KEY = OPENAI_API_KEY
        self.type = type
        if input_lang == "ko":
            self.input_lang = "Korean"
            country = "KR"
        elif input_lang == "en":
            self.input_lang = "English"
            country = "US"
        self.model = model
        self.keyword = None
        self.keyword_doc = None

        self.wiki = scrapWiki(lang=input_lang)

        self.gn = GoogleParser(lang=input_lang, country=country)

        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.reranker = reRanker(rerankerModel
                                 , trust_remote_code=True
                                 , torch_dtype=torch.float16
                                 )

        self.splitter = RecursiveCharacterTextSplitter(chunk_overlap=overlap, chunk_size=chunk_size)

    def __get_prompt(self):
        headline_template = '''
        Act as an Financial Analyst.
        I will give you document which explains the Theme Keyword.
        In the other hand, I'll also give you news headlines which about the company.
        Compare keyword and company with given documents, and give me the correlation score which Indicates how keyword and company are related
        Correlation score should be given by following rules:
            1. Give score based on how much keyword and company are related;
            2. Score should be given only when company is directly related to keyword according to document given. Relationship should be strong enough to affect company's business;
            3. Score is range from 0% to 100%. Score should be exact percentage, not a range. And wrap the score with square brackets!;
            4. Lastly, define company's role is demander of keyword product or supplier of keyword product. And wrap the role with curly brackets!;
        To make the answer more useful to the user, following strategies below:
            1. Use literal and explicit language;
            2. act as an expert on the subject;
            4. use 'step-by-step' instructions, especially in medium to complex tasks;
            5. given documents are wiritten in {input_lang}, but you can respond in English;

        Theme Keyword : {keyword}
        Document about Theme Keyword : {keyword_doc}
        
        Company Name : {company_name}
        News headlines about the company : {document}

        Correlation score :
        '''

        document_template = '''
        Act as an Financial Analyst.
        I will give you document which explains the Theme Keyword.
        In the other hand, I'll also give you documents which about the company's business.
        Compare keyword and company with given documents, and give me the correlation score.
        Correlation score should be given by following rules:
            1. Give score based on how much keyword and company are related;
            2. Score should be given only when company is directly related to keyword according to document given. Relationship should be strong enough to affect company's business;
            3. Score is range from 0% to 100%. Score should be exact percentage, not a range. And wrap the score with square brackets!;
            4. Lastly, define company's role is demander of keyword product or supplier of keyword product. And wrap the role with curly brackets!;
        To make the answer more useful to the user, following strategies below:
            1. Use literal and explicit language;
            2. act as an expert on the subject;
            4. use 'step-by-step' instructions, especially in medium to complex tasks;
            5. given documents are wiritten in {input_lang}, but you can respond in English;
            
        Theme Keyword : {keyword}
        Document about the Theme Keyword : {keyword_doc}
        
        Company Name : {company_name}
        Document about the company's business : {document}

        Correlation score :
        '''

        if self.type == "headline":
            template = headline_template
        elif self.type == "document":
            template = document_template
        else:
            raise ValueError("type should be headline or document")

        prompt = ChatPromptTemplate.from_template(template)
        return prompt

    def __cut_doc(self, doc, length_limit):
        '''
        Cut document to fit the max token length of GPT-4
        :param doc: document
        :return: cutted document
        '''
        #check if keyword_doc's token length is less than 8192

        length = len(self.tokenizer.encode(doc))

        # if length_limit is -1, don't clip it
        if length_limit == -1:
            return doc

        # if length of doc is more than limit, clip it
        if length > length_limit:
            portion = length_limit / length
            doc = doc[:int(len(doc) * portion)]

        return doc

    def set_theme(self, theme, theme_key, use_summary=True):
        '''
        Set theme keyword and document about theme keyword
        :param theme: 테마명
        :param theme_key: 테마 키워드(위키피디아 검색을 위한 것)
        :param use_summary: 위키피디아에서 서머리만 사용할지 전문을 사용할지 여부
        :return:
        '''
        self.keyword = theme
        if use_summary:
            self.keyword_doc = self.wiki.get_page(theme_key).summary
        else:
            self.keyword_doc = self.wiki.get_page(theme_key).text
        #check if keyword_doc's token length is less than 8192
        self.keyword_doc = self.__cut_doc(self.keyword_doc, 4086)

    def run(self, company_code, company_name, buss_detail_path: str='data/buss_detail', top_n: int = 3, news_window: str ='180d'):
        prompt = self.__get_prompt()
        model = ChatOpenAI(model=self.model
                           , openai_api_key=self.API_KEY
                           , max_retries=5)
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        output = None
        if self.type == 'headline':
            document = self.__cut_doc(self.gn.parse(company_name, when=news_window), 8000)

            output = chain.invoke({
                "input_lang": self.input_lang
                , "keyword": self.keyword
                , "keyword_doc": self.keyword_doc
                , "company_name": company_name
                , "document": document
            })

        elif self.type == 'document':
            bus_det = pd.read_json(f'./{buss_detail_path}/{company_code}.json', typ='series')
            doc = bus_det.detail[company_code]
            text_list = self.splitter.split_text(doc)
            ranked_text_list = self.reranker.rerank(self.keyword_doc, text_list)
            document = '. '.join(ranked_text_list[:top_n])

            output = chain.invoke({
                "input_lang": self.input_lang
                , "keyword": self.keyword
                , "keyword_doc": self.keyword_doc
                , "company_name": company_name
                , "document": document
            })

        return output


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('./data/config.ini')
    OPENAI_API_KEY = config.get('section', 'OPENAI_API_KEY')

    '''set Theme Keyword'''
    theme = '2차전지 셀 및 부품 생산'
    theme_key = '2차전지'
    input_lang = 'ko'

    '''Type Business Document'''
    typeinfo = 'headline'# 'document' or 'headline
    agent = GptAgent(OPENAI_API_KEY
                     , type=typeinfo # 'document' or 'headline'
                     , input_lang=input_lang
                     , model="gpt-4o-mini"
                     , rerankerModel='Alibaba-NLP/gte-multilingual-reranker-base')
    agent.set_theme(theme=theme, theme_key=theme_key, use_summary=False)

    company = 'A005930'
    company_name = '삼성전자'

    output_list = []
    output = agent.run(company_code=company
              , company_name=company_name)
    output_list.append([company, company_name, output])

    print(output_list)