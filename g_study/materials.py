from __future__ import annotations

from pathlib import Path

from .config import MATERIALS_DIR

PDF_CHAPTERS = [
    ("人工知能とは.pdf", "人工知能とは", "定義・古典的難問"),
    ("人工知能をめぐる動向.pdf", "人工知能をめぐる動向", "探索・知識・ML/DL史"),
    ("機械学習の具体的手法.pdf", "機械学習の概要", "教師あり／なし／強化学習・評価"),
    ("ディープラーニングの要素技術.pdf", "ディープラーニングの概要／要素技術", "層・最適化・Attention"),
    ("ディープラーニングの応用例.pdf", "ディープラーニングの応用例", "画像・言語・音声・生成・軽量化"),
    ("ディープラーニングの社会実装に向けて.pdf", "AIの社会実装に向けて", "プロジェクト・データ"),
    ("AIに必要な数理・統計知識①.pdf", "AIに必要な数理・統計知識", "統計の基礎①"),
    ("AIに必要な数理・統計知識②.pdf", "AIに必要な数理・統計知識", "統計の基礎②"),
    ("AIに関する法律と契約.pdf", "AIに関する法律と契約", "個情法・知財・契約"),
    ("AI倫理・AIガバナンス.pdf", "AI倫理・AIガバナンス", "公平性・安全・ガバナンス"),
    ("G検定チートシート.pdf", "横断", "既存の重要用語1枚まとめ"),
]


def list_pdfs() -> list[dict]:
    rows = []
    for name, chapter, note in PDF_CHAPTERS:
        path = MATERIALS_DIR / name
        rows.append(
            {
                "ファイル": name,
                "対応章": chapter,
                "内容": note,
                "あり": path.exists(),
                "path": path,
            }
        )
    extra = {
        p.name
        for p in MATERIALS_DIR.glob("*.pdf")
        if p.name not in {n for n, _, _ in PDF_CHAPTERS}
    }
    for name in sorted(extra):
        path = MATERIALS_DIR / name
        rows.append(
            {
                "ファイル": name,
                "対応章": "その他",
                "内容": "フォルダ内の追加PDF",
                "あり": True,
                "path": path,
            }
        )
    return rows


def open_path(path: Path) -> None:
    import os

    os.startfile(path)  # type: ignore[attr-defined]
