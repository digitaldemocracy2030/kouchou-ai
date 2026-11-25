import type { Argument } from "@/type";
import {
  DEFAULT_EXPLORATION,
  categoryKeys,
  coordinateOpinions,
  explorationSettings,
  explorationUrl,
  exploreGroups,
  opinionStance,
  readExploration,
} from "./explorationGroups";

const opinions = [
  { arg_id: "a", x: 0, y: 0, attributes: { topic: "tram", reason: "cost", stance_score: 0.9 } },
  { arg_id: "b", x: 0, y: 0, attributes: { topic: "bus", reason: "capacity", stance_score: -0.9 } },
  { arg_id: "c", x: 100, y: 0, attributes: { topic: "tram", reason: "capacity", stance_score: 0.8 } },
  { arg_id: "d", x: 100, y: 0, attributes: { topic: "bus", reason: "cost", stance_score: -0.8 } },
].map(
  (opinion): Argument => ({ ...opinion, argument: opinion.arg_id, comment_id: opinion.arg_id, p: 0, cluster_ids: [] }),
);

function grouped(overrides: Partial<typeof DEFAULT_EXPLORATION>) {
  return exploreGroups(opinions, { ...DEFAULT_EXPLORATION, count: 2, ...overrides })
    .map((group) =>
      group
        .map(({ arg_id }) => arg_id)
        .sort()
        .join(""),
    )
    .sort();
}

test("cuts by coordinates, then changes membership when stance, topic or reason has weight", () => {
  expect(grouped({})).toEqual(["ab", "cd"]);
  expect(grouped({ stance: 10 })).toEqual(["ac", "bd"]);
  expect(grouped({ topic: 10, topicKey: "topic" })).toEqual(["ac", "bd"]);
  expect(grouped({ reason: 10, reasonKey: "reason" })).toEqual(["ad", "bc"]);
});

test("includes unscored opinions without treating unknown as a zero score", () => {
  const withoutScore = { ...opinions[0], arg_id: "unknown", attributes: {} };
  expect(opinionStance(withoutScore)).toBeUndefined();
  expect(opinionStance({ ...withoutScore, attributes: { stance_score: 0 } })).toBe(0);
  expect(exploreGroups([...opinions, withoutScore], { ...DEFAULT_EXPLORATION, stance: 10 }).flat()).toHaveLength(5);
  expect(coordinateOpinions([...opinions, { ...withoutScore, x: Number.NaN }])).toEqual(opinions);
  expect(exploreGroups([withoutScore, withoutScore], DEFAULT_EXPLORATION)).toHaveLength(1);
});

test("share settings round-trip, preserve other query parameters and discard unavailable attributes", () => {
  const settings = { count: 3, stance: 10, topic: 5, reason: 1, topicKey: "topic", reasonKey: "missing" };
  const url = explorationUrl("https://example.org/report?lang=en", settings);
  expect(url.searchParams.get("lang")).toBe("en");
  expect(url.hash).toBe("#report-exploration");
  expect(readExploration(url.search)).toEqual(settings);
  expect(readExploration("?explore=1&groups=500&stance=-1")).toEqual({ ...DEFAULT_EXPLORATION, count: 12 });
  expect(explorationSettings(settings, opinions, categoryKeys(opinions))).toEqual({
    ...settings,
    reason: 0,
    reasonKey: "",
  });
});
