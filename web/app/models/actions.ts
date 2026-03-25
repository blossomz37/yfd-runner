"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { saveModel } from "../../lib/api";

function redirectWithMessage(model: string, key: "message" | "error", value: string): never {
  const params = new URLSearchParams({ model, [key]: value });
  redirect(`/models?${params.toString()}`);
}

export async function saveModelAction(formData: FormData): Promise<void> {
  const model = String(formData.get("model") ?? "").trim();
  const content = String(formData.get("content") ?? "");

  if (!model) {
    redirectWithMessage("gpt-5.4.yaml", "error", "Model name is required.");
  }

  try {
    await saveModel(model, content);
  } catch (error) {
    redirectWithMessage(model, "error", error instanceof Error ? error.message : "Unable to save model.");
  }

  revalidatePath("/models");
  revalidatePath("/settings");
  redirectWithMessage(model, "message", `Saved ${model}.`);
}
