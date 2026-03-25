"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { saveConfig } from "../../lib/api";

function redirectToConfig(key: "message" | "error", value: string): never {
  const search = new URLSearchParams({ [key]: value });
  redirect(`/config?${search.toString()}`);
}

export async function saveConfigAction(formData: FormData): Promise<void> {
  const content = String(formData.get("content") ?? "");

  try {
    await saveConfig(content);
  } catch (error) {
    redirectToConfig("error", error instanceof Error ? error.message : "Unable to save config.");
  }

  revalidatePath("/config");
  revalidatePath("/settings");
  redirectToConfig("message", "Saved config.yaml.");
}
