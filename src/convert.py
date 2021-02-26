import copy
import datetime as dt
import numpy as np
import pandas as pd
import re
import spacy
import ginza
from spacy.pipeline import EntityRuler
from xml.sax.saxutils import unescape

from bs4 import BeautifulSoup
# import dicttoxml
import xmltodict

num_of_topics = 5


class PageDataContainer:

    def __init__(self, i, df_thread, user_master, topic_detector):

        # ページタイトルに使用するindex
        self.id = i
        # title_idxから"Q&A-xxxx"を設定
        self.title = f'Q&A-{i:06d}'
        # 質問したチャンネル名
        self.question_channel = df_thread['channel_name'][0]
        # 質問した日付
        question_datetime = df_thread['thread_ts'].min()
        # dt.datetime.strptime(df_thread['thread_ts'][0][:10], '%Y-%m-%d')
        self.question_date = dt.date(
            question_datetime.year, question_datetime.month, question_datetime.day)

        # 質問したメンバーの表示名
        question_talk = df_thread.iloc[0]
        self.question_member = question_talk['user_name']
        # 回答したメンバーの表示名のlist
        if len(df_thread) < 2:
            self.answer_members = []
        elif len(df_thread) == 2:
            self.answer_members = [df_thread.loc[1, 'user_name']]
        else:
            self.answer_members = df_thread.loc[1:]['user_name'].tolist()

        self.tech_topics = self.annotate_topics(
            df_thread['talk_text'].tolist(), topic_detector)

        df_thread['talk_text_rpls'] = df_thread.apply(
            lambda r: replace_username(r.talk_text, user_master.get(r.target_date)), axis=1)

        # 質問本文
        self.question_contents = df_thread.loc[0, 'talk_text_rpls']
        # 回答本文
        self.answer_contents = df_thread.loc[1:, 'talk_text_rpls'].tolist()

    def annotate_topics(self, text_list, topic_detector):
        all_text = '\n'.join(text_list)
        retxt = topic_detector.replace_inconsistencies(
            all_text, topic_detector.str_replace_dict)
        retxt = topic_detector.delete_symbols(all_text)

        doc = topic_detector.detect(retxt)
        df_result = topic_detector.get_result(doc)

        return df_result.text.value_counts().index.tolist()[:num_of_topics]

    def generate_xml_text(self):
        text = '{{Infobox Q&A\n'
        text += f'| question_channel = [[チャンネル一覧##{unescape(self.question_channel)}|{unescape(self.question_channel)}]] <!-- チャンネル名 -->\n'
        text += f'| question_date = {self.question_date} <!-- 質問投稿日 -->\n'
        text += f'| question_member_1 = [[利用者:{unescape(self.question_member)}]] <!-- 質問者 -->\n'

        unique_answer_members = set(self.answer_members) \
            - {self.question_member}

        for i, answer_member in enumerate(unique_answer_members):
            text += f'| answer_member_{i+1} = [[利用者:{unescape(answer_member)}]]\n'

        for i in range(min(len(self.tech_topics), 5)):
            text += f'| tech_topic_{i+1} = [[質問トピック::{unescape(self.tech_topics[i])}]]\n'

        text += '}}'
        text += '\n\n'
        text += '==質問==\n'
        text += '<blockquote>\n'

        text += f'{unescape(self.question_contents)}\n'

        text += '<!-- 質問テキスト -->\n'
        text += '</blockquote>\n'
        text += '\n'
        text += '==回答==\n'

        if len(self.answer_members) != len(self.answer_contents):
            raise('Answer members & contents are different')

        for i, (answer_member, content) in enumerate(zip(self.answer_members, self.answer_contents)):
            text += f'===回答{i+1}:{unescape(answer_member)}さん===\n'
            text += f'{unescape(content)}\n\n'

        text += '<!-- 回答テキスト -->\n\n'
        text += '[[カテゴリ:Q&Aまとめ]]'
        return text

    def to_dict(self, output_template):
        container_dict = output_template
        container_dict['mediawiki']['page']['title'] = self.title
        container_dict['mediawiki']['page']['revision']['text']['#text'] = self.generate_xml_text()

        return container_dict


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
        retxt = re.sub(r'\s', '', retxt)
        return retxt

    def detect(self, text):
        if text == '':
            return None
        doc = self.nlp(text)
        return doc

    def get_result(self, doc):
        if doc is None:
            return []
        df_result = pd.DataFrame([[ent.text, ent.label_, str(ent.start_char), str(ent.end_char)] for ent in doc.ents],
                                 columns=['text', 'label', 'start_pos', 'end_pos'])
        return df_result[df_result['label'].isin(self.target_labels)]

# 投稿本文のusername を置換するための関数


def replace_username(text, user_master) -> 'replaced_text':
    pattern = r'(?<=<@)(.+?)(?=>)'
    usercodes = re.findall(pattern, text)

    for usercode in usercodes:
        text = text.replace(usercode, f'```{user_master.get(usercode)}```')
    return text


def setup(user_master_filepath, output_template_filepath):

    def create_user_master(df) -> {'target_date': {'user_id': 'user_name'}}:
        user_dict = dict()
        for td in df['target_date'].unique():
            df_tmp = df[df['target_date'] == td]
            user_dict[td] = dict(zip(df_tmp['user_id'], df_tmp['user_name']))
        return user_dict

    def create_template_xml_dxit(xml) -> 'dict':
        return xmltodict.parse(xml.read())

    user_master = create_user_master(pd.read_csv(user_master_filepath))

    with open(output_template_filepath, encoding='utf-8') as xml:
        output_template = create_template_xml_dxit(xml)

    return (user_master, output_template)


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
    user_master, output_template = setup(
        user_master_filepath, output_template_filepath)

    annotation_master = pd.read_csv(annotation_master_filepath)
    annotation_target_labels = tuple(
        pd.read_csv(annotation_target_labels_filepath, header=None).loc[:, 0]
    )

    topic_detector = TopicDetector(annotation_master, annotation_target_labels)
    container_list = []  # PageDataContainerを格納するリスト
    output_dict_list = []  # 出力dictを格納するdict
    num_of_pages_in_xml = 1  # 1xmlファイルあたりのページ数 どう使うかよくわからない

    # スレッドごとにコンテナクラスのオブジェクトにする
    thread_ts_list = sorted(df_talks['thread_ts'].unique())
    thread_idx = 1
    for ts in thread_ts_list:
        df_thread = df_talks[df_talks['thread_ts'] == ts]\
            .sort_values(by='talk_ts').reset_index()

        if len(df_thread) < 2:
            continue

        container = df_to_container(
            thread_idx, df_thread, user_master, topic_detector)
        container_list.append(container)
        thread_idx += 1
        break

    # 各コンテナをdict形にする
    for container in container_list:
        container_dict = copy.deepcopy(container.to_dict(output_template))
        output_dict_list.append(container_dict)

    # dictをxmlとして書き出す。
    for i, container_dict in enumerate(output_dict_list):
        dict_to_xml(i, container_dict, output_folderpath)
        break


if __name__ == '__main__':
    input_csv_filepath = r'../csv/question_talk_data.csv'
    user_master_filepath = r'../csv/user_name_master.csv'
    annotation_master_filepath = r'../csv/annotation_master.csv'
    annotation_target_labels_filepath = r'../csv/label_master.txt'
    output_template_filepath = r'../template/import-template.xml'
    output_folderpath = r'../xml/'
    main(input_csv_filepath, user_master_filepath,
         annotation_master_filepath, output_template_filepath, output_folderpath)
