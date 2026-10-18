"""ルートの .dockerignore が、ローカルの秘密情報や生成物をビルドコンテキストから除外しているかを確認する。

使い方: python scripts/check_docker_context.py

compose・Makefile・CI のビルドはリポジトリのルートを context にするため、効くのはルートの
.dockerignore だけ（apps/*/.dockerignore は使われない）。一時ディレクトリにルートの
.dockerignore と見本のファイルを置き、`COPY . /ctx/` だけのイメージを docker で作って、
イメージに入ったファイルを確かめる。docker が必要。
"""

import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ビルドコンテキストに入ってはいけないファイル（作業ツリーに残りうる秘密情報・ログ・生成物）
MUST_EXCLUDE = [
    ".env",
    ".env.azure",
    "apps/api/.env",
    "apps/api/error.log",
    "apps/admin/.env",
    "apps/admin/.env.local",
    "apps/public-viewer/.env",
    "apps/public-viewer/.env.local",
    "apps/public-viewer/public/meta/reporter.png",
    "apps/public-viewer/out-root/index.html",
    "packages/analysis-core/.env",
]

# ビルドに必要なので、除外してはいけないファイル
MUST_INCLUDE = [
    "apps/api/pyproject.toml",
    "apps/api/src/main.py",
    "apps/api/public/meta/default/reporter.png",
    "apps/public-viewer/package.json",
    "apps/public-viewer/public/images/dd2030-logo.svg",
    "packages/analysis-core/pyproject.toml",
]

DOCKERFILE = "FROM scratch\nCOPY . /ctx/\n"


def list_image_files(context: Path) -> set[str]:
    tag = f"kouchou-docker-context-check:{uuid.uuid4().hex[:12]}"
    subprocess.run(
        ["docker", "build", "-q", "-t", tag, "-f", "-", str(context)],
        input=DOCKERFILE.encode(),
        check=True,
        stdout=subprocess.DEVNULL,
    )
    container = None
    try:
        container = subprocess.run(
            ["docker", "create", tag, "/none"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        export = subprocess.run(
            ["docker", "export", container], check=True, capture_output=True
        ).stdout
        with tempfile.TemporaryFile() as fh:
            fh.write(export)
            fh.seek(0)
            with tarfile.open(fileobj=fh) as tar:
                names = tar.getnames()
    finally:
        if container:
            subprocess.run(
                ["docker", "rm", "-f", container], check=False, capture_output=True
            )
        subprocess.run(["docker", "rmi", "-f", tag], check=False, capture_output=True)
    prefix = "ctx/"
    return {name[len(prefix) :] for name in names if name.startswith(prefix)}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        context = Path(tmp)
        (context / ".dockerignore").write_bytes(
            (REPO_ROOT / ".dockerignore").read_bytes()
        )
        for rel in MUST_EXCLUDE + MUST_INCLUDE:
            path = context / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sentinel\n", encoding="utf-8")
        files = list_image_files(context)

    errors = [
        f"{rel} がビルドコンテキストに入る（ルートの .dockerignore で除外する）"
        for rel in MUST_EXCLUDE
        if rel in files
    ]
    errors += [
        f"{rel} がビルドコンテキストから除外されている（ビルドに必要）"
        for rel in MUST_INCLUDE
        if rel not in files
    ]
    if errors:
        print("\n".join(errors))
        return 1
    print("OK: .dockerignore")
    return 0


if __name__ == "__main__":
    sys.exit(main())
