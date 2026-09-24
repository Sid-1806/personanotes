"use client";

import { Download, KeyRound, LogOut, ShieldCheck, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import api, { API_BASE, errorMessage, getToken } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const toast = useToast();

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  // Notes you can't take out aren't really yours.
  const exportAll = async () => {
    setExporting(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/users/me/export`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = "personanotes-export.md";
      link.click();
      URL.revokeObjectURL(href);
      toast.success("Exported all of your notes.");
    } catch {
      toast.error("Couldn't export your notes right now.");
    } finally {
      setExporting(false);
    }
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await api.delete("/users/me");
      logout();
      router.push("/");
    } catch (deleteError) {
      toast.error(errorMessage(deleteError, "Couldn't delete your account."));
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-100">
          <ShieldCheck className="h-6 w-6 text-indigo-400" /> Settings
        </h1>
        <p className="mt-1 text-sm text-slate-400">Your account and your data.</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-200">Account</h2>
        </CardHeader>
        <CardBody className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Name</span>
            <span className="font-medium text-slate-200">{user?.name ?? "—"}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Email</span>
            <span className="truncate font-medium text-slate-200">{user?.email ?? "—"}</span>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-200">Your data</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm text-slate-200">Export everything</p>
              <p className="text-xs text-slate-400">
                Every note, including your edits, as a single markdown file.
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={exportAll} isLoading={exporting}>
              <Download className="h-4 w-4" /> Export
            </Button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
            <div className="min-w-0">
              <p className="text-sm text-slate-200">Delete account</p>
              <p className="text-xs text-slate-400">
                Removes your lectures, notes and style profile permanently.
              </p>
            </div>
            <Button variant="danger" size="sm" onClick={() => setConfirmDelete(true)}>
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <KeyRound className="h-4 w-4 text-indigo-400" /> AI provider
          </h2>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-slate-400">
            Generation uses Google Gemini. The API key is configured on the server via the{" "}
            <code className="rounded bg-slate-800 px-1.5 py-0.5 text-indigo-300">GEMINI_API_KEY</code>{" "}
            environment variable. Embeddings run locally.
          </p>
        </CardBody>
      </Card>

      <Button variant="danger" onClick={handleLogout}>
        <LogOut className="h-4 w-4" /> Log out
      </Button>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete your account?"
        description="Every lecture, note, edit and style version is permanently removed. This can't be undone."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={confirmText !== "DELETE"}
              isLoading={deleting}
              onClick={deleteAccount}
            >
              Delete everything
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-300">
            Export your notes first if you want to keep them.
          </p>
          <Field label="Type DELETE to confirm" htmlFor="confirm-delete">
            <Input
              id="confirm-delete"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              placeholder="DELETE"
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
