# G検定 スキマ学習

[JDLA公式「G検定とは」](https://www.jdla.org/certificate/general/) のシラバス（G2024#6〜）に沿った用語アプリです。スマホでは **章を選ぶ → 3 / 5 / 10 / 15問** ですぐ解けます。

講座PDFは公開物に含めていません。解説は公式キーワードの短い独自まとめです。

## スマホでの使い方

1. 上のメニューで「章から学ぶ」
2. 章のカードで **3問 / 5問 / 10問 / 15問** をタップ
3. 間違えたら「弱点ノートに追加」
4. 「弱点」タブから Excel / Word を端末に保存

公開版はサーバー上にファイルが残りません。外出先で追加したら、その場でダウンロードしてください。次に使うときは「以前のExcelを読み込む」で続きからできます。

## ローカル起動

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Streamlit Cloud への公開

1. このフォルダのうち `app.py` / `requirements.txt` / `g_study/` / `.streamlit/` だけを GitHub に上げる（PDFは上げない）
2. [share.streamlit.io](https://share.streamlit.io/) でそのリポジトリを選択
3. Main file は `app.py`
