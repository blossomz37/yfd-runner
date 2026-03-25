export type ReviewState = {
  review_required: boolean;
  review_reason: string;
  review_status: string;
  approved_candidate_id: string | null;
  last_reviewed_at: string | null;
};

export type CandidateOutput = {
  candidate_id: string;
  chapter: number;
  step: string;
  source: string;
  steering_note: string;
  content: string;
  status: string;
  created_at: string;
};

export type RunMetrics = {
  total_tokens: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  total_word_count: number;
};

export type RunSummary = {
  run_id: string;
  path: string;
  project: string | null;
  total_chapters: number | null;
  current_chapter: number | null;
  latest_step: string | null;
  updated_at: string | null;
  created_at: string | null;
  metrics: RunMetrics;
};

export type RunDetail = {
  run_id: string;
  state_path: string;
  updated_at: string | null;
  model_config: string | null;
  worksheet: string;
  chapters: Record<string, Record<string, string>>;
  metrics: RunMetrics;
  current_chapter: number | null;
  latest_step: string | null;
  current_review: {
    chapter: number | null;
    step: string | null;
    state: ReviewState | null;
  };
  current_candidate: CandidateOutput | null;
  studio?: {
    run_settings?: {
      review_policy?: Record<string, string>;
      output_dir?: string | null;
      created_from?: string;
    };
    review_state?: Record<string, Record<string, ReviewState>>;
    candidate_outputs?: CandidateOutput[];
    branch?: {
      parent_run_id?: string | null;
      branched_from_chapter?: number | null;
      branch_note?: string;
    };
  };
};

export type TemplateFile = {
  name: string;
  path: string;
};

export type TemplateDetail = {
  name: string;
  path: string;
  content: string;
};

export type ModelFile = {
  name: string;
  path: string;
};

export type ModelDetail = {
  name: string;
  path: string;
  content: string;
  data: Record<string, unknown>;
};

export type StepSetting = {
  step: string;
  model_config: string;
  max_tokens: number | null;
  temperature: number | null;
  extras: Record<string, unknown>;
};

export type ConfigDetail = {
  path: string;
  content: string;
  data: Record<string, unknown>;
};

export type JobEvent = {
  timestamp?: string;
  event: string;
  message: string;
  [key: string]: unknown;
};

export type JobStatus = {
  job_id: string;
  job_type: string;
  status: string;
  run_id: string;
  target: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  events: JobEvent[];
};

export type ArtifactType = "manuscript" | "rendered_prompt" | "validation_failure" | "cascade_failure";

export type RunArtifact = {
  artifact_id: string;
  artifact_type: ArtifactType;
  label: string;
  name: string;
  path: string;
  exists: boolean;
  updated_at: string | null;
  chapter: number | null;
  step: string | null;
  section_number: number | null;
};

export type RunArtifactsIndex = {
  run_id: string;
  manuscript: RunArtifact;
  artifacts: RunArtifact[];
};

export type ArtifactContent = {
  run_id: string;
  artifact: RunArtifact;
  content: string;
};

export type StepSettingUpdateInput = {
  model_config?: string;
  max_tokens?: number;
  temperature?: number;
  extras?: Record<string, unknown>;
};

export type CreateRunInput = {
  run_id: string;
  worksheet_path: string;
  model_config?: string;
  output_dir?: string;
  review_policy?: Record<string, string>;
};

export type DossierBlockInput = {
  label: string;
  source_type: string;
  source_name: string;
  text: string;
};

export type CreateProjectFromDossierInput = {
  run_id: string;
  blocks: DossierBlockInput[];
  model_config?: string;
  output_dir?: string;
};

export type BranchRunInput = {
  new_run_id: string;
  branched_from_chapter?: number;
  branch_note?: string;
};

export type StepRerunInput = {
  steering_note?: string;
  review_mode?: string;
  force?: boolean;
  model_config?: string;
};

const API_BASE = process.env.YFD_STUDIO_API_BASE || "http://127.0.0.1:8000";
const API_TIMEOUT_MS = 1200;
const STEP_ORDER = ["plan", "draft", "repetition_audit", "style", "craft", "final", "summary"];

type ApiRunSummary = {
  run_id: string;
  path: string;
  project: string | null;
  total_chapters: number | null;
  current_chapter: number | null;
  latest_step?: string | null;
  latest_completed_step?: string | null;
  updated_at: string | null;
  created_at: string | null;
  total_tokens?: number;
  total_tokens_in?: number;
  total_tokens_out?: number;
  total_cost_usd?: number;
  total_word_count?: number;
};

type ApiRunData = {
  run_id: string;
  model_config?: string | null;
  worksheet?: string;
  updated_at?: string | null;
  chapters?: Record<string, Record<string, string>>;
  metrics?: Partial<RunMetrics>;
  studio?: RunDetail["studio"];
};

type ApiRunDetail = {
  run_id: string;
  state_path: string;
  data: ApiRunData;
};

type ApiErrorPayload = {
  detail?: string;
  errors?: Array<{ message?: string }>;
  status?: string;
  active_job_id?: string;
};

type ApiRunArtifactsIndex = RunArtifactsIndex;
type ApiArtifactContent = ArtifactContent;
type ApiConfigDetail = ConfigDetail;

const fallbackRuns: RunSummary[] = [
  {
    run_id: "partial_ch2_20260319",
    path: "yfd-runner/state/partial_ch2_20260319.json",
    project: "eaw",
    total_chapters: 25,
    current_chapter: 3,
    latest_step: "draft",
    updated_at: "2026-03-25T08:55:00Z",
    created_at: "2026-03-19T19:55:00Z",
    metrics: {
      total_tokens: 468136,
      total_tokens_in: 370994,
      total_tokens_out: 97142,
      total_cost_usd: 0.574443,
      total_word_count: 51708
    }
  },
  {
    run_id: "phase11_ch1_auto",
    path: "yfd-runner/state/phase11_ch1_auto.json",
    project: "eaw",
    total_chapters: 25,
    current_chapter: 2,
    latest_step: "summary",
    updated_at: "2026-03-25T07:40:00Z",
    created_at: "2026-03-24T21:10:00Z",
    metrics: {
      total_tokens: 144210,
      total_tokens_in: 113902,
      total_tokens_out: 30308,
      total_cost_usd: 3.11,
      total_word_count: 7118
    }
  },
  {
    run_id: "phase11_offline",
    path: "yfd-runner/state/phase11_offline.json",
    project: "eaw",
    total_chapters: 25,
    current_chapter: 2,
    latest_step: "plan",
    updated_at: "2026-03-24T23:14:00Z",
    created_at: "2026-03-24T22:44:00Z",
    metrics: {
      total_tokens: 42210,
      total_tokens_in: 32110,
      total_tokens_out: 10100,
      total_cost_usd: 0.77,
      total_word_count: 1820
    }
  }
];

const fallbackArtifactIndexes: Record<string, RunArtifactsIndex> = {
  partial_ch2_20260319: {
    run_id: "partial_ch2_20260319",
    manuscript: {
      artifact_id: "manuscript",
      artifact_type: "manuscript",
      label: "Manuscript",
      name: "partial_ch2_20260319_manuscript.md",
      path: "yfd-runner/output/partial_ch2_20260319_manuscript.md",
      exists: true,
      updated_at: "2026-03-25T08:55:00Z",
      chapter: null,
      step: null,
      section_number: null
    },
    artifacts: [
      {
        artifact_id: "ch01_step01_plan.md",
        artifact_type: "rendered_prompt",
        label: "Ch 01 · plan prompt",
        name: "ch01_step01_plan.md",
        path: "yfd-runner/rendered/partial_ch2_20260319/ch01_step01_plan.md",
        exists: true,
        updated_at: "2026-03-25T08:20:00Z",
        chapter: 1,
        step: "plan",
        section_number: null
      },
      {
        artifact_id: "ch02_draft_validation_fail.md",
        artifact_type: "validation_failure",
        label: "Ch 02 · draft validation failure",
        name: "ch02_draft_validation_fail.md",
        path: "yfd-runner/rendered/partial_ch2_20260319/ch02_draft_validation_fail.md",
        exists: true,
        updated_at: "2026-03-25T08:42:00Z",
        chapter: 2,
        step: "draft",
        section_number: null
      }
    ]
  },
  phase11_ch1_auto: {
    run_id: "phase11_ch1_auto",
    manuscript: {
      artifact_id: "manuscript",
      artifact_type: "manuscript",
      label: "Manuscript",
      name: "phase11_ch1_auto_manuscript.md",
      path: "yfd-runner/output/phase11_ch1_auto_manuscript.md",
      exists: true,
      updated_at: "2026-03-25T07:40:00Z",
      chapter: null,
      step: null,
      section_number: null
    },
    artifacts: [
      {
        artifact_id: "ch02_step01_plan.md",
        artifact_type: "rendered_prompt",
        label: "Ch 02 · plan prompt",
        name: "ch02_step01_plan.md",
        path: "yfd-runner/rendered/phase11_ch1_auto/ch02_step01_plan.md",
        exists: true,
        updated_at: "2026-03-25T07:35:00Z",
        chapter: 2,
        step: "plan",
        section_number: null
      }
    ]
  },
  phase11_offline: {
    run_id: "phase11_offline",
    manuscript: {
      artifact_id: "manuscript",
      artifact_type: "manuscript",
      label: "Manuscript",
      name: "phase11_offline_manuscript.md",
      path: "yfd-runner/output/phase11_offline_manuscript.md",
      exists: true,
      updated_at: "2026-03-24T23:14:00Z",
      chapter: null,
      step: null,
      section_number: null
    },
    artifacts: [
      {
        artifact_id: "ch02_step01_plan.md",
        artifact_type: "rendered_prompt",
        label: "Ch 02 · plan prompt",
        name: "ch02_step01_plan.md",
        path: "yfd-runner/rendered/phase11_offline/ch02_step01_plan.md",
        exists: true,
        updated_at: "2026-03-24T23:10:00Z",
        chapter: 2,
        step: "plan",
        section_number: null
      }
    ]
  }
};

const fallbackArtifactContent: Record<string, Record<string, string>> = {
  partial_ch2_20260319: {
    manuscript: [
      "# Chapter 1",
      "",
      "Anna learned early that information moved faster when it passed through fear than when it passed through trust.",
      "",
      "# Chapter 2",
      "",
      "By the time she reached the apartment, the city had already decided what the sirens meant."
    ].join("\n"),
    "ch01_step01_plan.md": [
      "Generate a scene plan for Chapter 1.",
      "",
      "Constraints:",
      "- stay close to the dossier facts",
      "- foreground relational pressure",
      "- keep the turn concrete"
    ].join("\n"),
    "ch02_draft_validation_fail.md": [
      "This draft became too abstract and summary-heavy.",
      "",
      "It needs more scene-bound prose, sensory anchors, and fewer generalized statements."
    ].join("\n")
  },
  phase11_ch1_auto: {
    manuscript: "# Chapter 1\n\nAuto-run manuscript output.\n",
    "ch02_step01_plan.md": "Outline Chapter 2 with a clean escalation from the approved Chapter 1 ending.\n"
  },
  phase11_offline: {
    manuscript: "# Chapter 1\n\nOffline manuscript checkpoint.\n",
    "ch02_step01_plan.md": "Offline prompt render for the next planning pass.\n"
  }
};

const fallbackConfig: ConfigDetail = {
  path: "yfd-runner/config.yaml",
  content: [
    "openrouter:",
    "  api_key_env: OPENROUTER_API_KEY",
    "  base_url: https://openrouter.ai/api/v1/chat/completions",
    "",
    "project:",
    "  name: eaw",
    "  total_chapters: 25",
    "  default_model_config: default",
    "",
    "step_models:",
    "  cascade: gpt-5.2-think",
    "  plan: claude-sonnet-4.6",
    "  draft: gpt-5.4",
    "  repetition: gpt-5.4-nano",
    "  style: gpt-5.4-nano",
    "  craft: gpt-5.4-nano",
    "  final: gpt-5.4",
    "  summary: gpt-5.4-nano",
    "",
    "step_overrides:",
    "  plan:",
    "    max_tokens: 60000",
    "    temperature: 0.5",
    "  draft:",
    "    max_tokens: 60000",
    "    temperature: 0.8",
    "  final:",
    "    max_tokens: 60000",
    "    temperature: 0.7",
    "    reasoning:",
    "      effort: low"
  ].join("\n"),
  data: {
    openrouter: {
      api_key_env: "OPENROUTER_API_KEY",
      base_url: "https://openrouter.ai/api/v1/chat/completions"
    },
    project: {
      name: "eaw",
      total_chapters: 25,
      default_model_config: "default"
    }
  }
};

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(API_TIMEOUT_MS)
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function errorMessage(payload: ApiErrorPayload | null, fallback: string): string {
  if (payload?.detail) {
    return payload.detail;
  }
  if (payload?.status === "active_job_conflict" && payload.active_job_id) {
    return `Run already has an active job: ${payload.active_job_id}`;
  }
  if (payload?.errors?.length) {
    return payload.errors
      .map((entry) => entry.message)
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}

async function apiWrite<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(API_TIMEOUT_MS),
      ...init,
      headers: {
        "content-type": "application/json",
        ...(init.headers ?? {})
      }
    });
  } catch {
    throw new Error("Backend API is not reachable.");
  }

  let payload: T | ApiErrorPayload | null = null;
  try {
    payload = (await response.json()) as T | ApiErrorPayload;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(errorMessage(payload as ApiErrorPayload | null, "Backend request failed."));
  }

  return payload as T;
}

function sortChapterEntries(chapters: Record<string, Record<string, string>>): Array<[string, Record<string, string>]> {
  return Object.entries(chapters).sort((a, b) => Number(a[0]) - Number(b[0]));
}

function latestStepForChapters(chapters: Record<string, Record<string, string>>): {
  chapter: number | null;
  step: string | null;
} {
  const chapterEntries = sortChapterEntries(chapters);
  if (!chapterEntries.length) {
    return { chapter: null, step: null };
  }
  const [chapterNumber, chapterData] = chapterEntries[chapterEntries.length - 1];
  const step = STEP_ORDER.findLast((stepName) => Boolean(chapterData[stepName]));
  return {
    chapter: Number(chapterNumber),
    step: step ?? null
  };
}

function normalizeMetrics(input?: Partial<RunMetrics>): RunMetrics {
  return {
    total_tokens: Number(input?.total_tokens ?? 0),
    total_tokens_in: Number(input?.total_tokens_in ?? 0),
    total_tokens_out: Number(input?.total_tokens_out ?? 0),
    total_cost_usd: Number(input?.total_cost_usd ?? 0),
    total_word_count: Number(input?.total_word_count ?? 0)
  };
}

function normalizeRunSummary(summary: ApiRunSummary): RunSummary {
  return {
    run_id: summary.run_id,
    path: summary.path,
    project: summary.project,
    total_chapters: summary.total_chapters,
    current_chapter: summary.current_chapter,
    latest_step: summary.latest_step ?? summary.latest_completed_step ?? null,
    updated_at: summary.updated_at,
    created_at: summary.created_at,
    metrics: normalizeMetrics({
      total_tokens: summary.total_tokens,
      total_tokens_in: summary.total_tokens_in,
      total_tokens_out: summary.total_tokens_out,
      total_cost_usd: summary.total_cost_usd,
      total_word_count: summary.total_word_count
    })
  };
}

function pickCurrentReview(
  chapters: Record<string, Record<string, string>>,
  reviewState?: Record<string, Record<string, ReviewState>>,
) {
  const latest = latestStepForChapters(chapters);
  if (latest.chapter === null || !latest.step) {
    return { chapter: null, step: null, state: null };
  }
  const state = reviewState?.[String(latest.chapter)]?.[latest.step] ?? null;
  return {
    chapter: latest.chapter,
    step: latest.step,
    state
  };
}

function pickCurrentCandidate(
  currentReview: { chapter: number | null; step: string | null },
  candidates?: CandidateOutput[],
): CandidateOutput | null {
  if (!currentReview.chapter || !currentReview.step || !candidates?.length) {
    return null;
  }
  const matching = candidates.filter(
    (candidate) => candidate.chapter === currentReview.chapter && candidate.step === currentReview.step,
  );
  return matching[matching.length - 1] ?? null;
}

function normalizeRunDetail(payload: ApiRunDetail): RunDetail {
  const data = payload.data ?? {};
  const chapters = data.chapters ?? {};
  const currentReview = pickCurrentReview(chapters, data.studio?.review_state);
  return {
    run_id: payload.run_id,
    state_path: payload.state_path,
    updated_at: data.updated_at ?? null,
    model_config: data.model_config ?? null,
    worksheet: data.worksheet ?? "",
    chapters,
    metrics: normalizeMetrics(data.metrics),
    current_chapter: latestStepForChapters(chapters).chapter,
    latest_step: latestStepForChapters(chapters).step,
    current_review: currentReview,
    current_candidate: pickCurrentCandidate(currentReview, data.studio?.candidate_outputs),
    studio: data.studio
  };
}

function genericFallbackRunDetail(runId: string): RunDetail | null {
  const summary = fallbackRuns.find((entry) => entry.run_id === runId);
  if (!summary) {
    return null;
  }
  const chapter = summary.current_chapter ?? 1;
  const latestStep = summary.latest_step ?? "plan";
  return {
    run_id: summary.run_id,
    state_path: `yfd-runner/state/${summary.run_id}.json`,
    updated_at: summary.updated_at,
    model_config: "default",
    worksheet: [
      "## section_1_required_data_layer",
      "",
      "### required_data_layer",
      "",
      "Imported worksheet context.",
      "",
      "## section_2_story_concept",
      "",
      "Story concept checkpoint."
    ].join("\n"),
    chapters: {
      "1": {
        plan: "done",
        draft: "done",
        final: "done",
        summary: "done"
      },
      [String(chapter)]: {
        [latestStep]: `${latestStep} checkpoint`
      }
    },
    metrics: summary.metrics,
    current_chapter: chapter,
    latest_step: latestStep,
    current_review: {
      chapter,
      step: latestStep,
      state: null
    },
    current_candidate: null,
    studio: {
      run_settings: {
        review_policy: {},
        output_dir: "yfd-runner/output",
        created_from: "worksheet"
      },
      review_state: {},
      candidate_outputs: []
    }
  };
}

export async function loadRuns(): Promise<RunSummary[]> {
  const payload = await apiFetch<{ runs: ApiRunSummary[] }>("/api/runs");
  if (payload?.runs?.length) {
    return payload.runs.map(normalizeRunSummary);
  }
  return fallbackRuns;
}

export async function loadRun(runId: string): Promise<RunDetail | null> {
  const payload = await apiFetch<ApiRunDetail>(`/api/runs/${runId}`);
  if (payload) {
    return normalizeRunDetail(payload);
  }
  if (runId === "partial_ch2_20260319") {
    return {
    run_id: "partial_ch2_20260319",
    state_path: "yfd-runner/state/partial_ch2_20260319.json",
    updated_at: "2026-03-25T08:55:00Z",
    model_config: "default",
    worksheet: [
      "## section_1_required_data_layer",
      "",
      "### required_data_layer",
      "",
      "Imported dossier and worksheet context.",
      "",
      "## section_2_story_concept",
      "",
      "[Fill in the story concept with enough detail to guide the cascade.]",
      "",
      "## section_3_character_arc",
      "",
      "[Fill in the protagonist arc and the core relational pressure for the story.]"
    ].join("\n"),
    chapters: {
      "1": {
        plan: "done",
        draft: "done",
        style: "done",
        craft: "done",
        final: "done",
        summary: "done"
      },
      "2": {
        plan: "done",
        draft: "done",
        repetition_audit: "done",
        style: "done",
        craft: "done",
        final: "done",
        summary: "done"
      },
      "3": {
        plan: "Outline ready.",
        draft: "Candidate draft pending review."
      }
    },
    metrics: fallbackRuns[0].metrics,
    current_chapter: 3,
    latest_step: "draft",
    current_review: {
      chapter: 3,
      step: "draft",
      state: {
        review_required: true,
        review_reason: "policy",
        review_status: "pending",
        approved_candidate_id: null,
        last_reviewed_at: null
      }
    },
    current_candidate: {
      candidate_id: "cand_demo_001",
      chapter: 3,
      step: "draft",
      source: "initial_run",
      steering_note: "",
      content:
        "Anna did not answer immediately. The silence settled between them in a way that felt less like hesitation than calibration, as if the sentence she was willing to release had to clear some private threshold first.\n\nHe had expected distance or polish. Instead he got precision. Not warmth exactly. Something harder to dismiss: the kind of attention that made a room reorganize itself around what had not yet been said.",
      status: "candidate",
      created_at: "2026-03-25T08:55:00Z"
    },
    studio: {
      run_settings: {
        review_policy: {
          plan: "manual",
          draft: "manual",
          final: "manual"
        },
        output_dir: "yfd-runner/output",
        created_from: "worksheet"
      },
      review_state: {
        "3": {
          draft: {
            review_required: true,
            review_reason: "policy",
            review_status: "pending",
            approved_candidate_id: null,
            last_reviewed_at: null
          }
        }
      },
      candidate_outputs: [
        {
          candidate_id: "cand_demo_001",
          chapter: 3,
          step: "draft",
          source: "initial_run",
          steering_note: "",
          content:
            "Anna did not answer immediately. The silence settled between them in a way that felt less like hesitation than calibration, as if the sentence she was willing to release had to clear some private threshold first.\n\nHe had expected distance or polish. Instead he got precision. Not warmth exactly. Something harder to dismiss: the kind of attention that made a room reorganize itself around what had not yet been said.",
          status: "candidate",
          created_at: "2026-03-25T08:55:00Z"
        }
      ]
    }
  };
  }
  return genericFallbackRunDetail(runId);
}

export async function loadTemplates(): Promise<TemplateFile[]> {
  const payload = await apiFetch<{ templates: TemplateFile[] }>("/api/templates");
  if (payload?.templates?.length) {
    return payload.templates;
  }
  return [
    { name: "01-plan.j2", path: "yfd-runner/templates/01-plan.j2" },
    { name: "02-draft.j2", path: "yfd-runner/templates/02-draft.j2" },
    { name: "04-edit-style.j2", path: "yfd-runner/templates/04-edit-style.j2" },
    { name: "05-edit-craft.j2", path: "yfd-runner/templates/05-edit-craft.j2" },
    { name: "06-final.j2", path: "yfd-runner/templates/06-final.j2" }
  ];
}

export async function loadConfig(): Promise<ConfigDetail> {
  const payload = await apiFetch<ApiConfigDetail>("/api/config");
  return payload ?? fallbackConfig;
}

export async function saveConfig(content: string): Promise<ConfigDetail> {
  return apiWrite<ConfigDetail>("/api/config", {
    method: "PUT",
    body: JSON.stringify({ content })
  });
}

export async function loadTemplate(name: string): Promise<TemplateDetail | null> {
  const payload = await apiFetch<TemplateDetail>(`/api/templates/${name}`);
  if (payload) {
    return payload;
  }
  if (name !== "04-edit-style.j2") {
    return null;
  }
  return {
    name: "04-edit-style.j2",
    path: "yfd-runner/templates/04-edit-style.j2",
    content: [
      "Refer to section_8_writing_style_rules",
      "and section_9_genre_lens in the worksheet:",
      "",
      "{{ worksheet }}",
      "",
      "Only flag actual rule violations.",
      "Keep the edits precise.",
      "Preserve the existing sentence engine unless clarity demands intervention."
    ].join("\n")
  };
}

export async function loadModels(): Promise<ModelFile[]> {
  const payload = await apiFetch<{ models: ModelFile[] }>("/api/models");
  if (payload?.models?.length) {
    return payload.models;
  }
  return [
    { name: "default.yaml", path: "yfd-runner/models/default.yaml" },
    { name: "claude-sonnet-4.6.yaml", path: "yfd-runner/models/claude-sonnet-4.6.yaml" },
    { name: "gpt-5.4.yaml", path: "yfd-runner/models/gpt-5.4.yaml" },
    { name: "gpt-5.4-nano.yaml", path: "yfd-runner/models/gpt-5.4-nano.yaml" }
  ];
}

export async function loadModel(name: string): Promise<ModelDetail | null> {
  const payload = await apiFetch<ModelDetail>(`/api/models/${name}`);
  if (payload) {
    return payload;
  }
  if (name === "gpt-5.4.yaml") {
    return {
      name,
      path: "yfd-runner/models/gpt-5.4.yaml",
      content: [
        "# Converted from yfd/llm-config/openrouter-openai-gpt.4.6.json.",
        "model: openai/gpt-5.4",
        "reasoning:",
        "  effort: high",
        "temperature: 1",
        "max_completion_tokens: 128000"
      ].join("\n"),
      data: {
        model: "openai/gpt-5.4",
        reasoning: { effort: "high" },
        temperature: 1,
        max_completion_tokens: 128000
      }
    };
  }
  return null;
}

export async function saveModel(name: string, content: string): Promise<ModelDetail> {
  return apiWrite<ModelDetail>(`/api/models/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify({ content })
  });
}

export async function loadTemplatePreview(runId: string, chapter: number, step: string): Promise<string> {
  const query = new URLSearchParams({
    run_id: runId,
    chapter: String(chapter),
    step
  });
  const payload = await apiFetch<{ rendered: string }>(`/api/render/step?${query.toString()}`);
  if (payload?.rendered) {
    return payload.rendered;
  }
  return [
    "The current chapter draft stays within the declared genre lens,",
    "but two sentences harden into abstraction where the style pass",
    "should keep the prose tactile and scene-bound.",
    "",
    "Recommended intervention: reduce the abstract compression in",
    "paragraph two and preserve the existing emotional temperature."
  ].join("\n");
}

export async function loadStepSettings(): Promise<Record<string, StepSetting>> {
  const payload = await apiFetch<{ steps: Record<string, StepSetting> }>("/api/step-settings");
  if (payload?.steps) {
    return payload.steps;
  }
  return {
    plan: {
      step: "plan",
      model_config: "claude-sonnet-4.6",
      max_tokens: 60000,
      temperature: 0.5,
      extras: {}
    },
    draft: {
      step: "draft",
      model_config: "gpt-5.4",
      max_tokens: 60000,
      temperature: 0.8,
      extras: {}
    },
    repetition: {
      step: "repetition",
      model_config: "gpt-5.4-nano",
      max_tokens: 60000,
      temperature: 0.3,
      extras: {}
    },
    style: {
      step: "style",
      model_config: "gpt-5.4-nano",
      max_tokens: 60000,
      temperature: 0.3,
      extras: {}
    },
    craft: {
      step: "craft",
      model_config: "gpt-5.4-nano",
      max_tokens: 60000,
      temperature: 0.3,
      extras: {}
    },
    final: {
      step: "final",
      model_config: "gpt-5.4",
      max_tokens: 60000,
      temperature: 0.7,
      extras: { reasoning: { effort: "low" } }
    },
    summary: {
      step: "summary",
      model_config: "gpt-5.4-nano",
      max_tokens: 60000,
      temperature: 0.3,
      extras: {}
    },
    cascade: {
      step: "cascade",
      model_config: "gpt-5.2-think",
      max_tokens: null,
      temperature: null,
      extras: {}
    }
  };
}

export async function saveStepSetting(step: string, input: StepSettingUpdateInput): Promise<StepSetting> {
  return apiWrite<StepSetting>(`/api/step-settings/${encodeURIComponent(step)}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export async function createRun(input: CreateRunInput): Promise<{ run_id: string; status: string; state_path: string }> {
  return apiWrite<{ run_id: string; status: string; state_path: string }>("/api/runs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function createProjectFromDossier(
  input: CreateProjectFromDossierInput,
): Promise<{ run_id: string; status: string; state_path: string }> {
  return apiWrite<{ run_id: string; status: string; state_path: string }>("/api/projects/from-dossier", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function branchRun(
  runId: string,
  input: BranchRunInput,
): Promise<{ run_id: string; parent_run_id: string; status: string; state_path: string }> {
  return apiWrite<{ run_id: string; parent_run_id: string; status: string; state_path: string }>(
    `/api/runs/${encodeURIComponent(runId)}/branch`,
    {
      method: "POST",
      body: JSON.stringify(input)
    },
  );
}

export async function rerunStep(
  runId: string,
  chapter: number,
  step: string,
  input: StepRerunInput,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/chapters/${chapter}/steps/${encodeURIComponent(step)}/rerun`,
    {
      method: "POST",
      body: JSON.stringify(input)
    },
  );
}

export async function approveCandidate(
  runId: string,
  chapter: number,
  step: string,
  candidateId: string,
): Promise<{ run_id: string; chapter: number; step: string; approved_candidate_id: string; status: string }> {
  return apiWrite<{ run_id: string; chapter: number; step: string; approved_candidate_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/chapters/${chapter}/steps/${encodeURIComponent(step)}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId })
    },
  );
}

export async function manualContinueStep(
  runId: string,
  chapter: number,
  step: string,
  content: string,
  reviewNote: string,
): Promise<{ run_id: string; chapter: number; step: string; candidate_id: string; status: string }> {
  return apiWrite<{ run_id: string; chapter: number; step: string; candidate_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/chapters/${chapter}/steps/${encodeURIComponent(step)}/manual-continue`,
    {
      method: "POST",
      body: JSON.stringify({
        content,
        review_note: reviewNote
      })
    },
  );
}

export async function executeStep(
  runId: string,
  chapter: number,
  step: string,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/chapters/${chapter}/steps/${encodeURIComponent(step)}`,
    {
      method: "POST",
      body: JSON.stringify({ force: true })
    },
  );
}

export async function autoRunChapter(
  runId: string,
  chapter: number,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/chapters/${chapter}/auto`,
    {
      method: "POST",
      body: JSON.stringify({ force: true })
    },
  );
}

export async function runCascadeSection(
  runId: string,
  sectionNumber: number,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/cascade/${sectionNumber}`,
    {
      method: "POST",
      body: JSON.stringify({ force: true })
    },
  );
}

export async function autoRunCascade(
  runId: string,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/cascade/auto`,
    {
      method: "POST",
      body: JSON.stringify({ force: true })
    },
  );
}

export async function buildManuscript(
  runId: string,
): Promise<{ job_id: string; status: string }> {
  return apiWrite<{ job_id: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/build-manuscript`,
    {
      method: "POST",
      body: JSON.stringify({})
    },
  );
}

export async function loadJob(jobId: string): Promise<JobStatus | null> {
  return apiFetch<JobStatus>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function cancelJob(jobId: string): Promise<JobStatus> {
  return apiWrite<JobStatus>(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function saveWorksheetSection(
  runId: string,
  sectionKey: string,
  content: string,
): Promise<{ run_id: string; section_key: string; status: string }> {
  return apiWrite<{ run_id: string; section_key: string; status: string }>(
    `/api/runs/${encodeURIComponent(runId)}/worksheet/${encodeURIComponent(sectionKey)}`,
    {
      method: "PUT",
      body: JSON.stringify({ content })
    },
  );
}

export async function loadRunArtifacts(runId: string): Promise<RunArtifactsIndex | null> {
  const payload = await apiFetch<ApiRunArtifactsIndex>(`/api/runs/${encodeURIComponent(runId)}/artifacts`);
  if (payload) {
    return payload;
  }
  return fallbackArtifactIndexes[runId] ?? null;
}

export async function loadRunManuscript(runId: string): Promise<ArtifactContent | null> {
  const payload = await apiFetch<ApiArtifactContent>(`/api/runs/${encodeURIComponent(runId)}/manuscript`);
  if (payload) {
    return payload;
  }
  const index = fallbackArtifactIndexes[runId];
  const content = fallbackArtifactContent[runId]?.manuscript;
  if (!index || !content) {
    return null;
  }
  return {
    run_id: runId,
    artifact: index.manuscript,
    content
  };
}

export async function loadArtifactContent(runId: string, artifactId: string): Promise<ArtifactContent | null> {
  const query = new URLSearchParams({ artifact: artifactId });
  const payload = await apiFetch<ApiArtifactContent>(`/api/runs/${encodeURIComponent(runId)}/artifacts/content?${query.toString()}`);
  if (payload) {
    return payload;
  }
  const index = fallbackArtifactIndexes[runId];
  const content = fallbackArtifactContent[runId]?.[artifactId];
  const artifact = index?.artifacts.find((entry) => entry.artifact_id === artifactId);
  if (!artifact || !content) {
    return null;
  }
  return {
    run_id: runId,
    artifact,
    content
  };
}
