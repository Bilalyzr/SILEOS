import type { LucideIcon } from "lucide-react";
import { AlertCircle, Inbox, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CampusTone } from "@/api/campus-os";

export function CampusOsLoading({ label }: { label: string }) {
  return (
    <div className="campus-os-skeleton-grid" role="status" aria-label={label}>
      {[1, 2, 3, 4].map((item) => (
        <span className="campus-os-skeleton" aria-hidden="true" key={item} />
      ))}
    </div>
  );
}

export function CampusOsError({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="campus-os-inline-error" role="alert">
      <span className="flex items-center gap-2">
        <AlertCircle size={17} aria-hidden="true" /> {message}
      </span>
      <Button size="sm" variant="outline" leftIcon={<RotateCcw size={14} />} onClick={retry}>
        Try again
      </Button>
    </div>
  );
}

export function CampusOsEmpty({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="campus-os-table-empty">
      <Icon size={27} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function CampusOsBadge({
  children,
  tone = "orange",
}: {
  children: React.ReactNode;
  tone?: CampusTone;
}) {
  return (
    <span className="campus-os-badge" data-tone={tone}>
      {children}
    </span>
  );
}

export function initials(value: string) {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function formatMoney(amount: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(value?: string | null) {
  if (!value) return "No date";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: parsed.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  });
}

export function formatTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString("en-IN", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function readable(value: string) {
  return value.replace(/_/g, " ");
}

export function errorMessage(error: unknown, fallback: string) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (error as {
      response?: { data?: { detail?: string; message?: string } };
    }).response;
    return response?.data?.detail || response?.data?.message || fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
