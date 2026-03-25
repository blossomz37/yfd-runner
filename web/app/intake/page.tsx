export default function IntakePage() {
  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Intake Workspace</div>
          <h1 className="page-title">Create a run from a worksheet or dossier.</h1>
          <p className="page-copy">
            This shell reserves space for the confirmed V1 intake paths: direct worksheet creation and dossier-backed
            worksheet drafting.
          </p>
        </div>
      </section>
      <section className="run-grid">
        <article className="content-card">
          <div className="section-head">
            <h3>Worksheet</h3>
            <span className="status-chip" data-tone="success">
              ready
            </span>
          </div>
          <p className="muted-copy">
            Validate structure before any state file is created. The UI should surface H1 rejection and section errors
            inline.
          </p>
        </article>
        <article className="content-card">
          <div className="section-head">
            <h3>Story dossier</h3>
            <span className="status-chip" data-tone="accent">
              next
            </span>
          </div>
          <p className="muted-copy">
            Imported source blocks, mapping targets, and worksheet draft confirmation belong here before execution
            begins.
          </p>
        </article>
      </section>
    </>
  );
}
