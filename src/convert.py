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

        # 会話の中から単語リストに該当する単語のタプル。出現順位順
        cnt_dict = {word: " ".join(df_thread.talk_text.to_list()).count(word)
                    for word in anotation_master.values()}
        self.tech_topics = tuple(word_tuple[0] for word_tuple in sorted({k: v for k, v in cnt_dict.items()
                                                                         if v != 0}.items(), key=lambda x: x[1], reverse=True))

        df_thread['talk_text_rpls'] = df_thread.apply(
            lambda r: replace_username(r.talk_text, user_master.get(r.target_date)), axis=1)

        # 質問本文
        self.question_contents = df_thread.loc[0, 'talk_text_rpls']
        # 回答本文
        self.answer_contents = df_thread.loc[1:, 'talk_text_rpls'].tolist()

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


# 投稿本文のusername を置換するための関数
def replace_username(text, user_master) -> 'replaced_text':

    pattern = r'(?<=<@)(.+?)(?=>)'
    usercodes = re.findall(pattern, text)

    for usercode in usercodes:
        text = text.replace(usercode, f'```{user_master.get(usercode)}```')
    return text


def setup(user_master_filepath, anotation_master_filepath, output_template_filepath):

    def create_user_master(df) -> {'target_date': {'user_id': 'user_name'}}:
        user_dict = dict()
        for td in df['target_date'].unique():
            df_tmp = df[df['target_date'] == td]
            user_dict[td] = dict(zip(df_tmp['user_id'], df_tmp['user_name']))
        return user_dict

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
        'talk_ts', 'thread_ts'])

    max_target_date = df_talks.target_date.max()

    # user_master, anotation_master, xml_template をdict型で読み込み
    user_master, anotation_master, output_template = setup(user_master_filepath, anotation_master_filepath,
                                                           output_template_filepath)

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
        break


if __name__ == '__main__':
    input_csv_filepath = r'../csv/question_talk_data.csv'
    user_master_filepath = r'../csv/user_name_master.csv'
    anotation_master_filepath = r'../csv/annotation_master.csv'
    output_template_filepath = r'../template/import-template.xml'
    output_folderpath = r'../xml/'
    main(input_csv_filepath, user_master_filepath,
         anotation_master_filepath, output_template_filepath, output_folderpath)
