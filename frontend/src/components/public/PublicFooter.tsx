import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Instagram, Linkedin } from "lucide-react";
import { api } from "@/api/axios";

interface Course {
  id: number;
  title: string;
  category: string;
  slug?: string;
  post_name?: string;
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

  return (
    <footer
      style={{
        background: "#ffffff",
        backgroundColor: "#ffffff",
        color: "#442714",
        borderTop: "1px solid rgba(157, 85, 36, 0.16)",
      }}
      className="sympho-scope sympho-footer relative overflow-hidden bg-white"
    >
      <div className="container-page pt-12 pb-10 lg:pt-16">
        {/* 12-Col Sitemap & Headquarters */}
        <div className="grid grid-cols-1 gap-12 pb-12 md:grid-cols-2 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <Link to="/" className="inline-flex items-center gap-3">
              <span
                aria-hidden="true"
                className="relative grid size-10 place-items-center overflow-hidden rounded-xl border border-[#ffbe86]/80 bg-[#fffdf9] shadow-[0_6px_18px_rgba(179,99,24,0.14)]"
              >
                <img
                  src="/brand/sasha-logo-small.png?v=lion2"
                  alt=""
                  className="size-8 rounded-lg object-contain"
                />
              </span>
              <span className="flex flex-col leading-none">
                <span className="font-display text-lg font-bold tracking-tight text-[#442714]">
                  Sasha Infinity
                </span>
                <span className="mt-0.5 font-mono text-[0.62rem] font-semibold tracking-[0.2em] uppercase text-[#9a390b]">
                  Knowledge Architecture
                </span>
              </span>
            </Link>
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-[#5c3820]">
              Engineering-grade learning management, interactive simulation
              labs, spatial AR pedagogy, and verified internship cohorts built
              for ambitious learners and institutions.
            </p>
            <dl className="mt-6 space-y-2.5 text-xs text-[#75543e]">
              <div className="flex gap-3">
                <dt className="w-16 font-mono font-bold uppercase text-[#853b14]">
                  Studio
                </dt>
                <dd className="font-medium text-[#442714]">
                  Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu
                  636004
                </dd>
              </div>
              <div className="flex gap-3">
                <dt className="w-16 font-mono font-bold uppercase text-[#853b14]">
                  Direct
                </dt>
                <dd>
                  <a
                    href="tel:+918438740893"
                    className="font-semibold text-[#442714] hover:text-[#9a390b]"
                  >
                    +91 8438740893
                  </a>
                </dd>
              </div>
              <div className="flex gap-3">
                <dt className="w-16 font-mono font-bold uppercase text-[#853b14]">
                  Hours
                </dt>
                <dd className="font-medium text-[#442714]">
                  Mon – Sat · 9:00 AM – 7:00 PM IST
                </dd>
              </div>
            </dl>

            <div className="mt-6 flex items-center gap-3">
              <a
                href="https://www.instagram.com/sashainfinityedu?igsh=cmVycTFseHRjYmw2"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram"
                className="inline-flex size-9 items-center justify-center rounded-pill border border-[#9d5524]/25 bg-[#fffdf9] text-[#442714] transition-colors hover:border-[#9a390b] hover:bg-[#ffe8cf] hover:text-[#9a390b]"
              >
                <Instagram size={16} />
              </a>
              <a
                href="https://www.linkedin.com/company/sashainfinity/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
                className="inline-flex size-9 items-center justify-center rounded-pill border border-[#9d5524]/25 bg-[#fffdf9] text-[#442714] transition-colors hover:border-[#9a390b] hover:bg-[#ffe8cf] hover:text-[#9a390b]"
              >
                <Linkedin size={16} />
              </a>
            </div>
          </div>

          {/* Column 1: Ecosystem */}
          <div className="lg:col-span-2 lg:col-start-6">
            <h3 className="font-mono text-label font-bold text-[#853b14]">
              Ecosystem
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm font-medium">
              <li>
                <Link
                  to="/courses"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Courses Catalog
                </Link>
              </li>
              <li>
                <Link
                  to="/labs"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Learning Labs
                </Link>
              </li>
              <li>
                <Link
                  to="/library"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Digital Library
                </Link>
              </li>
              <li>
                <Link
                  to="/categories"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Subjects & Triad
                </Link>
              </li>
              <li>
                <Link
                  to="/meiporul-ar"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Meiporul AR
                </Link>
              </li>
              <li>
                <Link
                  to="/bundles"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Course Bundles
                </Link>
              </li>
              <li>
                <Link
                  to="/membership"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Membership
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 2: Featured Courses */}
          <div className="lg:col-span-3">
            <h3 className="font-mono text-label font-bold text-[#853b14]">
              Featured Programs
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm font-medium">
              {courses.length > 0 ? (
                courses.map((course) => (
                  <li key={course.id}>
                    <Link
                      to={`/courses/${
                        course.slug || course.post_name || course.id
                      }`}
                      className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim line-clamp-1"
                    >
                      {course.title}
                    </Link>
                  </li>
                ))
              ) : (
                <li>
                  <Link
                    to="/courses"
                    className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                  >
                    View All Courses
                  </Link>
                </li>
              )}
              <li>
                <Link
                  to="/campus"
                  className="inline-flex items-center gap-1 text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Campus OS for Institutions
                  <ArrowUpRight size={12} />
                </Link>
              </li>
              <li>
                <Link
                  to="/internships"
                  className="inline-flex items-center gap-1 text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Verified Internships
                  <ArrowUpRight size={12} />
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Resources & Governance */}
          <div className="lg:col-span-2">
            <h3 className="font-mono text-label font-bold text-[#853b14]">
              Resources
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm font-medium">
              <li>
                <Link
                  to="/about"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  About Us
                </Link>
              </li>
              <li>
                <Link
                  to="/hall-of-fame"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Wall of Fame
                </Link>
              </li>
              <li>
                <Link
                  to="/blog"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Field Notes (Blog)
                </Link>
              </li>
              <li>
                <Link
                  to="/for-companies"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  For Companies
                </Link>
              </li>
              <li>
                <Link
                  to="/contact"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Contact
                </Link>
              </li>
              <li>
                <Link
                  to="/refund-policy"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Refund and Returns
                </Link>
              </li>
              <li>
                <Link
                  to="/terms"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Conditions
                </Link>
              </li>
              <li>
                <Link
                  to="/privacy"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link
                  to="/shipping"
                  className="text-[#5c3820] transition-colors hover:text-[#9a390b] link-dim"
                >
                  Shipping & Delivery
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright Ledger */}
        <div className="flex flex-col gap-4 border-t border-[#9d5524]/18 pt-6 text-xs text-[#75543e] sm:flex-row sm:items-center sm:justify-between">
          <p className="font-medium text-[#442714]">
            Copyright © {new Date().getFullYear()} Sashainfinity. All rights
            reserved.
          </p>
          <div className="flex flex-wrap items-center gap-6 font-medium">
            <Link
              to="/privacy"
              className="text-[#5c3820] transition-colors hover:text-[#9a390b]"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className="text-[#5c3820] transition-colors hover:text-[#9a390b]"
            >
              Terms & Conditions
            </Link>
            <span className="font-mono text-[0.68rem] font-semibold text-[#9a390b]">
              SALEM · 11.6643° N, 78.1460° E
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default PublicFooter;
