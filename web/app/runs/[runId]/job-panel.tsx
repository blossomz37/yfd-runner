"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { JobStatus } from "../../../lib/api";

type JobPanelProps = {
  initialJob: JobStatus;
  runId: string;
  cancelAction: (formData: FormData) => Promise<void>;
};

const SSE_EVENT_NAMES = [
  "job_queued",
  "job_started",
  "job_finished",
  "job_failed",
  "job_cancelled",
  "cancel_requested",
  "step_started",
  "prompt_rendered",
  "attempt_started",
  "attempt_succeeded",
  "attempt_failed",
  "attempt_event",
  "warning",
  "validation_failed",
  "step_failed",
  "step_succeeded"
] as const;

function terminal(status: string): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}

export function JobPanel({ initialJob, runId, cancelAction }: JobPanelProps) {
  const router = useRouter();
  const [job, setJob] = useState<JobStatus>(initialJob);
  const [transportError, setTransportError] = useState<string | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const refreshTimeoutRef = useRef<number | null>(null);
  const refreshInFlightRef = useRef(false);
  const terminalRefreshRef = useRef<string | null>(null);

  useEffect(() => {
    setJob(initialJob);
    setTransportError(null);
    setSseConnected(false);
    terminalRefreshRef.current = null;
  }, [initialJob]);

  const refreshSnapshot = useCallback(
    async (source: "sse" | "poll") => {
      if (!job.job_id || refreshInFlightRef.current) {
        return;
      }
      refreshInFlightRef.current = true;
      try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(job.job_id)}`, {
          cache: "no-store"
        });
        if (!response.ok) {
          throw new Error(`Unable to refresh job status via ${source}.`);
        }
        const payload = (await response.json()) as JobStatus;
        setJob(payload);
        setTransportError(null);
      } catch (error) {
        setTransportError(error instanceof Error ? error.message : "Unable to refresh job status.");
      } finally {
        refreshInFlightRef.current = false;
      }
    },
    [job.job_id],
  );

  const scheduleSnapshotRefresh = useCallback(
    (delayMs = 200) => {
      if (refreshTimeoutRef.current !== null) {
        return;
      }
      refreshTimeoutRef.current = window.setTimeout(() => {
        refreshTimeoutRef.current = null;
        void refreshSnapshot("sse");
      }, delayMs);
    },
    [refreshSnapshot],
  );

  useEffect(() => {
    if (!job.job_id || terminal(job.status)) {
      return;
    }

    const eventSource = new EventSource(`/api/jobs/${encodeURIComponent(job.job_id)}/events`);

    eventSource.onopen = () => {
      setSseConnected(true);
      setTransportError(null);
    };

    const handleEvent = () => {
      scheduleSnapshotRefresh();
    };
    eventSource.onmessage = handleEvent;
    SSE_EVENT_NAMES.forEach((eventName) => {
      eventSource.addEventListener(eventName, handleEvent);
    });

    eventSource.onerror = () => {
      setSseConnected(false);
      setTransportError((current) => current ?? "Live stream unavailable. Falling back to polling.");
    };

    return () => {
      eventSource.close();
    };
  }, [job.job_id, job.status, scheduleSnapshotRefresh]);

  useEffect(() => {
    if (!job.job_id || terminal(job.status) || sseConnected) {
      return;
    }

    const interval = window.setInterval(() => {
      void refreshSnapshot("poll");
    }, 2000);

    return () => {
      window.clearInterval(interval);
    };
  }, [job.job_id, job.status, refreshSnapshot, sseConnected]);

  useEffect(() => {
    if (!job.job_id || !terminal(job.status) || terminalRefreshRef.current === job.job_id) {
      return;
    }
    terminalRefreshRef.current = job.job_id;
    router.refresh();
  }, [job.job_id, job.status, router]);

  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current !== null) {
        window.clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

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
        <div className="list-item">
          <div className="list-title">Transport</div>
          <div className="list-copy">{sseConnected ? "live stream" : terminal(job.status) ? "settled" : "polling fallback"}</div>
        </div>
        {job.error ? (
          <div className="list-item">
            <div className="list-title">Error</div>
            <div className="list-copy">{job.error}</div>
          </div>
        ) : null}
        {transportError ? (
          <div className="list-item">
            <div className="list-title">Live updates</div>
            <div className="list-copy">{transportError}</div>
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
