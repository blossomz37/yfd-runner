import Link from "next/link";
import { loadRun, loadRuns } from "../../lib/api";
import {
  normalizeWorksheetSectionContent,
  parseWorksheetSections,
  worksheetSectionBody,
  worksheetSectionLabel
} from "../../lib/worksheet";
import { saveWorksheetSectionAction } from "./actions";

type WorksheetsPageProps = {
  searchParams?: Promise<{
    runId?: string;
    section?: string;
    message?: string;
    error?: string;
  }>;
};

function worksheetHref(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (!value) {
      continue;
    }
    search.set(key, value);
  }
  return `/worksheets?${search.toString()}`;
}

export default async function WorksheetsPage({ searchParams }: WorksheetsPageProps) {
  const params = (await searchParams) ?? {};
  const runs = await loadRuns();

  if (!runs.length) {
    return <section className="empty-note">No runs are available yet. Create or import a run first.</section>;
  }

  const selectedRunId = runs.some((run) => run.run_id === params.runId) ? params.runId ?? runs[0].run_id : runs[0].run_id;
  const run = await loadRun(selectedRunId);

  if (!run) {
    return <section className="empty-note">Unable to load the selected run.</section>;
  }

  const sections = parseWorksheetSections(run.worksheet);
  const selectedSection =
    sections.find((section) => section.sectionKey === params.section) ??
    sections[0] ??
    null;

  if (!selectedSection) {
    return <section className="empty-note">This run does not contain any worksheet sections.</section>;
  }

  const normalizedContent = normalizeWorksheetSectionContent(selectedSection, worksheetSectionBody(selectedSection.text));

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Worksheets</div>
          <h1 className="page-title">Worksheet Explorer</h1>
          <p className="page-copy">
            Edit one section at a time against the real worksheet contract. Section saves preserve heading structure and
            round-trip directly through the existing run endpoint.
          </p>
        </div>
        <div className="action-row">
          <Link className="button-secondary" href={`/runs/${run.run_id}`}>
            Back to run
          </Link>
          <Link className="button-secondary" href={`/templates?runId=${run.run_id}`}>
            Open templates
          </Link>
        </div>
      </section>

      {params.message || params.error ? (
        <div className="flash-banner" data-tone={params.error ? "warning" : "success"}>
          {params.error ?? params.message}
        </div>
      ) : null}

      <div className="selector-row">
        {runs.map((runSummary) => (
          <Link
            key={runSummary.run_id}
            className={`mini-link${runSummary.run_id === run.run_id ? " active" : ""}`}
            href={worksheetHref({ runId: runSummary.run_id })}
          >
            {runSummary.run_id}
          </Link>
        ))}
      </div>

      <section className="outputs-grid">
        <aside className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>Sections</h3>
              <span className="pill">{sections.length}</span>
            </div>
            <div className="rail-list">
              {sections.map((section) => (
                <Link
                  key={section.sectionKey}
                  className={`list-item${section.sectionKey === selectedSection.sectionKey ? " active" : ""}`}
                  href={worksheetHref({ runId: run.run_id, section: section.sectionKey })}
                >
                  <div className="list-title">{worksheetSectionLabel(section)}</div>
                  <div className="list-copy mono">{section.sectionKey}</div>
                </Link>
              ))}
            </div>
          </article>

          <article className="content-card">
            <div className="section-head">
              <h3>Section metadata</h3>
              <span className="status-chip" data-tone="accent">
                {run.run_id}
              </span>
            </div>
            <div className="kv-grid">
              <div className="kv-row">
                <span className="kv-label">Selected section</span>
                <span className="kv-value mono">{selectedSection.sectionKey}</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Section number</span>
                <span className="kv-value">{selectedSection.sectionNumber}</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Current chapter</span>
                <span className="kv-value">{run.current_chapter ?? "not started"}</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Latest step</span>
                <span className="kv-value mono">{run.latest_step ?? "idle"}</span>
              </div>
            </div>
          </article>
        </aside>

        <div className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>{worksheetSectionLabel(selectedSection)}</h3>
              <span className="pill mono">{selectedSection.sectionKey}</span>
            </div>
            <form action={saveWorksheetSectionAction} className="stack">
              <input type="hidden" name="run_id" value={run.run_id} />
              <input type="hidden" name="section_key" value={selectedSection.sectionKey} />
              <label className="field-group">
                <span className="field-label">Section content</span>
                <textarea
                  className="editor-input mono"
                  name="content"
                  rows={18}
                  defaultValue={normalizedContent}
                />
              </label>
              <div className="action-row">
                <button className="button" type="submit">
                  Save section
                </button>
                <Link
                  className="button-secondary"
                  href={`/outputs?runId=${run.run_id}`}
                >
                  Inspect outputs
                </Link>
              </div>
            </form>
          </article>

          <article className="content-card">
            <div className="section-head">
              <h3>Raw worksheet snapshot</h3>
              <span className="pill">read-only</span>
            </div>
            <pre className="previewframe output-frame">{run.worksheet}</pre>
          </article>
        </div>
      </section>
    </>
  );
}
