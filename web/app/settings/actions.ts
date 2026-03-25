"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { saveStepSetting } from "../../lib/api";

function redirectWithMessage(step: string, key: "message" | "error", value: string): never {
  const params = new URLSearchParams({ focus: step, [key]: value });
  redirect(`/settings?${params.toString()}`);
}

export async function saveStepSettingAction(formData: FormData): Promise<void> {
  const step = String(formData.get("step") ?? "").trim();
  const modelConfig = String(formData.get("model_config") ?? "").trim();
  const maxTokensRaw = String(formData.get("max_tokens") ?? "").trim();
  const temperatureRaw = String(formData.get("temperature") ?? "").trim();
  const extrasRaw = String(formData.get("extras") ?? "").trim();

  if (!step) {
    redirectWithMessage("plan", "error", "Step is required.");
  }

  let extras: Record<string, unknown> = {};
  if (extrasRaw) {
    try {
      const parsed = JSON.parse(extrasRaw) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Extras must be a JSON object.");
      }
      extras = parsed as Record<string, unknown>;
    } catch (error) {
      redirectWithMessage(step, "error", error instanceof Error ? error.message : "Extras JSON is invalid.");
    }
  }

  try {
    await saveStepSetting(step, {
      model_config: modelConfig,
      max_tokens: maxTokensRaw ? Number(maxTokensRaw) : undefined,
      temperature: temperatureRaw ? Number(temperatureRaw) : undefined,
      extras
    });
  } catch (error) {
    redirectWithMessage(step, "error", error instanceof Error ? error.message : "Unable to save step settings.");
  }

  revalidatePath("/settings");
  redirectWithMessage(step, "message", `Saved settings for ${step}.`);
}
