"""embeddings.pkl の書き込み・読み込みの共通処理。

embeddings.pkl の形式:

- 現行: ``list[dict]``。各要素は ``{"arg-id": str, "embedding": np.ndarray}``
  （1 次元・float32）。
- 旧形式（読み込みのみ対応）:
  - ``list[dict]`` で ``"embedding"`` が Python float の list のもの
  - ``"arg-id"`` を持たない ``list[dict]``（行の順序で args.csv と対応させる）
  - pandas DataFrame（``"embedding"`` 列）

旧形式は ``--reuse-from`` やレポートの複製、ストレージ同期で残り続けるので、
読み込み側は全形式を扱う。現行形式も ``np.asarray([item["embedding"] ...])`` で
読めるので、旧バージョンの analysis-core からも読める。

埋め込みを Python float の list で持つと 1 値あたり約 32 バイトになり、
1536 次元・数万件で GB 単位のメモリを使う（float32 の配列なら 4 バイト）。
UMAP は入力を float32 に変換してから使うので、float32 で保存・展開しても
UMAP の入力は変わらない。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

EMBEDDING_DTYPE = np.float32


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
