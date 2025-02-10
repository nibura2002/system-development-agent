# FROM 行を Python 3.12-slim に変更
FROM python:3.12-slim

# Cloud Run が利用するポートを設定（デフォルトは8080）
ENV PORT 8080
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# システムパッケージの更新および必要なツールのインストール
RUN apt-get update && apt-get install -y build-essential curl

# Poetry のインストール
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# 作業ディレクトリの作成
WORKDIR /app

# pyproject.toml と poetry.lock をコピーして依存関係のインストール
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# アプリケーションコードのコピー
COPY . .

# Cloud Run 用ポートの公開
EXPOSE ${PORT}

# Streamlit アプリの起動
CMD ["streamlit", "run", "main.py", "--server.port", "8080", "--server.enableCORS", "false"]