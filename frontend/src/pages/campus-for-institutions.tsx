import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Building2,
  Check,
  GraduationCap,
  HeartHandshake,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  Users,
  WalletCards,
} from "lucide-react";
import { Helmet } from "react-helmet-async";
import toast from "react-hot-toast";

import { campusGrowthApi, type CampusLeadInput } from "@/api/campus-growth";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

const outcomes = [
  {
    code: "OS—01",
    icon: Users,
    title: "Admissions to enrollment",
    text: "Move every applicant through review, documents, offers and onboarding in one clear pipeline.",
  },
  {
    code: "OS—02",
    icon: WalletCards,
    title: "Fees without spreadsheet drift",
    text: "Create plans, installments, concessions and receipts with a trustworthy student ledger.",
  },
  {
    code: "OS—03",
    icon: BarChart3,
    title: "A useful start to every day",
    text: "Give each role one action centre for classes, dues, grading, attendance and follow-ups.",
  },
  {
    code: "OS—04",
    icon: MessageCircle,
    title: "Communication that respects consent",
    text: "Reach families through account-wide WhatsApp preferences, branded updates and delivery tracking.",
  },
];

const initial: CampusLeadInput = {
  contact_name: "",
  work_email: "",
  phone: "",
  institution_name: "",
  institution_kind: "school",
  learner_count: "100-499",
  interest: "demo",
  message: "",
  source: "campus-page",
  attribution: {},
  consent: false,
  website: "",
};

function formatHours(value: number) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(
    value,
  );
}

export default function CampusForInstitutionsPage() {
  const [params] = useSearchParams();
  const [form, setForm] = useState(initial);
  const [submitted, setSubmitted] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [learners, setLearners] = useState(800);
  const [minutes, setMinutes] = useState(12);
  const plans = useQuery({
    queryKey: ["campus-plans"],
    queryFn: campusGrowthApi.plans,
  });
  const hours = useMemo(
    () => Math.round((learners * minutes * 20) / 60),
    [learners, minutes],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const attribution = Object.fromEntries(
        ["utm_source", "utm_medium", "utm_campaign"]
          .map((key) => [key, params.get(key)])
          .filter((entry): entry is [string, string] => Boolean(entry[1])),
      );
      const result = await campusGrowthApi.enquire({ ...form, attribution });
      setSubmitted(result.reference);
      toast.success("Your campus request is in");
    } catch {
      toast.error("We couldn’t send that request. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sympho-scope campus-growth-page rd-screen rd-screen-campus-for-institutions min-h-screen bg-limestone-100 text-ink-900">
      <Helmet>
        <title>Campus OS for schools and colleges · SashaInfinity</title>
        <meta
          name="description"
          content="Run admissions, learning, student finance and family communication in one connected campus workspace."
        />
      </Helmet>

      <SymphoPageHero
        index="SI—CMP.01"
        category="SASHAINFINITY CAMPUS OS"
        code="INSTITUTIONAL INFRASTRUCTURE"
        title="One structural workspace for the whole student journey."
        subtitle="Bring admissions, teaching, fee ledgers, academic progress, and family communication together — engineered with the calm precision your institution deserves."
        metrics={[
          {
            value: "4",
            unit: "pillars",
            label: "Unified Campus Subsystems",
            code: "CMP—01",
          },
          {
            value: `${formatHours(hours)}`,
            unit: "hrs / mo",
            label: "Estimated Admin Capacity Saved",
            code: "CMP—02",
          },
          {
            value: "RBAC",
            unit: "verified",
            label: "Role-Aware Governance",
            code: "CMP—03",
          },
        ]}
        actions={
          <>
            <SymphoButton href="#campus-demo" variant="copper">
              Book a Campus Walkthrough
            </SymphoButton>
            <SymphoButton to="/register?role=instructor" variant="ghost-dark">
              Start Your Workspace
            </SymphoButton>
          </>
        }
      />

      {/* Platform Highlights Bar */}
      <section
        className="border-b border-ink-900/10 bg-limestone-50"
        aria-label="Campus platform highlights"
      >
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-4 px-gutter py-4">
          <div className="flex flex-wrap items-center gap-6 font-mono text-[11px] uppercase tracking-[0.15em] text-ink-700">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-copper-500" />
              Role-aware access
            </span>
            <span className="inline-flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-copper-500" />
              Guided daily actions
            </span>
            <span className="inline-flex items-center gap-2">
              <HeartHandshake className="h-4 w-4 text-copper-500" />
              Built for schools and colleges
            </span>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
            SPEC // K-12 · COLLEGES · UNIVERSITIES
          </span>
        </div>
      </section>

      {/* Outcomes Grid */}
      <section className="border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="CMP—01"
            category="CONNECTED BY DESIGN"
            code="OPERATIONAL ARCHITECTURE"
            title="Fewer hand-offs. A clearer campus."
            subtitle="Each team gets the exact ledger, classroom roster, and next action that belongs to them."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {outcomes.map(({ code, icon: Icon, title, text }) => (
              <article
                key={title}
                className="sheet-frame flex flex-col justify-between bg-limestone-50 p-7 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/40"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                      {code}
                    </span>
                    <span className="flex h-9 w-9 items-center justify-center rounded-full border border-ink-900/10 bg-limestone-100 text-ink-800">
                      <Icon className="h-4 w-4 text-copper-500" />
                    </span>
                  </div>
                  <h3 className="mt-5 font-display text-2xl font-light text-ink-900">
                    {title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-ink-600">
                    {text}
                  </p>
                </div>
                <div className="mt-6 border-t border-ink-900/10 pt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                  Unified Subsystem // Active
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ROI / Capacity Calculator */}
      <section className="on-dark relative overflow-hidden border-b border-limestone-100/10 bg-ink-950 py-section-sm text-limestone-100 blueprint-grid">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            dark
            index="CMP—02"
            category="CAPACITY TELEMETRY"
            code="ROI ESTIMATOR"
            title="Give routine administration back to your team."
            subtitle="Estimate the monthly staff hours reclaimed from repeated manual fee reminders, attendance reconciliation, and spreadsheet hand-offs."
          />

          <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-12">
            <div className="sheet-frame bg-ink-900/90 p-8 lg:col-span-7">
              <div className="space-y-8">
                <label className="block">
                  <div className="flex items-baseline justify-between">
                    <span className="font-mono text-xs uppercase tracking-[0.16em] text-limestone-200">
                      Learners Enrolled
                    </span>
                    <strong className="font-display text-3xl font-light text-copper-400">
                      {formatHours(learners)}
                    </strong>
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="10000"
                    step="100"
                    value={learners}
                    onChange={(e) => setLearners(Number(e.target.value))}
                    className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-pill bg-limestone-100/15 accent-copper-500"
                  />
                  <div className="mt-2 flex justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-limestone-300/50">
                    <span>100 Learners</span>
                    <span>10,000 Learners</span>
                  </div>
                </label>

                <label className="block">
                  <div className="flex items-baseline justify-between">
                    <span className="font-mono text-xs uppercase tracking-[0.16em] text-limestone-200">
                      Minutes of repeated work per learner
                    </span>
                    <strong className="font-display text-3xl font-light text-copper-400">
                      {minutes} min
                    </strong>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="30"
                    step="1"
                    value={minutes}
                    onChange={(e) => setMinutes(Number(e.target.value))}
                    className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-pill bg-limestone-100/15 accent-copper-500"
                  />
                  <div className="mt-2 flex justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-limestone-300/50">
                    <span>2 min / day</span>
                    <span>30 min / day</span>
                  </div>
                </label>
              </div>
            </div>

            <div className="sheet-frame flex flex-col justify-between bg-ink-900/95 p-8 lg:col-span-5">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-400">
                  PROJECTED MONTHLY RECLAMATION
                </span>
                <p className="mt-2 font-mono text-xs uppercase tracking-[0.14em] text-limestone-300/70">
                  Routine-work capacity each month
                </p>
                <strong className="mt-4 block font-display text-6xl font-light text-limestone-50 sm:text-7xl">
                  {formatHours(hours)} hours
                </strong>
              </div>
              <p className="mt-6 border-t border-limestone-100/10 pt-4 text-xs leading-relaxed text-limestone-300/70">
                This is a planning estimate across 20 operating days per month. Your guided walkthrough will map your exact institutional workflows and measurable targets.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Plans Section */}
      <section className="border-b border-ink-900/10 py-section-sm" id="plans">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="CMP—03"
            category="PLANS THAT GROW WITH YOU"
            code="LICENSING TIERS"
            title="Start with your campus today."
            subtitle="Flexible institutional tiers designed for emerging academies, full K-12 schools, and multi-department colleges."
          />

          <div className="mt-12">
            {plans.isError ? (
              <div
                className="sheet-frame border-red-500/40 bg-red-500/10 p-6 text-center"
                role="alert"
              >
                <p className="font-mono text-xs uppercase tracking-[0.14em] text-red-800">
                  Plans are temporarily unavailable.
                </p>
                <button
                  type="button"
                  onClick={() => void plans.refetch()}
                  className="mt-3 rounded-pill bg-ink-900 px-5 py-2 font-mono text-xs uppercase tracking-[0.14em] text-limestone-100 hover:bg-copper-500"
                >
                  Try again
                </button>
              </div>
            ) : (
              <div
                className="grid grid-cols-1 gap-6 md:grid-cols-3"
                aria-busy={plans.isPending}
              >
                {(plans.data || []).map((plan, idx) => (
                  <article
                    key={plan.key}
                    className={`sheet-frame flex flex-col justify-between p-8 ${
                      plan.featured
                        ? "on-dark bg-ink-950 text-limestone-100 shadow-lift"
                        : "bg-limestone-50 text-ink-900"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between border-b border-current/10 pb-4">
                        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                          <Building2 className="h-3.5 w-3.5" />
                          PLAN—0{idx + 1}
                        </span>
                        {plan.featured && (
                          <span className="rounded-pill bg-copper-500 px-3 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-limestone-50">
                            Most popular
                          </span>
                        )}
                      </div>

                      <h3 className="mt-5 font-display text-3xl font-light">
                        {plan.name}
                      </h3>
                      <p
                        className={`mt-2 text-sm leading-relaxed ${
                          plan.featured ? "text-limestone-200/75" : "text-ink-600"
                        }`}
                      >
                        {plan.description}
                      </p>

                      <strong className="mt-6 block border-y border-current/10 py-4 font-display text-3xl font-light text-copper-500">
                        {plan.price_label}
                      </strong>

                      <ul className="mt-6 space-y-3">
                        {plan.features.map((feature) => (
                          <li
                            key={feature}
                            className="flex items-start gap-2.5 text-sm"
                          >
                            <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-copper-500" />
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <a
                      href="#campus-demo"
                      onClick={() =>
                        setForm((value) => ({
                          ...value,
                          interest: plan.key === "starter" ? "trial" : "quote",
                        }))
                      }
                      className={`mt-8 inline-flex items-center justify-center gap-2 rounded-pill px-6 py-3.5 font-mono text-xs uppercase tracking-[0.16em] transition-colors ${
                        plan.featured
                          ? "bg-copper-500 text-limestone-50 hover:bg-copper-400"
                          : "bg-ink-900 text-limestone-100 hover:bg-copper-500"
                      }`}
                    >
                      Choose {plan.name} <ArrowRight size={15} />
                    </a>
                  </article>
                ))}
                {plans.isPending &&
                  [1, 2, 3].map((item) => (
                    <div
                      className="sheet-frame h-96 animate-pulse bg-limestone-50 p-8"
                      key={item}
                    />
                  ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Contact / Walkthrough Request Form */}
      <section className="py-section-sm" id="campus-demo">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-copper-500">
                <GraduationCap className="h-4 w-4" />
                CMP—04 // WALKTHROUGH BRIEFING
              </span>
              <h2 className="mt-4 font-display text-display-md font-light text-ink-900">
                See SashaInfinity with your real workflow.
              </h2>
              <p className="mt-4 text-base leading-relaxed text-ink-600">
                Tell us about your institution. Our implementation architects will prepare a focused walkthrough tailored to your academic calendar, fee structure, and faculty roles.
              </p>

              <div className="mt-8 sheet-frame bg-limestone-50 p-6">
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                  WHAT WE PREPARE FOR YOUR CALL
                </span>
                <ul className="mt-4 space-y-3 text-sm text-ink-700">
                  <li className="flex items-center gap-2.5">
                    <Check className="h-4 w-4 text-copper-500" />
                    Role-based workspaces for Principal, Faculty, Finance & Parents
                  </li>
                  <li className="flex items-center gap-2.5">
                    <Check className="h-4 w-4 text-copper-500" />
                    Fee installment & receipt ledger simulation
                  </li>
                  <li className="flex items-center gap-2.5">
                    <Check className="h-4 w-4 text-copper-500" />
                    3D STEM Lab & CBSE/State Board curriculum mapping
                  </li>
                </ul>
              </div>
            </div>

            <div className="lg:col-span-7">
              {submitted ? (
                <div
                  className="sheet-frame bg-limestone-50 p-10 text-center"
                  role="status"
                >
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-copper-500/15 text-copper-500">
                    <Check size={24} />
                  </div>
                  <h3 className="mt-4 font-display text-3xl font-light text-ink-900">
                    Your request is ready.
                  </h3>
                  <p className="mt-2 text-sm text-ink-600">
                    Reference{" "}
                    <strong className="font-mono text-ink-900">
                      {submitted}
                    </strong>
                    . Our campus team can now follow up with you.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setSubmitted(undefined);
                      setForm(initial);
                    }}
                    className="mt-6 rounded-pill border border-ink-900/20 px-6 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-ink-900 hover:border-copper-500 hover:text-copper-500"
                  >
                    Send another request
                  </button>
                </div>
              ) : (
                <form
                  className="sheet-frame bg-limestone-50 p-8"
                  onSubmit={submit}
                >
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Your name *
                      </span>
                      <input
                        required
                        minLength={2}
                        value={form.contact_name}
                        onChange={(e) =>
                          setForm({ ...form, contact_name: e.target.value })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      />
                    </label>
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Work email *
                      </span>
                      <input
                        required
                        type="email"
                        value={form.work_email}
                        onChange={(e) =>
                          setForm({ ...form, work_email: e.target.value })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      />
                    </label>
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Institution *
                      </span>
                      <input
                        required
                        minLength={2}
                        value={form.institution_name}
                        onChange={(e) =>
                          setForm({ ...form, institution_name: e.target.value })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      />
                    </label>
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Phone
                      </span>
                      <input
                        inputMode="tel"
                        value={form.phone}
                        onChange={(e) =>
                          setForm({ ...form, phone: e.target.value })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      />
                    </label>
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Institution type
                      </span>
                      <select
                        value={form.institution_kind}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            institution_kind:
                              e.target.value as CampusLeadInput["institution_kind"],
                          })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      >
                        <option value="school">School</option>
                        <option value="college">College</option>
                        <option value="university">University</option>
                        <option value="training">Training institute</option>
                      </select>
                    </label>
                    <label className="block">
                      <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                        Learners
                      </span>
                      <select
                        value={form.learner_count}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            learner_count:
                              e.target.value as CampusLeadInput["learner_count"],
                          })
                        }
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                      >
                        <option value="under-100">Under 100</option>
                        <option value="100-499">100–499</option>
                        <option value="500-1999">500–1,999</option>
                        <option value="2000-plus">2,000+</option>
                      </select>
                    </label>
                  </div>

                  <label className="mt-5 block">
                    <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                      What would you like to explore?
                    </span>
                    <select
                      value={form.interest}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          interest:
                            e.target.value as CampusLeadInput["interest"],
                        })
                      }
                      className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                    >
                      <option value="demo">Guided demo</option>
                      <option value="trial">Trial workspace</option>
                      <option value="quote">Institution quote</option>
                    </select>
                  </label>

                  <label className="mt-5 block">
                    <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700">
                      What should we prepare?
                    </span>
                    <textarea
                      rows={4}
                      maxLength={2000}
                      value={form.message}
                      onChange={(e) =>
                        setForm({ ...form, message: e.target.value })
                      }
                      placeholder="Admissions, fee collection, learning delivery, integrations…"
                      className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 focus:border-copper-500 focus:outline-none"
                    />
                  </label>

                  <label className="mt-5 flex items-start gap-3 text-xs text-ink-600">
                    <input
                      required
                      type="checkbox"
                      checked={form.consent}
                      onChange={(e) =>
                        setForm({ ...form, consent: e.target.checked })
                      }
                      className="mt-0.5 h-4 w-4 accent-copper-500"
                    />
                    <span>
                      I agree that SashaInfinity may contact me about this
                      request. I can withdraw this permission at any time.
                    </span>
                  </label>

                  <label className="sr-only" aria-hidden="true">
                    Website
                    <input
                      tabIndex={-1}
                      autoComplete="off"
                      value={form.website}
                      onChange={(e) =>
                        setForm({ ...form, website: e.target.value })
                      }
                    />
                  </label>

                  <div className="mt-7">
                    <button
                      type="submit"
                      disabled={busy}
                      className="inline-flex items-center gap-2 rounded-pill bg-ink-900 px-7 py-3.5 font-mono text-xs uppercase tracking-[0.16em] text-limestone-100 transition-colors hover:bg-copper-500 disabled:opacity-50"
                    >
                      {busy ? "Sending..." : "Request my walkthrough"}
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—CMP // 05"
        eyebrow="INSTITUTIONAL WORKSPACE"
        title="Ready to launch your campus workspace?"
        description="Create an instructor or administrator account now to explore SashaInfinity's classroom tools, interactive 3D labs, and assessment studio."
        primaryLabel="Start Your Workspace"
        primaryTo="/register?role=instructor"
        secondaryLabel="Explore Learning Labs"
        secondaryTo="/labs"
      />
    </div>
  );
}
