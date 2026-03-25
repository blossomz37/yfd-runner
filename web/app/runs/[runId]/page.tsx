import Link from "next/link";
import { notFound } from "next/navigation";
import { loadJob, loadRun } from "../../../lib/api";
import {
  approveCandidateAction,
  cancelJobAction,
  createBranchAction,
  manualContinueAction,
  rerunStepAction
} from "./actions";

const STEP_COLUMNS = ["plan", "draft", "repetition_audit", "style", "craft", "final", "summary"];

type RunDetailPageProps = {
  params: Promise<{ runId: string }>;
  searchParams?: Promise<{
    message?: string;
    error?: string;
    jobId?: string;
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

export default async function RunDetailPage({ params, searchParams }: RunDetailPageProps) {
  const { runId } = await params;
  const query = (await searchParams) ?? {};
  const run = await loadRun(runId);

  if (!run) {
    notFound();
  }

  const job = query.jobId ? await loadJob(query.jobId) : null;
  const chapters = Object.entries(run.chapters).sort((a, b) => Number(a[0]) - Number(b[0]));
  const currentReview = run.current_review.state;
  const currentChapter = run.current_review.chapter ?? run.current_chapter;
  const currentStep = run.current_review.step ?? run.latest_step ?? "draft";
  const candidateContent =
    run.current_candidate?.content ??
    (currentChapter ? run.chapters[String(currentChapter)]?.[currentStep ?? ""] : "") ??
    "No current candidate output is available for this run yet.";
  const flashMessage = query.error ?? query.message;
  const branch = run.studio?.branch;
  const recentEvents = job?.events?.slice(-5).reverse() ?? [];

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
          <Link className="button" href={`/templates?runId=${run.run_id}&chapter=${currentChapter ?? 1}&step=${currentStep}`}>
            Open preview
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
            <span className="status-chip" data-tone={currentReview?.review_required ? "warning" : "success"}>
              {currentReview?.review_status ?? "not_required"}
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
                {run.studio?.run_settings?.review_policy?.[currentStep ?? ""] ?? "default"}
              </span>
            </div>
            <div className="rail-list">
              <div className="list-item">
                <div className="list-title">Current focus</div>
                <div className="list-copy mono">
                  {chapterLabel(currentChapter)} · {currentStep}
                </div>
              </div>
              <div className="list-item">
                <div className="list-title">Model config</div>
                <div className="list-copy mono">{run.model_config ?? "default"}</div>
              </div>
              <div className="list-item">
                <div className="list-title">Review state</div>
                <div className="list-copy">
                  {currentReview?.review_reason ?? "none"} · {currentReview?.review_status ?? "not_required"}
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

          {job ? (
            <div className="content-card">
              <div className="section-head">
                <h3>Active job</h3>
                <span
                  className="status-chip"
                  data-tone={job.status === "failed" ? "warning" : job.status === "succeeded" ? "success" : "accent"}
                >
                  {job.status}
                </span>
              </div>
              <div className="rail-list">
                <div className="list-item">
                  <div className="list-title">Job</div>
                  <div className="list-copy mono">{job.job_type}</div>
                </div>
                <div className="list-item">
                  <div className="list-title">Target</div>
                  <div className="list-copy mono">
                    {String(job.target.chapter ?? job.target.section_number ?? "run")} · {String(job.target.step ?? "job")}
                  </div>
                </div>
                {job.error ? (
                  <div className="list-item">
                    <div className="list-title">Error</div>
                    <div className="list-copy">{job.error}</div>
                  </div>
                ) : null}
                <div className="event-list">
                  {recentEvents.map((event, index) => (
                    <div key={`${event.event}-${index}`} className="event-item">
                      <div className="event-name mono">{event.event}</div>
                      <div className="list-copy">{event.message}</div>
                    </div>
                  ))}
                </div>
                <div className="action-row">
                  <Link className="button-secondary" href={`/runs/${run.run_id}?jobId=${job.job_id}`}>
                    Refresh status
                  </Link>
                  {job.status === "queued" || job.status === "running" ? (
                    <form action={cancelJobAction}>
                      <input type="hidden" name="run_id" value={run.run_id} />
                      <input type="hidden" name="job_id" value={job.job_id} />
                      <button className="button-secondary" type="submit">
                        Cancel job
                      </button>
                    </form>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </aside>
      </section>

      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Review actions</h3>
            <span className="pill">{currentReview?.review_required ? "checkpoint" : "available"}</span>
          </div>
          <div className="stack">
            <form action={approveCandidateAction} className="action-row">
              <input type="hidden" name="run_id" value={run.run_id} />
              <input type="hidden" name="chapter" value={currentChapter ?? 1} />
              <input type="hidden" name="step" value={currentStep} />
              <input type="hidden" name="candidate_id" value={run.current_candidate?.candidate_id ?? ""} />
              <button className="button" type="submit" disabled={!run.current_candidate}>
                Approve candidate
              </button>
            </form>

            <form action={rerunStepAction} className="stack">
              <input type="hidden" name="run_id" value={run.run_id} />
              <input type="hidden" name="chapter" value={currentChapter ?? 1} />
              <input type="hidden" name="step" value={currentStep} />
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
                <Link className="button-secondary" href={`/templates?runId=${run.run_id}&chapter=${currentChapter ?? 1}&step=${currentStep}`}>
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
            <input type="hidden" name="chapter" value={currentChapter ?? 1} />
            <input type="hidden" name="step" value={currentStep} />
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
            <h3>Branch run</h3>
            <span className="pill">metadata only</span>
          </div>
          <form action={createBranchAction} className="stack">
            <input type="hidden" name="run_id" value={run.run_id} />
            <input type="hidden" name="branched_from_chapter" value={currentChapter ?? ""} />
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
            <Link className="button-secondary" href="/templates">
              Tune template
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
