"""セットアップスクリプトが生成した .env に、必要な環境変数が揃っているかを確認する。

使い方: python scripts/check_setup_env.py <生成された .env のパス>

.env.example のキーは、セットアップスクリプトが書き出すか、下の OPTIONAL_KEYS で
「書き出さなくてよい」と明示するかのどちらかにする。.env.example に変数を追加した時は、
セットアップスクリプトに追加するか OPTIONAL_KEYS に理由つきで追加すること。
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# セットアップスクリプトが書き出さなくてよいキー（コードまたは compose に既定値があるもの）
OPTIONAL_KEYS = {
    "OPENROUTER_API_KEY",  # 任意のプロバイダ
    "WITH_GPU",  # compose の既定値 false
    "NUMBA_CPU_NAME",  # compose の既定値 generic
    "BASIC_AUTH_USERNAME",  # 未設定なら Basic 認証なし
    "BASIC_AUTH_PASSWORD",
    "NEXT_PUBLIC_LOCAL_LLM_ADDRESS",  # admin の既定値 ollama:11434
    "OLLAMA_HOST_PORT",  # compose の既定値 11434
    "NEXT_PUBLIC_GA_MEASUREMENT_ID",  # 未設定なら計測なし
    "NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID",
    "NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH",  # 既定値は空
    # Azure は .env.example の値がダミーなので、書き出すと未設定時のエラー案内が出なくなる
    "AZURE_CHATCOMPLETION_ENDPOINT",
    "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME",
    "AZURE_CHATCOMPLETION_VERSION",
    "AZURE_CHATCOMPLETION_API_KEY",
    "AZURE_EMBEDDING_ENDPOINT",
    "AZURE_EMBEDDING_DEPLOYMENT_NAME",
    "AZURE_EMBEDDING_VERSION",
    "AZURE_EMBEDDING_API_KEY",
    "AZURE_CHATCOMPLETION_MODEL_NAME",
    "AZURE_CHATCOMPLETION_INPUT_PRICE",
    "AZURE_CHATCOMPLETION_OUTPUT_PRICE",
    "LLM_REQUEST_TIMEOUT_SECONDS",  # analysis-core の既定値 300
    "OPENAI_USE_FLEX",  # 未設定なら Flex を使わない
    "OPENAI_FLEX_TIMEOUT_SECONDS",  # analysis-core の既定値 900
}

ENV_LINE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=(.*)$")
# compose.yaml の ${VAR} のうち、${VAR:-default} のような既定値がないもの
COMPOSE_VAR_WITHOUT_DEFAULT = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = ENV_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def main() -> int:
    # Windows の CI でも日本語のメッセージを出力できるようにする
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    generated = read_env(Path(sys.argv[1]))
    example_keys = set(read_env(REPO_ROOT / ".env.example"))
    compose_keys = set(
        COMPOSE_VAR_WITHOUT_DEFAULT.findall(
            (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
        )
    )

    errors = []
    for key in sorted(example_keys - OPTIONAL_KEYS):
        if key not in generated:
            errors.append(
                f"{key} は .env.example にあるが、生成された .env にない（不要なら OPTIONAL_KEYS に追加）"
            )
    for key in sorted(compose_keys):
        if not generated.get(key):
            errors.append(
                f"{key} は compose.yaml で既定値なしに参照されているが、生成された .env で空または未設定"
            )
    for key in sorted(OPTIONAL_KEYS - example_keys):
        errors.append(
            f"{key} は OPTIONAL_KEYS にあるが、.env.example にない（OPTIONAL_KEYS から削除）"
        )

    if errors:
        print("\n".join(errors))
        return 1
    print(f"OK: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
