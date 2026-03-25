import { loadRuns, loadTemplate, loadTemplatePreview, loadTemplates } from "../../lib/api";

export default async function TemplatesPage() {
  const templates = await loadTemplates();
  const runs = await loadRuns();
  const activeTemplate = await loadTemplate("04-edit-style.j2");
  const activeRun = runs[0]?.run_id ?? "partial_ch2_20260319";
  const preview = await loadTemplatePreview(activeRun, 3, "style");

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Template Editor</div>
          <h1 className="page-title">Edit source without losing the reading surface.</h1>
          <p className="page-copy">
            Code stays crisp and low-noise. The preview reads like a document, with run and chapter context always
            visible.
          </p>
        </div>
        <div className="action-row">
          <button className="button" type="button">
            Save template
          </button>
          <button className="button-secondary" type="button">
            Render preview
          </button>
        </div>
      </section>

      <section className="template-grid">
        <aside className="content-card">
          <div className="section-head">
            <h3>Files</h3>
            <span className="pill">{templates.length} templates</span>
          </div>
          <div className="rail-list">
            {templates.map((template) => (
              <div
                key={template.name}
                className={`list-item${template.name === "04-edit-style.j2" ? " active" : ""}`}
              >
                <div className="list-title mono">{template.name}</div>
                <div className="list-copy">{template.path}</div>
              </div>
            ))}
          </div>
          <div className="stack">
            <div className="section-head">
              <h3>Bound context</h3>
              <span className="status-chip" data-tone="accent">
                live
              </span>
            </div>
            <div className="list-item">
              <div className="list-title">Run</div>
              <div className="list-copy mono">{activeRun}</div>
            </div>
            <div className="list-item">
              <div className="list-title">Step</div>
              <div className="list-copy mono">style</div>
            </div>
          </div>
        </aside>

        <div className="stack">
          <article className="editor-card">
            <div className="section-head">
              <h3>Source</h3>
              <span className="pill mono">{activeTemplate?.name ?? "04-edit-style.j2"}</span>
            </div>
            <pre className="codeframe mono">{activeTemplate?.content ?? "Template not available."}</pre>
          </article>

          <article className="preview-card">
            <div className="section-head">
              <h3>Rendered preview</h3>
              <span className="status-chip" data-tone="success">
                chapter 03
              </span>
            </div>
            <pre className="previewframe article">{preview}</pre>
          </article>
        </div>
      </section>
    </>
  );
}
