#!/usr/bin/env python
# coding: utf-8

# In[4]:


import pandas as pd
import xml.etree.ElementTree as et
import xml.dom.minidom as md

#できれば実行時の引数として渡したい
input_path = r'../csv/question_talk_data.csv'
output_path = r'../xml/temp.xml'

df = pd.read_csv(input_path).head(10)


# In[10]:


class Csv2Xml:

    def get_user_name(self):
        #あとで書く
        pass
    
    def merge_talks2thread(self):
        #あとで書く
        pass
    
    def df2xml(self):
        root = et.Element('root')
        for _, row in df.iterrows():
            channel = et.SubElement(root, 'channel')
            channel_id = et.SubElement(channel, 'channel_id')
            channel_name = et.SubElement(channel, 'channel_name')
            reply_num = et.SubElement(root, 'reply_num')
            user = et.SubElement(root, 'user')
            user_id = et.SubElement(user, 'user_id')
            user_name = et.SubElement(user, 'user_name')
            reply_user_is_in_current = et.SubElement(root, 'reply_user_is_in_current')
            talk = et.SubElement(root, 'talk')
            talk_id = et.SubElement(talk, 'talk_id')
            talk_text = et.SubElement(talk, 'talk_text')
            talk_ts = et.SubElement(talk, 'talk_ts')
            thread_ts = et.SubElement(root, 'thread_ts')
            target_date = et.SubElement(root, 'target_date')
            for iCol, _ in df.iteritems():
                if iCol == 'channel_id':
                    channel_id.text = str(row[iCol])
                if iCol == 'channel_name':
                    channel_name.text = str(row[iCol])
                if iCol == 'reply_num':
                    reply_num.text = str(row[iCol])
                if iCol == 'user_id':
                    user_id.text = str(row[iCol])
                if iCol == 'user_name':
                    user_name.text = str(row[iCol])
                if iCol == 'reply_user_is_in_current':
                    reply_user_is_in_current.text = str(row[iCol])
                if iCol == 'talk_id':
                    talk_id.text = str(row[iCol])
                if iCol == 'talk_text':
                    talk_text.text = str(row[iCol])
                if iCol == 'talk_ts':
                    talk_ts.text = str(row[iCol])
                if iCol == 'thread_ts':
                    thread_ts.text = str(row[iCol])
                if iCol == 'target_date':
                    target_date.text = str(row[iCol])

            document = md.parseString(et.tostring(root, 'utf-8'))
            file = open(output_path, 'w')
            document.writexml(file, encoding='utf-8', newl='\n', indent='', addindent='  ')
            file.close()


# In[12]:


if __name__ == '__main__':
    converter = Csv2Xml()
    converter.df2xml()


# In[ ]:




