"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  approveCandidate,
  branchRun,
  cancelJob,
  manualContinueStep,
  rerunStep
} from "../../../lib/api";

function redirectToRun(runId: string, params: Record<string, string>): never {
  const search = new URLSearchParams(params);
  redirect(`/runs/${encodeURIComponent(runId)}?${search.toString()}`);
}

export async function createBranchAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const newRunId = String(formData.get("new_run_id") ?? "").trim();
  const branchNote = String(formData.get("branch_note") ?? "").trim();
  const chapterRaw = String(formData.get("branched_from_chapter") ?? "").trim();

  if (!runId || !newRunId) {
    redirectToRun(runId || "partial_ch2_20260319", { error: "Run id and new branch id are required." });
  }

  try {
    const result = await branchRun(runId, {
      new_run_id: newRunId,
      branched_from_chapter: chapterRaw ? Number(chapterRaw) : undefined,
      branch_note: branchNote
    });
    revalidatePath("/");
    revalidatePath(`/runs/${runId}`);
    revalidatePath(`/runs/${result.run_id}`);
    redirect(`/runs/${encodeURIComponent(result.run_id)}?message=${encodeURIComponent(`Branch created from ${runId}.`)}`);
  } catch (error) {
    redirectToRun(runId, { error: error instanceof Error ? error.message : "Unable to create branch." });
  }
}

export async function rerunStepAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const chapter = Number(formData.get("chapter") ?? 0);
  const step = String(formData.get("step") ?? "").trim();
  const steeringNote = String(formData.get("steering_note") ?? "").trim();
  const reviewMode = String(formData.get("review_mode") ?? "manual").trim();

  if (!runId || !chapter || !step) {
    redirectToRun(runId || "partial_ch2_20260319", { error: "Run, chapter, and step are required for rerun." });
  }

  try {
    const result = await rerunStep(runId, chapter, step, {
      steering_note: steeringNote,
      review_mode: reviewMode,
      force: true
    });
    revalidatePath(`/runs/${runId}`);
    redirectToRun(runId, {
      message: `Rerun queued for ch${String(chapter).padStart(2, "0")} ${step}.`,
      jobId: result.job_id
    });
  } catch (error) {
    redirectToRun(runId, { error: error instanceof Error ? error.message : "Unable to queue rerun." });
  }
}

export async function approveCandidateAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const chapter = Number(formData.get("chapter") ?? 0);
  const step = String(formData.get("step") ?? "").trim();
  const candidateId = String(formData.get("candidate_id") ?? "").trim();

  if (!runId || !chapter || !step || !candidateId) {
    redirectToRun(runId || "partial_ch2_20260319", { error: "Candidate approval requires a candidate id." });
  }

  try {
    await approveCandidate(runId, chapter, step, candidateId);
    revalidatePath(`/runs/${runId}`);
    redirectToRun(runId, { message: `Approved ${step} candidate.` });
  } catch (error) {
    redirectToRun(runId, { error: error instanceof Error ? error.message : "Unable to approve candidate." });
  }
}

export async function manualContinueAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const chapter = Number(formData.get("chapter") ?? 0);
  const step = String(formData.get("step") ?? "").trim();
  const content = String(formData.get("content") ?? "");
  const reviewNote = String(formData.get("review_note") ?? "").trim();

  if (!runId || !chapter || !step) {
    redirectToRun(runId || "partial_ch2_20260319", { error: "Manual continue requires run, chapter, and step." });
  }

  try {
    await manualContinueStep(runId, chapter, step, content, reviewNote);
    revalidatePath(`/runs/${runId}`);
    redirectToRun(runId, { message: `Saved manual ${step} output.` });
  } catch (error) {
    redirectToRun(runId, { error: error instanceof Error ? error.message : "Unable to save manual output." });
  }
}

export async function cancelJobAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const jobId = String(formData.get("job_id") ?? "").trim();

  if (!runId || !jobId) {
    redirectToRun(runId || "partial_ch2_20260319", { error: "Job id is required for cancellation." });
  }

  try {
    await cancelJob(jobId);
    revalidatePath(`/runs/${runId}`);
    redirectToRun(runId, {
      message: "Cancellation requested.",
      jobId
    });
  } catch (error) {
    redirectToRun(runId, { error: error instanceof Error ? error.message : "Unable to cancel job." });
  }
}
