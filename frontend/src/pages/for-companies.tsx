import { CheckCircle2, ShieldCheck, Sparkles, Users } from "lucide-react";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

const PILLARS = [
  {
    code: "CORP—01",
    icon: CheckCircle2,
    title: "Pre-filtered candidates",
    body: "See only students who finished a rigorous course, completed verified project assessments, and explicitly opted in to be hired.",
  },
  {
    code: "CORP—02",
    icon: Sparkles,
    title: "Express interest, no spam",
    body: "Send one structured outreach message. The candidate accepts or declines. Direct contact details are revealed immediately upon acceptance.",
  },
  {
    code: "CORP—03",
    icon: ShieldCheck,
    title: "No recruiter fees",
    body: "Free to browse verified portfolios and course transcripts. Zero per-hire placement charges while in corporate partner beta.",
  },
];

const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Register Your Corporate Workspace",
    detail: "Create a verified company profile and invite your engineering or talent managers with role-scoped access.",
  },
  {
    step: "02",
    title: "Filter by Verified Skill & Cohort",
    detail: "Inspect candidate completion certificates, lab scores, internship attendance logs, and project deliverables.",
  },
  {
    step: "03",
    title: "Direct Consent-First Introductions",
    detail: "Initiate one-click interview requests or onboard cohorts directly into your corporate internship pipeline.",
  },
];

export function ForCompaniesPage() {
  return (
    <div className="sympho-scope rd-screen rd-screen-for-companies min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—CORP.01"
        category="CORPORATE TALENT & INTERNSHIP PORTAL"
        code="ENTERPRISE PARTNER NETWORK"
        title="Hire pre-vetted, course-certified talent."
        subtitle="SashaInfinity LMS graduates complete rigorous, instructor-led studio courses and supervised internships. Access engineers and analysts ready to contribute from day one — filtered by verified skills, roles, and availability."
        metrics={[
          {
            value: "100%",
            unit: "verified",
            label: "Course & Lab Transcripts",
            code: "CRP—01",
          },
          {
            value: "₹0",
            unit: "placement fee",
            label: "Direct Partner Access",
            code: "CRP—02",
          },
          {
            value: "DAY 01",
            unit: "readiness",
            label: "Production-Tested Cohorts",
            code: "CRP—03",
          },
        ]}
        actions={
          <>
            <SymphoButton to="/for-companies/signup" variant="copper">
              Create a company account
            </SymphoButton>
            <SymphoButton to="/login" variant="ghost-dark">
              Sign in
            </SymphoButton>
          </>
        }
      />

      {/* Core Value Pillars */}
      <section className="border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="CRP—01"
            category="HIRING ARCHITECTURE"
            code="SIGNAL OVER NOISE"
            title="Engineered for high-signal technical hiring."
            subtitle="Replace resume keyword guessing with verifiable learning telemetry, graded code labs, and mentor-endorsed internship logs."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {PILLARS.map((c) => {
              const Icon = c.icon;
              return (
                <div
                  key={c.title}
                  className="sheet-frame flex flex-col justify-between bg-limestone-50 p-8 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/40"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                        {c.code}
                      </span>
                      <Icon className="h-4 w-4 text-copper-500" />
                    </div>
                    <h3 className="mt-6 font-display text-2xl font-light text-ink-900">
                      {c.title}
                    </h3>
                    <p className="mt-3 text-sm leading-relaxed text-ink-600">
                      {c.body}
                    </p>
                  </div>
                  <div className="mt-8 border-t border-ink-900/10 pt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                    Corporate Portal // Verified Standard
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 3-Step Corporate Pipeline */}
      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="CRP—02"
            category="RECRUITMENT WORKFLOW"
            code="3-STAGE PIPELINE"
            title="From company signup to cohort onboarding."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {WORKFLOW_STEPS.map((w) => (
              <div
                key={w.step}
                className="sheet-frame bg-limestone-50/80 p-8"
              >
                <span className="font-display text-5xl font-light italic text-copper-500">
                  {w.step}
                </span>
                <h3 className="mt-4 font-display text-2xl font-light text-ink-900">
                  {w.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-ink-600">
                  {w.detail}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-10 sheet-frame flex flex-col items-start justify-between gap-6 bg-ink-950 p-8 text-limestone-100 sm:flex-row sm:items-center">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-limestone-100/15 bg-limestone-100/5 text-copper-400">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-400">
                  DEDICATED COMPANY DASHBOARD
                </span>
                <p className="mt-1 font-display text-2xl font-light text-limestone-50">
                  Manage interns, daily work logs, attendance & mentor reviews in one portal.
                </p>
              </div>
            </div>
            <SymphoButton to="/for-companies/signup" variant="copper">
              Create a company account
            </SymphoButton>
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—CORP // 03"
        eyebrow="START HIRING TODAY"
        title="Build your engineering & operations pipeline."
        description="Create your company account in under two minutes or sign in to your existing corporate workspace."
        primaryLabel="Create a company account"
        primaryTo="/for-companies/signup"
        secondaryLabel="Sign in"
        secondaryTo="/login"
      />
    </div>
  );
}

export default ForCompaniesPage;
