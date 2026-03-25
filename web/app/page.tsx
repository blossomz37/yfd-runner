import Link from "next/link";
import { loadRuns } from "../lib/api";

function formatDollars(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

export default async function RunsDashboardPage() {
  const runs = await loadRuns();
  const reviewCount = runs.filter((run) => run.latest_step === "draft" || run.latest_step === "final").length;

  return (
    <>
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">Hybrid Editorial Console</div>
          <h1 className="hero-title">Active runs, real state files, and the next meaningful move.</h1>
          <p className="hero-copy">
            This surface is not a metrics wall. It is an entry point into review state, chapter position, rendered
            prompt access, and branch-safe continuation.
          </p>
          <div className="action-row">
            <Link className="button" href="/intake">
              Create project
            </Link>
            <Link className="button-secondary" href="/templates">
              Open template editor
            </Link>
          </div>
        </div>
        <div className="command-card">
          <div className="section-head">
            <h3>Command palette preview</h3>
            <span className="kbd">⌘K</span>
          </div>
          <div className="stack">
            <div className="list-item">
              <div className="list-title">Open run</div>
              <div className="list-copy mono">partial_ch2_20260319</div>
            </div>
            <div className="list-item">
              <div className="list-title">Render template</div>
              <div className="list-copy mono">04-edit-style.j2 for ch03 style</div>
            </div>
            <div className="list-item">
              <div className="list-title">Branch current run</div>
              <div className="list-copy mono">preserve the parent before experimenting</div>
            </div>
          </div>
        </div>
      </section>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="metric-label">Tracked runs</div>
          <div className="stat-value">{runs.length}</div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Needs review</div>
          <div className="stat-value">{reviewCount}</div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Current focus</div>
          <div className="stat-value">ch03</div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Last action</div>
          <div className="stat-value">Resume</div>
        </div>
      </section>

      <section className="section-head">
        <div>
          <div className="eyebrow">Runs Dashboard</div>
          <h2 className="page-title">State-backed runs and quick continuation</h2>
        </div>
        <Link className="button-secondary" href="/settings">
          Step settings
        </Link>
      </section>

      <section className="run-grid">
        {runs.map((run) => (
          <article key={run.run_id} className="run-card">
            <div className="run-card-head">
              <div>
                <div className="list-title">{run.run_id}</div>
                <div className="muted-copy">
                  Chapter {String(run.current_chapter ?? 0).padStart(2, "0")} · {run.latest_step ?? "idle"}
                </div>
              </div>
              <span
                className="status-chip"
                data-tone={run.latest_step === "draft" ? "warning" : run.latest_step === "summary" ? "success" : "accent"}
              >
                {run.latest_step ?? "idle"}
              </span>
            </div>
            <div className="metric-row">
              <div className="metric-box">
                <div className="metric-label">Tokens</div>
                <div className="metric-value">{run.total_tokens.toLocaleString()}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Cost</div>
                <div className="metric-value">{formatDollars(run.total_cost_usd)}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Words</div>
                <div className="metric-value">{run.total_word_count.toLocaleString()}</div>
              </div>
            </div>
            <div className="row-between">
              <div className="muted-copy mono">{run.updated_at ?? "unknown update"}</div>
              <div className="run-meta">
                <Link className="button-secondary" href={`/runs/${run.run_id}`}>
                  Open detail
                </Link>
                <button className="button" type="button">
                  Resume
                </button>
              </div>
            </div>
          </article>
        ))}
      </section>
    </>
  );
}
