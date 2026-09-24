import { redirect } from "next/navigation";

/** Uploading happens inside a course now. */
export default function UploadRedirect() {
  redirect("/dashboard/courses");
}
