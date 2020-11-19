# 詳細設計書
## クラス設計
### PageDataContainerClass
#### 概要
出力xmlを作成する前段階として、ページごとに必要なデータを格納するクラス

#### メンバ
|name|type|default|description|
|----|----|-------|-----------|
|id|int|0|ページタイトルに使用するindex|
|title|string|Null|ページのタイトル。title_idxから"Q&A-xxxx"を設定|
|question_channel|string|Null|質問したチャンネル名|
|question_date|date|Null|質問した日付|
|question_members|tuple|質問したメンバーの表示名のタプル|
|answer_members|tuple|回答したメンバーの表示名のタプル|
|tech_topics|tuple|会話の中から単語リストに該当する単語のタプル。出現順位順。|
|question_contents|tuple|質問本文|
|answer_contents|tuple|回答本文|

#### メソッド

## グローバル変数
1. 各種ファイル名
2. output_dict_list

## 処理フロー
### メイン関数
#### 引数
1. 入力csvファイル名
2. 入力テンプレxmlファイル名
3. 出力先xmlフォルダパス

#### 処理
1. df = pd.read_csv **# csvデータ読み込み**
2. tmplate = read_xml　**# xmlテンプレ読み込み（辞書型）**
2. thread_ts_list = pd.unique(thread_ts).tolist() **# thread_tsの一覧取得**
3. for i, t in enumerate(thread_ts_list): **# thread_ts種類ごとにfor loop**
    1. df_tmp = df[df.thread_ts == t] **# thread_tsを取得**
    1. c = *df_to_container(df_tmp, i)* **# dfのデータをPageDataContainerへ変換**
    1. dict_tmp = *container_to_dict(c, template)* **# PageDataContainerを辞書型へ変換**
    1. output_dict_list.append(dict_tmp) **# 作成した辞書をグローバル変数へ格納**
4. for d in output_dict_list: **# 格納しておいたアウトプット辞書を１つずつ取り出し**
    1. *dict_to_xml(d)* **# 辞書をxmlへ出力**

### df_to_containerメソッド
#### 引数
- 入力csvのdf（1スレッド分）
- スレッドのindex
#### 返り値
- 1スレッド分のPageDataContainerClass
#### 処理
- PageDataContainerClassオブジェクトの初期化
- df内の各データを該当するメンバに割当
- 必要に応じてクラスメソッドへ処理を切り分け

### container_to_dictメソッド
#### 引数
- 1スレッド分のPageDataContainerClass
- テンプレートxmlのdict
#### 返り値
- 1スレッド分の出力dict
#### 処理
- PageDataContainerClassオブジェクトをもとに出力xmlのもととなるdictの作成
- テンプレートdictをコピー
- xmlに必要なテキストデータの整形→dictへ格納
- Key名について、要調査事項を参照

### dict_to_xmlメソッド
#### 引数
- xml出力用dict
#### 処理
- dictオブジェクトをxml形式のテキストに変換
- テキストファイルの出力

## 要調査事項
- dict -> xmlとする場合、並列する同一タグをどう扱うのか？
  - <page></page>タグが1つのxmlファイルに複数回、同じ階層に現れる
  - しかし、辞書型を使うと'page'キーは１つしか使えない
  - 対処方法を検討する必要あり
    - 仮に['page1'], ['page2']とおいておいて、テキスト出力後に修正…？

## 検討項目
- df -> ContainerClass -> dict を1つのfor loopでやらずとも、それぞれでfor loopを回しても良い
  - その方が、中間データのContainerClassをグローバル変数として保持できる