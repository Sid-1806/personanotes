"use client";

import { LogIn } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import api, { SESSION_EXPIRED_EVENT, errorMessage, setToken } from "@/lib/api";

/**
 * Re-authenticate in place when a session expires.
 *
 * The old behaviour was `window.location.href = '/login'` on any 401, which
 * discarded whatever was in the editor. Signing back in over the top keeps the
 * page — and the unsaved work on it — exactly where it was.
 */
export function SessionGuard({ email }: { email?: string | null }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [address, setAddress] = useState(email ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (email) setAddress(email);
  }, [email]);

  useEffect(() => {
    const onExpired = () => setOpen(true);
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.append("username", address);
      body.append("password", password);
      const { data } = await api.post("/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      setToken(data.access_token);
      setPassword("");
      setOpen(false);
      // Refetch whatever failed while the session was dead.
      await queryClient.invalidateQueries();
    } catch (loginError) {
      setError(errorMessage(loginError, "Those details didn't work."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => setOpen(false)}
      dismissible={false}
      title="Signed out"
      description="Your session expired. Sign back in — nothing on this page has been lost."
      size="sm"
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" htmlFor="reauth-email">
          <Input
            id="reauth-email"
            type="email"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            autoComplete="username"
            required
          />
        </Field>
        <Field label="Password" htmlFor="reauth-password">
          <Input
            id="reauth-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            error={error}
            required
          />
        </Field>
        <Button type="submit" className="w-full" isLoading={submitting}>
          <LogIn className="h-4 w-4" /> Sign back in
        </Button>
      </form>
    </Modal>
  );
}
