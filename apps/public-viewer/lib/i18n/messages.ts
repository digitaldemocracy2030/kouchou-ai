/**
 * レポート画面の UI 文言（日本語・英語・韓国語）。
 *
 * 日本語を正本とし、`Messages` 型は日本語の辞書から導出する。文言を足すときは
 * まず `ja` に追加し、型エラーで英語・韓国語の追加漏れに気づけるようにしている。
 * レポート本文（意見グループ名・説明・概要）は分析結果の `translations` から
 * 差し替えるので、この辞書には含めない（lib/i18n/translateResult.ts を参照）。
 */

import type { Language } from "./languages";

const ja = {
  /** html の lang 属性に使う値 */
  htmlLang: "ja",
  languageSwitcher: "表示言語",
  reportNotTranslated: "このレポートの本文は選択した言語に翻訳されていないため、元の言語で表示しています。",

  // Overview
  report: "レポート",
  opinionCount: (n: number) => `${n.toLocaleString()}件`,
  /** 意見グループ一覧の件数の後ろに付ける（属性フィルターの適用中） */
  filteredCountSuffix: "（フィルター後）",

  // ReadingGuide（本体・serverless で文言を揃える #696。日本語は変更しない）
  readingGuideLabel: "レポートの読み方",
  readingGuideLead:
    "このレポートは、集めた意見から論点や課題を見つけるためのものです。表示される件数は、社会全体の支持率を示すものではありません。",
  readingGuideSummary: "レポートの読み方",
  readingGuideItems: [
    "収集方法・対象・期間によって、含まれる声には偏りがあります。ここにない意見や、声を届けていない人の存在にも目を向けてください。",
    "1つのコメントから複数の意見が抽出されることがあります。意見数・コメント数を人数や賛成票数として扱わないでください。",
    "図の配置やグループ分けは、意見の内容を探索するための手がかりです。位置・距離・面積だけで重要度や合意の強さを判断しないでください。",
    "AIによる要約や分類には誤りや抜けがあり得ます。個々の意見を読み、必要に応じて収集元のコメントと照らし合わせてください。",
    "見つけた論点は結論ではなく、対話や追加調査の出発点です。少数の意見も読み、関係者への聞き取りや別の資料で確かめてください。",
  ],

  // チャート選択・ツールバー
  chartModes: {
    scatterAll: "全体",
    scatterDetail: "詳細クラスタ",
    scatterDensity: "濃い意見",
    treemap: "階層",
    hierarchyList: "リスト",
  } as Record<string, string>,
  chartModeDisabled: {
    scatterDetail: "クラスタが1階層のみのため利用できません",
    scatterDensity: "この設定条件では抽出できませんでした",
  } as Record<string, string>,
  filter: "フィルタ",
  displaySettings: "表示設定",
  fullscreen: "全画面表示",
  exitFullscreen: "全画面終了",
  /** 全画面ツールバーのクラスタ粒度切替（全体 / 詳細クラスタ / 濃い意見） */
  clusterLevelSwitcher: "クラスタの粒度",

  // 散布図・ツリーマップ
  clickToViewSource: "クリックしてソースを見る",
  originalCount: "元の件数",
  afterFilterCount: "フィルター後",
  treemapText: "%{label}<br>%{value:,}件<br>全意見の %{percentRoot:.2%}",
  treemapTextFiltered: "%{label}<br>%{value:,}件 (フィルター後)<br>全意見の %{percentRoot:.2%}",

  // 散布図の操作ヒントと、濃い意見グループの第一階層クラスタへの帰属表示
  scatterHelpButton: "散布図の操作方法を表示",
  scatterHelpTitle: "散布図の操作方法",
  scatterHelpItems: [
    "・ドラッグ: 表示位置を移動（パン）",
    "・マウスホイール / ピンチ: 拡大・縮小",
    "・右上ツールバー: 拡大・移動・初期表示へリセット",
    "・点にカーソルを合わせる: 意見の内容を表示",
  ],
  /** ソースリンクが有効なときだけ操作ヒントに足す */
  scatterHelpSourceLink: "・点をクリック: 元のソースを開く",
  parentCluster: (label: string) => `所属: ${label}`,
  unknownParentCluster: "不明",
  parentAttributionHeading: "濃い意見グループの第一階層クラスタへの帰属",
  hiddenInLegend: "（非表示）",

  // 表示設定ダイアログ
  displaySettingsDescription: "「全体図」「詳細クラスタ」および「濃い意見グループ」に関する設定項目です。",
  showClusterLabels: "意見グループ名を表示",
  showConvexHull: "意見グループの境界線を表示",
  denseSettings: "濃い意見グループ設定",
  denseSettingsDescription: "「濃い意見グループ」に関する設定項目です。",
  densityPercentLabel: (percent: number) => `上位何％の意見グループを表示するか: ${percent}%`,
  minSamplesLabel: (n: number) => `意見グループのサンプル数の最小数: ${n}`,
  apply: "設定を適用",

  // 属性フィルタダイアログ
  filterDescription: "表示する意見グループを絞り込みます。フィルタ間はAND結合され、フィルタ内の条件はOR結合されます。",
  textSearch: "テキスト検索",
  textSearchPlaceholder: "検索したいテキストを入力してください。入力されたテキストが含まれる意見のみ表示されます。",
  noAttributes: "このレポートには、絞り込みに使える属性情報がありません。",
  enableRange: "フィルター有効化",
  includeEmpty: "空の値を含める",
  min: "最小",
  max: "最大",
  empty: "(空)",
  clearAll: "すべてクリア",

  // ツリーマップの説明
  treemapDetailsLabel: "階層図の説明",
  treemapNavLabel: "階層の移動",
  goUp: "一つ上に戻る",
  goRoot: "全体に戻る",
  showing: "表示中",
  allOpinions: "全意見",
  allOpinionsAfterFilter: "フィルター後の全意見",
  metrics: (count: number, denominator: string, percentage: string) =>
    `${count.toLocaleString()}件（${denominator}に対する割合: ${percentage}）`,
  filteredMetricsNote: "件数と割合はフィルター後の値です。グループの説明はフィルター前の全意見を基に生成しています。",
  noOpinionsHere: "この階層に該当する意見はありません。",
  groupsInLevel: "この階層の意見グループ",
  leafHint: "図の各領域は個別の意見です。選択するとその意見を表示します。",

  // 階層リスト
  hierarchyList: "階層リスト",
  hierarchyListDescription: "クラスタを展開して詳細を表示できます",
  collapse: "折りたたむ",
  expand: "展開する",
  closeChildren: "子要素を閉じる",
  showChildren: (n: number) => `子要素を表示 (${n}件)`,
  closeItems: "個別データを閉じる",
  showItems: (n: number) => `個別データを表示 (${n}件)`,
  noItems: "個別データがありません",
  itemsHeading: (n: number) => `個別データ (${n}件)`,
  showLess: "表示を減らす",
  showMore: (n: number) => `さらに表示 (残り${n}件)`,

  // 分析の概要
  analysisOverview: "分析の概要",
  commentCount: "コメント数",
  extractedOpinionCount: "抽出した意見数",
  clusterCount: "集約した意見グループ数",
  commentCountTooltip:
    "全てのコメントをAIで分析し、意見が含まれるコメントを抽出します。意見が含まれないコメントや、議題と関係のないコメントは除外されます。",
  opinionCountTooltip:
    "抽出したコメントをAIで分析し、様々な意見を抽出します。複数の意見が混ざったコメントなども適切に分離します。",
  clusterCountTooltip:
    "抽出した意見をAIで分析し、近しい意見を一つの意見グループに分類します。意見グループごとの意見を要約し、大量の意見を見える化します。",
  analysisSteps: "分析手順",
  show: "表示",
  hide: "非表示",
  sourceCode: "ソースコード",
  prompt: "プロンプト",
  close: "閉じる",
  steps: {
    extraction: { title: "抽出", description: ["コメントデータから意見を抽出するステップです。"] },
    embedding: {
      title: "埋め込み",
      description: [
        "抽出された意見に対して埋め込み（ベクトル表現）を生成するステップです。",
        "これにより、意見の内容を数値ベクトルとして表現します。",
      ],
    },
    hierarchical_clustering: {
      title: "意見グループ化",
      description: ["埋め込みベクトルの値に基づいて意見の意見グループ化を行うステップです。"],
    },
    hierarchical_initial_labelling: {
      title: "初期ラベリング",
      description: [
        "意見グループ化の結果に対して、各意見グループに適切なタイトル・説明文を生成（ラベリング）するステップです。",
        "このステップでは、最も細かい粒度の意見グループ（最下層の意見グループ）に対して、各意見グループに属する意見に基づいて意見グループのタイトルと説明文を生成します。",
      ],
    },
    hierarchical_merge_labelling: {
      title: "統合ラベリング",
      description: [
        "意見グループを統合し、統合されたグループのタイトルと説明文を生成（ラベリング）するステップです。",
        "このステップでは、下層の意見グループのタイトル及び説明文と、意見に基づいて上層の意見グループのタイトル及び説明文を生成します。",
      ],
    },
    hierarchical_overview: {
      title: "要約",
      description: [
        "意見グループの概要を作成するステップです。",
        "各意見グループのタイトル及び説明文をもとに、全体の概要をまとめます。",
      ],
    },
    hierarchical_aggregation: {
      title: "出力",
      description: ["最終的な結果を出力するステップです。", "意見および各分析結果を含むJSONファイルを出力します。"],
    },
    hierarchical_visualization: {
      title: "表示",
      description: [
        "出力されたJSONファイルをグラフィカルに表示するステップです。",
        "意見グループの概要、意見の内容などを可視化します。あなたが見ているこの画面が出来上がります。",
      ],
    },
  } as Record<string, { title: string; description: string[] }>,

  backToList: "一覧へ戻る",
};

export type Messages = typeof ja;

const en: Messages = {
  htmlLang: "en",
  languageSwitcher: "Language",
  reportNotTranslated:
    "The body of this report has not been translated into the selected language, so it is shown in its original language.",

  report: "Report",
  opinionCount: (n) => `${n.toLocaleString()} opinions`,
  filteredCountSuffix: " (filtered)",

  readingGuideLabel: "How to read this report",
  readingGuideLead:
    "This report is meant to surface topics and issues from the opinions collected. The counts shown do not indicate levels of support in society as a whole.",
  readingGuideSummary: "How to read this report",
  readingGuideItems: [
    "The voices included are biased by how, from whom, and when they were collected. Keep in mind the opinions that are not here and the people who did not speak up.",
    "Several opinions may be extracted from a single comment. Do not treat opinion or comment counts as numbers of people or votes in favor.",
    "The layout and grouping in the charts are clues for exploring the content of opinions. Do not judge importance or strength of agreement from position, distance, or area alone.",
    "AI summaries and classifications can contain errors and omissions. Read individual opinions and check them against the source comments where needed.",
    "The topics you find are starting points for dialogue and further research, not conclusions. Read minority opinions too, and verify with interviews and other materials.",
  ],

  chartModes: {
    scatterAll: "Overview",
    scatterDetail: "Detailed clusters",
    scatterDensity: "Dense opinions",
    treemap: "Hierarchy",
    hierarchyList: "List",
  },
  chartModeDisabled: {
    scatterDetail: "Not available because the clusters have only one level",
    scatterDensity: "No clusters matched the current density settings",
  },
  filter: "Filter",
  displaySettings: "Display settings",
  fullscreen: "Fullscreen",
  exitFullscreen: "Exit fullscreen",
  clusterLevelSwitcher: "Cluster granularity",

  clickToViewSource: "Click to view the source",
  originalCount: "Original count",
  afterFilterCount: "After filter",
  treemapText: "%{label}<br>%{value:,} opinions<br>%{percentRoot:.2%} of all",
  treemapTextFiltered: "%{label}<br>%{value:,} opinions (filtered)<br>%{percentRoot:.2%} of all",

  scatterHelpButton: "Show how to use the scatter plot",
  scatterHelpTitle: "How to use the scatter plot",
  scatterHelpItems: [
    "• Drag: move the view (pan)",
    "• Mouse wheel / pinch: zoom in and out",
    "• Toolbar at the top right: zoom, pan, reset to the initial view",
    "• Hover over a point: show the opinion",
  ],
  scatterHelpSourceLink: "• Click a point: open the original source",
  parentCluster: (label) => `Top-level cluster: ${label}`,
  unknownParentCluster: "Unknown",
  parentAttributionHeading: "Top-level cluster of each dense opinion group",
  hiddenInLegend: " (hidden)",

  displaySettingsDescription: 'Settings for the "Overview", "Detailed clusters" and "Dense opinions" views.',
  showClusterLabels: "Show group names",
  showConvexHull: "Show group boundaries",
  denseSettings: "Dense opinion group settings",
  denseSettingsDescription: 'Settings for the "Dense opinions" view.',
  densityPercentLabel: (percent) => `Show the top ${percent}% densest groups`,
  minSamplesLabel: (n) => `Minimum number of opinions per group: ${n}`,
  apply: "Apply",

  filterDescription:
    "Narrow down the opinions to display. Filters are combined with AND, and conditions within a filter with OR.",
  textSearch: "Text search",
  textSearchPlaceholder: "Enter text to search. Only opinions containing the text will be shown.",
  noAttributes: "This report has no attributes available for filtering.",
  enableRange: "Enable filter",
  includeEmpty: "Include empty values",
  min: "Min",
  max: "Max",
  empty: "(empty)",
  clearAll: "Clear all",

  treemapDetailsLabel: "Description of the hierarchy chart",
  treemapNavLabel: "Navigate levels",
  goUp: "Go up one level",
  goRoot: "Back to all",
  showing: "Showing",
  allOpinions: "all opinions",
  allOpinionsAfterFilter: "all filtered opinions",
  metrics: (count, denominator, percentage) => `${count.toLocaleString()} opinions (${percentage} of ${denominator})`,
  filteredMetricsNote:
    "Counts and percentages reflect the filter. Group descriptions were generated from all opinions before filtering.",
  noOpinionsHere: "There are no opinions at this level.",
  groupsInLevel: "Opinion groups at this level",
  leafHint: "Each area in the chart is an individual opinion. Select one to view it.",

  hierarchyList: "Hierarchy list",
  hierarchyListDescription: "Expand clusters to see details",
  collapse: "Collapse",
  expand: "Expand",
  closeChildren: "Hide child groups",
  showChildren: (n) => `Show child groups (${n})`,
  closeItems: "Hide opinions",
  showItems: (n) => `Show opinions (${n})`,
  noItems: "No opinions",
  itemsHeading: (n) => `Opinions (${n})`,
  showLess: "Show less",
  showMore: (n) => `Show more (${n} remaining)`,

  analysisOverview: "About this analysis",
  commentCount: "Comments",
  extractedOpinionCount: "Extracted opinions",
  clusterCount: "Opinion groups",
  commentCountTooltip:
    "All comments are analyzed by AI and those containing opinions are extracted. Comments without opinions or unrelated to the topic are excluded.",
  opinionCountTooltip:
    "The extracted comments are analyzed by AI to extract individual opinions. Comments mixing several opinions are split appropriately.",
  clusterCountTooltip:
    "The extracted opinions are analyzed by AI and similar opinions are grouped together. Each group is summarized to make a large number of opinions visible.",
  analysisSteps: "Analysis steps",
  show: "Show",
  hide: "Hide",
  sourceCode: "Source code",
  prompt: "Prompt",
  close: "Close",
  steps: {
    extraction: { title: "Extraction", description: ["Extracts opinions from the comment data."] },
    embedding: {
      title: "Embedding",
      description: [
        "Generates embeddings (vector representations) for the extracted opinions.",
        "This expresses the content of each opinion as a numeric vector.",
      ],
    },
    hierarchical_clustering: {
      title: "Grouping",
      description: ["Groups the opinions based on their embedding vectors."],
    },
    hierarchical_initial_labelling: {
      title: "Initial labelling",
      description: [
        "Generates a suitable title and description (label) for each opinion group.",
        "In this step, titles and descriptions are generated for the most fine-grained groups (the lowest level) based on the opinions in each group.",
      ],
    },
    hierarchical_merge_labelling: {
      title: "Merge labelling",
      description: [
        "Merges opinion groups and generates titles and descriptions (labels) for the merged groups.",
        "In this step, titles and descriptions for the upper levels are generated from the lower-level titles, descriptions, and opinions.",
      ],
    },
    hierarchical_overview: {
      title: "Summary",
      description: [
        "Creates an overview of the opinion groups.",
        "Summarizes the whole based on the title and description of each opinion group.",
      ],
    },
    hierarchical_aggregation: {
      title: "Output",
      description: ["Outputs the final result.", "Writes a JSON file containing the opinions and analysis results."],
    },
    hierarchical_visualization: {
      title: "Display",
      description: [
        "Displays the output JSON file graphically.",
        "Visualizes the opinion group summaries and the opinions themselves. This is the screen you are looking at.",
      ],
    },
  },

  backToList: "Back to the list",
};

const ko: Messages = {
  htmlLang: "ko",
  languageSwitcher: "표시 언어",
  reportNotTranslated: "이 보고서의 본문은 선택한 언어로 번역되지 않아 원래 언어로 표시됩니다.",

  report: "보고서",
  opinionCount: (n) => `${n.toLocaleString()}건`,
  filteredCountSuffix: " (필터 후)",

  readingGuideLabel: "보고서 읽는 법",
  readingGuideLead:
    "이 보고서는 수집한 의견에서 쟁점과 과제를 찾기 위한 것입니다. 표시되는 건수는 사회 전체의 지지율을 나타내지 않습니다.",
  readingGuideSummary: "보고서 읽는 법",
  readingGuideItems: [
    "수집 방법·대상·기간에 따라 포함된 목소리에는 편향이 있습니다. 여기에 없는 의견과 목소리를 내지 않은 사람의 존재에도 눈을 돌려 주세요.",
    "하나의 댓글에서 여러 의견이 추출될 수 있습니다. 의견 수·댓글 수를 인원수나 찬성표 수로 취급하지 마세요.",
    "그림의 배치와 그룹 나누기는 의견 내용을 탐색하기 위한 단서입니다. 위치·거리·면적만으로 중요도나 합의의 강도를 판단하지 마세요.",
    "AI의 요약과 분류에는 오류나 누락이 있을 수 있습니다. 개별 의견을 읽고 필요하면 원래 댓글과 대조해 주세요.",
    "발견한 쟁점은 결론이 아니라 대화와 추가 조사의 출발점입니다. 소수 의견도 읽고 관계자 인터뷰나 다른 자료로 확인해 주세요.",
  ],

  chartModes: {
    scatterAll: "전체",
    scatterDetail: "세부 클러스터",
    scatterDensity: "밀집 의견",
    treemap: "계층",
    hierarchyList: "목록",
  },
  chartModeDisabled: {
    scatterDetail: "클러스터가 한 계층뿐이어서 사용할 수 없습니다",
    scatterDensity: "현재 설정 조건에서는 추출되지 않았습니다",
  },
  filter: "필터",
  displaySettings: "표시 설정",
  fullscreen: "전체 화면",
  exitFullscreen: "전체 화면 종료",
  clusterLevelSwitcher: "클러스터 단위",

  clickToViewSource: "클릭하여 출처 보기",
  originalCount: "원래 건수",
  afterFilterCount: "필터 후",
  treemapText: "%{label}<br>%{value:,}건<br>전체 의견의 %{percentRoot:.2%}",
  treemapTextFiltered: "%{label}<br>%{value:,}건 (필터 후)<br>전체 의견의 %{percentRoot:.2%}",

  scatterHelpButton: "산점도 조작 방법 보기",
  scatterHelpTitle: "산점도 조작 방법",
  scatterHelpItems: [
    "• 드래그: 표시 위치 이동(팬)",
    "• 마우스 휠 / 핀치: 확대·축소",
    "• 오른쪽 위 도구 모음: 확대·이동·초기 화면으로 되돌리기",
    "• 점에 커서 올리기: 의견 내용 표시",
  ],
  scatterHelpSourceLink: "• 점 클릭: 원래 출처 열기",
  parentCluster: (label) => `소속: ${label}`,
  unknownParentCluster: "알 수 없음",
  parentAttributionHeading: "밀집 의견 그룹이 속한 제1계층 클러스터",
  hiddenInLegend: " (숨김)",

  displaySettingsDescription: "「전체」「세부 클러스터」「밀집 의견 그룹」에 관한 설정 항목입니다.",
  showClusterLabels: "의견 그룹 이름 표시",
  showConvexHull: "의견 그룹 경계선 표시",
  denseSettings: "밀집 의견 그룹 설정",
  denseSettingsDescription: "「밀집 의견 그룹」에 관한 설정 항목입니다.",
  densityPercentLabel: (percent) => `상위 몇 %의 의견 그룹을 표시할지: ${percent}%`,
  minSamplesLabel: (n) => `의견 그룹의 최소 샘플 수: ${n}`,
  apply: "설정 적용",

  filterDescription: "표시할 의견 그룹을 좁힙니다. 필터 간에는 AND, 필터 내 조건은 OR로 결합됩니다.",
  textSearch: "텍스트 검색",
  textSearchPlaceholder: "검색할 텍스트를 입력하세요. 입력한 텍스트가 포함된 의견만 표시됩니다.",
  noAttributes: "이 보고서에는 필터링에 사용할 수 있는 속성 정보가 없습니다.",
  enableRange: "필터 활성화",
  includeEmpty: "빈 값 포함",
  min: "최소",
  max: "최대",
  empty: "(비어 있음)",
  clearAll: "모두 지우기",

  treemapDetailsLabel: "계층도 설명",
  treemapNavLabel: "계층 이동",
  goUp: "한 단계 위로",
  goRoot: "전체로 돌아가기",
  showing: "표시 중",
  allOpinions: "전체 의견",
  allOpinionsAfterFilter: "필터 후 전체 의견",
  metrics: (count, denominator, percentage) => `${count.toLocaleString()}건 (${denominator} 대비 비율: ${percentage})`,
  filteredMetricsNote: "건수와 비율은 필터 후의 값입니다. 그룹 설명은 필터 전 전체 의견을 바탕으로 생성되었습니다.",
  noOpinionsHere: "이 계층에 해당하는 의견이 없습니다.",
  groupsInLevel: "이 계층의 의견 그룹",
  leafHint: "그림의 각 영역은 개별 의견입니다. 선택하면 그 의견을 표시합니다.",

  hierarchyList: "계층 목록",
  hierarchyListDescription: "클러스터를 펼쳐 자세히 볼 수 있습니다",
  collapse: "접기",
  expand: "펼치기",
  closeChildren: "하위 그룹 닫기",
  showChildren: (n) => `하위 그룹 표시 (${n}건)`,
  closeItems: "개별 의견 닫기",
  showItems: (n) => `개별 의견 표시 (${n}건)`,
  noItems: "개별 의견이 없습니다",
  itemsHeading: (n) => `개별 의견 (${n}건)`,
  showLess: "줄여서 보기",
  showMore: (n) => `더 보기 (남은 ${n}건)`,

  analysisOverview: "분석 개요",
  commentCount: "댓글 수",
  extractedOpinionCount: "추출한 의견 수",
  clusterCount: "집계한 의견 그룹 수",
  commentCountTooltip:
    "모든 댓글을 AI로 분석하여 의견이 포함된 댓글을 추출합니다. 의견이 없는 댓글이나 주제와 관계없는 댓글은 제외됩니다.",
  opinionCountTooltip:
    "추출한 댓글을 AI로 분석하여 다양한 의견을 추출합니다. 여러 의견이 섞인 댓글도 적절히 분리합니다.",
  clusterCountTooltip:
    "추출한 의견을 AI로 분석하여 비슷한 의견을 하나의 의견 그룹으로 분류합니다. 의견 그룹별로 요약하여 많은 의견을 한눈에 볼 수 있게 합니다.",
  analysisSteps: "분석 절차",
  show: "표시",
  hide: "숨기기",
  sourceCode: "소스 코드",
  prompt: "프롬프트",
  close: "닫기",
  steps: {
    extraction: { title: "추출", description: ["댓글 데이터에서 의견을 추출하는 단계입니다."] },
    embedding: {
      title: "임베딩",
      description: [
        "추출된 의견에 대해 임베딩(벡터 표현)을 생성하는 단계입니다.",
        "이를 통해 의견의 내용을 수치 벡터로 표현합니다.",
      ],
    },
    hierarchical_clustering: {
      title: "의견 그룹화",
      description: ["임베딩 벡터 값을 바탕으로 의견을 그룹화하는 단계입니다."],
    },
    hierarchical_initial_labelling: {
      title: "초기 라벨링",
      description: [
        "그룹화 결과에 대해 각 의견 그룹에 적절한 제목과 설명문을 생성(라벨링)하는 단계입니다.",
        "이 단계에서는 가장 세분화된 의견 그룹(최하위 계층)에 대해 각 그룹에 속한 의견을 바탕으로 제목과 설명문을 생성합니다.",
      ],
    },
    hierarchical_merge_labelling: {
      title: "통합 라벨링",
      description: [
        "의견 그룹을 통합하고 통합된 그룹의 제목과 설명문을 생성(라벨링)하는 단계입니다.",
        "이 단계에서는 하위 그룹의 제목·설명문과 의견을 바탕으로 상위 그룹의 제목과 설명문을 생성합니다.",
      ],
    },
    hierarchical_overview: {
      title: "요약",
      description: [
        "의견 그룹의 개요를 작성하는 단계입니다.",
        "각 의견 그룹의 제목과 설명문을 바탕으로 전체 개요를 정리합니다.",
      ],
    },
    hierarchical_aggregation: {
      title: "출력",
      description: ["최종 결과를 출력하는 단계입니다.", "의견과 각 분석 결과를 포함한 JSON 파일을 출력합니다."],
    },
    hierarchical_visualization: {
      title: "표시",
      description: [
        "출력된 JSON 파일을 그래픽으로 표시하는 단계입니다.",
        "의견 그룹의 개요와 의견 내용을 시각화합니다. 지금 보고 있는 이 화면이 만들어집니다.",
      ],
    },
  },

  backToList: "목록으로 돌아가기",
};

export const messages: Record<Language, Messages> = { ja, en, ko };

export function getMessages(language: Language): Messages {
  return messages[language] ?? ja;
}
