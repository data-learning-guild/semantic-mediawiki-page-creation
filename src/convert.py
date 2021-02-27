import copy
import numpy as np
import pandas as pd
import re
import xmltodict
from bs4 import BeautifulSoup

import spacy
import ginza
from spacy.pipeline import EntityRuler

from page_container import PageDataContainer
from page_container import UserInfoContainer

num_of_pages_in_xml = 20  # 1xmlファイルあたりのページ数
num_of_min_talks = 2


class TopicDetector:
    def __init__(self, df_annotation_master, target_label_list):
        # set dicts
        self.str_replace_dict = dict(
            zip(df_annotation_master.keyword, df_annotation_master.property))
        topic_dict = [{"label": "Tech", "pattern": x}
                      for x in df_annotation_master.property.unique()]

        self.target_labels = target_label_list

        # nlp model
        self.nlp = spacy.load('ja_ginza')
        self.ruler = EntityRuler(self.nlp, overwrite_ents=True)
        self.ruler.add_patterns(topic_dict)
        self.nlp.add_pipe(self.ruler)

    def replace_inconsistencies(self, text, replace_dict):
        regex = re.compile('|'.join(map(re.escape, replace_dict)))
        return regex.sub(lambda match: replace_dict[match.group(0)], text)

    def delete_symbols(self, text):
        # sub 'url link'
        retxt = re.sub(r'<http.+?>', '', text)
        # sub 'mention'
        retxt = re.sub(r'<@\w+?>', '', retxt)
        # sub 'reaction'
        retxt = re.sub(r':\S+?:', '', retxt)
        # sub 'mention'
        retxt = re.sub(r'<#\S+?>', '', retxt)
        # sub 'html key words'
        retxt = re.sub(r'(&).+?\w(;)', '', retxt)
        # sub spaces
        #retxt = re.sub(r'\s', '', retxt)
        return retxt

    def detect(self, text):
        if text == '':
            return None
        doc = self.nlp(text)
        return doc

    def get_ent_result(self, doc):
        if doc is None:
            return pd.DataFrame()
        df_result = pd.DataFrame([[ent.text, ent.label_, str(ent.start_char), str(ent.end_char)] for ent in doc.ents],
                                 columns=['text', 'label', 'start_pos', 'end_pos'])
        return df_result[df_result['label'].isin(self.target_labels)]

    def get_token_result(self, doc):
        if doc is None:
            return pd.DataFrame()
        result_list = []
        for sent in doc.sents:
            result_list = result_list + \
                [[str(token.i), token.text, token.lemma_, token.pos_, token.tag_]
                 for token in sent]
        df_result = pd.DataFrame(result_list, columns=[
                                 'token_no', 'text', 'lemma', ',pos', 'tag'])
        return df_result

    def get_annotation_value(self, key_str):
        return self.__str_annotation_dict.get(key_str)


def setup(user_master_filepath, output_template_filepath):

    def create_user_master(df) -> {'target_date': UserInfoContainer}:
        return {td: UserInfoContainer(df[df['target_date'] == td]) for td in df['target_date'].unique()}

    def create_template_xml_dxit(xml) -> 'dict':
        return xmltodict.parse(xml.read())

    user_master = create_user_master(pd.read_csv(user_master_filepath))

    with open(output_template_filepath, encoding='utf-8') as xml:
        output_template = create_template_xml_dxit(xml)
    page_template = copy.deepcopy(output_template['mediawiki']['page'])
    output_template['mediawiki']['page'] = []

    return (user_master, output_template, page_template)


def df_to_container(i, df, user_master, anotation) -> 'container class':
    return PageDataContainer(i, df, user_master, anotation)


def dict_to_xml(i, container_dict, output_folderpath):
    xml = xmltodict.unparse(container_dict, pretty=True)
    soup = BeautifulSoup(xml, 'xml')
    with open(output_folderpath + f'Q&A-{i:04d}.xml', mode='w') as f:
        f.write(str(soup))


def main(input_csv_filepath, user_master_filepath, annotation_master_filepath, output_template_filepath, output_folderpath):
    df_talks = pd.read_csv(input_csv_filepath, parse_dates=[
        'talk_ts', 'thread_ts'])

    max_target_date = df_talks.target_date.max()

    # user_master,  xml_template をdict型で読み込み
    user_master, output_template, page_template = setup(
        user_master_filepath, output_template_filepath)

    annotation_master = pd.read_csv(annotation_master_filepath)
    annotation_target_labels = tuple(
        pd.read_csv(annotation_target_labels_filepath, header=None).loc[:, 0]
    )

    topic_detector = TopicDetector(annotation_master, annotation_target_labels)
    container_list = []  # PageDataContainerを格納するリスト
    output_dict_list = []  # 出力dictを格納するdict

    # スレッドごとにコンテナクラスのオブジェクトにする
    thread_ts_list = sorted(df_talks['thread_ts'].unique())
    thread_idx = 1
    for ts in thread_ts_list:
        df_thread = df_talks[df_talks['thread_ts'] == ts]\
            .sort_values(by='talk_ts').reset_index()

        if len(df_thread) < num_of_min_talks:
            continue

        container = df_to_container(
            thread_idx, df_thread, user_master, topic_detector)
        container_list.append(container)
        thread_idx += 1

    # 各コンテナをdict形にする
    base_dict = copy.deepcopy(output_template)
    for i, container in enumerate(container_list):
        base_dict = container.to_dict(base_dict,
                                      copy.deepcopy(page_template))

        if i % num_of_pages_in_xml == num_of_pages_in_xml - 1:
            output_dict_list.append(base_dict)
            base_dict = copy.deepcopy(output_template)

    # dictをxmlとして書き出す。
    for i, container_dict in enumerate(output_dict_list):
        dict_to_xml(i, container_dict, output_folderpath)


if __name__ == '__main__':
    input_csv_filepath = r'../csv/question_talk_data.csv'
    user_master_filepath = r'../csv/user_name_master.csv'
    annotation_master_filepath = r'../csv/annotation_master.csv'
    annotation_target_labels_filepath = r'../csv/label_master.txt'
    output_template_filepath = r'../template/import-template.xml'
    output_folderpath = r'../xml/'
    main(input_csv_filepath, user_master_filepath,
         annotation_master_filepath, output_template_filepath, output_folderpath)
