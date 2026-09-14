import * as React from "react";
import {
  RefreshCw,
  Search,
  Wrench,
  CheckCircle2,
  WifiOff,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";

type ServerStatus = "down" | "maintenance" | "live";

const STATUS_CONFIG: Record<
  ServerStatus,
  {
    label: string;
    dotColor: string;
    dotShadow: string;
    pillBg: string;
  }
> = {
  down: {
    label: "Status: Server Down",
    dotColor: "bg-red-500",
    dotShadow: "shadow-[0_0_10px_rgba(239,68,68,0.8)]",
    pillBg: "border-red-200 bg-red-50",
  },
  maintenance: {
    label: "Status: Under Maintenance",
    dotColor: "bg-blue-500",
    dotShadow: "shadow-[0_0_10px_rgba(59,130,246,0.8)]",
    pillBg: "border-blue-200 bg-blue-50",
  },
  live: {
    label: "Status: All Systems Live",
    dotColor: "bg-green-500",
    dotShadow: "shadow-[0_0_10px_rgba(34,197,94,0.8)]",
    pillBg: "border-green-200 bg-green-50",
  },
};

interface StatusCard {
  icon: React.ReactNode;
  title: string;
  badge: string;
}

const STATUS_CARDS: StatusCard[] = [
  {
    icon: <Search className="w-14 h-14 text-white" strokeWidth={2.5} />,
    title: "Identifying the Issue",
    badge: "DIAGNOSTIC",
  },
  {
    icon: <Wrench className="w-14 h-14 text-white" strokeWidth={2.5} />,
    title: "Resolving the Issue",
    badge: "REPAIR",
  },
  {
    icon: <CheckCircle2 className="w-14 h-14 text-white" strokeWidth={2.5} />,
    title: "Verifying Updates",
    badge: "VERIFIED",
  },
];

export const ServerDownPage: React.FC<{ status?: ServerStatus }> = ({
  status: initialStatus = "down",
}) => {
  const [activeCard, setActiveCard] = React.useState(0);
  const [status] = React.useState<ServerStatus>(initialStatus);

  // Auto-cycle through status cards
  React.useEffect(() => {
    const interval = setInterval(() => {
      setActiveCard((prev) => (prev + 1) % STATUS_CARDS.length);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  const config = STATUS_CONFIG[status];

  return (
    <div className="relative min-h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* ── Ambient background mesh ── */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -top-[100px] -right-[50px] h-[550px] w-[550px] rounded-full bg-orange-400/30 blur-[110px]" />
        <div className="absolute -bottom-[150px] -left-[100px] h-[650px] w-[650px] rounded-full bg-blue-900/25 blur-[110px]" />
        {/* Subtle grid */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(#082a5e 1px, transparent 1px), linear-gradient(90deg, #082a5e 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
      </div>

      {/* ── Header ── */}
      <header className="relative z-10 border-b border-blue-900/[0.09] bg-white/92 backdrop-blur-xl shadow-[0_1px_16px_rgba(8,42,94,0.06)]">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-5 px-6 py-3.5 sm:px-8">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-orange-400/25 shadow-[0_2px_10px_rgba(244,145,26,0.18)]">
              <WifiOff className="h-6 w-6 text-orange-500" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-lg font-extrabold tracking-tight text-blue-900">
                Sasha <span className="text-orange-500">Infinity</span>
              </span>
              <span className="text-[0.65rem] font-medium uppercase tracking-widest text-gray-500">
                Democratize Education
              </span>
            </div>
          </div>

          {/* Status widget */}
          <div className="hidden items-center gap-3 rounded-full border border-blue-900/10 bg-blue-900/[0.04] px-4 py-1.5 sm:flex">
            <span className="text-xs font-bold uppercase tracking-wide text-blue-900">
              Server Status:
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-semibold shadow-sm ${
                  status === "live"
                    ? "ring-1 ring-green-200"
                    : status === "down"
                      ? "ring-1 ring-red-200"
                      : "ring-1 ring-blue-200"
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${config.dotColor} ${config.dotShadow} ${
                    status === "down" ? "animate-pulse" : ""
                  }`}
                />
                <span className="capitalize text-gray-600">
                  {status === "live"
                    ? "Live"
                    : status === "down"
                      ? "Down"
                      : "Under Maintenance"}
                </span>
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="relative z-5 flex flex-1 items-center justify-center px-6 py-12 sm:px-8 md:py-16">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 md:grid-cols-[1.1fr_1fr] md:gap-16 lg:gap-20">
          {/* Left — copy */}
          <div className="flex flex-col items-center text-center md:items-start md:text-left">
            {/* Status pill */}
            <div
              className={`mb-6 inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-widest ${config.pillBg}`}
            >
              <span
                className={`h-2 w-2 rounded-full ${config.dotColor} ${config.dotShadow} ${
                  status === "down" ? "animate-pulse" : ""
                }`}
              />
              <span className="text-blue-900">{config.label}</span>
            </div>

            <h1 className="mb-4 text-4xl font-extrabold leading-tight tracking-tight text-gray-900 sm:text-5xl lg:text-[3.5rem]">
              The server is currently offline and will{" "}
              <span className="bg-gradient-to-r from-orange-400 to-orange-500 bg-clip-text text-transparent">
                get back in a while.
              </span>
            </h1>

            <p className="mb-8 max-w-lg text-base leading-relaxed text-gray-500 md:text-lg">
              We're experiencing some technical difficulties. Our team has been
              notified and is working to get everything back up and running.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <Button
                size="lg"
                onClick={() => window.location.reload()}
                className="gap-2.5 rounded-xl bg-gradient-to-r from-orange-400 via-orange-500 to-orange-600 px-7 py-3.5 font-bold shadow-[0_10px_24px_rgba(244,145,26,0.35)] transition-all hover:-translate-y-0.5 hover:shadow-[0_16px_36px_rgba(244,145,26,0.5)]"
              >
                <RefreshCw className="h-[18px] w-[18px]" />
                Refresh Status
              </Button>
            </div>
          </div>

          {/* Right — status cards */}
          <div className="flex flex-col items-center">
            <div className="w-full max-w-md">
              {/* Active card */}
              <div
                className="relative overflow-hidden rounded-2xl border border-orange-200/60 bg-white shadow-xl shadow-orange-500/10 transition-all duration-500"
                data-glass="content"
              >
                <div className="relative h-48 bg-gradient-to-br from-orange-100 via-orange-50 to-amber-50">
                  <div className="absolute inset-0 flex items-center justify-center">
                    {/* Decorative glow circle */}
                    <div className="absolute h-36 w-36 rounded-full bg-orange-400/10 blur-2xl" />
                    <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-orange-400 via-orange-500 to-amber-600 shadow-[0_12px_14px_rgba(244,145,26,0.3)]">
                      {STATUS_CARDS[activeCard].icon}
                    </div>
                  </div>
                  {/* Badge */}
                  <div className="absolute right-4 top-4 flex items-center gap-2 rounded-full border border-orange-300/60 bg-white/90 px-3 py-1">
                    <span className="h-2 w-2 rounded-full bg-orange-500" />
                    <span className="text-[10px] font-extrabold tracking-wider text-orange-700">
                      {STATUS_CARDS[activeCard].badge}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-orange-100 px-6 py-4">
                  <h3 className="text-lg font-bold text-gray-900">
                    {STATUS_CARDS[activeCard].title}
                  </h3>
                  <ShieldAlert className="h-5 w-5 text-orange-400" />
                </div>
              </div>

              {/* Card dots */}
              <div className="mt-5 flex items-center justify-center gap-2">
                {STATUS_CARDS.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveCard(idx)}
                    className={`h-2 rounded-full transition-all duration-300 ${
                      idx === activeCard
                        ? "w-8 bg-orange-500"
                        : "w-2 bg-orange-200 hover:bg-orange-300"
                    }`}
                    aria-label={`Show card: ${STATUS_CARDS[idx].title}`}
                  />
                ))}
              </div>

              {/* Animated progress bar */}
              <div
                className="mt-6 rounded-2xl border border-orange-200/40 bg-white/88 p-3 shadow-lg shadow-blue-900/[0.08] backdrop-blur-lg"
                data-glass="content"
              >
                <div className="mb-2.5 h-1 w-full overflow-hidden rounded-full bg-orange-200/50">
                  <div className="h-full w-full animate-[progressPulse_4.5s_infinite_linear] bg-gradient-to-r from-orange-500 to-orange-400" />
                </div>
                <div className="flex items-center justify-between text-xs font-semibold text-gray-500">
                  <span>Cycling status updates</span>
                  <span className="font-extrabold tracking-wide text-orange-500">
                    LIVE ∞
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-blue-900/[0.06] bg-white/60 px-6 py-5 text-center text-sm text-gray-500 backdrop-blur-md sm:px-8">
        &copy; {new Date().getFullYear()} Sasha Infinity. All Rights Reserved.
      </footer>

      {/* Keyframe for progress bar animation */}
      <style>{`
        @keyframes progressPulse {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(0%); }
        }
      `}</style>
    </div>
  );
};

export default ServerDownPage;
