"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createProjectFromDossier, createRun, type DossierBlockInput } from "../../lib/api";

function redirectIntake(key: "message" | "error", value: string): never {
  const params = new URLSearchParams({ [key]: value });
  redirect(`/intake?${params.toString()}`);
}

export async function createWorksheetRunAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const worksheetPath = String(formData.get("worksheet_path") ?? "").trim();
  const modelConfig = String(formData.get("model_config") ?? "").trim();
  const outputDir = String(formData.get("output_dir") ?? "").trim();

  if (!runId || !worksheetPath) {
    redirectIntake("error", "Run id and worksheet path are required.");
  }

  try {
    const result = await createRun({
      run_id: runId,
      worksheet_path: worksheetPath,
      model_config: modelConfig || undefined,
      output_dir: outputDir || undefined
    });
    revalidatePath("/");
    revalidatePath(`/runs/${result.run_id}`);
    redirect(`/worksheets?runId=${encodeURIComponent(result.run_id)}&message=${encodeURIComponent("Worksheet run created.")}`);
  } catch (error) {
    redirectIntake("error", error instanceof Error ? error.message : "Unable to create run from worksheet.");
  }
}

export async function createDossierProjectAction(formData: FormData): Promise<void> {
  const runId = String(formData.get("run_id") ?? "").trim();
  const modelConfig = String(formData.get("model_config") ?? "").trim();
  const outputDir = String(formData.get("output_dir") ?? "").trim();

  if (!runId) {
    redirectIntake("error", "Run id is required for dossier intake.");
  }

  const blocks = [1, 2, 3]
    .map((index) => {
      const text = String(formData.get(`block_${index}_text`) ?? "").trim();
      if (!text) {
        return null;
      }
      return {
        label: String(formData.get(`block_${index}_label`) ?? `Block ${index}`).trim() || `Block ${index}`,
        source_type: String(formData.get(`block_${index}_source_type`) ?? "notes").trim() || "notes",
        source_name: String(formData.get(`block_${index}_source_name`) ?? `source_${index}`).trim() || `source_${index}`,
        text
      };
    })
    .filter((block): block is DossierBlockInput => block !== null);

  if (!blocks.length) {
    redirectIntake("error", "Add at least one dossier block before creating a project.");
  }

  try {
    const result = await createProjectFromDossier({
      run_id: runId,
      blocks,
      model_config: modelConfig || undefined,
      output_dir: outputDir || undefined
    });
    revalidatePath("/");
    revalidatePath(`/runs/${result.run_id}`);
    redirect(`/worksheets?runId=${encodeURIComponent(result.run_id)}&message=${encodeURIComponent("Dossier draft created.")}`);
  } catch (error) {
    redirectIntake("error", error instanceof Error ? error.message : "Unable to create project from dossier.");
  }
}
