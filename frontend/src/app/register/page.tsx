"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const { register } = useAuth();
  const router = useRouter();

  const passwordTooShort = password.length > 0 && password.length < 8;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (passwordTooShort) return;
    setError(null);
    try {
      await register.mutateAsync({ name, email, password });
      // Registration signs you in, so go straight to setup rather than bouncing
      // back to a login form for credentials typed seconds ago.
      router.push("/dashboard/onboarding");
    } catch (registerError) {
      setError(registerError);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2 text-slate-100">
          <Sparkles className="h-5 w-5 text-indigo-400" />
          <span className="text-lg font-semibold">PersonaNotes</span>
        </Link>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8">
          <h1 className="text-xl font-semibold text-slate-100">Create your account</h1>
          <p className="mt-1 text-sm text-slate-400">
            Next you&apos;ll upload a couple of your old notes, so the first set already sounds
            like you.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field label="Name" htmlFor="name">
              <Input
                id="name"
                required
                autoComplete="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
            <Field label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>
            <Field label="Password" htmlFor="password">
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                error={passwordTooShort ? "Use at least 8 characters." : null}
              />
            </Field>

            {error ? <ErrorNotice error={error} /> : null}

            <Button
              type="submit"
              className="w-full"
              isLoading={register.isPending}
              disabled={passwordTooShort}
            >
              Create account
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link href="/login" className="text-indigo-400 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </main>
  );
}
