import { loadModels, loadStepSettings } from "../../lib/api";
import { saveStepSettingAction } from "./actions";

type SettingsPageProps = {
  searchParams?: Promise<{
    focus?: string;
    message?: string;
    error?: string;
  }>;
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const params = (await searchParams) ?? {};
  const stepSettings = await loadStepSettings();
  const settings = Object.values(stepSettings);
  const models = await loadModels();
  const modelOptions = models.map((model) => model.name.replace(/\.yaml$/, ""));

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Settings</div>
          <h1 className="page-title">Structured step settings, now editable through the real contract.</h1>
          <p className="page-copy">
            Each card submits to <span className="mono">PUT /api/step-settings/{`{step}`}</span>. Extras stay JSON so
            the UI can preserve non-core overrides without inventing a second schema.
          </p>
        </div>
      </section>

      {params.message || params.error ? (
        <div className="flash-banner" data-tone={params.error ? "warning" : "success"}>
          {params.error ?? params.message}
        </div>
      ) : null}

      <datalist id="model-configs">
        {modelOptions.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>

      <section className="run-grid">
        {settings.map((setting) => (
          <article
            key={setting.step}
            className={`content-card${params.focus === setting.step ? " focus-card" : ""}`}
          >
            <div className="section-head">
              <h3>{setting.step}</h3>
              <span className="status-chip" data-tone="accent">
                {setting.model_config}
              </span>
            </div>
            <form action={saveStepSettingAction} className="stack">
              <input type="hidden" name="step" value={setting.step} />
              <label className="field-group">
                <span className="field-label">Model config</span>
                <input
                  className="field-input mono"
                  list="model-configs"
                  name="model_config"
                  defaultValue={setting.model_config}
                />
              </label>
              <div className="form-grid">
                <label className="field-group">
                  <span className="field-label">Max tokens</span>
                  <input className="field-input mono" name="max_tokens" type="number" defaultValue={setting.max_tokens ?? ""} />
                </label>
                <label className="field-group">
                  <span className="field-label">Temperature</span>
                  <input
                    className="field-input mono"
                    name="temperature"
                    type="number"
                    step="0.1"
                    defaultValue={setting.temperature ?? ""}
                  />
                </label>
              </div>
              <label className="field-group">
                <span className="field-label">Extras JSON</span>
                <textarea
                  className="field-input mono"
                  name="extras"
                  rows={4}
                  defaultValue={Object.keys(setting.extras).length ? JSON.stringify(setting.extras, null, 2) : ""}
                />
              </label>
              <div className="action-row">
                <button className="button" type="submit">
                  Save step
                </button>
              </div>
            </form>
          </article>
        ))}
      </section>
    </>
  );
}
