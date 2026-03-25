"use client";

import { useEffect, useMemo, useState } from "react";
import type { JobStatus } from "../../../lib/api";

type JobPanelProps = {
  initialJob: JobStatus;
  runId: string;
  cancelAction: (formData: FormData) => Promise<void>;
};

function terminal(status: string): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}

export function JobPanel({ initialJob, runId, cancelAction }: JobPanelProps) {
  const [job, setJob] = useState<JobStatus>(initialJob);
  const [pollError, setPollError] = useState<string | null>(null);

  useEffect(() => {
    setJob(initialJob);
    setPollError(null);
  }, [initialJob]);

  useEffect(() => {
    if (!job.job_id || terminal(job.status)) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(job.job_id)}`, {
          cache: "no-store"
        });
        if (!response.ok) {
          throw new Error("Unable to refresh job status.");
        }
        const payload = (await response.json()) as JobStatus;
        setJob(payload);
        setPollError(null);
      } catch (error) {
        setPollError(error instanceof Error ? error.message : "Unable to refresh job status.");
      }
    }, 2000);

    return () => {
      window.clearInterval(interval);
    };
  }, [job.job_id, job.status]);

  const recentEvents = useMemo(() => job.events.slice(-5).reverse(), [job.events]);
  const targetLabel = `${String(job.target.chapter ?? job.target.section_number ?? "run")} · ${String(job.target.step ?? "job")}`;

  return (
    <div className="content-card">
      <div className="section-head">
        <h3>Active job</h3>
        <span
          className="status-chip"
          data-tone={job.status === "failed" ? "warning" : job.status === "succeeded" ? "success" : "accent"}
        >
          {job.status}
        </span>
      </div>
      <div className="rail-list">
        <div className="list-item">
          <div className="list-title">Job</div>
          <div className="list-copy mono">{job.job_type}</div>
        </div>
        <div className="list-item">
          <div className="list-title">Target</div>
          <div className="list-copy mono">{targetLabel}</div>
        </div>
        {job.error ? (
          <div className="list-item">
            <div className="list-title">Error</div>
            <div className="list-copy">{job.error}</div>
          </div>
        ) : null}
        {pollError ? (
          <div className="list-item">
            <div className="list-title">Polling</div>
            <div className="list-copy">{pollError}</div>
          </div>
        ) : null}
        <div className="event-list">
          {recentEvents.map((event, index) => (
            <div key={`${event.event}-${index}`} className="event-item">
              <div className="event-name mono">{event.event}</div>
              <div className="list-copy">{event.message}</div>
            </div>
          ))}
        </div>
        <div className="action-row">
          {job.status === "queued" || job.status === "running" ? (
            <form action={cancelAction}>
              <input type="hidden" name="run_id" value={runId} />
              <input type="hidden" name="job_id" value={job.job_id} />
              <button className="button-secondary" type="submit">
                Cancel job
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  );
}
