import type { ReactNode } from "react";
import { BookOpen, Sparkles, GraduationCap, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

/** One visual language for dashboard, campus and share artwork. */
export function BrandBanner({
  title,
  description,
  eyebrow = "SashaInfinity · Keep discovering",
  children,
  compact = false,
  image,
  headingLevel = "h2",
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  children?: ReactNode;
  compact?: boolean;
  image?: string;
  headingLevel?: "h1" | "h2";
}) {
  const Heading = headingLevel;

  return (
    <section
      className={`brand-banner ${compact ? "brand-banner-compact" : ""}`}
    >
      {image && <img className="brand-banner-cover" src={image} alt="" />}
      <div className="brand-banner-copy">
        <span className="brand-eyebrow">
          <Sparkles size={14} />
          {eyebrow}
        </span>
        <Heading>{title}</Heading>
        {description && <p>{description}</p>}
        {children && <div className="brand-banner-actions">{children}</div>}
      </div>
      <div className="brand-art" aria-hidden="true">
        <span className="brand-art-orbit" />
        <span className="brand-art-orbit second" />
        <span className="brand-art-book">
          <BookOpen size={64} strokeWidth={1.3} />
        </span>
        <span className="brand-art-spark">
          <Sparkles size={25} />
        </span>
        <span className="brand-art-cap">
          <GraduationCap size={28} />
        </span>
        <span className="brand-art-label">Small steps. Lasting skills.</span>
      </div>
    </section>
  );
}

export function WorkspaceBanner({
  pathname,
  role,
}: {
  pathname: string;
  role: string;
}) {
  if (!/\/(dashboard|parent)\/?$/.test(pathname)) return null;
  const teaching = role === "instructor" || role === "spoc";
  const admin = role === "admin" || role === "superadmin";
  return (
    <div className="brand-workspace-banner">
      <BrandBanner
        title={
          teaching
            ? "Make your next lesson their next discovery."
            : admin
              ? "A connected community. A clearer view."
              : "Your next possibility starts with a little progress."
        }
        description={
          teaching
            ? "Bring your ideas to life, support your learners and build a campus that grows together."
            : admin
              ? "Keep your people, learning and daily operations moving forward together."
              : "Come back to your learning, try something hands-on and make today count."
        }
        eyebrow={
          teaching
            ? "Made for the way you teach"
            : "Your learning journey, connected"
        }
      >
        <Link
          className="sf-primary"
          to={
            teaching
              ? "/instructor/courses"
              : admin
                ? "/institutions"
                : "/courses"
          }
        >
          {teaching
            ? "Your courses"
            : admin
              ? "Campus workspaces"
              : "Explore courses"}
          <ArrowUpRight size={16} />
        </Link>
        <Link
          className="brand-text-link"
          to={teaching ? "/institutions" : "/labs"}
        >
          {teaching ? "Open your campus" : "Try a learning lab"} →
        </Link>
      </BrandBanner>
    </div>
  );
}
