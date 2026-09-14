import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Boxes,
  CheckCircle2,
  CircleDashed,
  IndianRupee,
  Network,
  School,
} from "lucide-react";
import {
  BUSINESS_VERTICAL_KEYS,
  BUSINESS_VERTICALS,
  verticalPublicHref,
  type BusinessVerticalKey,
} from "@/config/businessVerticals";

const colorStyles = {
  violet: {
    hero: "from-violet-950 via-violet-900 to-slate-950",
    badge: "bg-violet-100 text-violet-800",
    button: "bg-violet-600 hover:bg-violet-700 focus-visible:ring-violet-500",
    border: "hover:border-violet-300",
    icon: "bg-violet-100 text-violet-700",
  },
  emerald: {
    hero: "from-emerald-950 via-emerald-900 to-slate-950",
    badge: "bg-emerald-100 text-emerald-800",
    button: "bg-emerald-600 hover:bg-emerald-700 focus-visible:ring-emerald-500",
    border: "hover:border-emerald-300",
    icon: "bg-emerald-100 text-emerald-700",
  },
  sky: {
    hero: "from-sky-950 via-sky-900 to-slate-950",
    badge: "bg-sky-100 text-sky-800",
    button: "bg-sky-600 hover:bg-sky-700 focus-visible:ring-sky-500",
    border: "hover:border-sky-300",
    icon: "bg-sky-100 text-sky-700",
  },
} as const;

const icons = [Boxes, School, BookOpen, Network, CheckCircle2, CircleDashed];

export function BusinessVerticalPage({ verticalKey }: { verticalKey: BusinessVerticalKey }) {
  const vertical = BUSINESS_VERTICALS[verticalKey];
  const colors = colorStyles[vertical.color];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className={`relative overflow-hidden bg-gradient-to-br ${colors.hero} text-white`}>
        <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_20%_20%,white_0,transparent_26%),radial-gradient(circle_at_80%_75%,white_0,transparent_22%)]" />
        <div className="relative mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-28">
          <div className="max-w-4xl">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-white/70">
              {vertical.code} · {vertical.eyebrow}
            </p>
            <div className="mt-5 flex flex-wrap items-baseline gap-x-5 gap-y-2">
              <h1 className="text-5xl font-bold tracking-tight sm:text-7xl">{vertical.label}</h1>
              <span className="text-2xl text-white/70 sm:text-3xl" lang="ta">{vertical.tamil}</span>
            </div>
            <p className="mt-7 max-w-3xl text-2xl font-medium leading-snug text-white/95">
              {vertical.promise}
            </p>
            <p className="mt-5 max-w-3xl text-base leading-7 text-white/70 sm:text-lg">
              {vertical.description}
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                to={vertical.workspaces[0].href}
                className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white shadow-lg outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ${colors.button}`}
              >
                Explore {vertical.label} <ArrowRight size={17} />
              </Link>
              <span className="rounded-full border border-white/20 bg-white/10 px-5 py-3 text-sm text-white/75">
                {vertical.subdomain}
              </span>
            </div>
          </div>
        </div>
      </section>

      <nav aria-label="Sasha Infinity pillars" className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-6 py-4 lg:px-8">
          {BUSINESS_VERTICAL_KEYS.map((key) => {
            const item = BUSINESS_VERTICALS[key];
            return (
              <a
                key={key}
                href={verticalPublicHref(key)}
                aria-current={key === verticalKey ? "page" : undefined}
                className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${
                  key === verticalKey ? colors.badge : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {item.code} {item.label}
              </a>
            );
          })}
        </div>
      </nav>

      <section className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Existing capabilities reorganized</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight">One vertical, clear workspaces</h2>
          <p className="mt-4 leading-7 text-slate-600">
            Each workspace keeps its specialist workflow. Identity, course delivery, payments, evidence, and admin reporting remain shared so learners and operators do not have to maintain separate accounts.
          </p>
        </div>
        <div className="mt-9 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {vertical.workspaces.map((workspace, index) => {
            const Icon = icons[index % icons.length];
            const card = (
              <>
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${colors.icon}`}><Icon size={21} /></div>
                <div className="mt-5 flex items-center justify-between gap-4">
                  <h3 className="text-lg font-semibold">{workspace.title}</h3>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${workspace.state === "live" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-800"}`}>
                    {workspace.state === "live" ? "Available" : "Planned"}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">{workspace.description}</p>
                {workspace.state === "live" && (
                  <span className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-slate-900">Open workspace <ArrowRight size={15} /></span>
                )}
              </>
            );
            return workspace.state === "live" ? (
              <Link key={workspace.title} to={workspace.href} className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${colors.border}`}>
                {card}
              </Link>
            ) : (
              <article id={workspace.title === "Live coding assessment" ? "coding-assessment" : undefined} key={workspace.title} className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-6">
                {card}
              </article>
            );
          })}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-[1.2fr_0.8fr] lg:px-8">
          <div>
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${colors.icon}`}><IndianRupee size={20} /></div>
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Independent business model</p>
                <h2 className="text-2xl font-bold">Multiple revenue streams</h2>
              </div>
            </div>
            <div className="mt-7 divide-y divide-slate-200 rounded-2xl border border-slate-200">
              {vertical.revenueModels.map((model) => (
                <div key={model.key} className="grid gap-1 p-5 sm:grid-cols-[1fr_1.2fr] sm:gap-6">
                  <h3 className="font-semibold">{model.label}</h3>
                  <p className="text-sm text-slate-600">{model.model}</p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${colors.icon}`}><Network size={20} /></div>
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Shared foundation</p>
                <h2 className="text-2xl font-bold">Connected to Sasha Infinity</h2>
              </div>
            </div>
            <ul className="mt-7 space-y-4">
              {vertical.integrations.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-slate-700">
                  <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-600" size={18} /> {item}
                </li>
              ))}
            </ul>
            <p className="mt-8 rounded-2xl bg-slate-100 p-5 text-sm leading-6 text-slate-600">
              Revenue is generated inside this pillar and consolidated in the Sasha Admin Control Center. The other two pillars remain operational if this one slows, making concentration visible before it becomes a business risk.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
