import Lean.Data.Json

open Lean

namespace OpinionSources

structure Relation where
  opinion : String
  source : String
  deriving FromJson

structure SourceBody where
  id : String
  body : String
  deriving FromJson

structure Case where
  arguments : List Json
  relations : Option (List Relation)
  comments : List SourceBody
  publish : Bool
  inputCount : Option Nat
  deriving FromJson

def distinctSources (ids : List String) : List String := ids.eraseDups

def representative (ids : List String) : String := ids.head?.getD ""

def publishedBodies (allowed : Bool) (linked : List String) (comments : List SourceBody) :
    List SourceBody :=
  if allowed then comments.filter (fun comment => linked.contains comment.id) else []

theorem noBodiesWhenOff (linked : List String) (comments : List SourceBody) :
    publishedBodies false linked comments = [] := rfl

theorem representativeIsSource (ids : List String) (id : String)
    (h : ids.head? = some id) : id ∈ ids := by
  cases ids <;> simp_all

theorem noLostSource (ids : List String) (id : String) :
    id ∈ distinctSources ids ↔ id ∈ ids := by
  simp [distinctSources]

theorem publishedBodyWasLinked (comments : List SourceBody) (linked : List String)
    (body : SourceBody) (h : body ∈ publishedBodies true linked comments) :
    body.id ∈ linked := by
  have linkedBody : body ∈ comments ∧ body.id ∈ linked := by
    simpa [publishedBodies] using h
  exact linkedBody.2

def decodeLegacyId (value : Json) : Except String (List String) :=
  match value with
  | .null => .ok []
  | .str text => .ok (if text == "" then [] else [text])
  | other => do
    let number ← other.getNum?
    if number.exponent == 0 then
      return [toString number.mantissa]
    let scale : Int := 10 ^ number.exponent
    let id := number.mantissa / scale
    if number.mantissa % scale == 0 && id.natAbs ≤ 9007199254740991 then
      return [toString id]
    throw "legacy decimal comment ID must be a safe integer"

def readSources (argument : Json) : Except String (List String) := do
  match argument.getObjVal? "comment_ids" with
  | .ok raw =>
    let ids ← raw.getArr?
    let strings ← ids.toList.mapM Json.getStr?
    if strings.contains "" then
      throw "empty comment ID in comment_ids"
    else
      return distinctSources strings
  | .error _ =>
    decodeLegacyId ((argument.getObjVal? "comment_id").toOption.getD .null)

def wireArgument (id : String) (sources : List String) : Json :=
  let fields := [("arg_id", toJson id), ("comment_id", toJson (representative sources))]
  Json.mkObj (if sources.length > 1 then fields ++ [("comment_ids", toJson sources)] else fields)

def project (input : Case) : Except String Json := do
  let arguments ← input.arguments.mapM fun arg => do
    let id ← arg.getObjValAs? String "arg_id"
    let sources ← match input.relations with
      | none => readSources arg
      | some edges =>
        pure (distinctSources ((edges.filter (fun edge => edge.opinion == id && edge.source != "")).map Relation.source))
    return (id, sources)
  let linked := distinctSources (arguments.flatMap Prod.snd)
  let bodies := publishedBodies input.publish linked input.comments
  return Json.mkObj [
    ("schemaVersion", toJson (2 : Nat)),
    ("arguments", toJson (arguments.map (fun (id, sources) => wireArgument id sources))),
    ("comments", Json.mkObj (bodies.map (fun body => (body.id, Json.mkObj [("comment", toJson body.body)])))),
    ("inputCount", toJson input.inputCount),
    ("opinionCount", toJson arguments.length),
    ("relationCount", toJson ((arguments.flatMap Prod.snd).length)),
    ("linkedCommentCount", toJson linked.length)
  ]

def run (data : Json) : Json :=
  match (fromJson? data : Except String Case).bind project with
  | .ok result => result
  | .error _ => Json.mkObj [("error", toJson true)]

end OpinionSources

def main : IO Unit := do
  let input ← (← IO.getStdin).readToEnd
  match Json.parse input with
  | .ok data => IO.println (OpinionSources.run data).compress
  | .error message => throw (IO.userError message)
