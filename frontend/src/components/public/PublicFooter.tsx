import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Instagram, Linkedin, MapPin, Phone, Clock } from "lucide-react";
import { api } from "@/api/axios";

interface Course {
  id: number;
  title: string;
  category: string;
  slug?: string;
  post_name?: string;
}

type FooterLink = { to: string; label: string; external?: boolean };

const ECOSYSTEM: FooterLink[] = [
  { to: "/courses", label: "Courses Catalog" },
  { to: "/labs", label: "Learning Labs" },
  { to: "/library", label: "Digital Library" },
  { to: "/categories", label: "Subjects & Triad" },
  { to: "/meiporul-ar", label: "Meiporul AR" },
  { to: "/bundles", label: "Course Bundles" },
  { to: "/membership", label: "Membership" },
];

// Privacy Policy and Terms live in the bottom bar.
const RESOURCES: FooterLink[] = [
  { to: "/about", label: "About Us" },
  { to: "/hall-of-fame", label: "Wall of Fame" },
  { to: "/blog", label: "Field Notes (Blog)" },
  { to: "/for-companies", label: "For Companies" },
  { to: "/contact", label: "Contact" },
  { to: "/refund-policy", label: "Refund and Returns" },
  { to: "/shipping", label: "Shipping & Delivery" },
];

// Navy footer palette (matches the dashboard sidebar and dark page heroes):
// body #cbd5e1 (12:1 on #0f1a2e), muted #94a3b8 (7:1), headings #fdba74.
const linkClass =
  "rounded-sm !text-[#cbd5e1] transition-colors hover:!text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#fdba74]";
const headingClass =
  "font-mono text-[0.72rem] font-bold uppercase tracking-[0.16em] !text-[#fdba74]";
const socialClass =
  "inline-flex size-10 items-center justify-center rounded-full border border-white/15 bg-white/5 !text-[#e2e8f0] transition-colors hover:border-[#c2410c] hover:bg-[#c2410c] hover:!text-white";

function LinkList({ items }: { items: FooterLink[] }) {
  return (
    <ul className="mt-4 space-y-2.5 text-sm font-medium">
      {items.map((item) => (
        <li key={item.to} className="min-w-0">
          <Link
            to={item.to}
            className={`inline-flex max-w-full items-center gap-1 ${linkClass}`}
          >
            <span className="truncate">{item.label}</span>
            {item.external && (
              <ArrowUpRight size={12} className="shrink-0" aria-hidden="true" />
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}

const PublicFooter = () => {
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await api.get("/courses/", {
          params: {
            page: 1,
            page_size: 4,
          },
        });
        setCourses(response.data.courses || []);
      } catch (error) {
        console.error("Error fetching courses for footer:", error);
      }
    };

    fetchCourses();
  }, []);

  const featured: FooterLink[] = [
    ...(courses.length > 0
      ? courses.map((course) => ({
          to: `/courses/${course.slug || course.post_name || course.id}`,
          label: course.title,
        }))
      : [{ to: "/courses", label: "View All Courses" }]),
    { to: "/campus", label: "Campus OS for Institutions", external: true },
    { to: "/internships", label: "Verified Internships", external: true },
  ];

  return (
    <footer
      style={{
        background: "#0f1a2e",
        backgroundColor: "#0f1a2e",
        color: "#cbd5e1",
        borderTop: "3px solid #c2410c",
      }}
      className="sympho-scope sympho-footer relative overflow-hidden"
    >
      <div className="container-page pt-12 pb-8 lg:pt-16">
        <div className="grid grid-cols-1 gap-10 pb-10 lg:grid-cols-12 lg:gap-12">
          {/* Brand + headquarters */}
          <div className="lg:col-span-4">
            <Link to="/" className="inline-flex items-center gap-3">
              <span
                aria-hidden="true"
                className="grid size-11 place-items-center overflow-hidden rounded-xl bg-white shadow-[0_6px_18px_rgba(0,0,0,0.25)]"
              >
                <img
                  src="/brand/sasha-logo-small.png?v=lion2"
                  alt=""
                  className="size-8 rounded-lg object-contain"
                />
              </span>
              <span className="flex flex-col leading-none">
                <span className="font-display text-lg font-bold tracking-tight !text-white">
                  Sasha Infinity
                </span>
                <span className="mt-1 font-mono text-[0.62rem] font-semibold uppercase tracking-[0.2em] !text-[#94a3b8]">
                  Knowledge Architecture
                </span>
              </span>
            </Link>
            <p className="mt-5 max-w-sm text-sm leading-relaxed !text-[#cbd5e1]">
              Engineering-grade learning management, interactive simulation
              labs, spatial AR pedagogy, and verified internship cohorts built
              for ambitious learners and institutions.
            </p>

            <ul className="mt-6 space-y-3 text-sm">
              <li className="flex gap-3">
                <MapPin size={16} className="mt-0.5 shrink-0 text-[#fdba74]" aria-hidden="true" />
                <span className="!text-[#cbd5e1]">
                  Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu
                  636004
                </span>
              </li>
              <li className="flex gap-3">
                <Phone size={16} className="mt-0.5 shrink-0 text-[#fdba74]" aria-hidden="true" />
                <a href="tel:+918438740893" className={`font-semibold ${linkClass}`}>
                  +91 84387 40893
                </a>
              </li>
              <li className="flex gap-3">
                <Clock size={16} className="mt-0.5 shrink-0 text-[#fdba74]" aria-hidden="true" />
                <span className="!text-[#cbd5e1]">Mon – Sat · 9:00 AM – 7:00 PM IST</span>
              </li>
            </ul>

            <div className="mt-6 flex items-center gap-3">
              <a
                href="https://www.instagram.com/sashainfinityedu?igsh=cmVycTFseHRjYmw2"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram"
                className={socialClass}
              >
                <Instagram size={17} />
              </a>
              <a
                href="https://www.linkedin.com/company/sashainfinity/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
                className={socialClass}
              >
                <Linkedin size={17} />
              </a>
            </div>
          </div>

          {/* Sitemap: two columns on phones (programs full width), three from sm */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:col-span-8 lg:pl-8">
            <nav aria-label="Ecosystem" className="!p-0">
              <h3 className={headingClass}>Ecosystem</h3>
              <LinkList items={ECOSYSTEM} />
            </nav>
            <nav aria-label="Resources" className="!p-0 sm:order-last">
              <h3 className={headingClass}>Resources</h3>
              <LinkList items={RESOURCES} />
            </nav>
            <nav aria-label="Featured programs" className="col-span-2 min-w-0 !p-0 sm:col-span-1">
              <h3 className={headingClass}>Featured Programs</h3>
              <LinkList items={featured} />
            </nav>
          </div>
        </div>

        {/* Copyright. Opted out of auto scroll-reveal: at the very bottom of
            the page it never crossed the observer threshold and stayed hidden. */}
        <div data-no-auto-reveal className="flex flex-col gap-3 border-t border-white/10 pt-6 text-xs sm:flex-row sm:items-center sm:justify-between sm:pr-14">
          <p className="font-medium !text-[#94a3b8]">
            © {new Date().getFullYear()} Sashainfinity. All rights reserved.
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 font-medium">
            <Link to="/privacy" className={linkClass}>
              Privacy Policy
            </Link>
            <Link to="/terms" className={linkClass}>
              Terms & Conditions
            </Link>
            <span className="font-mono text-[0.68rem] font-semibold !text-[#94a3b8]">
              SALEM · 11.6643° N, 78.1460° E
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default PublicFooter;
