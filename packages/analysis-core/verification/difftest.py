"""Lean のモデル（verification/lean）と本物のコードを、同じ乱数入力で突き合わせる差分テスト。

Lean で証明した性質は「モデルについて」の性質なので、モデルがコードと同じ振る舞いをすることをここで確かめる。

    cd verification/lean && lake build
    cd ../.. && .venv/bin/python -m pytest verification/difftest.py -q

対象
- resolve_execution_order / validate_dependencies（workflow/resolver.py）
- decide_what_to_run（core/orchestration.py）。`_disabled_reason` だけは差し替えて、任意の工程を無効にできるようにする
- melt_cluster_data / _build_parent_child_mapping と left join（steps/hierarchical_merge_labelling.py）
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import polars as pl
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from analysis_core.core import orchestration
from analysis_core.steps.hierarchical_merge_labelling import _build_parent_child_mapping, melt_cluster_data
from analysis_core.workflow.definition import WorkflowDefinition, WorkflowStep
from analysis_core.workflow.resolver import (
    CyclicDependencyError,
    DuplicateStepError,
    MissingDependencyError,
    resolve_execution_order,
    validate_dependencies,
)

ORACLE = Path(__file__).parent / "lean" / ".lake" / "build" / "bin" / "oracle"
EXAMPLES = 1500


@pytest.fixture(scope="module")
def oracle():
    if not ORACLE.exists():
        pytest.skip("lake build で oracle を作ってから実行する")
    proc = subprocess.Popen([str(ORACLE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def ask(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    yield ask
    proc.stdin.close()
    proc.wait()


# ---------------------------------------------------------------- resolver

steps_strategy = st.integers(0, 6).flatmap(
    lambda n: st.lists(
        st.tuples(
            # たまに id を重複させる
            st.integers(0, max(n - 1, 0)) if n else st.just(0),
            st.lists(st.integers(0, n + 1), max_size=4),  # n, n+1 は存在しない工程
        ),
        min_size=n,
        max_size=n,
    )
)


def unique_ids(draw_steps):
    """大半のケースは id を 0..n-1 にそろえる（重複ありのケースは別に混ぜる）"""
    return [(k, deps) for k, (_, deps) in enumerate(draw_steps)]


def to_workflow(steps):
    return WorkflowDefinition(
        id="w",
        version="1",
        steps=[WorkflowStep(id=str(i), plugin="p", depends_on=[str(d) for d in deps]) for i, deps in steps],
    )


def py_resolve(steps):
    try:
        return {"ok": [int(x) for x in resolve_execution_order(to_workflow(steps))]}
    except DuplicateStepError as e:
        return {"duplicate": [int(x) for x in ast.literal_eval(str(e).split("more than one step: ", 1)[1])]}
    except MissingDependencyError as e:
        s, d = re.match(r"Step '(\d+)' depends on non-existent step '(\d+)'", str(e)).groups()
        return {"missing": [int(s), int(d)]}
    except CyclicDependencyError as e:
        return {"cyclic": [int(x) for x in ast.literal_eval(str(e).split("involving steps: ", 1)[1])]}


def parse_msg(msg):
    if m := re.fullmatch(r"Step ID '(\d+)' is used by more than one step", msg):
        return ["duplicate", int(m.group(1))]
    if m := re.fullmatch(r"Step '(\d+)' depends on itself", msg):
        return ["self", int(m.group(1))]
    if m := re.fullmatch(r"Step '(\d+)' depends on non-existent step '(\d+)'", msg):
        return ["missing", int(m.group(1)), int(m.group(2))]
    return ["cyclic", [int(x) for x in ast.literal_eval(msg.split("involving steps: ", 1)[1])]]


def py_validate(steps):
    return [parse_msg(m) for m in validate_dependencies(to_workflow(steps))]


@settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(raw=steps_strategy, dup=st.booleans())
def test_resolver_matches_lean(oracle, raw, dup):
    steps = [list(s) for s in raw] if dup else [list(s) for s in unique_ids(raw)]
    steps_json = [[i, deps] for i, deps in steps]
    assert py_resolve(steps) == oracle({"kind": "resolve", "steps": steps_json})
    assert py_validate(steps) == oracle({"kind": "validate", "steps": steps_json})


# ---------------------------------------------------------------- decide_what_to_run

REASONS = [
    ("x-disabled", "disabled"),
    ("forced another step with -o", "otherOnly"),
    ("forced with -f", "force"),
    ("forced this step with -o", "thisOnly"),
    ("no trace of previous run", "noPrev"),
    ("previous data not found", "noArtifact"),
    ("some dependent steps will re-run", "depRerun"),
    ("some dependent steps have newer outputs", "staleDep"),
    ("some parameters changed", "params"),
    ("nothing changed", "nothing"),
]


def reason_key(reason):
    for prefix, key in REASONS:
        if reason.startswith(prefix):
            return key
    raise AssertionError(reason)


@st.composite
def plan_inputs(draw):
    n = draw(st.integers(1, 6))
    order = draw(st.permutations(range(n)))  # 依存順でない並びも混ぜる
    deps = {i: draw(st.lists(st.integers(0, n - 1), max_size=3, unique=True)) for i in range(n)}
    steps = {
        i: {
            "disabled": draw(st.booleans()) and draw(st.booleans()),
            "found": draw(st.booleans()) or draw(st.booleans()),
            "artifact": draw(st.booleans()) or draw(st.booleans()),
            "time": draw(st.integers(0, 3)),
            "prev": draw(st.integers(0, 1)),
            "cur": draw(st.integers(0, 1)),
        }
        for i in range(n)
    }
    only = draw(st.one_of(st.none(), st.integers(0, n - 1))) if draw(st.integers(0, 4)) == 0 else None
    force = draw(st.integers(0, 6)) == 0
    return n, list(order), deps, steps, only, force


@settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(inp=plan_inputs())
def test_plan_matches_lean(oracle, inp, tmp_path_factory, monkeypatch_module):
    n, order, deps, steps, only, force = inp
    out = tmp_path_factory.mktemp("plan")
    (out / "out").mkdir()
    specs = [
        {
            "step": f"s{i}",
            "filename": f"f{i}.txt",
            "dependencies": {"steps": [f"s{d}" for d in deps[i]], "params": ["p"]},
            "options": {},
        }
        for i in order
    ]
    completed = []
    for i in range(n):
        if steps[i]["found"]:
            completed.append(
                {
                    "step": f"s{i}",
                    "completed": f"2026-01-01T00:00:0{steps[i]['time']}",
                    "params": {"p": steps[i]["prev"]},
                }
            )
        if steps[i]["artifact"]:
            (out / "out" / f"f{i}.txt").write_text("x")
    previous = {"completed_jobs": completed, "previously_completed_jobs": []}
    config = {"output_dir": "out", "previous": previous, **{f"s{i}": {"p": steps[i]["cur"]} for i in range(n)}}
    if only is not None:
        config["only"] = f"s{only}"
    if force:
        config["force"] = True
    disabled = {f"s{i}" for i in range(n) if steps[i]["disabled"]}
    monkeypatch_module.setattr(
        orchestration, "_disabled_reason", lambda name, cfg: "x-disabled" if name in disabled else None
    )
    with contextlib.redirect_stdout(io.StringIO()):
        plan = orchestration.decide_what_to_run(config, previous, specs, out)
    got = [[int(p["step"][1:]), p["run"], reason_key(p["reason"])] for p in plan]

    def stale(i):
        if not steps[i]["found"]:
            return False
        return any(steps[d]["found"] and steps[d]["time"] > steps[i]["time"] for d in deps[i])

    obs = [
        [
            steps[i]["disabled"],
            steps[i]["found"],
            steps[i]["artifact"],
            stale(i),
            steps[i]["found"] and steps[i]["prev"] != steps[i]["cur"],
        ]
        for i in range(n)
    ]
    want = oracle(
        {
            "kind": "plan",
            "specs": [[i, deps[i]] for i in order],
            "obs": obs,
            "only": only,
            "force": force,
            "rerun": [],
        }
    )
    assert got == want


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


# ---------------------------------------------------------------- cluster tree


@st.composite
def tree_inputs(draw):
    L = draw(st.integers(1, 3))
    m = draw(st.integers(1, 6))
    nested = draw(st.booleans())
    if nested:
        # 最下層から決め、上の層は下の層の関数にする（入れ子）
        leaf = draw(st.lists(st.integers(0, 3), min_size=m, max_size=m))
        ups = [draw(st.lists(st.integers(0, 2), min_size=4, max_size=4)) for _ in range(L - 1)]
        rows = []
        for x in leaf:
            cols = [x]
            for f in ups:
                cols.append(f[cols[-1] % 4])
            rows.append(list(reversed(cols)))
    else:
        rows = [draw(st.lists(st.integers(0, 2), min_size=L, max_size=L)) for _ in range(m)]
    return L, rows


@settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(inp=tree_inputs())
def test_tree_matches_lean(oracle, inp):
    L, rows = inp
    data = {"arg-id": [f"A{k}" for k in range(len(rows))]}
    for j in range(1, L + 1):
        ids = [f"{j}_{r[j - 1]}" for r in rows]
        data[f"cluster-level-{j}-id"] = ids
        data[f"cluster-level-{j}-label"] = ids
        data[f"cluster-level-{j}-description"] = ids
    df = pl.DataFrame(data)
    id_columns = [f"cluster-level-{j}-id" for j in range(1, L + 1)]
    lean = oracle({"kind": "tree", "rows": rows, "L": L})
    try:
        parents = _build_parent_child_mapping(df, id_columns)
    except ValueError as e:
        assert "not nested" in str(e)
        assert lean == {"error": "not_nested"}
        return
    melted = melt_cluster_data(df)
    joined = melted.join(parents, on=["level", "id"], how="left")
    got = Counter((r["level"], r["id"], r["value"], r["parent"]) for r in joined.iter_rows(named=True))

    def pref(p):
        if p is None:
            return None
        if p == "root":
            return "0"
        return f"{p[0]}_{p[1]}"

    want = Counter((lv, f"{lv}_{i}", v, pref(p)) for lv, i, v, p in lean)
    assert got == want
