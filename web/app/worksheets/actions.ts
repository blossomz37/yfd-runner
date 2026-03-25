"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { saveWorksheetSection } from "../../lib/api";

function redirectToWorksheet(runId: string, params: Record<string, string>): never {
  const search = new URLSearchParams({ runId, ...params });
  redirect(`/worksheets?${search.toString()}`);
}

export async function saveWorksheetSectionAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const sectionKey = String(formData.get("section_key") ?? "").trim();
  const content = String(formData.get("content") ?? "");

  if (!runId || !sectionKey) {
    redirectToWorksheet(runId || "partial_ch2_20260319", {
      error: "Run id and section key are required."
    });
  }

  try {
    await saveWorksheetSection(runId, sectionKey, content);
  } catch (error) {
    redirectToWorksheet(runId, {
      section: sectionKey,
      error: error instanceof Error ? error.message : "Unable to save worksheet section."
    });
  }

  revalidatePath(`/runs/${runId}`);
  revalidatePath("/worksheets");
  redirectToWorksheet(runId, {
    section: sectionKey,
    message: `Saved ${sectionKey}.`
  });
}
