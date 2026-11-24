import Lean.Data.Json

open Lean
open Std.Internal.Parsec Std.Internal.Parsec.String

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

private def decodeLegacyNumber (literal : String) (number : JsonNumber) : Option String := do
  if !(literal.any fun c : Char => c == '.' || c == 'e' || c == 'E') then
    return toString number.mantissa
  -- Decimal and exponent tokens are read as binary64 by both implementations.
  let value := number.toFloat
  if value.abs ≤ 9007199254740991.0 then
    let id := value.toInt64
    if id.toFloat == value then
      return toString id.toInt
  none

private def legacyNumber : Parser Json := fun start =>
  match Json.Parser.num start with
  | .error atPos err => .error atPos err
  | .success stop number =>
    let literal := String.Pos.Raw.extract start.1 start.2.offset stop.2.offset
    -- Keep invalid numbers so an authoritative comment_ids can still take precedence.
    let value := (decodeLegacyNumber literal number).map Json.str
    .success stop (value.getD (.num number))

private def commaSeparated (item : Parser α) : Parser (Array α) :=
  (do
    let first ← item
    let rest ← many (skipChar ',' *> ws *> item)
    return #[first] ++ rest) <|> pure #[]

private def readObject (valueFor : String → Parser Json) : Parser Json := do
  skipChar '{'; ws
  let entries ← commaSeparated (do
    skipChar '"'
    let key ← Json.Parser.str
    ws; skipChar ':'; ws
    return (key, ← valueFor key))
  skipChar '}'; ws
  let mut fields : Std.TreeMap.Raw String Json := ∅
  for (key, value) in entries do
    if fields.contains key then
      fail s!"duplicate object key {key.quote}"
    fields := fields.insert key value
  return .obj fields

private def readArgument : Parser Json := do
  if (← peek!) != '{' then
    return ← Json.Parser.anyCore
  readObject fun key => do
    let c ← peek!
    if key == "comment_id" && (c == '-' || ('0' ≤ c && c ≤ '9')) then
      legacyNumber <* ws
    else
      Json.Parser.anyCore

private def inputParser : Parser Json := do
  ws
  let result ← if (← peek!) == '{' then
    readObject fun key => do
      if key == "arguments" && (← peek!) == '[' then
        skipChar '['; ws
        let arguments ← commaSeparated readArgument
        skipChar ']'; ws
        return .arr arguments
      Json.Parser.anyCore
  else
    Json.Parser.anyCore
  eof
  return result

def parseInput (input : String) : Except String Json := inputParser.run input

def decodeLegacyId (value : Json) : Except String (List String) := do
  if value == .null then
    return []
  let id ← value.getStr?
  return if id.isEmpty then [] else [id]

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
  match OpinionSources.parseInput input with
  | .ok data => IO.println (OpinionSources.run data).compress
  | .error message => throw (IO.userError message)
