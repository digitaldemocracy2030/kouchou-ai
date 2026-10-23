"""LLM への要求を workers 本のスレッドで回す共通処理。"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TypeVar

T = TypeVar("T")


def iter_pool_completed(
    fn: Callable[[T], Any],
    items: Sequence[T],
    workers: int,
    *,
    stop: Callable[[], bool] = lambda: False,
) -> Iterator[tuple[int, concurrent.futures.Future]]:
    """``items`` の各要素に ``fn`` を ``workers`` 本のスレッドで適用し、完了した順に ``(index, future)`` を返す。

    - 空いた worker にはすぐ次の要素を渡す。workers 件ずつのバッチの全件完了を待たないので、
      1 件の遅い応答（Flex・SDK の再試行・429 のバックオフなど）が他の worker を止めない。
    - 同時に実行中の要素は workers 件までに抑える（数万件の future を一度に作らない）。
    - 各 future を返したあと、次の要素を投入する前に ``stop()`` を確かめる。True なら新しい要素は
      投入せず、実行中の要素の完了だけを待って返す（実行中の要求は取り消せない）。
    - 結果の集計・進捗更新・ファイル書き込みは、呼び出し側がこのジェネレータを回すスレッド
      （メインスレッド）で行う。
    """
    workers = max(1, int(workers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        in_flight: dict[concurrent.futures.Future, int] = {}
        next_index = 0

        def fill() -> None:
            nonlocal next_index
            while next_index < len(items) and len(in_flight) < workers and not stop():
                in_flight[executor.submit(fn, items[next_index])] = next_index
                next_index += 1

        fill()
        while in_flight:
            done, _ = concurrent.futures.wait(in_flight, return_when=concurrent.futures.FIRST_COMPLETED)
            # 同時に終わったものは入力順に返す
            for future in sorted(done, key=in_flight.__getitem__):
                yield in_flight.pop(future), future
            fill()
