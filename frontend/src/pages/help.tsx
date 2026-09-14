import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Building2,
  ChevronRight,
  HelpCircle,
  GraduationCap,
  MessageCircle,
  Search,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import { Helmet } from "react-helmet-async";

import { BrandBanner } from "@/components/design-system/BrandBanner";

const articles = [
  { category: "Getting started", icon: GraduationCap, title: "Create your account and choose a workspace", text: "Set up your profile, verify your email and open the dashboard for your role.", href: "/register" },
  { category: "Learning", icon: BookOpen, title: "Find courses, assignments and results", text: "Continue lessons, submit work and see your learning progress from one place.", href: "/courses" },
  { category: "Campus", icon: Building2, title: "Set up a school or college", text: "Create an institution, invite your team, add batches and connect courses.", href: "/institutions" },
  { category: "Campus", icon: Building2, title: "Manage admissions and enrollment", text: "Review applications, verify documents, send offers and convert accepted applicants.", href: "/institutions" },
  { category: "Finance", icon: WalletCards, title: "Understand plans, invoices and student fees", text: "See subscriptions, payment recovery, fee ledgers, dues and receipts.", href: "/institutions" },
  { category: "Communication", icon: MessageCircle, title: "Control WhatsApp communication", text: "Confirm or withdraw your account-wide permission and understand delivery status.", href: "/communication-preferences" },
  { category: "Privacy and access", icon: ShieldCheck, title: "Manage privacy, consent and account security", text: "Review your preferences, security settings and privacy choices.", href: "/settings" },
];

export default function HelpPage() {
  const [query, setQuery] = useState("");
  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return articles;
    return articles.filter((article) =>
      `${article.category} ${article.title} ${article.text}`.toLowerCase().includes(term),
    );
  }, [query]);

  return (
    <div className="campus-growth-page">
      <Helmet><title>Help centre · SashaInfinity</title></Helmet>
      <div className="campus-growth-wrap">
        <BrandBanner
          headingLevel="h1"
          eyebrow="SashaInfinity Help Centre"
          title="What would you like to do?"
          description="Find the shortest path to your next step across learning, teaching and campus operations."
          compact
        />
        <section className="campus-panel help-search-panel">
          <label className="help-search">
            <Search size={20} />
            <span className="sr-only">Search help</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search setup, admissions, fees, WhatsApp…" autoFocus />
          </label>
        </section>
        <section className="help-results" aria-live="polite">
          {matches.map(({ icon: Icon, ...article }) => (
            <Link className="campus-panel help-card" to={article.href} key={article.title}>
              <span className="campus-icon"><Icon size={20} /></span>
              <span><small>{article.category}</small><strong>{article.title}</strong><p>{article.text}</p></span>
              <ChevronRight size={19} />
            </Link>
          ))}
          {!matches.length && (
            <div className="campus-panel campus-empty">
              <span className="campus-icon"><HelpCircle size={22} /></span>
              <h2>No matching guide yet</h2>
              <p>Try a shorter phrase, or ask the SashaInfinity team for help.</p>
              <Link className="sf-primary" to="/contact">Contact support</Link>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
