import { redirect } from "next/navigation";

/** Imported notes are style training data, so they live under Style > Sources. */
export default function ImportRedirect() {
  redirect("/dashboard/style?tab=sources");
}
