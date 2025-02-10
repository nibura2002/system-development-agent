# System development assistant
要件定義からコード生成してくれるアシスタント。PoCや簡単なテストラン向けの簡易的なもの。遊びで作成しているため何も整理されてはいない。また、動作は不安定である。


## 現状の仕様
- `poetry + python`環境構築済みであることが前提
- Streamlitを使用した簡単なWEB UI上で動作するPythonコードを生成
- プロジェクト作成から実行までを自動で実施するシェルスクリプトを出力し、UI上でコード実行まで実施
- OpenAIのAPIを使用してLLMを呼び出すようになっている。プロンプト生成には`gpt-4o`を使用。コード生成には`o1`を使用


## How to Use
ルートディレクトリに下記を記載した`.env`を作成して、main.pyをstreamlitで実行。
```
# .env
OPENAI_API_KEY='your-openai-key'
```

- 実行コマンド
```
poetry run streamlit run main.py 
```

## Tips
- 作成したコードが初回の実行でそのまま完全に動作するとは限らない。フィードバックにエラーメッセージをコピペしてLLMに修正させることで改善することが多い



test change
