import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
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
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { Button } from "@/components/ui/button";

const outcomes = [
  {
    icon: Users,
    title: "Admissions to enrollment",
    text: "Move every applicant through review, documents, offers and onboarding in one clear pipeline.",
  },
  {
    icon: WalletCards,
    title: "Fees without spreadsheet drift",
    text: "Create plans, installments, concessions and receipts with a trustworthy student ledger.",
  },
  {
    icon: BarChart3,
    title: "A useful start to every day",
    text: "Give each role one action centre for classes, dues, grading, attendance and follow-ups.",
  },
  {
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
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
}

export default function CampusForInstitutionsPage() {
  const [params] = useSearchParams();
  const [form, setForm] = useState(initial);
  const [submitted, setSubmitted] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [learners, setLearners] = useState(800);
  const [minutes, setMinutes] = useState(12);
  const plans = useQuery({ queryKey: ["campus-plans"], queryFn: campusGrowthApi.plans });
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
    <div className="campus-growth-page">
      <Helmet>
        <title>Campus OS for schools and colleges · SashaInfinity</title>
        <meta
          name="description"
          content="Run admissions, learning, student finance and family communication in one connected campus workspace."
        />
      </Helmet>

      <div className="campus-growth-wrap">
        <BrandBanner
          headingLevel="h1"
          eyebrow="SashaInfinity Campus OS"
          title="One beautiful workspace for the whole student journey."
          description="Bring admissions, teaching, fees, progress and family communication together—with the calm, clear experience your campus deserves."
        >
          <a className="sf-primary" href="#campus-demo">
            Book a campus walkthrough <ArrowRight size={16} />
          </a>
          <Link className="brand-text-link" to="/register?role=instructor">
            Start your workspace →
          </Link>
        </BrandBanner>

        <section className="campus-growth-proof" aria-label="Campus platform highlights">
          <span><ShieldCheck size={17} /> Role-aware access</span>
          <span><Sparkles size={17} /> Guided daily actions</span>
          <span><HeartHandshake size={17} /> Built for schools and colleges</span>
        </section>

        <section className="campus-growth-section">
          <div className="campus-growth-heading">
            <span className="campus-eyebrow"><GraduationCap size={14} /> Connected by design</span>
            <h2>Fewer hand-offs. A clearer campus.</h2>
            <p>Each team gets the information and next action that belongs to them.</p>
          </div>
          <div className="campus-growth-grid">
            {outcomes.map(({ icon: Icon, title, text }) => (
              <article className="campus-growth-card" key={title}>
                <span className="campus-icon"><Icon size={21} /></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="campus-growth-roi">
          <div>
            <span className="campus-eyebrow"><BarChart3 size={14} /> Capacity calculator</span>
            <h2>Give routine administration back to your team.</h2>
            <p>Estimate the staff time represented by repeated monthly updates, reminders and reconciliation.</p>
            <label>
              Learners
              <input type="range" min="100" max="10000" step="100" value={learners} onChange={(e) => setLearners(Number(e.target.value))} />
              <strong>{formatHours(learners)}</strong>
            </label>
            <label>
              Minutes of repeated work per learner
              <input type="range" min="2" max="30" step="1" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
              <strong>{minutes} min</strong>
            </label>
          </div>
          <div className="campus-growth-roi-result">
            <span>Routine-work capacity each month</span>
            <strong>{formatHours(hours)} hours</strong>
            <p>This is a planning estimate. Your walkthrough will map real workflows and measurable targets.</p>
          </div>
        </section>

        <section className="campus-growth-section" id="plans">
          <div className="campus-growth-heading">
            <span className="campus-eyebrow"><Building2 size={14} /> Plans that grow with you</span>
            <h2>Start with your campus today.</h2>
          </div>
          {plans.isError ? (
            <div className="campus-error" role="alert">Plans are temporarily unavailable. <button onClick={() => void plans.refetch()}>Try again</button></div>
          ) : (
            <div className="campus-growth-plans" aria-busy={plans.isPending}>
              {(plans.data || []).map((plan) => (
                <article className={`campus-growth-plan ${plan.featured ? "is-featured" : ""}`} key={plan.key}>
                  {plan.featured && <span className="campus-chip" data-tone="success">Most popular</span>}
                  <h3>{plan.name}</h3>
                  <p>{plan.description}</p>
                  <strong>{plan.price_label}</strong>
                  <ul>{plan.features.map((feature) => <li key={feature}><Check size={16} /> {feature}</li>)}</ul>
                  <a href="#campus-demo" onClick={() => setForm((value) => ({ ...value, interest: plan.key === "starter" ? "trial" : "quote" }))}>Choose {plan.name} <ArrowRight size={15} /></a>
                </article>
              ))}
              {plans.isPending && [1, 2, 3].map((item) => <div className="campus-skeleton" key={item} />)}
            </div>
          )}
        </section>

        <section className="campus-growth-contact" id="campus-demo">
          <div>
            <span className="campus-eyebrow"><Sparkles size={14} /> Your campus, thoughtfully set up</span>
            <h2>See SashaInfinity with your real workflow.</h2>
            <p>Tell us about your institution. We’ll prepare a focused walkthrough for your team.</p>
          </div>
          {submitted ? (
            <div className="campus-growth-thanks" role="status">
              <span className="campus-icon"><Check size={22} /></span>
              <h3>Your request is ready.</h3>
              <p>Reference <strong>{submitted}</strong>. Our campus team can now follow up with you.</p>
              <Button variant="outline" onClick={() => { setSubmitted(undefined); setForm(initial); }}>Send another request</Button>
            </div>
          ) : (
            <form className="campus-form campus-growth-form" onSubmit={submit}>
              <div className="campus-form-grid">
                <label>Your name<input required minLength={2} value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} /></label>
                <label>Work email<input required type="email" value={form.work_email} onChange={(e) => setForm({ ...form, work_email: e.target.value })} /></label>
                <label>Institution<input required minLength={2} value={form.institution_name} onChange={(e) => setForm({ ...form, institution_name: e.target.value })} /></label>
                <label>Phone<input inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
                <label>Institution type<select value={form.institution_kind} onChange={(e) => setForm({ ...form, institution_kind: e.target.value as CampusLeadInput["institution_kind"] })}><option value="school">School</option><option value="college">College</option><option value="university">University</option><option value="training">Training institute</option></select></label>
                <label>Learners<select value={form.learner_count} onChange={(e) => setForm({ ...form, learner_count: e.target.value as CampusLeadInput["learner_count"] })}><option value="under-100">Under 100</option><option value="100-499">100–499</option><option value="500-1999">500–1,999</option><option value="2000-plus">2,000+</option></select></label>
              </div>
              <label>What would you like to explore?<select value={form.interest} onChange={(e) => setForm({ ...form, interest: e.target.value as CampusLeadInput["interest"] })}><option value="demo">Guided demo</option><option value="trial">Trial workspace</option><option value="quote">Institution quote</option></select></label>
              <label>What should we prepare?<textarea rows={4} maxLength={2000} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Admissions, fee collection, learning delivery, integrations…" /></label>
              <label className="campus-check"><input required type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} /><span>I agree that SashaInfinity may contact me about this request. I can withdraw this permission at any time.</span></label>
              <label className="campus-honeypot" aria-hidden="true">Website<input tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} /></label>
              <Button type="submit" loading={busy} rightIcon={<ArrowRight size={16} />}>Request my walkthrough</Button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}

