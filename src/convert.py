import copy
import datetime as dt
import numpy as np
import pandas as pd
import re
from xml.sax.saxutils import unescape

from bs4 import BeautifulSoup
# import dicttoxml
import xmltodict


class PageDataContainer:

    def __init__(self, i, df_thread, user_master, anotation_master):
        # 投稿本文のusername を置換するための関数
        def replace_username(text, user_master) -> 'replaced_text':
            pattern = r'(?<=<@)(.+?)(?=>)'
            usercodes = re.findall(pattern, text)

            for usercode in usercodes:
                date_list = []
                for key in user_master:
                    if usercode in key:
                        username_datetime = dt.datetime.strptime(
                            key[1], '%Y-%m-%d')
                        username_date = dt.date(
                            username_datetime.year, username_datetime.month, username_datetime.day)
                        date_list.append(username_date)
                date_list.sort(reverse=True)

                for date in date_list:
                    if date < self.question_date:
                        text = text.replace(
                            f'<@{usercode}>', f'@```{user_master[(usercode, date.strftime("%Y-%m-%d"))]}``` ')
                        break
            return text

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
        # 質問したメンバーの表示名のタプル
        # 回答したメンバーの表示名のタプル

        question_talk = df_thread.iloc[0]
        self.question_member = question_talk['user_name']
        if len(df_thread) < 2:
            self.answer_members = []
        elif len(df_thread) == 2:
            self.answer_members = [df_thread.iloc[1:]['user_name']]
        else:
            self.answer_members = df_thread.iloc[1:]['user_name'].tolist()
        '''
        if len(df_thread[df_thread.reply_num == 0]) == 0:
            self.question_members = '',
            self.answer_members = tuple(
                user for user in df_thread.user_name.unique())
        else:
            self.question_members = tuple(
                user for user in df_thread[df_thread.reply_num == 0].user_name)
            self.answer_members = tuple(user for user in df_thread.user_name.unique()
                                        if user != df_thread[df_thread.reply_num == 0].user_name.tolist()[0])
        '''
        # 会話の中から単語リストに該当する単語のタプル。出現順位順
        cnt_dict = {word: " ".join(df_thread.talk_text.to_list()).count(
            word) for word in anotation_master.values()}
        self.tech_topics = tuple(word_tuple[0] for word_tuple in sorted({k: v for k, v in cnt_dict.items()
                                                                         if v != 0}.items(), key=lambda x: x[1], reverse=True))
        # 質問本文
        self.question_contains = tuple(replace_username(
            text, user_master) for text in df_thread[df_thread.reply_num == 0].talk_text)
        # 回答本文
        self.answer_contains = tuple(replace_username(
            text, user_master) for text in df_thread[df_thread.reply_num != 0].talk_text)
        # テンプレート読み込み
        # with open(r'../template/import-template.xml', encoding='utf-8') as xml:
        #    self.dict = xmltodict.parse(xml.read())

    def to_dict(self, output_template):
        container_dict = output_template

        text = f'{{{{Infobox Q&A\n\
| question_channel = ﻿[[チャンネル一覧##{unescape(self.question_channel)}|{unescape(self.question_channel)}]] <!-- チャンネル名 -->\n\
| question_date = {self.question_date} <!-- 質問投稿日 -->\n\
| question_member_1 = [[利用者:{unescape(self.question_members[0])}]] <!-- 質問者 -->\n'

        unique_answer_members = set(
            self.answer_members) - {self.question_member}
        for i, answer_member in enumerate(unique_answer_members):
            text += f'| answer_member_{i+1} = [[利用者:{unescape(answer_member)}]]\n'

        for i in range(min(len(self.tech_topics), 5)):
            text += f'tech_topic_{i+1} = [[質問トピック::{unescape(self.tech_topics[i])}]]\n'

        text += f'}}}}\n\
\n\
==質問==\n\
<blockquote>\n'
        for question_contains in self.question_contains:
            text += f'{unescape(question_contains)}\n'

        text += f'<!-- 質問テキスト -->\n\
</blockquote>\n\
\n\
==回答==\n'

        for i, answer_contains in enumerate(self.answer_contains):
            text += f'===回答{i}:XXXさん==='
            text += f'{unescape(answer_contains)}\n'

        text += f'<!-- 回答テキスト -->\n\n[[カテゴリ:Q&Aまとめ]]'

        container_dict['mediawiki']['page']['title'] = self.title
        container_dict['mediawiki']['page']['revision']['text']['#text'] = text

        return container_dict


def setup(user_master_filepath, anotation_master_filepath, output_template_filepath):

    def create_user_master(df) -> {('user_id', 'target_date'): 'user_name'}:
        return dict(zip(tuple(zip(df['user_id'], df['target_date'])), df['user_name']))

    def create_anotation_dict(df) -> {'keyword': 'property'}:
        return dict(zip(df['keyword'], df['property']))

    def create_template_xml_dxit(xml) -> 'dict':
        return xmltodict.parse(xml.read())

    user_master = create_user_master(pd.read_csv(user_master_filepath))

    anotation_master = create_anotation_dict(
        pd.read_csv(anotation_master_filepath))

    with open(output_template_filepath, encoding='utf-8') as xml:
        output_template = create_template_xml_dxit(xml)

    return (user_master, anotation_master, output_template)


def df_to_container(i, df, user_master, anotation) -> 'container class':
    return PageDataContainer(i, df, user_master, anotation)


def dict_to_xml(i, container_dict, output_folderpath):
    xml = xmltodict.unparse(container_dict, pretty=True)
    soup = BeautifulSoup(xml, 'xml')
    with open(output_folderpath + f'Q&A-{i:04d}.xml', mode='w') as f:
        f.write(str(soup))


def main(input_csv_filepath, user_master_filepath, anotation_master_filepath, output_template_filepath, output_folderpath):
    df_talks = pd.read_csv(input_csv_filepath, parse_dates=[
                           'talk_ts', 'thread_ts', 'target_date'])

    # user_master, anotation_master, xml_template をdict型で読み込み
    user_master, anotation_master, output_template = setup(
        user_master_filepath, anotation_master_filepath, output_template_filepath)

    container_list = []  # PageDataContainerを格納するリスト
    output_dict_list = []  # 出力dictを格納するdict
    num_of_pages_in_xml = 1  # 1xmlファイルあたりのページ数 どう使うかよくわからない

    # スレッドごとにコンテナクラスのオブジェクトにする
    thread_ts_list = df_talks['thread_ts'].unique()
    for i, ts in enumerate(thread_ts_list):
        df_thread = df_talks[df_talks['thread_ts'] == ts]\
            .sort_values(by='talk_ts').reset_index()
        container = df_to_container(
            i, df_thread, user_master, anotation_master)
        container_list.append(container)

    # 各コンテナをdict形にする
    for container in container_list:
        container_dict = copy.deepcopy(container.to_dict(output_template))
        output_dict_list.append(container_dict)

    # dictをxmlとして書き出す。
    for i, container_dict in enumerate(output_dict_list):
        dict_to_xml(i, container_dict, output_folderpath)


if __name__ == '__main__':
    input_csv_filepath = r'../csv/question_talk_data.csv'
    user_master_filepath = r'../csv/user_name_master.csv'
    anotation_master_filepath = r'../csv/annotation_master.csv'
    output_template_filepath = r'../template/import-template.xml'
    output_folderpath = r'../xml/'
    main(input_csv_filepath, user_master_filepath,
         anotation_master_filepath, output_template_filepath, output_folderpath)
