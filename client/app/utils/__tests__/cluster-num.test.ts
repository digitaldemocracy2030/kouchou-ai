import type { Result } from "@/type";
import { getClusterNum } from "../cluster-num";

describe("getClusterNum", () => {
  it("correctly counts clusters by level", () => {
    const mockResult: Result = {
      arguments: [],
      clusters: [
        {
          id: "1",
          level: 1,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
        {
          id: "2",
          level: 1,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
        {
          id: "3",
          level: 2,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
        {
          id: "4",
          level: 2,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
        {
          id: "5",
          level: 2,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
        {
          id: "6",
          level: 3,
          value: 0,
          label: "",
          takeaway: "",
          parent: "",
          density_rank_percentile: 0,
        },
      ],
      comments: {},
      propertyMap: {},
      translations: {},
      overview: "",
      config: {
        name: "",
        question: "",
        input: "",
        model: "",
        intro: "",
        output_dir: "",
        is_embedded_at_local: false,
        extraction: {
          workers: 0,
          limit: 0,
          properties: [],
          categories: {},
          category_batch_size: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_clustering: {
          cluster_nums: [],
          source_code: "",
        },
        embedding: {
          model: "",
          source_code: "",
        },
        hierarchical_initial_labelling: {
          workers: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_merge_labelling: {
          workers: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_overview: {
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_aggregation: {
          hidden_properties: {},
          source_code: "",
        },
        hierarchical_visualization: {
          replacements: {},
          source_code: "",
        },
        plan: [],
        status: "",
      },
      comment_num: 0,
    };

    const result = getClusterNum(mockResult);

    expect(result).toEqual({
      1: 2, // レベル1のクラスタは2つ
      2: 3, // レベル2のクラスタは3つ
      3: 1, // レベル3のクラスタは1つ
    });
  });

  it("returns empty object when no clusters exist", () => {
    const mockResult: Result = {
      arguments: [],
      clusters: [],
      comments: {},
      propertyMap: {},
      translations: {},
      overview: "",
      config: {
        name: "",
        question: "",
        input: "",
        model: "",
        intro: "",
        output_dir: "",
        is_embedded_at_local: false,
        extraction: {
          workers: 0,
          limit: 0,
          properties: [],
          categories: {},
          category_batch_size: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_clustering: {
          cluster_nums: [],
          source_code: "",
        },
        embedding: {
          model: "",
          source_code: "",
        },
        hierarchical_initial_labelling: {
          workers: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_merge_labelling: {
          workers: 0,
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_overview: {
          source_code: "",
          prompt: "",
          model: "",
        },
        hierarchical_aggregation: {
          hidden_properties: {},
          source_code: "",
        },
        hierarchical_visualization: {
          replacements: {},
          source_code: "",
        },
        plan: [],
        status: "",
      },
      comment_num: 0,
    };

    const result = getClusterNum(mockResult);

    expect(result).toEqual({});
  });
});
