import warnings

import pandas as pd
import OpenDartReader
from glob import glob
import urllib3
import urllib.request as urlreq
from tqdm import tqdm
from dateutil.relativedelta import relativedelta
from datetime import datetime as dt
from bs4 import BeautifulSoup
import re

warnings.filterwarnings('ignore')


def text_output(url_link):

    url_open = urlreq.urlopen((url_link)).read()
    soup = BeautifulSoup(url_open, 'html5lib')
    wording = soup.select('body')[0].get_text().replace("\n","").replace("\xa0","")
    return wording


def proc_xml(xml_doc):

    xml_file = BeautifulSoup(xml_doc, features="html.parser")
    lib_list = xml_file.select('Library')
    for lib in lib_list:
        lib_text = lib.get_text()
        if ('1. 사업의 개요' in lib_text) or ('1. (제조서비스업)사업의 개요' in lib_text) or ('1. (금융업)사업의 개요' in lib_text):
            xml_doc = lib
            break
    section_list = xml_doc.select('section-2')
    buss_doc_list = []
    for section in section_list:
        section_text = section.get_text()
        if ('사업의 개요' in section_text) or ('기타 참고사항' in section_text):
            buss_doc = section.get_text()
            #buss_doc = buss_doc.replace('\n\n', '\n').replace('\xa0', '').replace('\t', '').replace('\r', '')
            buss_doc_list.append(buss_doc)
    xml_doc = '\n\n '.join(buss_doc_list)

    return xml_doc

def get_buss_detail(Dart_df):

    enddate = dt.today().strftime('%Y-%m-%d')
    #buss_detail_list = []

    for i in tqdm(Dart_df.index):
        try:
            code = i[1:]
            startdate = dt.strftime(dt.strptime(enddate, '%Y-%m-%d') - relativedelta(months=12), '%Y-%m-%d')
            result_list = dart.list(code, start=startdate, kind='A', final=False)
            try:
                result_list['Rpt_Date'] = result_list.report_nm.apply(lambda x: str.split(x, "(")[1].replace(')', ''))
                result_list = result_list.sort_values(by='Rpt_Date', ascending=False)
            except:
                pass

            #공시 검색 결과가 없는 경우, 예외 처리
            if len(result_list) == 0:
                raise ValueError('조회 데이터 없음')

            for _, result in result_list.iterrows():
                if '정정' not in result.report_nm:
                    result_temp = result[['report_nm', 'rcept_no']]
                    result_temp = pd.DataFrame([result_temp.values], columns=result_temp.index)
                    break

            #사업의 내용 부분 텍스트 추출
            buss_detail = proc_xml(dart.document(result_temp.values[0][1]))

            #in case we scrap other report
            if '감사대상업무' in buss_detail[:100] or '내부회계관리제도' in buss_detail[:100]:
                raise ValueError('Scraped wrong report.')
            elif buss_detail == '':
                raise ValueError('Scraped wrong report.')
        except:
            try:
                code = i[1:]
                result_list = dart.list(code, end=enddate, kind='A', final=False)

                for _, result in result_list.iterrows():
                    if '정정' not in result.report_nm:
                        result_temp = result[['report_nm', 'rcept_no']]
                        result_temp = pd.DataFrame([result_temp.values], columns=result_temp.index)

                # 추출한 결과값에 존재하는 보고서의 url 주소를 직접 가져오자
                listofsubdocs = dart.sub_docs(result_temp.values[0][1], match='사업의 내용')
                dcmno = listofsubdocs.iloc[0]['url'][:-4]

                buss_detail = text_output(dcmno)

            except:
                result_temp = pd.DataFrame({'report_nm': ['조회 데이터 없음'], 'rcept_no': ['조회 데이터 없음']})
                buss_detail = '조회 데이터 없음'

        if buss_detail == None:
            result_temp['detail'] = None
        else:
            result_temp['detail'] = buss_detail
        result_temp.index = [i]

        result_temp.to_json(f'./data/buss_detail/{i}.json', force_ascii=False)
        #buss_detail_list.append(result_temp)

    #result_df = pd.concat(buss_detail_list, axis=0)

    return True

#한국 기업에 대해서는 중형주까지만 점수를 산출하는게 더 낫지 않을까?
#대형주만 하기에는 조금 데이터가 부족한 느낌이 있음

#read sheet"list" from ./data/KOSPI_L+M.xlsx file
list = pd.read_excel('./data/KOSPI_L+M.xlsx', sheet_name='list', index_col=0)

api_key = '16166465c8bcc04467fedc3f5ff3226d01baebf9'
dart = OpenDartReader(api_key)
buss_df = get_buss_detail(list)

print('finished')