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
num_of_pages_in_xml = 10  # 1xmlファイルあたりのページ数


class PageDataContainer:

    def __init__(self, i, df_thread, user_master, topic_detector):

        # ページタイトルに使用するindex
        self.id = i
        # 質問したチャンネル名
        self.question_channel = df_thread['channel_name'][0]
        # 質問した日付
        question_datetime = df_thread['thread_ts'].min()
        # dt.datetime.strptime(df_thread['thread_ts'][0][:10], '%Y-%m-%d')
        self.question_date = dt.date(
            question_datetime.year, question_datetime.month, question_datetime.day)

        # 質問したメンバーの表示名
        question_talk = df_thread.iloc[0]
        self.question_user_real_name = user_master[question_talk['target_date']].get_real_name(
            question_talk['user_id'])
        self.question_member = question_talk['user_name']
        # 回答したメンバーの表示名のlist
        if len(df_thread) < 2:
            self.answer_user_real_names = []
            self.answer_members = []
        elif len(df_thread) == 2:
            answer_talk = df_thread.loc[1]
            self.answer_user_real_names = [
                user_master[answer_talk['target_date']
                            ].get_real_name(answer_talk['user_id'])
            ]
            self.answer_members = [answer_talk['user_name']]
        else:
            answer_talks = df_thread.loc[1:]
            self.answer_user_real_names = answer_talks.apply(
                lambda r: user_master[r.target_date].get_real_name(r.user_id), axis=1).tolist()
            self.answer_members = answer_talks['user_name'].tolist()

        topic_terms = self.find_topic_terms(
            df_thread['talk_text'].tolist(), topic_detector)
        self.tech_topics = topic_terms[:num_of_topics]

        # title_idxから"Q&A-xxxx"を設定
        self.title = f'Q&A-{i:06d}:' + '-'.join(sorted(self.tech_topics))

        df_thread['talk_text_rpls'] = df_thread.apply(
            lambda r: replace_username(r.talk_text, user_master.get(r.target_date)), axis=1)

        # annotate
        for term in topic_terms:
            df_thread['talk_text_rpls'] = \
                df_thread['talk_text_rpls'].str.replace(
                    term,  f'[[質問トピック::{term}]]', regex=False)

        self.question_contents = df_thread.loc[0, 'talk_text_rpls']  # 質問本文
        self.answer_contents = \
            df_thread.loc[1:, 'talk_text_rpls'].tolist()  # 回答本文

    def find_topic_terms(self, text_list, topic_detector):
        all_text = '\n'.join(text_list)
        retxt = topic_detector.replace_inconsistencies(
            all_text, topic_detector.str_replace_dict)
        retxt = topic_detector.delete_symbols(all_text)

        doc = topic_detector.detect(retxt)
        df_env_result = topic_detector.get_ent_result(doc)
        df_token_result = topic_detector.get_token_result(doc)
        return df_env_result.text.value_counts().index.tolist()

    def generate_xml_text(self):
        text = '{{Infobox Q&A\n'
        text += f'| question_channel = [[チャンネル一覧##{unescape(self.question_channel)}|{unescape(self.question_channel)}]] <!-- チャンネル名 -->\n'
        text += f'| question_date = {self.question_date} <!-- 質問投稿日 -->\n'
        text += f'| question_member_1 = [[利用者:{unescape(self.question_user_real_name)}]] <!-- 質問者 -->\n'

        unique_answer_real_names = set(self.answer_user_real_names) \
            - {self.question_user_real_name}

        for i, answer_real_name in enumerate(unique_answer_real_names):
            text += f'| answer_member_{i+1} = [[利用者:{unescape(answer_real_name)}]]\n'

        for i in range(min(len(self.tech_topics), 5)):
            text += f'| tech_topic_{i+1} = [[質問トピック::{unescape(self.tech_topics[i])}]]\n'

        text += '}}'
        text += '\n\n'
        text += '==質問==\n'
        text += f'===質問者: {unescape(self.question_member)}さん===\n'

        text += '<blockquote>\n'
        text += f'{unescape(self.question_contents)}\n'
        text += '<!-- 質問テキスト -->\n'
        text += '</blockquote>\n'
        text += '\n'

        text += '==回答==\n'

        if len(self.answer_members) != len(self.answer_contents):
            raise('Answer members & contents are different')

        latest_user = ''
        answer_idx = 1
        for answer_member, content in zip(self.answer_members, self.answer_contents):
            if latest_user != answer_member:  # Combine the same user names
                text += f'===回答{answer_idx}: {unescape(answer_member)}さん===\n'
                latest_user = answer_member
                answer_idx += 1
            text += f'{unescape(content)}\n\n'

        text += '<!-- 回答テキスト -->\n\n'
        text += '[[カテゴリ:Q&Aまとめ]]'
        return text

    def to_dict(self, base_xml_dict, new_page):

        new_page['id'] = self.id
        new_page['title'] = self.title
        new_page['revision']['text']['#text'] = self.generate_xml_text()

        base_xml_dict['mediawiki']['page'].append(new_page)

        return base_xml_dict


class UserInfoContainer:
    def __init__(self, df_user_master):
        self.__display_name_dict = self.set_name_dict(
            df_user_master, 'display_name')
        self.__real_name_dict = self.set_name_dict(df_user_master, 'base_name')

    def set_name_dict(self, df_user_info, col_name):
        return dict(zip(df_user_info['user_id'], df_user_info[col_name]))

    def get_display_name(self, user_id):
        return self.__display_name_dict.get(user_id)

    def get_real_name(self, user_id):
        return self.__real_name_dict.get(user_id)


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
            return []
        df_result = pd.DataFrame([[ent.text, ent.label_, str(ent.start_char), str(ent.end_char)] for ent in doc.ents],
                                 columns=['text', 'label', 'start_pos', 'end_pos'])
        return df_result[df_result['label'].isin(self.target_labels)]

    def get_token_result(self, doc):
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

# 投稿本文のusername を置換するための関数


def replace_username(text, user_master) -> 'replaced_text':
    pattern = r'(?<=<@)(.+?)(?=>)'
    usercodes = re.findall(pattern, text)

    for usercode in usercodes:
        text = text.replace(
            usercode, f"''{user_master.get_display_name(usercode)}'''")
    return text


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

        if len(df_thread) < 2:
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
