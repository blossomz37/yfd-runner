import Link from "next/link";
import { notFound } from "next/navigation";
import { loadRun } from "../../../lib/api";

const STEP_COLUMNS = ["plan", "draft", "repetition_audit", "style", "craft", "final", "summary"];

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

export default async function RunDetailPage({
  params
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const run = await loadRun(runId);

  if (!run) {
    notFound();
  }

  const chapters = Object.entries(run.chapters).sort((a, b) => Number(a[0]) - Number(b[0]));
  const currentReview = run.current_review.state;
  const currentChapter = run.current_review.chapter ?? run.current_chapter;
  const currentStep = run.current_review.step ?? run.latest_step ?? "draft";
  const candidateContent =
    run.current_candidate?.content ??
    (currentChapter ? run.chapters[String(currentChapter)]?.[currentStep ?? ""] : "") ??
    "No current candidate output is available for this run yet.";

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
            <span className="status-chip" data-tone="warning">
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
            </div>
          </div>

          <div className="content-card">
            <div className="section-head">
              <h3>Actions</h3>
              <span className="pill">safe</span>
            </div>
            <div className="rail-list">
              <Link className="button" href={`/templates?runId=${run.run_id}&chapter=${currentChapter ?? 1}&step=${currentStep}`}>
                Render prompt
              </Link>
              <Link className="button-secondary" href="/templates">
                Tune template
              </Link>
              <Link className="button-secondary" href="/settings">
                Inspect step settings
              </Link>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}
