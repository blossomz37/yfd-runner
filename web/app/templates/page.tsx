import Link from "next/link";
import { loadRun, loadRuns, loadTemplate, loadTemplatePreview, loadTemplates } from "../../lib/api";

type TemplatesPageProps = {
  searchParams?: Promise<{
    template?: string;
    runId?: string;
    chapter?: string;
    step?: string;
  }>;
};

const PREVIEW_STEPS = ["plan", "draft", "style", "craft", "final", "summary"];

export default async function TemplatesPage({ searchParams }: TemplatesPageProps) {
  const params = (await searchParams) ?? {};
  const templates = await loadTemplates();
  const runs = await loadRuns();
  const activeTemplateName = params.template ?? templates[0]?.name ?? "04-edit-style.j2";
  const activeRunId = params.runId ?? runs[0]?.run_id ?? "partial_ch2_20260319";
  const activeRun = await loadRun(activeRunId);
  const activeChapter = Number(params.chapter ?? activeRun?.current_chapter ?? 1);
  const activeStep = params.step ?? activeRun?.latest_step ?? "draft";
  const activeTemplate = await loadTemplate(activeTemplateName);
  const preview = await loadTemplatePreview(activeRunId, activeChapter, activeStep);

  const templateHref = (templateName: string) =>
    `/templates?template=${encodeURIComponent(templateName)}&runId=${encodeURIComponent(activeRunId)}&chapter=${activeChapter}&step=${encodeURIComponent(activeStep)}`;
  const stepHref = (stepName: string) =>
    `/templates?template=${encodeURIComponent(activeTemplateName)}&runId=${encodeURIComponent(activeRunId)}&chapter=${activeChapter}&step=${encodeURIComponent(stepName)}`;
  const runHref = (runId: string) =>
    `/templates?template=${encodeURIComponent(activeTemplateName)}&runId=${encodeURIComponent(runId)}&chapter=${activeChapter}&step=${encodeURIComponent(activeStep)}`;

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
              <Link
                key={template.name}
                className={`list-item${template.name === activeTemplateName ? " active" : ""}`}
                href={templateHref(template.name)}
              >
                <div className="list-title mono">{template.name}</div>
                <div className="list-copy">{template.path}</div>
              </Link>
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
              <div className="list-copy mono">{activeRunId}</div>
            </div>
            <div className="list-item">
              <div className="list-title">Chapter</div>
              <div className="list-copy mono">ch{String(activeChapter).padStart(2, "0")}</div>
            </div>
            <div className="selector-row">
              {runs.slice(0, 4).map((run) => (
                <Link key={run.run_id} className={`mini-link${run.run_id === activeRunId ? " active" : ""}`} href={runHref(run.run_id)}>
                  {run.run_id}
                </Link>
              ))}
            </div>
            <div className="selector-row">
              {PREVIEW_STEPS.map((stepName) => (
                <Link key={stepName} className={`mini-link${stepName === activeStep ? " active" : ""}`} href={stepHref(stepName)}>
                  {stepName}
                </Link>
              ))}
            </div>
          </div>
        </aside>

        <div className="stack">
          <article className="editor-card">
            <div className="section-head">
              <h3>Source</h3>
              <span className="pill mono">{activeTemplate?.name ?? activeTemplateName}</span>
            </div>
            <pre className="codeframe mono">{activeTemplate?.content ?? "Template not available."}</pre>
          </article>

          <article className="preview-card">
            <div className="section-head">
              <h3>Rendered preview</h3>
              <span className="status-chip" data-tone="success">
                {activeRunId} · ch{String(activeChapter).padStart(2, "0")} · {activeStep}
              </span>
            </div>
            <pre className="previewframe article">{preview}</pre>
          </article>
        </div>
      </section>
    </>
  );
}
