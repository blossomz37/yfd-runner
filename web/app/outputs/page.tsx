import Link from "next/link";
import {
  type CandidateOutput,
  type RunArtifact,
  loadArtifactContent,
  loadRun,
  loadRunArtifacts,
  loadRunManuscript,
  loadRuns
} from "../../lib/api";

type OutputsPageProps = {
  searchParams?: Promise<{
    runId?: string;
    artifact?: string;
    chapter?: string;
    step?: string;
    candidateId?: string;
  }>;
};

type ComparisonTarget = {
  chapter: number;
  step: string;
};

function outputsHref(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const suffix = search.toString();
  return suffix ? `/outputs?${suffix}` : "/outputs";
}

function uniqueComparisonTargets(candidates: CandidateOutput[]): ComparisonTarget[] {
  const seen = new Set<string>();
  const targets: ComparisonTarget[] = [];
  for (const candidate of candidates) {
    const key = `${candidate.chapter}:${candidate.step}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    targets.push({ chapter: candidate.chapter, step: candidate.step });
  }
  return targets;
}

function pickComparisonTarget(
  run: Awaited<ReturnType<typeof loadRun>>,
  candidates: CandidateOutput[],
  chapterRaw?: string,
  stepRaw?: string,
): ComparisonTarget | null {
  if (!run) {
    return null;
  }
  const targets = uniqueComparisonTargets(candidates);
  const requestedChapter = Number(chapterRaw ?? 0);
  const requestedStep = (stepRaw ?? "").trim();
  if (requestedChapter && requestedStep && candidates.some((candidate) => candidate.chapter === requestedChapter && candidate.step === requestedStep)) {
    return { chapter: requestedChapter, step: requestedStep };
  }
  if (
    run.current_review.chapter &&
    run.current_review.step &&
    candidates.some((candidate) => candidate.chapter === run.current_review.chapter && candidate.step === run.current_review.step)
  ) {
    return { chapter: run.current_review.chapter, step: run.current_review.step };
  }
  return targets[0] ?? null;
}

function pickSelectedCandidate(
  candidates: CandidateOutput[],
  target: ComparisonTarget | null,
  candidateId?: string,
  currentCandidate?: CandidateOutput | null,
): CandidateOutput | null {
  if (!target) {
    return null;
  }
  const matching = candidates.filter((candidate) => candidate.chapter === target.chapter && candidate.step === target.step);
  if (!matching.length) {
    return null;
  }
  if (candidateId) {
    return matching.find((candidate) => candidate.candidate_id === candidateId) ?? null;
  }
  if (currentCandidate && currentCandidate.chapter === target.chapter && currentCandidate.step === target.step) {
    return currentCandidate;
  }
  return matching[matching.length - 1] ?? null;
}

function canonicalTextForComparison(run: NonNullable<Awaited<ReturnType<typeof loadRun>>>, target: ComparisonTarget | null): string {
  if (!target) {
    return "";
  }
  const raw = run.chapters[String(target.chapter)]?.[target.step] ?? "";
  if (raw === "Candidate draft pending review.") {
    return "";
  }
  return raw;
}

function artifactItems(index: Awaited<ReturnType<typeof loadRunArtifacts>>): RunArtifact[] {
  if (!index) {
    return [];
  }
  return [index.manuscript, ...index.artifacts];
}

export default async function OutputsPage({ searchParams }: OutputsPageProps) {
  const query = (await searchParams) ?? {};
  const runs = await loadRuns();

  if (!runs.length) {
    return <section className="empty-note">No runs are available yet. Create or import a run first.</section>;
  }

  const selectedRunId = runs.some((run) => run.run_id === query.runId) ? query.runId ?? runs[0].run_id : runs[0].run_id;
  const [run, index] = await Promise.all([loadRun(selectedRunId), loadRunArtifacts(selectedRunId)]);

  if (!run || !index) {
    return <section className="empty-note">Unable to load outputs for the selected run.</section>;
  }

  const availableArtifacts = artifactItems(index);
  const selectedArtifactId =
    query.artifact && availableArtifacts.some((artifact) => artifact.artifact_id === query.artifact)
      ? query.artifact
      : index.manuscript.exists
        ? "manuscript"
        : index.artifacts[0]?.artifact_id;
  const selectedArtifact = availableArtifacts.find((artifact) => artifact.artifact_id === selectedArtifactId) ?? index.manuscript;
  const contentPayload =
    selectedArtifactId === "manuscript"
      ? await loadRunManuscript(selectedRunId)
      : selectedArtifactId
        ? await loadArtifactContent(selectedRunId, selectedArtifactId)
        : null;

  const candidates = run.studio?.candidate_outputs ?? [];
  const comparisonTarget = pickComparisonTarget(run, candidates, query.chapter, query.step);
  const comparisonCandidates = comparisonTarget
    ? candidates.filter((candidate) => candidate.chapter === comparisonTarget.chapter && candidate.step === comparisonTarget.step)
    : [];
  const selectedCandidate = pickSelectedCandidate(candidates, comparisonTarget, query.candidateId, run.current_candidate);
  const canonicalText = canonicalTextForComparison(run, comparisonTarget);

  return (
    <>
      <section className="section-head">
        <div>
          <div className="eyebrow">Outputs</div>
          <h1 className="page-title">Run-scoped inspector</h1>
          <p className="page-copy">
            Browse manuscript output, inspect rendered prompt and failure artifacts, and compare canonical text against
            the current candidate for a single run.
          </p>
        </div>
        <div className="action-row">
          <Link className="button-secondary" href={outputsHref({ runId: selectedRunId, artifact: "manuscript" })}>
            Open manuscript
          </Link>
          <Link className="button-secondary" href={`/runs/${selectedRunId}`}>
            Back to run
          </Link>
        </div>
      </section>

      <div className="selector-row">
        {runs.map((runSummary) => (
          <Link
            key={runSummary.run_id}
            className={`mini-link${runSummary.run_id === selectedRunId ? " active" : ""}`}
            href={outputsHref({ runId: runSummary.run_id })}
          >
            {runSummary.run_id}
          </Link>
        ))}
      </div>

      <section className="outputs-grid">
        <aside className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>Artifacts</h3>
              <span className="pill">{index.artifacts.length + (index.manuscript.exists ? 1 : 0)} files</span>
            </div>
            <div className="rail-list">
              {availableArtifacts.map((artifact) => (
                <Link
                  key={artifact.artifact_id}
                  className={`list-item${artifact.artifact_id === selectedArtifact.artifact_id ? " active" : ""}`}
                  href={outputsHref({
                    runId: selectedRunId,
                    artifact: artifact.artifact_id,
                    chapter: comparisonTarget?.chapter,
                    step: comparisonTarget?.step,
                    candidateId: selectedCandidate?.candidate_id
                  })}
                >
                  <div className="list-title">{artifact.label}</div>
                  <div className="list-copy mono">{artifact.path}</div>
                </Link>
              ))}
              {!availableArtifacts.length ? <div className="empty-note">No manuscript or rendered artifacts are available yet.</div> : null}
            </div>
          </article>

          <article className="content-card">
            <div className="section-head">
              <h3>Comparison focus</h3>
              <span className="pill">{comparisonTarget ? "candidate" : "empty"}</span>
            </div>
            {comparisonTarget ? (
              <div className="stack">
                <div className="selector-row">
                  {uniqueComparisonTargets(candidates).map((target) => {
                    const active = comparisonTarget.chapter === target.chapter && comparisonTarget.step === target.step;
                    return (
                      <Link
                        key={`${target.chapter}:${target.step}`}
                        className={`mini-link${active ? " active" : ""}`}
                        href={outputsHref({
                          runId: selectedRunId,
                          artifact: selectedArtifact.artifact_id,
                          chapter: target.chapter,
                          step: target.step
                        })}
                      >
                        ch{String(target.chapter).padStart(2, "0")} · {target.step}
                      </Link>
                    );
                  })}
                </div>
                <div className="selector-row">
                  {comparisonCandidates.map((candidate) => {
                    const active = candidate.candidate_id === selectedCandidate?.candidate_id;
                    return (
                      <Link
                        key={candidate.candidate_id}
                        className={`mini-link${active ? " active" : ""}`}
                        href={outputsHref({
                          runId: selectedRunId,
                          artifact: selectedArtifact.artifact_id,
                          chapter: comparisonTarget.chapter,
                          step: comparisonTarget.step,
                          candidateId: candidate.candidate_id
                        })}
                      >
                        {candidate.source} · {candidate.status}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="empty-note">No candidate outputs exist for this run yet. Comparison will appear after a review checkpoint creates one.</div>
            )}
          </article>
        </aside>

        <div className="stack">
          <article className="content-card">
            <div className="section-head">
              <h3>{selectedArtifact.label}</h3>
              <span className="status-chip" data-tone={selectedArtifact.artifact_type === "manuscript" ? "accent" : "warning"}>
                {selectedArtifact.artifact_type}
              </span>
            </div>
            <div className="kv-grid">
              <div className="kv-row">
                <span className="kv-label">Path</span>
                <span className="kv-value mono">{selectedArtifact.path}</span>
              </div>
              <div className="kv-row">
                <span className="kv-label">Updated</span>
                <span className="kv-value">{selectedArtifact.updated_at ?? "unknown"}</span>
              </div>
            </div>
            {contentPayload?.content ? (
              <pre className="previewframe output-frame">{contentPayload.content}</pre>
            ) : (
              <div className="empty-note">The selected artifact could not be loaded.</div>
            )}
          </article>

          <article className="content-card">
            <div className="section-head">
              <h3>Canonical vs candidate</h3>
              <span className="pill">
                {comparisonTarget ? `ch${String(comparisonTarget.chapter).padStart(2, "0")} · ${comparisonTarget.step}` : "no candidates"}
              </span>
            </div>
            {comparisonTarget && selectedCandidate ? (
              <div className="comparison-grid">
                <div className="nested-card">
                  <div className="section-head">
                    <h3>Canonical</h3>
                    <span className="pill">saved state</span>
                  </div>
                  {canonicalText ? (
                    <pre className="previewframe output-frame">{canonicalText}</pre>
                  ) : (
                    <div className="empty-note">No canonical output has been approved for this chapter and step yet.</div>
                  )}
                </div>
                <div className="nested-card focus-card">
                  <div className="section-head">
                    <h3>Candidate</h3>
                    <span className="pill">{selectedCandidate.source}</span>
                  </div>
                  <div className="kv-grid">
                    <div className="kv-row">
                      <span className="kv-label">Candidate id</span>
                      <span className="kv-value mono">{selectedCandidate.candidate_id}</span>
                    </div>
                    <div className="kv-row">
                      <span className="kv-label">Status</span>
                      <span className="kv-value">{selectedCandidate.status}</span>
                    </div>
                  </div>
                  <pre className="previewframe output-frame">{selectedCandidate.content}</pre>
                </div>
              </div>
            ) : (
              <div className="empty-note">No candidate comparison is available for the current run selection.</div>
            )}
          </article>
        </div>
      </section>
    </>
  );
}
