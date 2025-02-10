import streamlit as st
import os
import subprocess
import time
import shutil
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
# セッション状態の初期化
# ─────────────
if "stage" not in st.session_state:
    st.session_state["stage"] = "requirements"

if "generated_prompt" not in st.session_state:
    st.session_state["generated_prompt"] = ""
if "generated_code" not in st.session_state:
    st.session_state["generated_code"] = ""
if "revised_prompt" not in st.session_state:
    st.session_state["revised_prompt"] = ""
if "stop_test" not in st.session_state:
    st.session_state["stop_test"] = False

if "questions" not in st.session_state:
    st.session_state["questions"] = [
        "【業務目的】このシステムで実現したい目的は何ですか？",
        "【利用者】主な利用者や対象ユーザーは誰ですか？",
        "【主要機能】実現したい主要な機能は何ですか？",
        "【業務プロセスとコンテキスト】システムが組み込まれる業務プロセスや、必要な背景情報（コンテキスト）について教えてください。",
        "【課題と期待効果】システム導入により解決したい課題や期待する効果は何ですか？",
        "【システム環境】このシステムは、Python、Poetry、Streamlitがインストールされたローカル環境で動作する簡易Webアプリとして実行されることを前提とします。その他必要な要件があれば教えてください。"
    ]
if "answers" not in st.session_state:
    st.session_state["answers"] = {}
if "additional_answers" not in st.session_state:
    st.session_state["additional_answers"] = []
if "additional_question" not in st.session_state:
    st.session_state["additional_question"] = None

st.title("要件定義＆コード生成アシスタント")

# ─────────────
# 安全に再読み込みする関数
# ─────────────
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.info("ページを手動で再読み込みしてください。")

# ─────────────
# Step2 (システム要件定義) + Step3 (コード生成) を内部的にまとめて実行する関数
# ─────────────
def generate_prompt_and_code_internally(requirements_text: str) -> None:
    """
    Step2(システム要件定義)とStep3(コード生成)をUI表示なしで内部的に実行。
    生成結果を st.session_state["generated_code"] に保存する。
    """
    # Step2: システム要件定義（プロンプト生成）
    with st.spinner("システム要件定義（プロンプト生成）を内部的に実行中…"):
        llm = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key)
        system_prompt_2 = (
            "あなたは有能なシステムアーキテクトです。以下の業務要件定義サマリーをもとに、"
            "システムは、Python、Poetry、Streamlitがインストールされたローカル環境で動作する簡易Webアプリとして実行されることを前提に、"
            "その他必要な要件を考慮した具体的な指示プロンプトを生成してください。"
            "出力はマークダウン形式で、特別な指示がなければこの環境向けに生成してください。"
        )
        step2_messages = [
            SystemMessage(content=system_prompt_2),
            HumanMessage(content=requirements_text)
        ]
        step2_response = llm.invoke(step2_messages)
        st.session_state["generated_prompt"] = step2_response.content

    # Step3: コード生成
    with st.spinner("コード生成中…"):
        llm2 = ChatOpenAI(model="o1", openai_api_key=openai_api_key)
        system_prompt_3 = (
            "以下の指示プロンプトに基づいて、"
            "システムは、Python、Poetry、Streamlitがインストールされたローカル環境で動作する簡易Webアプリとして、"
            "環境構築から実行までを自動化するシェルスクリプトを生成してください。"
            "具体的には、Poetry環境のセットアップ、依存関係のインストール、必要なディレクトリやファイルの作成、"
            "そしてStreamlitアプリの起動までを含む内容にしてください。"
            "\n\n【出力形式】以下のフォーマットに厳密に従って出力してください。余計な文言は含めず、"
            "区切り線はシェルスクリプト内のコメント行として出力してください。"
            "\n\n例："
            "\n# [使い方]"
            "\n# （ここに使い方の説明を記述）"
            "\n# [シェルスクリプト]"
            "\n#!/bin/bash"
            "\n# （ここにシェルスクリプト本文を記述）"
        )
        step3_messages = [
            SystemMessage(content=system_prompt_3),
            HumanMessage(content=st.session_state["generated_prompt"])
        ]
        step3_response = llm2.invoke(step3_messages)
        st.session_state["generated_code"] = step3_response.content

# ─────────────
# 追加質問生成関数
# ─────────────
def generate_additional_question(summary_text: str) -> str:
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key)
    system_prompt = (
        "あなたは有能なシステムアーキテクトです。以下の業務要件定義サマリーをもとに、"
        "不足している情報があれば具体的かつ詳細な追加質問を1件生成してください。"
        "全ての必要な情報が揃っている場合は『追加の質問は不要です』と返答してください。"
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=summary_text)]
    response = llm.invoke(messages)
    return response.content.strip()

# ─────────────
# コード生成関数（内部処理用）
# ─────────────
def generate_code_internally(prompt_text: str) -> str:
    llm = ChatOpenAI(model="o1", openai_api_key=openai_api_key)
    system_prompt = (
        "以下の指示プロンプトに基づいて、"
        "システムは、Python、Poetry、Streamlitがインストールされたローカル環境で動作する簡易Webアプリとして、"
        "環境構築から実行までを自動化するシェルスクリプトを生成してください。"
        "具体的には、Poetry環境のセットアップ、依存関係のインストール、必要なディレクトリやファイルの作成、"
        "そしてStreamlitアプリの起動までを含む内容にしてください。"
        "\n\n【出力形式】以下のフォーマットに厳密に従って出力してください。余計な文言は含めず、"
        "区切り線はシェルスクリプト内のコメント行として出力してください。"
        "\n\n例："
        "\n# [使い方]"
        "\n# （ここに使い方の説明を記述）"
        "\n# [シェルスクリプト]"
        "\n#!/bin/bash"
        "\n# （ここにシェルスクリプト本文を記述）"
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt_text)
    ]
    response = llm.invoke(messages)
    return response.content

# ─────────────
# フィードバック後の更新用（内部処理用）
# ─────────────
def generate_updated_code(prompt_text: str) -> str:
    return generate_code_internally(prompt_text)

# ─────────────
# エラー修正やテスト実行の関数
# ─────────────
def fix_shell_script(original_script: str, error_message: str) -> str:
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key)
    system_prompt = (
        "あなたはシェルスクリプトのエラー修正の専門家です。以下のシェルスクリプトと実行時のエラー出力をもとに、"
        "エラーを解消するためのシェルスクリプトの修正案を生成してください。"
    )
    combined_input = f"【シェルスクリプト】\n{original_script}\n\n【エラー出力】\n{error_message}"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=combined_input)]
    response = llm.invoke(messages)
    return response.content.strip()

def execute_test_with_retries(shell_script: str, max_attempts=3):
    attempt = 0
    current_script = shell_script
    final_stdout, final_stderr = "", ""
    base_dir = os.path.join(os.getcwd(), "test_run_pj")
    os.makedirs(base_dir, exist_ok=True)
    test_dir = ""

    while attempt < max_attempts:
        # 停止フラグチェック
        if st.session_state.get("stop_test", False):
            st.info("テスト実行が停止されました。")
            if test_dir and os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)
            break

        attempt += 1
        test_dir = os.path.join(base_dir, f"test_project_{int(time.time())}")
        os.makedirs(test_dir, exist_ok=True)
        script_path = os.path.join(test_dir, "run.sh")
        with open(script_path, "w") as f:
            f.write(current_script)
        os.chmod(script_path, 0o755)

        with st.spinner(f"プロジェクト作成・実行中…（試行 {attempt}）"):
            result = subprocess.run(["/bin/bash", "run.sh"], cwd=test_dir, capture_output=True, text=True)
        if result.returncode == 0:
            final_stdout, final_stderr = result.stdout, result.stderr
            break
        else:
            shutil.rmtree(test_dir, ignore_errors=True)
            current_script = fix_shell_script(current_script, result.stderr)

    return final_stdout, final_stderr, test_dir, attempt, current_script

# ─────────────
# ステージ1：業務要件定義
# ─────────────
if st.session_state["stage"] == "requirements":
    st.subheader("業務要件定義：質問に回答してください")
    with st.form(key="requirements_form"):
        answers_input = {}
        for i, question in enumerate(st.session_state["questions"]):
            answers_input[i] = st.text_area(
                f"質問 {i+1}: {question}",
                value=st.session_state["answers"].get(i, ""),
                key=f"q_{i}"
            )
        if st.form_submit_button("回答を保存"):
            st.session_state["answers"] = answers_input
            st.success("回答が保存されました。")

    if st.session_state["answers"]:
        # 確認・コード生成ボタン
        if st.button("情報が十分かチェックしてコード生成へ", key="check_and_generate"):
            # 業務要件定義サマリー相当を組み立て（画面に表示はしない）
            summary_text = ""
            for idx, question in enumerate(st.session_state["questions"]):
                summary_text += f"{question}\n回答: {st.session_state['answers'].get(idx, '未回答')}\n\n"
            if st.session_state["additional_answers"]:
                summary_text += "追加質問への回答:\n"
                for ans in st.session_state["additional_answers"]:
                    summary_text += f"- {ans}\n"

            with st.spinner("追加質問を確認中..."):
                add_q = generate_additional_question(summary_text)

            if add_q.strip().startswith("追加の質問は不要です"):
                # 追加質問がなければそのままコード生成（Step2+3を内部実行）
                with st.spinner("コード生成中..."):
                    generate_prompt_and_code_internally(summary_text)
                st.session_state["stage"] = "feedback"  # フィードバック画面へ
                safe_rerun()
            else:
                st.session_state["additional_question"] = add_q
                st.warning("まだ不足情報があるようです。下の追加質問に回答してください。")

        # 追加質問があれば入力フォーム表示
        if st.session_state["additional_question"] and not st.session_state["additional_question"].strip().startswith("追加の質問は不要です"):
            st.markdown("### 追加質問")
            st.write(st.session_state["additional_question"])
            with st.form("additional_question_form"):
                ans_add = st.text_area("追加質問への回答:", key="additional_question_answer")
                if st.form_submit_button("保存"):
                    st.session_state["additional_answers"].append(ans_add.strip())
                    st.session_state["additional_question"] = None
                    st.success("追加回答が保存されました。")
                    safe_rerun()

# ─────────────
# ステージ2,3：非表示
# ─────────────
elif st.session_state["stage"] in ["prompt_generation", "code_generation"]:
    st.warning("処理は内部的に実行されます。この画面は表示されない想定です。")
    st.stop()

# ─────────────
# ステージ4：テストフィードバック（コード確認＋編集＋テスト）
# ─────────────
elif st.session_state["stage"] == "feedback":
    st.subheader("コード確認＆テストフィードバック")

    if not st.session_state["generated_code"]:
        st.error("コードが生成されていません。Step1で回答し、コード生成を実行してください。")
    else:
        # 生成されたコードを区切り文字で分割
        if "[シェルスクリプト]" in st.session_state["generated_code"]:
            parts = st.session_state["generated_code"].split("[シェルスクリプト]")
            instructions = parts[0].strip()
            shell_script = parts[1].strip() if len(parts) > 1 else ""
        else:
            instructions = ""
            shell_script = st.session_state["generated_code"]

        st.markdown("### シェルスクリプトの使い方 (編集可)")
        new_instructions = st.text_area("使い方", instructions, height=100, key="instructions_edit_fb")
        st.markdown("### 生成されたシェルスクリプト (編集可)")
        edited_shell = st.text_area("シェルスクリプト本文", shell_script, height=300, key="shell_script_edit_fb")
        # ユーザー編集内容を session_state["generated_code"] に戻す
        st.session_state["generated_code"] = f"{new_instructions}\n[シェルスクリプト]\n{edited_shell}"

        # フィードバックフォーム
        with st.form("feedback_form"):
            feedback_input = st.text_area("フィードバックを入力してください", height=150, key="feedback_input")
            if st.form_submit_button("フィードバックを送信してコード更新"):
                def generate_revised_prompt(original_prompt: str, feedback: str) -> str:
                    llm = ChatOpenAI(model="o1", openai_api_key=openai_api_key)
                    system_prompt = (
                        "あなたは有能なシステムアーキテクトです。以下の既存の指示プロンプトと、実際の実装・テストのフィードバックをもとに、"
                        "修正された指示プロンプトを生成してください。出力はマークダウン形式で行ってください。"
                    )
                    combined_input = (
                        "【元の指示プロンプト】\n" + st.session_state["generated_prompt"] + "\n\n" +
                        "【テストフィードバック】\n" + feedback
                    )
                    messages = [SystemMessage(content=system_prompt), HumanMessage(content=combined_input)]
                    response = llm.invoke(messages)
                    return response.content

                with st.spinner("コード更新中..."):
                    try:
                        revised_prompt = generate_revised_prompt(st.session_state["generated_prompt"], feedback_input)
                        # 新しいコードを生成
                        new_code = generate_code_internally(revised_prompt)
                        st.session_state["generated_code"] = new_code
                        st.success("コードが更新されました。")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

        st.markdown("---")
        st.markdown("## テスト実行")
        if st.button("テストを実行", key="run_test"):
            st.session_state["stop_test"] = False
            if st.button("停止", key="stop_test_button"):
                st.session_state["stop_test"] = True

            # テスト実行ロジック
            # 生成コードを改めて区切り文字で抽出
            if "[シェルスクリプト]" in st.session_state["generated_code"]:
                parts2 = st.session_state["generated_code"].split("[シェルスクリプト]")
                shell_script2 = parts2[1].strip() if len(parts2) > 1 else ""
            else:
                shell_script2 = st.session_state["generated_code"]

            # execute_test_with_retriesで最大3回まで修正試行
            final_out, final_err, test_dir, attempt_used, final_script = execute_test_with_retries(shell_script2)
            st.subheader("テスト実行結果")
            st.text_area("標準出力", final_out, height=150)
            st.text_area("標準エラー出力", final_err, height=150)
            st.write(f"最終試行: {attempt_used} 回目")
            st.write(f"最終試行のディレクトリ: {test_dir}")