import Link from "next/link";
import { loadModel, loadModels, loadStepSettings } from "../../lib/api";
import { saveModelAction } from "./actions";

type ModelsPageProps = {
  searchParams?: Promise<{
    model?: string;
    message?: string;
    error?: string;
  }>;
};

function flashTone(error?: string) {
  return error ? "warning" : "success";
}

export default async function ModelsPage({ searchParams }: ModelsPageProps) {
  const params = (await searchParams) ?? {};
  const models = await loadModels();
  const stepSettings = await loadStepSettings();
  const activeModelName = params.model ?? models[0]?.name ?? "gpt-5.4.yaml";
  const activeModel = await loadModel(activeModelName);
  const message = params.error ?? params.message;
  const usedBySteps = Object.values(stepSettings)
    .filter((setting) => `${setting.model_config}.yaml` === activeModelName || setting.model_config === activeModelName.replace(/\.yaml$/, ""))
    .map((setting) => setting.step);

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Models</div>
          <h1 className="page-title">Inspect model configs and keep step routing honest.</h1>
          <p className="page-copy">
            These files are the real YAML model configs under <span className="mono">yfd-runner/models</span>. Save
            goes through the safe backend writer instead of editing a mock textarea.
          </p>
        </div>
      </section>

      {message ? (
        <div className="flash-banner" data-tone={flashTone(params.error)}>
          {message}
        </div>
      ) : null}

      <section className="template-grid">
        <aside className="content-card">
          <div className="section-head">
            <h3>Model files</h3>
            <span className="pill">{models.length} configs</span>
          </div>
          <div className="rail-list">
            {models.map((model) => (
              <Link
                key={model.name}
                className={`list-item${model.name === activeModelName ? " active" : ""}`}
                href={`/models?model=${encodeURIComponent(model.name)}`}
              >
                <div className="list-title mono">{model.name}</div>
                <div className="list-copy">{model.path}</div>
              </Link>
            ))}
          </div>
        </aside>

        <div className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>Routing context</h3>
              <span className="status-chip" data-tone="accent">
                live
              </span>
            </div>
            <div className="kv-grid">
              <div className="kv-row">
                <span className="kv-label">Resolved model</span>
                <span className="kv-value mono">
                  {String(activeModel?.data?.model ?? "unknown")}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Reasoning</span>
                <span className="kv-value mono">
                  {String((activeModel?.data?.reasoning as { effort?: string } | undefined)?.effort ?? "default")}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Used by steps</span>
                <span className="kv-value mono">{usedBySteps.length ? usedBySteps.join(", ") : "unassigned"}</span>
              </div>
            </div>
          </article>

          <article className="editor-card">
            <div className="section-head">
              <h3>Model source</h3>
              <span className="pill mono">{activeModel?.path ?? "not found"}</span>
            </div>
            <form action={saveModelAction} className="stack">
              <input type="hidden" name="model" value={activeModelName} />
              <textarea
                className="editor-input mono"
                name="content"
                defaultValue={activeModel?.content ?? "# Model file not available."}
                rows={18}
              />
              <div className="action-row">
                <button className="button" type="submit">
                  Save model
                </button>
                <Link className="button-secondary" href="/settings">
                  Review step settings
                </Link>
              </div>
            </form>
          </article>
        </div>
      </section>
    </>
  );
}
