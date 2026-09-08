"""Opt-in, read-only validation of shared report artifacts (no LLM calls)."""

import argparse
import json
import math
from pathlib import Path


def validate_output(data):
    """Check structural invariants needed by both viewers, not analytical quality."""
    errors = []
    if not isinstance(data, dict):
        return ["report must be an object"]
    clusters = data.get("clusters")
    arguments = data.get("arguments")
    if not isinstance(clusters, list) or not clusters:
        return ["clusters must be a non-empty array"]
    if not isinstance(arguments, list):
        return ["arguments must be an array"]
    groups = {}
    for index, group in enumerate(clusters):
        if not isinstance(group, dict) or not isinstance(group.get("id"), str) or not group["id"]:
            errors.append(f"clusters[{index}]: missing string id")
            continue
        if group["id"] in groups:
            errors.append(f"clusters[{index}]: duplicate id")
        groups[group["id"]] = group
        for field in ("label", "takeaway", "parent"):
            if not isinstance(group.get(field), str):
                errors.append(f"clusters[{index}]: {field} must be a string")
        value = group.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            errors.append(f"clusters[{index}]: invalid value")
    root = clusters[0].get("id") if isinstance(clusters[0], dict) else None
    for index, group in enumerate(clusters):
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            continue
        visited = set()
        current = group["id"]
        while current != root:
            if not isinstance(current, str) or current not in groups:
                errors.append(f"clusters[{index}]: parent chain does not reach root")
                break
            if current in visited:
                errors.append(f"clusters[{index}]: parent cycle")
                break
            visited.add(current)
            current = groups[current].get("parent")
    ids = set(groups)
    for index, arg in enumerate(arguments):
        if not isinstance(arg, dict):
            errors.append(f"arguments[{index}]: must be an object")
            continue
        arg_id = arg.get("arg_id")
        if not isinstance(arg_id, str) or not arg_id or arg_id in ids:
            errors.append(f"arguments[{index}]: missing or duplicate id")
        else:
            ids.add(arg_id)
        if not isinstance(arg.get("argument"), str):
            errors.append(f"arguments[{index}]: argument must be a string")
        for field in ("x", "y"):
            value = arg.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                errors.append(f"arguments[{index}]: {field} must be finite")
        path = arg.get("cluster_ids")
        if not isinstance(path, list) or not path or path[0] != root:
            errors.append(f"arguments[{index}]: path must start at root")
            continue
        for position, group_id in enumerate(path):
            if not isinstance(group_id, str) or group_id not in groups:
                errors.append(f"arguments[{index}]: unknown cluster reference")
                break
            if position and groups[group_id].get("parent") != path[position - 1]:
                errors.append(f"arguments[{index}]: inconsistent cluster path")
                break
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="レポートJSONの参照整合性を検査します（読み取り専用）")
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.report.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        print("レポートJSONを読み込めません。パス・文字コード・JSON形式を確認してください。")
        return 2
    errors = validate_output(data)
    for error in errors:
        print(error)
    print(f"参照整合性検査: {len(errors)}件の問題")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
