import Link from "next/link";
import { notFound } from "next/navigation";
import { loadJob, loadRun } from "../../../lib/api";
import { parseWorksheetSections, worksheetSectionLabel } from "../../../lib/worksheet";
import {
  approveCandidateAction,
  autoRunCascadeAction,
  autoRunChapterAction,
  buildManuscriptAction,
  cancelJobAction,
  createBranchAction,
  executeStepAction,
  manualContinueAction,
  runCascadeSectionAction,
  rerunStepAction
} from "./actions";
import { JobPanel } from "./job-panel";

const STEP_COLUMNS = ["plan", "draft", "repetition_audit", "style", "craft", "final", "summary"];
const SECTION_HEADING_PATTERN = /^## (section_(\d+)_([^\n]+))\s*$/gm;
const BRACKET_PATTERN = /\[[A-Z][^\]\n]{15,}\]/;

type RunDetailPageProps = {
  params: Promise<{ runId: string }>;
  searchParams?: Promise<{
    message?: string;
    error?: string;
    jobId?: string;
    q?: string;
    chapter?: string;
    step?: string;
  }>;
};

function stepDot(content: string | undefined) {
  if (!content) {
    return "wait";
  }
  if (content === "Candidate draft pending review.") {
    return "live";
  }
  return "done";
}

function chapterLabel(chapter: number | null): string {
  if (!chapter) {
    return "ch00";
  }
  return `ch${String(chapter).padStart(2, "0")}`;
}

function flashTone(error?: string) {
  return error ? "warning" : "success";
}

function branchSuggestion(runId: string): string {
  return `${runId}_branch_a`;
}

function hasUnfilledBrackets(text: string): boolean {
  return BRACKET_PATTERN.test(text) || /\[[\s\S]{15,}\]/.test(text);
}

function nextIncompleteSection(worksheet: string): { number: number; key: string } | null {
  const matches = Array.from(worksheet.matchAll(SECTION_HEADING_PATTERN));
  if (!matches.length) {
    return null;
  }

  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const sectionNumber = Number(match[2]);
    if (sectionNumber === 1) {
      continue;
    }
    const start = match.index ?? 0;
    const end = index + 1 < matches.length ? (matches[index + 1].index ?? worksheet.length) : worksheet.length;
    const body = worksheet.slice(start, end).trim();
    if (hasUnfilledBrackets(body)) {
      return {
        number: sectionNumber,
        key: match[1]
      };
    }
  }

  return null;
}

function excerpt(text: string, query: string): string {
  const compact = text.replace(/\s+/g, " ").trim();
  const lower = compact.toLowerCase();
  const matchIndex = lower.indexOf(query.toLowerCase());
  if (matchIndex === -1) {
    return compact.slice(0, 160);
  }
  const start = Math.max(0, matchIndex - 45);
  const end = Math.min(compact.length, matchIndex + query.length + 80);
  const prefix = start > 0 ? "..." : "";
  const suffix = end < compact.length ? "..." : "";
  return `${prefix}${compact.slice(start, end)}${suffix}`;
}

function searchRun(run: NonNullable<Awaited<ReturnType<typeof loadRun>>>, query: string) {
  const trimmed = query.trim();
  if (!trimmed) {
    return { worksheet: [], outputs: [] } as const;
  }

  const lower = trimmed.toLowerCase();
  const worksheet = parseWorksheetSections(run.worksheet)
    .filter((section) => section.text.toLowerCase().includes(lower))
    .map((section) => ({
      sectionKey: section.sectionKey,
      label: worksheetSectionLabel(section),
      excerpt: excerpt(section.text, trimmed)
    }));

  const outputs = Object.entries(run.chapters)
    .flatMap(([chapter, chapterData]) =>
      Object.entries(chapterData)
        .filter(([, content]) => content.toLowerCase().includes(lower))
        .map(([step, content]) => ({
          chapter: Number(chapter),
          step,
          excerpt: excerpt(content, trimmed)
        })),
    )
    .sort((a, b) => a.chapter - b.chapter || a.step.localeCompare(b.step));

  return { worksheet, outputs } as const;
}

export default async function RunDetailPage({ params, searchParams }: RunDetailPageProps) {
  const { runId } = await params;
  const query = (await searchParams) ?? {};
  const run = await loadRun(runId);

  if (!run) {
    notFound();
  }

  const job = query.jobId ? await loadJob(query.jobId) : null;
  const chapters = Object.entries(run.chapters).sort((a, b) => Number(a[0]) - Number(b[0]));
  const requestedChapter = Number(query.chapter ?? 0);
  const requestedStep = String(query.step ?? "").trim();
  const requestedBucket = requestedChapter ? run.chapters[String(requestedChapter)] : undefined;
  const defaultFocusChapter = run.current_review.chapter ?? run.current_chapter ?? 1;
  const defaultFocusStep = run.current_review.step ?? run.latest_step ?? "plan";
  const focusChapter = requestedBucket && requestedStep && requestedBucket[requestedStep] ? requestedChapter : defaultFocusChapter;
  const focusStep = requestedBucket && requestedStep && requestedBucket[requestedStep] ? requestedStep : defaultFocusStep;
  const focusReview =
    run.studio?.review_state?.[String(focusChapter)]?.[focusStep] ??
    (run.current_review.chapter === focusChapter && run.current_review.step === focusStep ? run.current_review.state : null);
  const focusCandidate =
    run.studio?.candidate_outputs
      ?.filter((candidate) => candidate.chapter === focusChapter && candidate.step === focusStep)
      .slice(-1)[0] ??
    (run.current_candidate?.chapter === focusChapter && run.current_candidate.step === focusStep ? run.current_candidate : null);
  const candidateContent =
    focusCandidate?.content ??
    run.chapters[String(focusChapter)]?.[focusStep] ??
    "No current candidate output is available for this run yet.";
  const flashMessage = query.error ?? query.message;
  const branch = run.studio?.branch;
  const pendingReview = Boolean(focusReview?.review_required);
  const activeJob = job?.status === "queued" || job?.status === "running";
  const executionBlocked = pendingReview || activeJob;
  const nextCascade = nextIncompleteSection(run.worksheet);
  const searchQuery = String(query.q ?? "").trim();
  const searchResults = searchRun(run, searchQuery);
  const executionBlockReason = pendingReview
    ? "Review checkpoint pending. Approve, rerun, or manually continue before resuming execution."
    : activeJob
      ? "A job is already running for this run. Wait for it to finish or cancel it first."
      : null;

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Run Detail</div>
          <h1 className="page-title">{run.run_id}</h1>
          <p className="page-copy">
            Review comes first. The execution matrix provides orientation, but the central reading surface determines
            whether the output should advance.
          </p>
        </div>
        <div className="action-row">
          <Link className="button" href={`/templates?runId=${run.run_id}&chapter=${focusChapter}&step=${focusStep}`}>
            Open preview
          </Link>
          <Link className="button-secondary" href={`/worksheets?runId=${run.run_id}`}>
            Open worksheet
          </Link>
          <Link
            className="button-secondary"
            href={`/outputs?runId=${run.run_id}&chapter=${focusChapter}&step=${focusStep}${focusCandidate ? `&candidateId=${focusCandidate.candidate_id}` : ""}`}
          >
            Inspect outputs
          </Link>
          <Link className="button-secondary" href="/settings">
            Review settings
          </Link>
        </div>
      </section>

      {flashMessage ? (
        <div className="flash-banner" data-tone={flashTone(query.error)}>
          {flashMessage}
        </div>
      ) : null}

      <section className="matrix">
        <table>
          <thead>
            <tr>
              <th>Chapter</th>
              {STEP_COLUMNS.map((step) => (
                <th key={step}>{step.replace("_audit", "")}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {chapters.map(([chapterNumber, chapterData]) => (
              <tr key={chapterNumber}>
                <td className="mono">#{String(chapterNumber).padStart(2, "0")}</td>
                {STEP_COLUMNS.map((step) => (
                  <td key={step}>
                    <span className={`dot ${stepDot(chapterData[step])}`} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="detail-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Candidate output</h3>
            <span className="status-chip" data-tone={focusReview?.review_required ? "warning" : "success"}>
              {focusReview?.review_status ?? "not_required"}
            </span>
          </div>
          <div className="article">
            {candidateContent.split(/\n\n+/).map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
        </article>

        <aside className="stack">
          <div className="content-card">
            <div className="section-head">
              <h3>Review rail</h3>
              <span className="pill">
                {run.studio?.run_settings?.review_policy?.[focusStep] ?? "default"}
              </span>
            </div>
            <div className="rail-list">
              <div className="list-item">
                <div className="list-title">Current focus</div>
                <div className="list-copy mono">
                  {chapterLabel(focusChapter)} · {focusStep}
                </div>
              </div>
              <div className="list-item">
                <div className="list-title">Model config</div>
                <div className="list-copy mono">{run.model_config ?? "default"}</div>
              </div>
              <div className="list-item">
                <div className="list-title">Review state</div>
                <div className="list-copy">
                  {focusReview?.review_reason ?? "none"} · {focusReview?.review_status ?? "not_required"}
                </div>
              </div>
              <div className="list-item">
                <div className="list-title">State file</div>
                <div className="list-copy mono">{run.state_path}</div>
              </div>
              <div className="list-item">
                <div className="list-title">Output directory</div>
                <div className="list-copy mono">{run.studio?.run_settings?.output_dir ?? "yfd-runner/output"}</div>
              </div>
              <div className="list-item">
                <div className="list-title">Metrics</div>
                <div className="list-copy">
                  {run.metrics.total_tokens.toLocaleString()} tokens · {run.metrics.total_word_count.toLocaleString()} words
                </div>
              </div>
              {branch ? (
                <div className="list-item">
                  <div className="list-title">Branch lineage</div>
                  <div className="list-copy mono">
                    {branch.parent_run_id ?? "parent?"}
                    {branch.branched_from_chapter ? ` · from ch${String(branch.branched_from_chapter).padStart(2, "0")}` : ""}
                  </div>
                  {branch.branch_note ? <div className="list-copy">{branch.branch_note}</div> : null}
                </div>
              ) : null}
            </div>
          </div>

          {job ? <JobPanel initialJob={job} runId={run.run_id} cancelAction={cancelJobAction} /> : null}
        </aside>
      </section>

      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Run retrieval</h3>
            <span className="pill">{searchQuery ? "active" : "single run"}</span>
          </div>
          <form className="stack" action={`/runs/${run.run_id}`} method="get">
            <label className="field-group">
              <span className="field-label">Search this run</span>
              <input
                className="field-input mono"
                type="search"
                name="q"
                defaultValue={searchQuery}
                placeholder="Search worksheet sections, plans, drafts, finals, or summaries."
              />
            </label>
            <div className="action-row">
              <button className="button-secondary" type="submit">
                Search
              </button>
              {searchQuery ? (
                <Link className="button-secondary" href={`/runs/${run.run_id}`}>
                  Clear
                </Link>
              ) : null}
            </div>
          </form>
        </article>

        <article className="content-card">
          <div className="section-head">
            <h3>Search results</h3>
            <span className="pill">
              {searchQuery ? searchResults.worksheet.length + searchResults.outputs.length : 0}
            </span>
          </div>
          {!searchQuery ? (
            <div className="empty-note">Search stays inside this run and links directly to worksheet sections or chapter-step output.</div>
          ) : (
            <div className="stack">
              <div className="nested-card">
                <div className="section-head">
                  <h3>Worksheet</h3>
                  <span className="pill">{searchResults.worksheet.length}</span>
                </div>
                <div className="rail-list">
                  {searchResults.worksheet.length ? (
                    searchResults.worksheet.map((result) => (
                      <Link
                        key={result.sectionKey}
                        className="list-item"
                        href={`/worksheets?runId=${run.run_id}&section=${result.sectionKey}`}
                      >
                        <div className="list-title">{result.label}</div>
                        <div className="list-copy">{result.excerpt}</div>
                      </Link>
                    ))
                  ) : (
                    <div className="empty-note">No worksheet section matches this query.</div>
                  )}
                </div>
              </div>
              <div className="nested-card">
                <div className="section-head">
                  <h3>Chapter output</h3>
                  <span className="pill">{searchResults.outputs.length}</span>
                </div>
                <div className="rail-list">
                  {searchResults.outputs.length ? (
                    searchResults.outputs.map((result) => (
                      <Link
                        key={`${result.chapter}-${result.step}-${result.excerpt}`}
                        className="list-item"
                        href={`/runs/${run.run_id}?q=${encodeURIComponent(searchQuery)}&chapter=${result.chapter}&step=${encodeURIComponent(result.step)}`}
                      >
                        <div className="list-title">
                          ch{String(result.chapter).padStart(2, "0")} · {result.step}
                        </div>
                        <div className="list-copy">{result.excerpt}</div>
                      </Link>
                    ))
                  ) : (
                    <div className="empty-note">No chapter-step output matches this query.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </article>
      </section>

      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Review actions</h3>
            <span className="pill">{focusReview?.review_required ? "checkpoint" : "available"}</span>
          </div>
          <div className="stack">
            <form action={approveCandidateAction} className="action-row">
              <input type="hidden" name="run_id" value={run.run_id} />
              <input type="hidden" name="chapter" value={focusChapter} />
              <input type="hidden" name="step" value={focusStep} />
              <input type="hidden" name="candidate_id" value={focusCandidate?.candidate_id ?? ""} />
              <button className="button" type="submit" disabled={!focusCandidate}>
                Approve candidate
              </button>
            </form>

            <form action={rerunStepAction} className="stack">
              <input type="hidden" name="run_id" value={run.run_id} />
              <input type="hidden" name="chapter" value={focusChapter} />
              <input type="hidden" name="step" value={focusStep} />
              <label className="field-group">
                <span className="field-label">Steering note</span>
                <textarea
                  className="field-input mono"
                  name="steering_note"
                  rows={4}
                  placeholder="Reduce exposition, darken the chapter turn, or tighten the opening beat."
                />
              </label>
              <label className="field-group">
                <span className="field-label">Review mode</span>
                <select className="field-input mono" name="review_mode" defaultValue="manual">
                  <option value="manual">manual</option>
                  <option value="on_warning">on_warning</option>
                  <option value="auto">auto</option>
                </select>
              </label>
              <div className="action-row">
                <button className="button-secondary" type="submit">
                  Rerun step
                </button>
                <Link className="button-secondary" href={`/templates?runId=${run.run_id}&chapter=${focusChapter}&step=${focusStep}`}>
                  Render prompt
                </Link>
              </div>
            </form>
          </div>
        </article>

        <article className="content-card">
          <div className="section-head">
            <h3>Manual continue</h3>
            <span className="pill">canonical write</span>
          </div>
          <form action={manualContinueAction} className="stack">
            <input type="hidden" name="run_id" value={run.run_id} />
            <input type="hidden" name="chapter" value={focusChapter} />
            <input type="hidden" name="step" value={focusStep} />
            <label className="field-group">
              <span className="field-label">Edited output</span>
              <textarea className="editor-input mono" name="content" rows={14} defaultValue={candidateContent} />
            </label>
            <label className="field-group">
              <span className="field-label">Review note</span>
              <input className="field-input mono" name="review_note" placeholder="Explain what changed." />
            </label>
            <div className="action-row">
              <button className="button" type="submit">
                Save and continue
              </button>
            </div>
          </form>
        </article>
      </section>

      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Execution controls</h3>
            <span className="pill">{executionBlocked ? "blocked" : "ready"}</span>
          </div>
          <div className="stack">
            <div className="kv-grid">
              <div className="kv-row">
                <span className="kv-label">Current step target</span>
                <span className="kv-value mono">
                  {chapterLabel(focusChapter)} · {focusStep}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Chapter auto target</span>
                <span className="kv-value mono">{chapterLabel(focusChapter)}</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Cascade target</span>
                <span className="kv-value mono">
                  {nextCascade ? `${nextCascade.key} (#${nextCascade.number})` : "complete"}
                </span>
              </div>
            </div>
            {executionBlockReason ? <div className="empty-note">{executionBlockReason}</div> : null}
            <div className="action-grid">
              <form action={executeStepAction}>
                <input type="hidden" name="run_id" value={run.run_id} />
                <input type="hidden" name="chapter" value={focusChapter} />
                <input type="hidden" name="step" value={focusStep} />
                <button className="button-secondary action-block" type="submit" disabled={executionBlocked}>
                  Run once
                </button>
              </form>
              <form action={autoRunChapterAction}>
                <input type="hidden" name="run_id" value={run.run_id} />
                <input type="hidden" name="chapter" value={focusChapter} />
                <button className="button-secondary action-block" type="submit" disabled={executionBlocked}>
                  Auto-run chapter
                </button>
              </form>
              <form action={runCascadeSectionAction}>
                <input type="hidden" name="run_id" value={run.run_id} />
                <input type="hidden" name="section_number" value={nextCascade?.number ?? ""} />
                <button
                  className="button-secondary action-block"
                  type="submit"
                  disabled={executionBlocked || !nextCascade}
                >
                  Run next cascade section
                </button>
              </form>
              <form action={autoRunCascadeAction}>
                <input type="hidden" name="run_id" value={run.run_id} />
                <button
                  className="button-secondary action-block"
                  type="submit"
                  disabled={executionBlocked || !nextCascade}
                >
                  Auto-run remaining cascade
                </button>
              </form>
              <form action={buildManuscriptAction}>
                <input type="hidden" name="run_id" value={run.run_id} />
                <button className="button-secondary action-block" type="submit" disabled={executionBlocked}>
                  Build manuscript
                </button>
              </form>
            </div>
          </div>
        </article>

        <article className="content-card">
          <div className="section-head">
            <h3>Branch run</h3>
            <span className="pill">metadata only</span>
          </div>
          <form action={createBranchAction} className="stack">
            <input type="hidden" name="run_id" value={run.run_id} />
            <input type="hidden" name="branched_from_chapter" value={focusChapter} />
            <label className="field-group">
              <span className="field-label">New run id</span>
              <input className="field-input mono" name="new_run_id" defaultValue={branchSuggestion(run.run_id)} />
            </label>
            <label className="field-group">
              <span className="field-label">Branch note</span>
              <input className="field-input mono" name="branch_note" placeholder="Try a darker chapter progression." />
            </label>
            <div className="action-row">
              <button className="button-secondary" type="submit">
                Create branch
              </button>
            </div>
          </form>
        </article>

        <article className="content-card">
          <div className="section-head">
            <h3>Other actions</h3>
            <span className="pill">safe</span>
          </div>
          <div className="rail-list">
            <Link
              className="button-secondary"
              href={`/outputs?runId=${run.run_id}&chapter=${focusChapter}&step=${focusStep}${focusCandidate ? `&candidateId=${focusCandidate.candidate_id}` : ""}`}
            >
              Inspect outputs
            </Link>
            <Link className="button-secondary" href="/templates">
              Tune template
            </Link>
            <Link className="button-secondary" href={`/worksheets?runId=${run.run_id}`}>
              Edit worksheet
            </Link>
            <Link className="button-secondary" href="/settings">
              Inspect step settings
            </Link>
          </div>
        </article>
      </section>
    </>
  );
}
