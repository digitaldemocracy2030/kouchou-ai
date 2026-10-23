"""embeddings.pkl の書き込み・読み込みの共通処理。

embeddings.pkl の形式:

- 現行: ``list[dict]``。各要素は ``{"arg-id": str, "embedding": np.ndarray}``
  （1 次元・float32）。
- 旧形式（読み込みのみ対応）:
  - ``list[dict]`` で ``"embedding"`` が Python float の list のもの
  - ``"arg-id"`` を持たない ``list[dict]``（行の順序で args.csv と対応させる）
  - pandas DataFrame（``"embedding"`` 列）。v2.0.0〜v4.0.0 が書いた形式。unpickle に
    pandas が要るので、pandas の入った環境でしか読めない（analysis-core と API の依存には
    pandas が無い）。実行計画では、埋め込みを読むステップが走るときに embedding を
    再実行して作り直す（``is_pandas_embeddings_pickle``）。

旧形式は ``--reuse-from`` やレポートの複製、ストレージ同期で残り続けるので、
読み込み側は全形式を扱う。現行形式も ``np.asarray([item["embedding"] ...])`` で
読めるので、旧バージョンの analysis-core からも読める。

埋め込みを Python float の list で持つと 1 値あたり約 32 バイトになり、
1536 次元・数万件で GB 単位のメモリを使う（float32 の配列なら 4 バイト）。
UMAP は入力を float32 に変換してから使うので、float32 で保存・展開しても
UMAP の入力は変わらない。
"""

from __future__ import annotations

import importlib.util
import io
import pickle
import pickletools
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

EMBEDDING_DTYPE = np.float32

# pickle の先頭（トップレベルのオブジェクトのクラス参照）を調べる範囲
_PICKLE_HEADER_BYTES = 64 * 1024
_STRING_OPCODES = {
    "STRING",
    "BINSTRING",
    "SHORT_BINSTRING",
    "UNICODE",
    "BINUNICODE",
    "SHORT_BINUNICODE",
    "BINUNICODE8",
}


class LegacyEmbeddingsFormatError(RuntimeError):
    """pandas の無い環境で、旧形式（pandas の DataFrame）の embeddings.pkl を読もうとした。"""


def _top_level_class_module(path: Path) -> str | None:
    """pickle のトップレベルのオブジェクトのクラスの module 名を、unpickle せずに返す。

    クラスのインスタンスでない（list などの）場合、読めない場合は None を返す。
    先頭だけを pickletools で走査するので、ファイルが大きくても速い。
    """
    try:
        with open(path, "rb") as f:
            head = f.read(_PICKLE_HEADER_BYTES)
    except OSError:
        return None

    strings: list[Any] = []
    memo: dict[int, Any] = {}
    last: Any = None
    try:
        for opcode, arg, _ in pickletools.genops(io.BytesIO(head)):
            name = opcode.name
            if name in ("PROTO", "FRAME"):
                continue
            if name in _STRING_OPCODES:
                last = arg
                strings.append(arg)
            elif name == "MEMOIZE":
                memo[len(memo)] = last
            elif name in ("PUT", "BINPUT", "LONG_BINPUT"):
                memo[arg] = last
            elif name in ("GET", "BINGET", "LONG_BINGET"):
                last = memo.get(arg)
                strings.append(last)
            elif name == "GLOBAL":
                # arg は "module name"
                return str(arg).split(" ", 1)[0]
            elif name == "STACK_GLOBAL":
                module = strings[-2] if len(strings) >= 2 else None
                return module if isinstance(module, str) else None
            else:
                # list / dict などから始まる（トップレベルがクラスのインスタンスではない）
                return None
    except Exception:
        # 先頭で切ったための途中終了や、pickle でないファイル
        return None
    return None


def is_pandas_embeddings_pickle(path: str | Path) -> bool:
    """embeddings.pkl が旧形式（pandas のオブジェクトの pickle）かを、unpickle せずに判定する。

    pandas の有無に関係なく同じ結果を返すので、実行計画や再利用の判定に使える。
    """
    module = _top_level_class_module(Path(path))
    return module is not None and (module == "pandas" or module.startswith("pandas."))


def _pandas_available() -> bool:
    return importlib.util.find_spec("pandas") is not None


def load_embeddings_pickle(path: str | Path) -> Any:
    """embeddings.pkl を読む。

    旧形式（pandas の DataFrame）を pandas の無い環境で読もうとした場合は、unpickle の
    ModuleNotFoundError ではなく、原因と対処の分かる LegacyEmbeddingsFormatError を投げる。
    """
    path = Path(path)
    if not _pandas_available() and is_pandas_embeddings_pickle(path):
        raise LegacyEmbeddingsFormatError(
            f"{path} is in the old embeddings.pkl format (pandas DataFrame, written by v4.0.0 or earlier) "
            "and cannot be read without pandas. Re-run from the embedding step "
            "(remove embeddings.pkl, or run with --only embedding) to regenerate it."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


def to_embedding_rows(embeds: Iterable[Sequence[float]]) -> list[np.ndarray]:
    """API が返した 1 バッチ分の埋め込みを、float32 の行（1 次元配列）の list にする。"""
    batch = np.asarray(embeds, dtype=EMBEDDING_DTYPE)
    if batch.ndim != 2:
        raise ValueError(f"埋め込みの形が不正です: shape={batch.shape}")
    return list(batch)


def build_embedding_records(arg_ids: Sequence[Any], rows: Sequence[np.ndarray]) -> list[dict[str, Any]]:
    """embeddings.pkl に保存する list[dict] を作る。"""
    if len(arg_ids) != len(rows):
        raise ValueError(f"arg-id と埋め込みの件数が一致しません: arg_ids={len(arg_ids)}, embeddings={len(rows)}")
    return [{"arg-id": arg_id, "embedding": row} for arg_id, row in zip(arg_ids, rows, strict=True)]


def stack_embedding_rows(rows: Sequence[Any], dtype: Any = EMBEDDING_DTYPE) -> np.ndarray:
    """行（list[float] または 1 次元配列）の並びを 2 次元配列にする。

    ``np.asarray(rows)`` と違い、出力の配列を先に確保して 1 行ずつ埋めるので、
    float64 の中間配列を作らない。
    """
    n_rows = len(rows)
    if n_rows == 0:
        return np.empty((0, 0), dtype=dtype)
    first = np.asarray(rows[0], dtype=dtype)
    if first.ndim != 1:
        raise ValueError(f"埋め込みの行の形が不正です: shape={first.shape}")
    width = first.shape[0]
    out = np.empty((n_rows, width), dtype=dtype)
    for index, row in enumerate(rows):
        row_array = np.asarray(row, dtype=dtype)
        # 次元数の違う行を代入すると、長さ 1 の行が全列にブロードキャストされて
        # 誤った座標になるので、形がそろわない行は読み込みエラーにする
        if row_array.shape != (width,):
            raise ValueError(
                f"埋め込みの次元がそろっていません: 行 {index} の shape={row_array.shape}、先頭行の次元={width}"
            )
        out[index] = row_array
    return out
