export type RunSummary = {
  run_id: string;
  current_chapter: number | null;
  latest_step: string | null;
  updated_at: string | null;
  total_tokens: number;
  total_cost_usd: number;
  total_word_count: number;
};

export type RunDetail = {
  run_id: string;
  worksheet: string;
  model_config: string | null;
  updated_at: string | null;
  chapters: Record<string, Record<string, string>>;
  studio?: {
    run_settings?: {
      review_policy?: Record<string, string>;
      output_dir?: string | null;
      created_from?: string;
    };
    review_state?: Record<string, Record<string, ReviewState>>;
    branch?: {
      parent_run_id?: string | null;
      branched_from_chapter?: number | null;
      branch_note?: string;
    };
  };
};

export type ReviewState = {
  review_required: boolean;
  review_reason: string;
  review_status: string;
  approved_candidate_id: string | null;
  last_reviewed_at: string | null;
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

const API_BASE = process.env.YFD_STUDIO_API_BASE || "http://127.0.0.1:8000";

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store"
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function loadRuns(): Promise<RunSummary[]> {
  const payload = await apiFetch<{ runs: RunSummary[] }>("/api/runs");
  if (payload?.runs?.length) {
    return payload.runs;
  }
  return [
    {
      run_id: "partial_ch2_20260319",
      current_chapter: 3,
      latest_step: "draft",
      updated_at: "2026-03-25T08:55:00Z",
      total_tokens: 186240,
      total_cost_usd: 4.18,
      total_word_count: 9271
    },
    {
      run_id: "phase11_ch1_auto",
      current_chapter: 2,
      latest_step: "summary",
      updated_at: "2026-03-25T07:40:00Z",
      total_tokens: 144210,
      total_cost_usd: 3.11,
      total_word_count: 7118
    },
    {
      run_id: "phase11_offline",
      current_chapter: 2,
      latest_step: "plan",
      updated_at: "2026-03-24T23:14:00Z",
      total_tokens: 42210,
      total_cost_usd: 0.77,
      total_word_count: 1820
    }
  ];
}

export async function loadRun(runId: string): Promise<RunDetail | null> {
  const payload = await apiFetch<RunDetail>(`/api/runs/${runId}`);
  if (payload) {
    return payload;
  }
  if (runId !== "partial_ch2_20260319") {
    return null;
  }
  return {
    run_id: "partial_ch2_20260319",
    worksheet: "## section_1_required_data_layer\n\n### required_data_layer\n\nImported dossier and worksheet context.",
    model_config: "default",
    updated_at: "2026-03-25T08:55:00Z",
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
        plan: "done",
        draft: "Candidate draft pending review."
      }
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
      }
    }
  };
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
