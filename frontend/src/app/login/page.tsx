"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push("/dashboard");
    } catch (loginError) {
      // Inline and specific, rather than an alert() that says nothing useful.
      setError(loginError);
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
          <h1 className="text-xl font-semibold text-slate-100">Welcome back</h1>
          <p className="mt-1 text-sm text-slate-400">Pick up where you left off.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>

            {error ? <ErrorNotice error={error} /> : null}

            <Button type="submit" className="w-full" isLoading={login.isPending}>
              Log in
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-slate-400">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-indigo-400 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
