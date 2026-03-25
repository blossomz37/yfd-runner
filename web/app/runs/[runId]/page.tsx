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
  const currentReview = run.studio?.review_state?.["3"]?.draft;

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
          <button className="button" type="button">
            Approve candidate
          </button>
          <button className="button-secondary" type="button">
            Rerun with note
          </button>
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
              {currentReview?.review_status ?? "pending"}
            </span>
          </div>
          <div className="article">
            <p>
              Anna did not answer immediately. The silence settled between them in a way that felt less like hesitation
              than calibration, as if the sentence she was willing to release had to clear some private threshold first.
            </p>
            <p>
              He had expected distance or polish. Instead he got precision. Not warmth exactly. Something harder to
              dismiss: the kind of attention that made a room reorganize itself around what had not yet been said.
            </p>
          </div>
        </article>

        <aside className="stack">
          <div className="content-card">
            <div className="section-head">
              <h3>Review rail</h3>
              <span className="pill">manual</span>
            </div>
            <div className="rail-list">
              <div className="list-item">
                <div className="list-title">Template</div>
                <div className="list-copy mono">02-draft.j2</div>
              </div>
              <div className="list-item">
                <div className="list-title">Model config</div>
                <div className="list-copy mono">{run.model_config ?? "default"}</div>
              </div>
              <div className="list-item">
                <div className="list-title">Review state</div>
                <div className="list-copy">
                  {currentReview?.review_reason ?? "policy"} · {currentReview?.review_status ?? "pending"}
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
              <button className="button" type="button">
                Approve and continue
              </button>
              <button className="button-secondary" type="button">
                Open rendered prompt
              </button>
              <Link className="button-secondary" href="/templates">
                Tune template
              </Link>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}
