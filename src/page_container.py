import pandas as pd
from datetime import date


class PageDataContainer:
    def __init__(self, i, df_thread, user_master, topic_detector):

        # ページタイトルに使用するindex
        self.id = i
        # 質問したチャンネル名
        self.channel_name = df_thread['channel_name'][0]
        # 質問した日付
        question_datetime = df_thread['thread_ts'].min()
        self.question_date = date(
            question_datetime.year, question_datetime.month, question_datetime.day)

        # 質問したメンバーの表示名
        question_talk = df_thread.iloc[0]
        self.question_user_real_name = user_master[question_talk['target_date']].get_real_name(
            question_talk['user_id'])
        self.question_member = question_talk['user_name']
        # 回答したメンバーの表示名のlist
        if len(df_thread) < 2:  # 質問トークしかない場合は空list
            self.answer_user_real_names = []
            self.answer_members = []
        elif len(df_thread) == 2:  # 返答トークが1つしかない場合は1項目のlist作成
            answer_talk = df_thread.loc[1]
            self.answer_user_real_names = [
                user_master[answer_talk['target_date']
                            ].get_real_name(answer_talk['user_id'])
            ]
            self.answer_members = [answer_talk['user_name']]
        else:  # 2つ以上の返答トークがある場合
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

        unique_answer_real_names = [x for x in pd.Series(self.answer_user_real_names).value_counts().index
                                    if x != self.question_user_real_name][:num_of_topics]

        for i, answer_real_name in enumerate(unique_answer_real_names[:num_of_topics]):
            text += f'| answer_member_{i+1} = [[利用者:{unescape(answer_real_name)}]]\n'

        for i in range(min(len(self.tech_topics), 5)):
            text += f'| tech_topic_{i+1} = [[質問トピック::{unescape(self.tech_topics[i])}]]\n'

        text += '}}'
        text += '\n\n'
        text += '==質問==\n'
        text += f'===質問者: {unescape(self.question_member)}さん===\n'

        text += '<blockquote>\n'
        text += f'{unescape(self.question_contents)}\n'
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
