import KV
import KV.Check
import Lean.Data.Json
/-
差分テスト用の oracle。標準入力から 1 行 1 件の JSON を読み、Lean のモデルで計算した結果を 1 行ずつ返す。
Python 側（`verification/difftest.py`）が同じ入力を本物のコードに流して突き合わせる。
-/
open Lean (Json)

def natsOf (j : Json) : List Nat :=
  match j.getArr? with
  | .ok a => a.toList.filterMap (fun x => (x.getNat?).toOption)
  | .error _ => []

def arrOf (j : Json) : List Json :=
  match j.getArr? with
  | .ok a => a.toList
  | .error _ => []

def natAt (j : Json) (i : Nat) : Nat := ((j.getArrVal? i).toOption.bind (fun x => (x.getNat?).toOption)).getD 0
def boolAt (j : Json) (i : Nat) : Bool := ((j.getArrVal? i).toOption.bind (fun x => (x.getBool?).toOption)).getD false
def field (j : Json) (k : String) : Json := (j.getObjVal? k).toOption.getD Json.null

def jnats (l : List Nat) : Json := Lean.toJson l

def resolveOut (steps : KV.Resolver.Steps) : Json :=
  match KV.Resolver.resolve steps with
  | .ok o => Json.mkObj [("ok", jnats o)]
  | .error (.duplicate ds) => Json.mkObj [("duplicate", jnats ds)]
  | .error (.missing s d) => Json.mkObj [("missing", jnats [s, d])]
  | .error (.cyclic u) => Json.mkObj [("cyclic", jnats u)]

def validateOut (steps : KV.Resolver.Steps) : Json :=
  Json.arr ((KV.Resolver.validate steps).map (fun
    | .duplicateId i => Json.arr #["duplicate", Lean.toJson i]
    | .selfDep s => Json.arr #["self", Lean.toJson s]
    | .missing s d => Json.arr #["missing", Lean.toJson s, Lean.toJson d]
    | .cyclic u => Json.arr #["cyclic", jnats u])).toArray

def reasonStr : KV.Rerun.Reason → String
  | .disabled => "disabled" | .otherOnly => "otherOnly" | .force => "force" | .thisOnly => "thisOnly"
  | .rerun => "rerun" | .noPrev => "noPrev" | .noArtifact => "noArtifact" | .depRerun => "depRerun"
  | .staleDep => "staleDep" | .params => "params" | .nothing => "nothing"

def planOut (j : Json) : Json :=
  let specs : List KV.Rerun.Spec := (arrOf (field j "specs")).map (fun s =>
    ⟨natAt s 0, natsOf ((s.getArrVal? 1).toOption.getD Json.null)⟩)
  let obsArr := arrOf (field j "obs")
  let obs : Nat → KV.Rerun.Obs := fun n =>
    match obsArr[n]? with
    | some o => ⟨boolAt o 0, boolAt o 1, boolAt o 2, boolAt o 3, boolAt o 4⟩
    | none => ⟨false, false, false, false, false⟩
  let only := (field j "only").getNat?.toOption
  let force := (field j "force").getBool?.toOption.getD false
  let cfg : KV.Rerun.Cfg := { only := only, force := force, rerun := natsOf (field j "rerun") }
  Json.arr ((KV.Rerun.buildPlan cfg obs specs).map (fun it =>
    Json.arr #[Lean.toJson it.name, Json.bool it.run, Json.str (reasonStr it.reason)])).toArray

def prefJson : KV.Tree.PRef → Json
  | .root => "root"
  | .node l i => jnats [l, i]
  | .missing => Json.null

def treeOut (j : Json) : Json :=
  let rows := (arrOf (field j "rows")).map natsOf
  let L := ((field j "L").getNat?).toOption.getD 0
  if !KV.Tree.singleParent rows L then Json.mkObj [("error", "not_nested")] else
  Json.arr ((KV.Tree.clusters rows L).map (fun c =>
    Json.arr #[Lean.toJson c.level, Lean.toJson c.id, Lean.toJson c.value, prefJson c.parent])).toArray

def stepsOf (j : Json) : KV.Resolver.Steps :=
  (arrOf (field j "steps")).map (fun s => ⟨natAt s 0, natsOf ((s.getArrVal? 1).toOption.getD Json.null)⟩)

def handle (line : String) : Json :=
  match Json.parse line with
  | .error e => Json.mkObj [("error", Json.str e)]
  | .ok j =>
    match (field j "kind").getStr? with
    | .ok "resolve" => resolveOut (stepsOf j)
    | .ok "validate" => validateOut (stepsOf j)
    | .ok "plan" => planOut j
    | .ok "tree" => treeOut j
    | _ => Json.mkObj [("error", "unknown kind")]

partial def loop (stdin : IO.FS.Stream) (stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line.isEmpty then return
  let t := line.trimAscii.toString
  if !t.isEmpty then
    stdout.putStrLn (handle t).compress
    stdout.flush
  loop stdin stdout

def main (args : List String) : IO UInt32 := do
  match args with
  | ["check", n] => KV.Check.run (n.toNat?.getD 4)
  | _ =>
    loop (← IO.getStdin) (← IO.getStdout)
    return 0
