import configparser

import pandas as pd
from tqdm import tqdm
import json
import time

from defineGPT import GptAgent

#ignore warnings
import warnings
warnings.filterwarnings('ignore')


def save_log(log, log_path: str = './data/log.txt'):
    with open('./data/log.txt', 'w') as f:
        json.dump(log, f)


def load_log(path: str = './data/log.txt'):
    with open(path, 'r') as f:
        log = json.load(f)
    return log


if __name__ == '__main__':
    #import api key from "./data/config.ini"
    config = configparser.ConfigParser()
    config.read('./data/config.ini')
    OPENAI_API_KEY = config.get('section', 'OPENAI_API_KEY')

    #read sheet"list" from "./data/KOSPI_L+M.xlsx" file
    list = pd.read_excel('./data/KOSPI_L+M.xlsx', sheet_name='list', index_col=0)
    #list = list.iloc[75:80]

    '''set Theme Keyword'''
    theme = '2차전지 셀 및 부품 생산'
    theme_key = '2차전지'
    input_lang = 'ko'

    '''Type Business Document'''
    typeinfo = 'document'# 'document' or 'headline
    agent = GptAgent(OPENAI_API_KEY
                     , model="gpt-4o-mini"
                     , type=typeinfo # 'document' or 'headline'
                     , input_lang=input_lang)
    agent.set_theme(theme=theme, theme_key=theme_key, use_summary=False)

    output_list = []
    #output_list = load_log()
    for company in tqdm(list.index[len(output_list):]):
        company_name = list.loc[company, "Name"]

        output = agent.run(company_code=company
                  , company_name=company_name)
        output_list.append([company, company_name, output])
        save_log(output_list, log_path='./data/log_doc.txt')

        time.sleep(2)

    result = pd.DataFrame(output_list, columns=['Code', 'Name', 'Detail']).set_index('Code')
    result.to_csv(f'./data/{theme}_{typeinfo}_result.csv', encoding='utf-8-sig')

    '''Type News Headlines'''
    typeinfo = 'headline'# 'document' or 'headline
    agent = GptAgent(OPENAI_API_KEY
                     , type=typeinfo # 'document' or 'headline'
                     , input_lang=input_lang)
    agent.set_theme(theme=theme, theme_key=theme_key, use_summary=False)

    output_list = []
    for company in tqdm(list.index[len(output_list):]):
        company_name = list.loc[company, "Name"]

        output = agent.run(company_code=company
                  , company_name=company_name)
        output_list.append([company, company_name, output])
        save_log(output_list, log_path='./data/log_head.txt')

        time.sleep(2)

    result = pd.DataFrame(output_list, columns=['Code', 'Name', 'Detail']).set_index('Code')
    result.to_csv(f'./data/{theme}_{typeinfo}_result.csv', encoding='utf-8-sig')
