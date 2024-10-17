import re

import numpy as np
import pandas as pd

def find_correl(x):

    # if we have score in bracket, return it
    if len(x.score) > 0:
        result = x.score[0]
        try:
            result = re.findall(r'[0-9]+[.][0-9]?[\%]|[0-9]+[\%]', result)[0]
            result = float(result.replace('%', '').replace('[', '').replace(']', ''))
        except:
            result = 0.0

        return result

def find_role(x):
    if len(x.role) > 0:
        result = x.role[0].lower()
        if 'neither' in result:
            return 0
        elif 'demand' in result:
            return -1
        elif 'suppl' in result:
            return 1
        else:
            return 0
    else:
        return 0


def getFormattedAssetWeight(df):
    weight_df = df.copy()
    # find all text inside [] and {}
    weight_df['score'] = weight_df.Detail.apply(lambda x: re.findall(r'\[.*?\]', x))
    weight_df['score'] = weight_df.apply(find_correl, axis=1)
    #weight_df['sub_score'] = weight_df.Detail.apply(lambda x: re.findall(r'[0-9]+[.][0-9]?[\%]|[0-9]+[\%]', x))
    weight_df['role'] = weight_df.Detail.apply(lambda x: re.findall(r'\{.*?\}', x))
    weight_df['role'] = weight_df.apply(find_role, axis=1)

    return weight_df


theme = '미국 대선 트럼프 수혜주' #'2차전지 셀 및 부품 생산', '소형모듈원자로 설계 및 제조(부품,소재)' '미국 대선 트럼프 수혜주'
doc_weight = 0.67
head_weight = 0.33

doc_result = pd.read_csv(f'./data/{theme}_document_result.csv', index_col=0)
head_result = pd.read_csv(f'./data/{theme}_headline_result.csv', index_col=0)

doc_score = getFormattedAssetWeight(doc_result).fillna(0)
head_score = getFormattedAssetWeight(head_result).fillna(0)

avg_score = (doc_score.score.astype(float)*doc_score.role.astype(float)*doc_weight + head_score.score.astype(float)*head_score.role.astype(float)*head_weight)
#avg_score = (doc_score.score.astype(float)*doc_weight + head_score.score.astype(float)*head_weight)


result = pd.DataFrame(
    {'Name': doc_score.Name
        , 'DocScore': doc_score.score * doc_score.role
        , 'HeadScore': head_score.score * head_score.role
        , 'AvgScore': avg_score
     },
    index=doc_score.index)

result = result.sort_values(by='AvgScore')

result.to_csv(f'./data/{theme}_average_result.csv', encoding='utf-8-sig')

print('done')