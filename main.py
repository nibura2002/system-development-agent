import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# .env ファイルから環境変数をロード
load_dotenv()

# --- APIキーの設定 ---
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEYが設定されていません。.env ファイルに設定してください。")

# ─────────────
# セッション状態の初期化（辞書形式で）
# ─────────────
if "stage" not in st.session_state:
    st.session_state["stage"] = "requirements"

if "generated_prompt" not in st.session_state:
    st.session_state["generated_prompt"] = ""
if "generated_code" not in st.session_state:
    st.session_state["generated_code"] = ""
if "revised_prompt" not in st.session_state:
    st.session_state["revised_prompt"] = ""

if "questions" not in st.session_state:
    st.session_state["questions"] = [
        "【業務目的】このシステムで実現したい目的は何ですか？",
        "【利用者】主な利用者や対象ユーザーは誰ですか？",
        "【主要機能】実現したい主要な機能は何ですか？",
        "【業務プロセスとコンテキスト】システムが組み込まれる業務プロセスや、必要な背景情報（コンテキスト）について教えてください。",
        "【課題と期待効果】システム導入により解決したい課題や期待する効果は何ですか？",
        "【システム環境】システムをどのような環境で構築しますか？ (特別な指示がなければ、Poetry環境でStreamlitで動作するコードを生成します)"
    ]
if "answers" not in st.session_state:
    st.session_state["answers"] = {}
if "additional_answers" not in st.session_state:
    st.session_state["additional_answers"] = []
if "additional_question" not in st.session_state:
    st.session_state["additional_question"] = None

st.title("対話型 システム要件定義＆コード生成アシスタント")

# ─────────────
# 安全に再読み込みするための関数
# ─────────────
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.info("ページを手動で再読み込みしてください。")

# ─────────────
# サイドバー：ボタンのスタイルを設定する CSS（幅80%、中央揃え）
# ─────────────
sidebar_buttons_css = """
<style>
[data-testid="stSidebar"] button {
    width: 80% !important;
    margin: 10px auto !important;
    display: block;
}
</style>
"""
st.sidebar.markdown(sidebar_buttons_css, unsafe_allow_html=True)

# ─────────────
# サイドバー：各ステップへの遷移用ボタン
# ─────────────
if st.sidebar.button("業務要件定義", key="btn_req"):
    st.session_state["stage"] = "requirements"
    safe_rerun()
if st.sidebar.button("システム要件定義", key="btn_prompt"):
    st.session_state["stage"] = "prompt_generation"
    safe_rerun()
if st.sidebar.button("コード生成", key="btn_code"):
    st.session_state["stage"] = "code_generation"
    safe_rerun()
if st.sidebar.button("テストフィードバック", key="btn_feedback"):
    st.session_state["stage"] = "feedback"
    safe_rerun()

# ─────────────
# 下部ナビゲーションボタン
# ─────────────
def navigation_buttons():
    stage = st.session_state["stage"]
    cols = st.columns(2)
    # ステージ1：次へボタンのみ（完了状態なら次へが表示）
    if stage == "requirements":
        if st.session_state["answers"]:
            if cols[1].button("次へ"):
                st.session_state["stage"] = "prompt_generation"
                safe_rerun()
    # ステージ2：前へと次へ（次へは generated_prompt がある場合のみ）
    elif stage == "prompt_generation":
        if cols[0].button("前へ"):
            st.session_state["stage"] = "requirements"
            safe_rerun()
        if st.session_state["generated_prompt"]:
            if cols[1].button("次へ"):
                st.session_state["stage"] = "code_generation"
                safe_rerun()
    # ステージ3：前へと次へ（次へは generated_code がある場合のみ）
    elif stage == "code_generation":
        if cols[0].button("前へ"):
            st.session_state["stage"] = "prompt_generation"
            safe_rerun()
        if st.session_state["generated_code"]:
            if cols[1].button("次へ"):
                st.session_state["stage"] = "feedback"
                safe_rerun()
    # ステージ4：前へボタンのみ
    elif stage == "feedback":
        if cols[0].button("前へ"):
            st.session_state["stage"] = "code_generation"
            safe_rerun()

# ─────────────
# ステージ1：業務要件定義
# ─────────────
if st.session_state["stage"] == "requirements":
    st.header("ステージ 1: 業務要件定義")
    st.markdown("**すべての質問に回答してください。**\n\n既に入力済みの回答は下に保持されています。")
    with st.form(key="requirements_form"):
        answers_input = {}
        for i, question in enumerate(st.session_state["questions"]):
            answers_input[i] = st.text_area(
                f"質問 {i+1}: {question}",
                value=st.session_state["answers"].get(i, ""),
                key=f"q_{i}"
            )
        if st.form_submit_button("回答を保存する"):
            st.session_state["answers"] = answers_input
            st.success("回答が保存されました。")
    if st.session_state["answers"]:
        md_summary = "# 業務要件定義サマリー\n\n"
        for idx, question in enumerate(st.session_state["questions"]):
            md_summary += f"**質問 {idx+1}:** {question}\n\n"
            md_summary += f"**回答:** {st.session_state['answers'].get(idx, '未回答')}\n\n"
        if st.session_state["additional_answers"]:
            md_summary += "## 追加質問への回答\n"
            for i, additional in enumerate(st.session_state["additional_answers"]):
                md_summary += f"**追加質問 {i+1} の回答:** {additional}\n\n"
        st.markdown(md_summary)
        all_answered = (len(st.session_state["answers"]) == len(st.session_state["questions"]))
        if all_answered and st.session_state["additional_question"] is None:
            st.session_state["additional_question"] = generate_additional_question(md_summary)
        if st.session_state["additional_question"] and st.session_state["additional_question"].strip().startswith("追加の質問は不要です"):
            st.success("全ての必要な情報が揃っています。")
        elif st.session_state["additional_question"]:
            st.markdown("### 追加の質問")
            st.write(st.session_state["additional_question"])
            with st.form("additional_question_form"):
                additional_ans = st.text_input("上記追加質問に対する回答を入力してください:")
                if st.form_submit_button("送信") and additional_ans:
                    st.session_state["additional_answers"].append(additional_ans.strip())
                    st.session_state["additional_question"] = None
                    st.success("追加質問への回答が保存されました。")
    navigation_buttons()

# ─────────────
# ステージ2：システム要件定義（指示プロンプト生成）
# ─────────────
elif st.session_state["stage"] == "prompt_generation":
    st.header("ステージ 2: システム要件定義（指示プロンプト生成）")
    requirements_summary = (
        f"## 業務目的\n{st.session_state['answers'].get(0, '未回答')}\n\n"
        f"## 利用者\n{st.session_state['answers'].get(1, '未回答')}\n\n"
        f"## 主要機能\n{st.session_state['answers'].get(2, '未回答')}\n\n"
        f"## 業務プロセスとコンテキスト\n{st.session_state['answers'].get(3, '未回答')}\n\n"
        f"## 課題と期待効果\n{st.session_state['answers'].get(4, '未回答')}\n\n"
        f"## システム環境\n{st.session_state['answers'].get(5, '未回答')}\n\n"
    )
    if st.session_state["additional_answers"]:
        requirements_summary += "## 追加質問への回答\n"
        for i, additional in enumerate(st.session_state["additional_answers"]):
            requirements_summary += f"追加回答 {i+1}: {additional}\n\n"
    st.markdown("### 業務要件定義サマリー")
    st.markdown(requirements_summary)
    def generate_prompt(req_text: str) -> str:
        llm = ChatOpenAI(
            model="gpt-4o",
            openai_api_key=openai_api_key
        )
        system_prompt = (
            "あなたは有能なシステムアーキテクトです。以下の業務要件定義サマリーをもとに、"
            "o1やo3などの推論モデルで処理させるための具体的な指示プロンプトを生成してください。"
            "業務目的、必要なコンテキスト、システム環境について詳細に記述し、"
            "出力はマークダウン形式で、特別な指示がなければ『Poetry環境でStreamlitで動作』する前提としてください。"
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=req_text)
        ]
        response = llm.invoke(messages)
        return response.content
    if st.button("指示プロンプトを生成する"):
        with st.spinner("指示プロンプト生成中…"):
            try:
                prompt_result = generate_prompt(requirements_summary)
                st.session_state["generated_prompt"] = prompt_result
                st.success("指示プロンプトが生成されました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
    if st.session_state["generated_prompt"]:
        st.subheader("生成された指示プロンプト")
        st.text_area("", st.session_state["generated_prompt"], height=300)
    navigation_buttons()

# ─────────────
# ステージ3：コード生成（o1 を使用）
# ─────────────
elif st.session_state["stage"] == "code_generation":
    st.header("ステージ 3: コード生成")
    if not st.session_state["generated_prompt"]:
        st.error("指示プロンプトが生成されていません。前のステップに戻ってください。")
    else:
        st.markdown("### 使用する指示プロンプト")
        st.text_area("", st.session_state["generated_prompt"], height=200)
        def generate_code(prompt_text: str) -> str:
            llm = ChatOpenAI(
                model="o1",
                openai_api_key=openai_api_key
            )
            system_message = (
                "以下の指示プロンプトに基づいて、"
                "プロジェクト全体を作成可能なシェルスクリプトを生成してください。"
                "シェルスクリプトには、必要なディレクトリ作成、ファイル配置、依存関係のインストール手順などを含めてください。"
                "出力は次の形式で行い、\n\n"
                "[使い方]\n<使い方の説明>\n\n[シェルスクリプト]\n<シェルスクリプト本文>"
            )
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt_text)
            ]
            response = llm.invoke(messages)
            return response.content
        if st.button("コードを生成する"):
            with st.spinner("コード生成中…"):
                try:
                    code_result = generate_code(st.session_state["generated_prompt"])
                    st.session_state["generated_code"] = code_result
                    st.success("シェルスクリプトが生成されました。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        if st.session_state["generated_code"]:
            if "[シェルスクリプト]" in st.session_state["generated_code"]:
                parts = st.session_state["generated_code"].split("[シェルスクリプト]")
                instructions = parts[0].strip()
                shell_script = parts[1].strip() if len(parts) > 1 else ""
            else:
                instructions = ""
                shell_script = st.session_state["generated_code"]
            st.subheader("シェルスクリプトの使い方")
            st.text_area("", instructions, height=150)
            st.subheader("生成されたシェルスクリプト")
            st.code(shell_script, language="bash")
    navigation_buttons()

# ─────────────
# ステージ4：テストフィードバック
# ─────────────
elif st.session_state["stage"] == "feedback":
    st.header("ステージ 4: テストフィードバック")
    if not st.session_state["generated_code"]:
        st.error("生成されたコードがありません。コード生成のステップに戻ってください。")
    else:
        if "[シェルスクリプト]" in st.session_state["generated_code"]:
            parts = st.session_state["generated_code"].split("[シェルスクリプト]")
            instructions = parts[0].strip()
            shell_script = parts[1].strip() if len(parts) > 1 else ""
        else:
            instructions = ""
            shell_script = st.session_state["generated_code"]
        st.markdown("### シェルスクリプトの使い方")
        st.text_area("", instructions, height=150)
        st.markdown("### 生成されたシェルスクリプト")
        st.code(shell_script, language="bash")
    with st.form("feedback_form"):
        feedback_input = st.text_area("フィードバックを入力してください", height=150)
        if st.form_submit_button("フィードバックを送信して指示プロンプトを修正する") and feedback_input:
            def generate_revised_prompt(original_prompt: str, feedback: str) -> str:
                llm = ChatOpenAI(
                    model="gpt-4o",
                    openai_api_key=openai_api_key
                )
                system_prompt = (
                    "あなたは有能なシステムアーキテクトです。以下の既存の指示プロンプトと、実際の実装・テストのフィードバックをもとに、"
                    "修正された指示プロンプトを生成してください。出力はマークダウン形式で行ってください。"
                )
                combined_input = (
                    "【元の指示プロンプト】\n" + original_prompt + "\n\n" +
                    "【テストフィードバック】\n" + feedback
                )
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=combined_input)
                ]
                response = llm.invoke(messages)
                return response.content
            with st.spinner("フィードバックを反映した指示プロンプトを生成中…"):
                try:
                    revised = generate_revised_prompt(st.session_state["generated_prompt"], feedback_input)
                    st.session_state["revised_prompt"] = revised
                    st.success("修正された指示プロンプトが生成されました。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
    if st.session_state["revised_prompt"]:
        st.subheader("修正された指示プロンプト")
        st.text_area("", st.session_state["revised_prompt"], height=300)
    cols = st.columns(2)
    with cols[0]:
        if st.button("前へ"):
            st.session_state["stage"] = "code_generation"
            safe_rerun()