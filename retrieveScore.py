import re

import numpy as np
import pandas as pd

def find_correl_and_role(x):

    score = x.Detail.apply(lambda x: re.findall(r'\[.*?\]', x))

    # if we have score in bracket, return it
    if len(x.score) > 0:
        result = x.score[0]
        try:
            result = re.findall(r'[0-9]+[.][0-9]?[\%]|[0-9]+[\%]', result)[0]
            result = float(result.replace('%', '').replace('[', '').replace(']', ''))
        except:
            result = 0.0

        return result
    # else, we should find score in text
    else:
        full_text = x.Detail.lower()
        score_loc = full_text.find('score')
        loc_list = []
        if len(x.sub_score) == 0: return 0
        for sc in x.sub_score:
            sc_loc = full_text.find(sc)
            loc_list.append(abs(sc_loc - score_loc))
        result = x.sub_score[np.argmin(loc_list)]
        result = float(result.replace('%', ''))

        return result


def getFormattedAssetWeight(df):
    weight_df = df.copy()
    # find all text inside [] and {}
    weight_df['score'] = weight_df.Detail.apply(lambda x: re.findall(r'\[.*?\]', x))
    weight_df['sub_score'] = weight_df.Detail.apply(lambda x: re.findall(r'[0-9]+[.][0-9]?[\%]|[0-9]+[\%]', x))
    weight_df['score'] = weight_df.apply(lambda x: find_correl(x), axis=1)

    weight_df['role'] = weight_df.Detail.apply(lambda x: re.findall(r'\{.*?\}', x))
    #calculate distance between location of score elements and location of 'score' text

    return weight_df


theme = '2차전지 셀 및 부품 생산'
doc_weight = 0.67
head_weight = 0.33

doc_result = pd.read_csv(f'./data/{theme}_document_result.csv', index_col=0)
head_result = pd.read_csv(f'./data/{theme}_headline_result.csv', index_col=0)

doc_score = getFormattedAssetWeight(doc_result)
head_score = getFormattedAssetWeight(head_result)

avg_score = (doc_score.score.astype(float)*doc_weight + head_score.score.astype(float)*head_weight)

result = pd.DataFrame(
    {'Name': doc_score.Name
        , 'DocScore': doc_score.score
        , 'HeadScore': head_score.score
        , 'AvgScore': avg_score
     },
    index=doc_score.index)

result.to_csv(f'./data/{theme}_average_result.csv', encoding='utf-8-sig')

print('done')