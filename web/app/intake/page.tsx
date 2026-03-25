import { loadModels } from "../../lib/api";
import { createDossierProjectAction, createWorksheetRunAction } from "./actions";

type IntakePageProps = {
  searchParams?: Promise<{
    message?: string;
    error?: string;
  }>;
};

const WORKSHEET_SUGGESTIONS = [
  "yfd-runner/worksheet_trial.md",
  "yfd-runner/worksheet_trial_complete.md",
  "yfd-runner/test/fixtures/sample_worksheet.md"
];

const DOSSIER_BLOCKS = [
  { id: 1, label: "Premise", sourceType: "concept", sourceName: "premise_notes" },
  { id: 2, label: "Character", sourceType: "character", sourceName: "character_sheet" },
  { id: 3, label: "Constraint", sourceType: "world", sourceName: "world_notes" }
];

export default async function IntakePage({ searchParams }: IntakePageProps) {
  const params = (await searchParams) ?? {};
  const models = await loadModels();
  const defaultModel = models[0]?.name.replace(/\.yaml$/, "") ?? "default";

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Intake Workspace</div>
          <h1 className="page-title">Create a run from a worksheet or draft a run from dossier blocks.</h1>
          <p className="page-copy">
            These forms are now live against the backend create endpoints. Worksheet intake is direct. Dossier intake
            creates a draft worksheet-backed state file before execution begins.
          </p>
        </div>
      </section>

      {params.message || params.error ? (
        <div className="flash-banner" data-tone={params.error ? "warning" : "success"}>
          {params.error ?? params.message}
        </div>
      ) : null}

      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Worksheet run</h3>
            <span className="status-chip" data-tone="success">
              ready
            </span>
          </div>
          <form action={createWorksheetRunAction} className="stack">
            <label className="field-group">
              <span className="field-label">Run id</span>
              <input className="field-input mono" name="run_id" defaultValue="phase12_frontend_trial" />
            </label>
            <label className="field-group">
              <span className="field-label">Worksheet path</span>
              <input className="field-input mono" list="worksheet-paths" name="worksheet_path" defaultValue={WORKSHEET_SUGGESTIONS[0]} />
            </label>
            <div className="form-grid">
              <label className="field-group">
                <span className="field-label">Model config</span>
                <input className="field-input mono" name="model_config" defaultValue={defaultModel} />
              </label>
              <label className="field-group">
                <span className="field-label">Output dir</span>
                <input className="field-input mono" name="output_dir" defaultValue="yfd-runner/output" />
              </label>
            </div>
            <div className="action-row">
              <button className="button" type="submit">
                Create worksheet run
              </button>
            </div>
          </form>
        </article>

        <article className="content-card">
          <div className="section-head">
            <h3>Dossier project</h3>
            <span className="status-chip" data-tone="accent">
              V1
            </span>
          </div>
          <form action={createDossierProjectAction} className="stack">
            <div className="form-grid">
              <label className="field-group">
                <span className="field-label">Run id</span>
                <input className="field-input mono" name="run_id" defaultValue="phase12_dossier_trial" />
              </label>
              <label className="field-group">
                <span className="field-label">Model config</span>
                <input className="field-input mono" name="model_config" defaultValue={defaultModel} />
              </label>
            </div>
            <label className="field-group">
              <span className="field-label">Output dir</span>
              <input className="field-input mono" name="output_dir" defaultValue="yfd-runner/output" />
            </label>
            <div className="stack">
              {DOSSIER_BLOCKS.map((block) => (
                <div key={block.id} className="nested-card">
                  <div className="section-head">
                    <h3>{block.label}</h3>
                    <span className="pill mono">block {block.id}</span>
                  </div>
                  <div className="form-grid">
                    <label className="field-group">
                      <span className="field-label">Label</span>
                      <input className="field-input mono" name={`block_${block.id}_label`} defaultValue={block.label} />
                    </label>
                    <label className="field-group">
                      <span className="field-label">Source type</span>
                      <input
                        className="field-input mono"
                        name={`block_${block.id}_source_type`}
                        defaultValue={block.sourceType}
                      />
                    </label>
                  </div>
                  <label className="field-group">
                    <span className="field-label">Source name</span>
                    <input
                      className="field-input mono"
                      name={`block_${block.id}_source_name`}
                      defaultValue={block.sourceName}
                    />
                  </label>
                  <label className="field-group">
                    <span className="field-label">Block text</span>
                    <textarea
                      className="field-input mono"
                      name={`block_${block.id}_text`}
                      rows={5}
                      placeholder={`Paste ${block.label.toLowerCase()} material here.`}
                    />
                  </label>
                </div>
              ))}
            </div>
            <div className="action-row">
              <button className="button" type="submit">
                Create dossier draft
              </button>
            </div>
          </form>
        </article>
      </section>

      <datalist id="worksheet-paths">
        {WORKSHEET_SUGGESTIONS.map((path) => (
          <option key={path} value={path} />
        ))}
      </datalist>
    </>
  );
}
