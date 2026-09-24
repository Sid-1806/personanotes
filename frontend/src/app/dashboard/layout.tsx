"use client";

import { LogOut, Menu, Search, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CommandPalette } from "@/components/layout/CommandPalette";
import { NAV_ITEMS, isActiveHref, routeTitle } from "@/components/layout/Nav";
import { SessionGuard } from "@/components/layout/SessionGuard";
import { useAuth } from "@/hooks/useAuth";
import { useDashboardSummary } from "@/hooks/useDashboard";
import { cn } from "@/lib/utils";

/**
 * The authenticated shell.
 *
 * Responsive by breakpoint rather than by shrinking: a phone gets a bottom tab
 * bar with no sidebar in the layout at all, a tablet gets an icon rail, and a
 * desktop gets the full sidebar. The previous fixed `w-64` aside consumed most
 * of a 375px viewport.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const { data: summary } = useDashboardSummary();
  const personalization = summary?.personalization_metrics?.current_score ?? 0;

  useEffect(() => {
    if (!isLoading && !user) router.push("/login");
  }, [user, isLoading, router]);

  // Close the drawer on navigation, or it covers the page you just opened.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
        return;
      }
      // "/" focuses search, but not while the user is typing into something.
      const target = event.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (event.key === "/" && !typing) {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-3">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading your workspace…</p>
        </div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const title = routeTitle(pathname);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Desktop sidebar / tablet icon rail */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-20 flex-col border-r border-slate-800 bg-slate-900/70 backdrop-blur md:flex xl:w-60">
        <div className="flex h-16 items-center justify-center border-b border-slate-800 xl:justify-start xl:px-5">
          <Link href="/dashboard" className="flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded">
            <Sparkles className="h-5 w-5 shrink-0 text-indigo-400" />
            <span className="hidden text-lg font-semibold tracking-tight text-slate-100 xl:block">
              PersonaNotes
            </span>
          </Link>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const active = isActiveHref(pathname, item);
            return (
              <Link
                key={item.name}
                href={item.href}
                aria-current={active ? "page" : undefined}
                title={item.name}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                  "justify-center xl:justify-start",
                  active
                    ? "bg-indigo-500/10 text-indigo-300"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200",
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                <span className="hidden xl:block">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-800 p-3">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 justify-center xl:justify-start focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Search className="h-4 w-4 shrink-0" />
            <span className="hidden xl:block">Search</span>
            <kbd className="ml-auto hidden rounded border border-slate-700 px-1.5 text-xs text-slate-500 xl:block">
              ⌘K
            </kbd>
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-slate-800 bg-slate-900">
            <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
              <span className="flex items-center gap-2 font-semibold text-slate-100">
                <Sparkles className="h-5 w-5 text-indigo-400" /> PersonaNotes
              </span>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close menu"
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 space-y-1 overflow-y-auto p-3">
              {NAV_ITEMS.map((item) => {
                const active = isActiveHref(pathname, item);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium",
                      active
                        ? "bg-indigo-500/10 text-indigo-300"
                        : "text-slate-300 hover:bg-slate-800/60",
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            <div className="border-t border-slate-800 p-4">
              <p className="truncate text-sm font-medium text-slate-200">{user.name}</p>
              <p className="truncate text-xs text-slate-400">{user.email}</p>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-3 flex items-center gap-2 text-sm text-rose-400 hover:text-rose-300"
              >
                <LogOut className="h-4 w-4" /> Log out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content column */}
      <div className="flex min-h-screen flex-col md:pl-20 xl:pl-60">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-800 bg-slate-950/90 px-4 backdrop-blur sm:px-6">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* A real page title — this used to render the raw URL segment, so a
              note at /notes/42 got a header that just said "42". */}
          <h1 className="min-w-0 flex-1 truncate text-lg font-semibold text-slate-100">{title}</h1>

          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            aria-label="Search"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 md:hidden"
          >
            <Search className="h-5 w-5" />
          </button>

          <Link
            href="/dashboard/style"
            className="hidden items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-sm text-indigo-300 hover:bg-indigo-500/20 sm:flex"
            title="How well PersonaNotes matches your style"
          >
            Personalization <span className="font-semibold">{Math.round(personalization)}%</span>
          </Link>

          <div className="hidden items-center gap-3 border-l border-slate-800 pl-4 md:flex">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500 text-sm font-semibold text-white">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="hidden lg:block">
              <p className="text-sm font-medium leading-none text-slate-200">{user.name}</p>
              <p className="mt-1 text-xs text-slate-400">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              aria-label="Log out"
              title="Log out"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-rose-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* pb-20 leaves room for the phone tab bar */}
        <main className="flex-1 px-4 pb-24 pt-6 sm:px-6 md:pb-8">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>

      {/* Phone tab bar */}
      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-slate-800 bg-slate-900/95 backdrop-blur md:hidden"
      >
        {NAV_ITEMS.filter((item) => item.mobile).map((item) => {
          const active = isActiveHref(pathname, item);
          return (
            <Link
              key={item.name}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition-colors",
                active ? "text-indigo-400" : "text-slate-500",
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <SessionGuard email={user.email} />
    </div>
  );
}
