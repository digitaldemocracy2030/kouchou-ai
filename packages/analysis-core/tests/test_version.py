"""pyproject.toml の version と analysis_core.__version__ の一致を確かめる。

`kouchou-analyze --version` は __version__ を表示するので、リリース時に片方だけ更新すると
公開物のメタデータと CLI の表示が食い違う。
"""

import tomllib
from pathlib import Path

import analysis_core


def test_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with open(pyproject, "rb") as f:
        version = tomllib.load(f)["project"]["version"]

    assert analysis_core.__version__ == version
