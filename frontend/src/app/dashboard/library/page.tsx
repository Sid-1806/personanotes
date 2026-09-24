import { redirect } from "next/navigation";

/** Lectures now live inside their course. */
export default function LibraryRedirect() {
  redirect("/dashboard/courses");
}
