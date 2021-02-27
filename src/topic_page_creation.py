import pandas as pd
import copy
from argparse import ArgumentParser

from xml.sax.saxutils import unescape


from convert import setup
from convert import dict_to_xml
from convert import num_of_pages_in_xml


def create_topic_page_dict(idx, topic, base_xml_dict, new_page):
    new_page['id'] = idx
    new_page['title'] = unescape(topic)

    page_contents = f'==トピックのプロパティ==\n[[特別:閲覧/:{unescape(topic)}|{unescape(topic)}がアノテーションされたページ一覧]]'
    new_page['revision']['text']['#text'] = page_contents

    base_xml_dict['mediawiki']['page'].append(new_page)

    return base_xml_dict


def create_user_page_dict(idx, user, base_xml_dict, new_page):
    new_page['id'] = idx
    new_page['title'] = f'利用者:{unescape(user)}'

    page_contents = f'==ユーザのプロパティ==\n[[特別:閲覧/:利用者:{unescape(user)}|{unescape(user)}さんがアノテーションされたページ一覧]]\n'

    new_page['revision']['text']['#text'] = page_contents

    base_xml_dict['mediawiki']['page'].append(new_page)

    return base_xml_dict


def set_single_users():
    df_user = pd.read_csv('../csv/user_name_master.csv')
    df_intro = pd.read_csv('../csv/intro_talk_data.csv')
    df_question = pd.read_csv('../csv/question_talk_data.csv')

    question_set = set(df_question.user_id.unique())
    intro_set = set(df_intro[df_intro.reply_num == 0].user_id.unique())
    return df_user[df_user.user_id.isin(
        question_set - intro_set)]['base_name'].unique()


def main(run_type, user_master_filepath, output_template_filepath,
         annotation_master_filepath, output_folderpath):

    user_master, output_template, page_template = setup(
        user_master_filepath, output_template_filepath)

    annotation_master = pd.read_csv(annotation_master_filepath)

    if run_type == 't':
        page_create_func = create_topic_page_dict
        file_name = 'TOPICS'
        all_titles_list = annotation_master.property.unique()
    elif run_type == 'u':
        page_create_func = create_user_page_dict
        file_name = 'USER'
        all_titles_list = set_single_users()

    output_dict_list = []
    base_dict = copy.deepcopy(output_template)
    for i, topic in enumerate(all_titles_list):
        base_dict = page_create_func(i, topic, base_dict,
                                     copy.deepcopy(page_template))

        if i % num_of_pages_in_xml == num_of_pages_in_xml - 1:
            output_dict_list.append(base_dict)
            base_dict = copy.deepcopy(output_template)

    # dictをxmlとして書き出す。
    for i, topic_dict in enumerate(output_dict_list):
        dict_to_xml(i, file_name, topic_dict, output_folderpath)


if __name__ == '__main__':
    user_master_filepath = r'../csv/user_name_master.csv'
    annotation_master_filepath = r'../csv/annotation_master.csv'
    annotation_target_labels_filepath = r'../csv/label_master.txt'
    output_template_filepath = r'../template/import-template.xml'
    output_folderpath = r'../xml/'

    parser = ArgumentParser(
        description='Create single page for Mediawiki xml')
    parser.add_argument('arg_page_type', help='Type name of the page')

    args = parser.parse_args()

    main(args.arg_page_type, user_master_filepath, output_template_filepath,
         annotation_master_filepath, output_folderpath)
