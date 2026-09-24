import {
  BookOpen,
  Home,
  MessageSquare,
  Search,
  Settings,
  Sparkles,
  StickyNote,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  /** Shown in the phone tab bar. Space there is scarce, so not everything is. */
  mobile?: boolean;
  /** Matches child routes too, e.g. /dashboard/courses/3. */
  prefix?: boolean;
}

/**
 * Labels are in the user's vocabulary, not the schema's.
 *
 * "Historical Notes" is gone from the top level: those files are style training
 * data, not a second content library, so they live inside Style › Sources where
 * they make sense.
 */
export const NAV_ITEMS: NavItem[] = [
  { name: "Home", href: "/dashboard", icon: Home, mobile: true },
  { name: "Courses", href: "/dashboard/courses", icon: BookOpen, mobile: true, prefix: true },
  { name: "Notes", href: "/dashboard/notes", icon: StickyNote, mobile: true, prefix: true },
  { name: "Ask", href: "/dashboard/ask", icon: MessageSquare, mobile: true, prefix: true },
  { name: "Search", href: "/dashboard/search", icon: Search },
  { name: "Style", href: "/dashboard/style", icon: Sparkles, mobile: true, prefix: true },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function isActiveHref(pathname: string, item: NavItem): boolean {
  if (item.prefix) return pathname === item.href || pathname.startsWith(`${item.href}/`);
  return pathname === item.href;
}

/** Human title for the current route, so a header never reads "42". */
export function routeTitle(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length <= 1) return "Home";

  const match = NAV_ITEMS.find((item) => isActiveHref(pathname, item));
  if (match) return match.name;

  const section = segments[1];
  const labels: Record<string, string> = {
    courses: "Courses",
    notes: "Notes",
    lectures: "Lectures",
    search: "Search",
    style: "Style",
    ask: "Ask",
    settings: "Settings",
    generate: "Generate notes",
    onboarding: "Get started",
  };
  return labels[section] ?? "PersonaNotes";
}
