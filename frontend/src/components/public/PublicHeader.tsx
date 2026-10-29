import React, { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Search,
  ShoppingCart,
  Menu,
  X,
  ChevronDown,
  User,
  ArrowUpRight,
} from "lucide-react";
import { AccessibilityMenu } from "@/components/a11y/AccessibilityMenu";
import { useAuthStore } from "@/store/auth";
import { useCart } from "@/contexts/CartContext";
import { roleHomePath } from "@/utils/role-routing";

const learnMegaItems = [
  {
    code: "SI—01",
    to: "/courses",
    label: "Courses & Tracks",
    blurb: "Full-stack, AI, cloud & deep-engineering cohorts.",
  },
  {
    code: "SI—02",
    to: "/labs",
    label: "Learning Labs",
    blurb: "Interactive sandboxes, CBSE & engineering simulations.",
  },
  {
    code: "SI—03",
    to: "/library",
    label: "Digital Library",
    blurb: "Curated technical volumes, playbooks & monographs.",
  },
  {
    code: "SI—04",
    to: "/categories",
    label: "Subjects & Triad",
    blurb: "Meiporul, Utporul & Seyappaduporul knowledge taxonomy.",
  },
  {
    code: "SI—05",
    to: "/meiporul-ar",
    label: "Meiporul AR",
    blurb: "Spatial WebGL & augmented reality concept exploration.",
  },
  {
    code: "SI—06",
    to: "/bundles",
    label: "Course Bundles",
    blurb: "Multi-course architectural mastery tracks at cohort value.",
  },
  {
    code: "SI—07",
    to: "/membership",
    label: "Membership",
    blurb: "All-access studio pass for continuous skill evolution.",
  },
];

const communityMegaItems = [
  {
    code: "CM—01",
    to: "/blog",
    label: "Field Notes & Blog",
    blurb: "Essays on engineering pedagogy, AI & systems design.",
  },
  {
    code: "CM—02",
    to: "/hall-of-fame",
    label: "Wall of Fame",
    blurb: "Distinguished builders, fellows & cohort laureates.",
  },
  {
    code: "CM—03",
    to: "/about",
    label: "About SashaInfinity",
    blurb: "Our architectural philosophy, leadership & origins.",
  },
  {
    code: "CM—04",
    to: "/for-companies",
    label: "For Companies",
    blurb: "Hire verified interns, host capstone sprints & talent.",
  },
  {
    code: "CM—05",
    to: "/contact",
    label: "Contact Studio",
    blurb: "Speak with our academic & institutional directors.",
  },
  {
    code: "CM—06",
    to: "/register?role=instructor",
    label: "Become an Instructor",
    blurb: "Lead cohorts and author interactive labs on SashaInfinity.",
  },
];

export default function PublicHeader() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openMenu, setOpenMenu] = useState<"learn" | "community" | null>(null);
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [query, setQuery] = useState("");
  const { user, logout } = useAuthStore();
  const { getItemCount } = useCart();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setMobileOpen(false);
    setOpenMenu(null);
    setWorkspaceOpen(false);
    setSearchOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        setOpenMenu(null);
        setWorkspaceOpen(false);
        setSearchOpen(false);
      }
    };
    const outside = (event: MouseEvent) => {
      if (
        headerRef.current &&
        !headerRef.current.contains(event.target as Node)
      ) {
        setOpenMenu(null);
        setWorkspaceOpen(false);
      }
    };
    document.addEventListener("keydown", close);
    document.addEventListener("click", outside);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("click", outside);
    };
  }, []);

  const dashboard =
    user?.role === "parent" ? "/parent" : roleHomePath(user?.role);
  const count = getItemCount();

  const search = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim()) {
      navigate(`/courses?search=${encodeURIComponent(query.trim())}`);
      setMobileOpen(false);
      setSearchOpen(false);
    }
  };

  return (
    <header
      ref={headerRef}
      style={{
        viewTransitionName: "site-header",
        background: scrolled
          ? "rgba(255, 255, 255, 0.96)"
          : "rgba(255, 255, 255, 0.92)",
        color: "var(--color-ink-900)",
        borderBottom: "1px solid #e4e7ec",
      }}
      className={`sympho-scope sympho-header sticky top-0 z-50 border-b transition-all duration-300 ${
        scrolled
          ? "shadow-[0_8px_26px_-12px_rgba(15,26,46,0.14)]"
          : "shadow-[0_4px_16px_-12px_rgba(15,26,46,0.08)]"
      }`}
    >
      {/* Phones: subtitle + search icon hide below sm so the menu toggle
          and cart stay on-screen (the bar was ~460px wide at 390px). */}
      <div className="container-page flex h-[4.25rem] items-center justify-between gap-2 sm:gap-3">
        {/* SashaInfinity Brand Mark */}
        <Link
          to="/"
          aria-label="SashaInfinity — Home"
          className="group inline-flex shrink-0 items-center gap-2.5 focus-visible:outline-offset-4"
        >
          <span
            aria-hidden="true"
            className="relative grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-xl border border-limestone-300 bg-limestone-100 shadow-[0_3px_10px_rgba(15,26,46,0.08)] transition-transform duration-300 group-hover:scale-105"
          >
            <img
              src="/brand/sasha-logo-small.png?v=lion2"
              alt=""
              className="h-7 w-7 rounded-lg object-contain"
            />
          </span>
          <span className="flex flex-col leading-none">
            <span
              style={{ color: "var(--color-ink-900)" }}
              className="font-display text-[1.02rem] font-bold tracking-[-0.02em]"
            >
              Sasha Infinity
            </span>
            <span
              style={{ color: "#64748b" }}
              className="mt-0.5 hidden font-mono text-[0.72rem] font-semibold tracking-[0.16em] uppercase sm:block"
            >
              Knowledge Architecture
            </span>
          </span>
        </Link>

        {/* Primary Desktop Navigation Capsule */}
        <nav
          aria-label="Primary"
          className="hidden items-center gap-0.5 rounded-full border border-limestone-300/70 bg-limestone-100/95 p-1 shadow-[inset_0_1px_0_#ffffff,0_2px_10px_rgba(15,26,46,0.05)] lg:inline-flex"
        >
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-[#c2410c] text-white shadow-[0_2px_8px_rgba(194,65,12,0.25)]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`
            }
          >
            Home
          </NavLink>

          {/* Learn Mega Dropdown */}
          <div
            className="relative"
            onMouseEnter={() => setOpenMenu("learn")}
            onMouseLeave={() => setOpenMenu(null)}
          >
            <button
              type="button"
              aria-expanded={openMenu === "learn"}
              onClick={() =>
                setOpenMenu((prev) => (prev === "learn" ? null : "learn"))
              }
              className={`inline-flex items-center gap-1 rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                openMenu === "learn"
                  ? "bg-limestone-200 text-[#c2410c]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`}
            >
              <span>Learn</span>
              <ChevronDown
                size={12}
                className={`transition-transform duration-300 ${
                  openMenu === "learn" ? "rotate-180 text-[#c2410c]" : ""
                }`}
              />
            </button>

            <div
              role="region"
              aria-label="Learn submenu"
              className={`absolute top-full left-1/2 z-50 w-[36rem] -translate-x-1/2 pt-2.5 transition-all duration-200 ease-out-expo ${
                openMenu === "learn"
                  ? "visible translate-y-0 opacity-100"
                  : "invisible pointer-events-none -translate-y-1 opacity-0"
              }`}
            >
              <div
                style={{
                  background: "#ffffff",
                  color: "var(--color-ink-900)",
                  border: "1px solid #e4e7ec",
                }}
                className="rounded-2xl p-4 shadow-[0_18px_42px_rgba(15,26,46,0.14)]"
              >
                <div className="mb-3 flex items-center justify-between border-b border-[#eaeef4] pb-2.5 px-1">
                  <span className="font-mono text-[0.72rem] font-bold tracking-widest uppercase text-[#c2410c]">
                    01 — Learning Architecture
                  </span>
                  <Link
                    to="/courses"
                    onClick={() => setOpenMenu(null)}
                    className="inline-flex items-center gap-1 font-mono text-[0.72rem] font-semibold uppercase tracking-wider text-[#c2410c] hover:underline"
                  >
                    All Catalogs
                    <ArrowUpRight size={12} />
                  </Link>
                </div>
                <ul className="grid grid-cols-2 gap-1">
                  {learnMegaItems.map((item) => (
                    <li key={item.to}>
                      <Link
                        to={item.to}
                        onClick={() => setOpenMenu(null)}
                        className="group flex items-start gap-2.5 rounded-xl p-2.5 transition-colors hover:bg-limestone-100"
                      >
                        <span className="mt-0.5 rounded-md bg-limestone-200 px-1.5 py-0.5 font-mono text-[0.72rem] font-bold tracking-wider text-[#c2410c]">
                          {item.code}
                        </span>
                        <span className="flex-1">
                          <span className="flex items-center justify-between font-display text-[0.84rem] font-bold text-ink-900 group-hover:text-[#c2410c]">
                            {item.label}
                            <ArrowUpRight
                              size={13}
                              className="opacity-0 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:opacity-100"
                            />
                          </span>
                          <span className="mt-0.5 block text-[0.75rem] leading-snug text-ink-600">
                            {item.blurb}
                          </span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <NavLink
            to="/courses"
            className={({ isActive }) =>
              `relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-[#c2410c] text-white shadow-[0_2px_8px_rgba(194,65,12,0.25)]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`
            }
          >
            Courses
          </NavLink>

          <NavLink
            to="/labs"
            className={({ isActive }) =>
              `relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-[#c2410c] text-white shadow-[0_2px_8px_rgba(194,65,12,0.25)]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`
            }
          >
            Labs
          </NavLink>

          <NavLink
            to="/campus"
            className={({ isActive }) =>
              `relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-[#c2410c] text-white shadow-[0_2px_8px_rgba(194,65,12,0.25)]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`
            }
          >
            Institutions
          </NavLink>

          <NavLink
            to="/internships"
            className={({ isActive }) =>
              `relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-[#c2410c] text-white shadow-[0_2px_8px_rgba(194,65,12,0.25)]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`
            }
          >
            Internships
          </NavLink>

          {/* Community Mega Dropdown */}
          <div
            className="relative"
            onMouseEnter={() => setOpenMenu("community")}
            onMouseLeave={() => setOpenMenu(null)}
          >
            <button
              type="button"
              aria-expanded={openMenu === "community"}
              onClick={() =>
                setOpenMenu((prev) =>
                  prev === "community" ? null : "community"
                )
              }
              className={`inline-flex items-center gap-1 rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold transition-all duration-200 ${
                openMenu === "community"
                  ? "bg-limestone-200 text-[#c2410c]"
                  : "text-ink-700 hover:bg-white hover:text-[#c2410c]"
              }`}
            >
              <span>Community</span>
              <ChevronDown
                size={12}
                className={`transition-transform duration-300 ${
                  openMenu === "community" ? "rotate-180 text-[#c2410c]" : ""
                }`}
              />
            </button>

            <div
              role="region"
              aria-label="Community submenu"
              className={`absolute top-full right-0 z-50 w-[32rem] pt-2.5 transition-all duration-200 ease-out-expo ${
                openMenu === "community"
                  ? "visible translate-y-0 opacity-100"
                  : "invisible pointer-events-none -translate-y-1 opacity-0"
              }`}
            >
              <div
                style={{
                  background: "#ffffff",
                  color: "var(--color-ink-900)",
                  border: "1px solid #e4e7ec",
                }}
                className="rounded-2xl p-4 shadow-[0_18px_42px_rgba(15,26,46,0.14)]"
              >
                <div className="mb-3 flex items-center justify-between border-b border-[#eaeef4] pb-2.5 px-1">
                  <span className="font-mono text-[0.72rem] font-bold tracking-widest uppercase text-[#c2410c]">
                    02 — Community & Discourse
                  </span>
                  <Link
                    to="/hall-of-fame"
                    onClick={() => setOpenMenu(null)}
                    className="inline-flex items-center gap-1 font-mono text-[0.72rem] font-semibold uppercase tracking-wider text-[#c2410c] hover:underline"
                  >
                    Wall of Fame
                    <ArrowUpRight size={12} />
                  </Link>
                </div>
                <ul className="grid grid-cols-2 gap-1">
                  {communityMegaItems.map((item) => (
                    <li key={item.to}>
                      <Link
                        to={item.to}
                        onClick={() => setOpenMenu(null)}
                        className="group flex items-start gap-2.5 rounded-xl p-2.5 transition-colors hover:bg-limestone-100"
                      >
                        <span className="mt-0.5 rounded-md bg-limestone-200 px-1.5 py-0.5 font-mono text-[0.72rem] font-bold tracking-wider text-[#c2410c]">
                          {item.code}
                        </span>
                        <span className="flex-1">
                          <span className="flex items-center justify-between font-display text-[0.84rem] font-bold text-ink-900 group-hover:text-[#c2410c]">
                            {item.label}
                            <ArrowUpRight
                              size={13}
                              className="opacity-0 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:opacity-100"
                            />
                          </span>
                          <span className="mt-0.5 block text-[0.75rem] leading-snug text-ink-600">
                            {item.blurb}
                          </span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </nav>

        {/* Right Utility & Action Rail */}
        <div className="flex shrink-0 items-center gap-2">
          {/* Compact Search Pill on 2XL or Icon Toggle */}
          <form
            onSubmit={search}
            role="search"
            className="hidden items-center gap-1.5 rounded-full border border-limestone-300/75 bg-limestone-100 px-3 py-1.5 shadow-[inset_0_1px_0_#ffffff] 2xl:flex"
          >
            <Search size={13} className="text-[#64748b]" />
            <input
              aria-label="Search courses"
              placeholder="Search courses..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-28 bg-transparent text-xs text-ink-900 placeholder:text-[#64748b] focus:outline-none"
            />
          </form>

          <button
            type="button"
            aria-label="Search catalog"
            onClick={() => setSearchOpen((v) => !v)}
            className={`hidden h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-colors sm:inline-flex 2xl:hidden ${
              searchOpen
                ? "border-[#9a390b] bg-limestone-200 text-[#c2410c]"
                : "border-limestone-300/80 bg-limestone-100 text-ink-900 hover:border-[#c2410c] hover:text-[#c2410c]"
            }`}
          >
            <Search size={15} />
          </button>

          <AccessibilityMenu />

          <Link
            to="/cart"
            aria-label={`Cart, ${count} items`}
            className="relative inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-limestone-300/80 bg-limestone-100 text-ink-900 transition-colors hover:border-[#c2410c] hover:bg-limestone-200 hover:text-ink-900"
          >
            <ShoppingCart size={15} />
            {count > 0 && (
              <span
                style={{
                  background: "#c2410c",
                  color: "#ffffff",
                }}
                className="absolute -top-1 -right-1 grid h-4 w-4 place-items-center rounded-full font-mono text-[0.72rem] font-bold"
              >
                {count}
              </span>
            )}
          </Link>

          {user ? (
            <div className="relative">
              <button
                type="button"
                aria-expanded={workspaceOpen}
                onClick={() => setWorkspaceOpen((v) => !v)}
                style={{
                  background: "#17233a",
                  color: "#ffffff",
                  border: "1px solid #17233a",
                }}
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-bold shadow-[0_4px_14px_rgba(15,26,46,0.18)] transition-colors hover:!bg-[#1e2d48]"
              >
                <User size={13} />
                <span>Workspace</span>
                <ChevronDown
                  size={11}
                  className={`transition-transform duration-200 ${
                    workspaceOpen ? "rotate-180" : ""
                  }`}
                />
              </button>
              {workspaceOpen && (
                <div
                  style={{
                    background: "#ffffff",
                    color: "var(--color-ink-900)",
                  }}
                  className="absolute right-0 z-50 mt-2 w-44 rounded-2xl border border-[#e4e7ec] p-1.5 shadow-[0_14px_34px_rgba(15,26,46,0.14)]"
                >
                  <Link
                    to={dashboard}
                    onClick={() => setWorkspaceOpen(false)}
                    className="block rounded-lg px-3 py-1.5 text-xs font-semibold text-ink-900 hover:bg-limestone-100 hover:text-[#c2410c]"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/profile"
                    onClick={() => setWorkspaceOpen(false)}
                    className="block rounded-lg px-3 py-1.5 text-xs font-semibold text-ink-900 hover:bg-limestone-100 hover:text-[#c2410c]"
                  >
                    Profile
                  </Link>
                  <Link
                    to="/settings"
                    onClick={() => setWorkspaceOpen(false)}
                    className="block rounded-lg px-3 py-1.5 text-xs font-semibold text-ink-900 hover:bg-limestone-100 hover:text-[#c2410c]"
                  >
                    Settings
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setWorkspaceOpen(false);
                      navigate("/");
                      setMobileOpen(false);
                    }}
                    className="mt-1 w-full rounded-lg border-t border-[#eaeef4] px-3 py-1.5 text-left text-xs font-bold text-[#c2410c] hover:bg-limestone-100"
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="hidden items-center gap-1.5 sm:flex">
              <Link
                to="/login"
                className="rounded-full border border-[#cbd5e1] bg-white px-3.5 py-1.5 text-xs font-semibold text-[#17233a] transition-colors hover:border-[#17233a] hover:bg-[#f4f6fa]"
              >
                Log in
              </Link>
              <Link
                to="/register"
                style={{
                  background: "#c2410c",
                  color: "#ffffff",
                  border: "1px solid #c2410c",
                }}
                className="inline-flex items-center gap-1 rounded-full px-3.5 py-1.5 text-xs font-bold shadow-[0_4px_14px_rgba(194,65,12,0.25)] transition-all hover:brightness-110"
              >
                <span>Sign up</span>
                <ArrowUpRight size={12} />
              </Link>
            </div>
          )}

          <button
            type="button"
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
            aria-controls="public-mobile-nav"
            onClick={() => setMobileOpen((v) => !v)}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-limestone-300 bg-limestone-100 text-ink-900 lg:hidden"
          >
            {mobileOpen ? <X size={17} /> : <Menu size={17} />}
          </button>
        </div>
      </div>

      {/* Expandable Search Bar */}
      {searchOpen && (
        <div
          style={{
            background: "#ffffff",
            color: "var(--color-ink-900)",
          }}
          className="border-t border-[#eaeef4] py-2.5 shadow-md 2xl:hidden"
        >
          <div className="container-page">
            <form onSubmit={search} className="flex items-center gap-2.5">
              <Search size={15} className="text-[#64748b]" />
              <input
                aria-label="Search courses"
                placeholder="Search courses, interactive labs, subjects..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 bg-transparent text-xs text-ink-900 focus:outline-none sm:text-sm"
                autoFocus
              />
              <button
                type="submit"
                style={{
                  background: "#c2410c",
                  color: "#ffffff",
                }}
                className="rounded-full px-3.5 py-1 font-mono text-[0.72rem] font-bold uppercase"
              >
                Search
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Mobile Navigation Drawer */}
      {mobileOpen && (
        <nav
          id="public-mobile-nav"
          aria-label="Mobile navigation"
          style={{
            background: "#ffffff",
            color: "var(--color-ink-900)",
          }}
          className="fixed inset-x-0 top-[4.25rem] bottom-0 z-50 overflow-y-auto border-t border-[#e4e7ec] lg:hidden"
        >
          <div className="container-page flex min-h-full flex-col justify-between py-6">
            <div>
              <form
                onSubmit={search}
                className="mb-6 flex items-center gap-2.5 rounded-xl border border-limestone-300 bg-limestone-100 px-3.5 py-2.5"
              >
                <Search size={15} className="text-[#64748b]" />
                <input
                  aria-label="Search courses on mobile"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search courses..."
                  className="flex-1 bg-transparent text-xs text-ink-900 placeholder:text-[#64748b] focus:outline-none"
                />
                <button
                  type="submit"
                  className="font-mono text-label font-bold text-[#c2410c]"
                >
                  Search
                </button>
              </form>

              <p className="sheet-label mb-3 text-[#c2410c]">
                01 — Learn & Practice
              </p>
              <ul className="divide-y divide-[#eaeef4] border-y border-[#eaeef4]">
                {learnMegaItems.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className="flex items-baseline justify-between py-2.5 font-display text-base font-bold text-ink-900 hover:text-[#c2410c]"
                    >
                      <span>{item.label}</span>
                      <span className="font-mono text-[0.72rem] font-semibold text-[#c2410c]">
                        {item.code}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>

              <p className="sheet-label mt-6 mb-3 text-[#c2410c]">
                02 — Institutions, Careers & Community
              </p>
              <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <li>
                  <Link
                    to="/campus"
                    className="block rounded-xl border border-limestone-300/70 bg-limestone-100 p-2.5 text-xs font-semibold text-ink-900 hover:border-[#c2410c]"
                  >
                    For Institutions (Campus OS)
                  </Link>
                </li>
                <li>
                  <Link
                    to="/internships"
                    className="block rounded-xl border border-limestone-300/70 bg-limestone-100 p-2.5 text-xs font-semibold text-ink-900 hover:border-[#c2410c]"
                  >
                    Internships Marketplace
                  </Link>
                </li>
                {communityMegaItems.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className="block rounded-xl border border-limestone-300/70 bg-limestone-100 p-2.5 text-xs font-semibold text-ink-900 hover:border-[#c2410c]"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {!user && (
              <div className="mt-6 flex flex-wrap gap-2.5 border-t border-[#eaeef4] pt-5">
                <Link
                  to="/login"
                  className="rounded-full border border-[#cbd5e1] bg-white px-4 py-2 text-xs font-semibold text-[#17233a]"
                >
                  Log in
                </Link>
                <Link
                  to="/register"
                  style={{
                    background: "#c2410c",
                    color: "#ffffff",
                  }}
                  className="rounded-full px-4 py-2 text-xs font-bold"
                >
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
