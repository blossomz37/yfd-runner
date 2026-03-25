import Link from "next/link";
import { loadConfig } from "../../lib/api";
import { saveConfigAction } from "./actions";

type ConfigPageProps = {
  searchParams?: Promise<{
    message?: string;
    error?: string;
  }>;
};

export default async function ConfigPage({ searchParams }: ConfigPageProps) {
  const params = (await searchParams) ?? {};
  const config = await loadConfig();

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Config</div>
          <h1 className="page-title">Raw config editor</h1>
          <p className="page-copy">
            This is the advanced YAML surface for <span className="mono">config.yaml</span>. Structured step settings
            remain in <span className="mono">/settings</span>; this page exists for lower-level edits only.
          </p>
        </div>
        <div className="action-row">
          <Link className="button-secondary" href="/settings">
            Back to settings
          </Link>
        </div>
      </section>

      {params.message || params.error ? (
        <div className="flash-banner" data-tone={params.error ? "warning" : "success"}>
          {params.error ?? params.message}
        </div>
      ) : null}

      <section className="detail-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>config.yaml</h3>
            <span className="status-chip" data-tone="accent">
              advanced
            </span>
          </div>
          <form action={saveConfigAction} className="stack">
            <label className="field-group">
              <span className="field-label">Config path</span>
              <input className="field-input mono" value={config.path} readOnly />
            </label>
            <label className="field-group">
              <span className="field-label">YAML</span>
              <textarea className="editor-input mono" name="content" rows={24} defaultValue={config.content} />
            </label>
            <div className="action-row">
              <button className="button" type="submit">
                Save config
              </button>
            </div>
          </form>
        </article>

        <aside className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>Notes</h3>
              <span className="pill">raw YAML</span>
            </div>
            <div className="empty-note">
              Use this page for project-level or non-step overrides that do not fit the structured settings UI.
            </div>
          </article>

          <article className="content-card">
            <div className="section-head">
              <h3>Preserve</h3>
              <span className="pill">current workflow</span>
            </div>
            <div className="kv-grid">
              <div className="kv-row">
                <span className="kv-label">Structured editing</span>
                <span className="kv-value mono">/settings</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Runner state</span>
                <span className="kv-value mono">yfd-runner/state</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Template routing</span>
                <span className="kv-value mono">step_models + step_overrides</span>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </>
  );
}
