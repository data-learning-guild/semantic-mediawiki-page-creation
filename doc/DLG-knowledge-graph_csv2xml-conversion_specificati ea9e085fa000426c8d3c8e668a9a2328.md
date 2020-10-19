# DLG-knowledge-graph_csv2xml-conversion_specification

# What is this?

- DLGナレッジグラフにおいて、BigQueryに蓄積されているSlack上のデータをSemanticMediaWikiにインポートを目的とする
- BigQueryから出力したcsvデータをxmlへ変換
- 本ドキュメントでは、csvデータとxmlデータの仕様及び変換仕様を示す

![DLG-knowledge-graph_csv2xml-conversion_specificati%20ea9e085fa000426c8d3c8e668a9a2328/Screenshot_2020-10-18_at_11.45.43.png](DLG-knowledge-graph_csv2xml-conversion_specificati%20ea9e085fa000426c8d3c8e668a9a2328/Screenshot_2020-10-18_at_11.45.43.png)

# 1. slack csvデータ仕様

[csv data](DLG-knowledge-graph_csv2xml-conversion_specificati%20ea9e085fa000426c8d3c8e668a9a2328/csv%20data%20cc88b4f10a8042439c004e35701ccee7.csv)

# 2. MediaWiki xmlデータ仕様

- <page>タグ以降を編集
    - １つの<page></page>タグで１ページ
- 詳細
    - [https://www.mediawiki.org/wiki/Help:Export/ja#書き出しの形式](https://www.mediawiki.org/wiki/Help:Export/ja#%E6%9B%B8%E3%81%8D%E5%87%BA%E3%81%97%E3%81%AE%E5%BD%A2%E5%BC%8F)
- <title>: ページのタイトル
    - 今回は"Q&A-xxxx"とする
- <text>
    - {{Infobox Q&A}}
        - MediaWiki上でのテンプレート
- <sha1>
    - インポート時に自動生成されるハッシュ値

# 3. 変換仕様

- １スレッド１ページ（<page></page>）とする
    - 30ページ/1xmlファイルとする
        - インポート時に重すぎるため
- <title>: ページのタイトル
    - 今回は"Q&A-xxxx"とする（古い順から連番を付ける、桁数どうしよう）
- <text>
    - {{Infobox Q&A}}
        - 下記テーブルの通り
    - 質問talk(reply_num=0)の内容は"==質問=="ブロックへ
    - それ以降の返信（reply_num>0）の内容は"==回答=="ブロックへ
        - 回答talkごとにブロックを作れると見やすい？
    - メンションの変換
        - talk中のメンションがuser_idになってしまっているため、表示名に変換する

[Infobox Q&A](DLG-knowledge-graph_csv2xml-conversion_specificati%20ea9e085fa000426c8d3c8e668a9a2328/Infobox%20Q&A%2033043340556d4708aafad4c0f4c00184.csv)