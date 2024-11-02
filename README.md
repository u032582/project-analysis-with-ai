# プロジェクト名

このプロジェクトは、フォルダの構造を解析し、ファイルとディレクトリの数を数え、ファイルの総サイズを計算するためのPythonスクリプトです。さらに、フォルダ内のファイルをGPT（Generative Pre-trained Transformer）を使用して解析し、その結果をJSONファイルに保存する機能も提供しています。

## インストール

以下の手順に従って、必要な依存関係をインストールしてください。

1. 仮想環境を作成します（オプションですが推奨されます）。

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windowsの場合は `venv\Scripts\activate`
    ```

2. `requirements.txt`ファイルから依存関係をインストールします。

    ```bash
    pip install -r requirements.txt
    ```

## 使用方法

以下の手順に従って、スクリプトを実行してください。

1. スクリプトを実行します。

    ```bash
    python src/main.py
    ```

2. インタラクティブなメニューが表示されます。以下の選択肢から選んでください。

    - `new` または `n`: 新しい解析を開始します。
    - `inter` または `i`: 中間ファイルから続行します。
    - `update` または `u`: GPTを使用して解析を更新します。
    - `final` または `f`: 最終ファイルを確認します。

