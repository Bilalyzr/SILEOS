/**
 * Wall of Fame - public page celebrating company staff.
 *
 * Everyone is shown EQUALLY. No ranking, no positions.
 * Glassmorphism + 3D tilt portrait cards: big photo on top, frosted info
 * below, and the card tilts toward your cursor with real perspective.
 *
 * EDIT THE PEOPLE HERE - no backend, no fetching.
 * The HALL_OF_FAME array below is the source of truth.
 * Add / remove people freely - order does NOT matter (no ranking).
 *
 * Each entry:
 *   name        person's display name            (required)
 *   role        their job title / designation    (required)
 *   company     company they work for            (required)
 *   photo       URL of their photo (or empty ''  -> initials avatar)
 *   tenure      how long they've been there      (e.g. "5 years")
 *   location    city, country                     (optional)
 *   linkedin    full LinkedIn URL                 (optional)
 *   blurb       short one-liner about them        (optional)
 *   highlight   optional badge text               (e.g. "Top Mentor")
 */

export interface HallOfFamePerson {
  name: string;
  role: string;
  company: string;
  photo?: string;
  tenure: string;
  location?: string;
  linkedin?: string;
  blurb?: string;
  highlight?: string;
}

export const HALL_OF_FAME: HallOfFamePerson[] = [
  {
    name: "Priya Sharma",
    role: "Founder & CEO",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "5 years",
    location: "Salem, India",
    linkedin: "https://www.linkedin.com/company/sashainfinity/",
    blurb: "Building the future of accessible, premium education.",
    highlight: "Top Mentor",
  },
  {
    name: "Arjun Mehta",
    role: "Head of Operations",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "4 years",
    location: "Bengaluru, India",
    linkedin: "",
    blurb: "Keeps every internship cohort running like clockwork.",
  },
  {
    name: "Kavya Nair",
    role: "Senior Program Manager",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "3 years",
    location: "Chennai, India",
    linkedin: "",
    blurb: "Mentored 120+ interns from campus to career.",
    highlight: "Intern Favourite",
  },
  {
    name: "Rohan Verma",
    role: "Lead Engineer",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "2.5 years",
    location: "Pune, India",
    linkedin: "",
    blurb: "Architected the streaming platform from scratch.",
  },
  {
    name: "Ananya Iyer",
    role: "Talent & Partnerships",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "2 years",
    location: "Coimbatore, India",
    linkedin: "",
    blurb: "Onboarded 40+ partner companies into the program.",
  },
  {
    name: "Vikram Reddy",
    role: "Product Designer",
    company: "SashaInfinity Pvt Ltd",
    photo: "",
    tenure: "1.5 years",
    location: "Hyderabad, India",
    linkedin: "",
    blurb: "Crafted the student experience you use today.",
  },
];

// --- Rendering code below. Plain Tailwind. Feel free to tweak styles. ---

import React, { useState, useEffect } from "react";
import { Trophy, Linkedin } from "lucide-react";
import { hallOfFameApi } from "@/api/hallOfFame";

const initials = (name: string): string =>
  name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

// useTilt: tracks mouse over a card and returns a transform that tilts the
// card in 3D toward the cursor. Resets on mouse leave. On touch devices the
// card stays flat (no mousemove) - content is still fully readable.
const MAX_TILT = 8; // degrees - subtle, not dizzying

function useTilt() {
  const ref = React.useRef<HTMLDivElement>(null);
  const [style, setStyle] = React.useState<React.CSSProperties>({
    transform: "perspective(1000px) rotateX(0deg) rotateY(0deg)",
    transition: "transform 0.4s cubic-bezier(0.22,1,0.36,1)",
  });
  const [glare, setGlare] = React.useState<{ x: number; y: number; o: number }>(
    {
      x: 50,
      y: 50,
      o: 0,
    },
  );

  const onMove = React.useCallback((e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    // cursor position as a -0.5 .. 0.5 fraction from the card center
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setStyle({
      transform:
        "perspective(1000px) rotateX(" +
        (-py * MAX_TILT).toFixed(2) +
        "deg) rotateY(" +
        (px * MAX_TILT).toFixed(2) +
        "deg) scale(1.02)",
      transition: "transform 0.1s ease-out",
    });
    // glare follows the cursor (0-100% position, opacity ramps in)
    setGlare({ x: (px + 0.5) * 100, y: (py + 0.5) * 100, o: 0.25 });
  }, []);

  const onLeave = React.useCallback(() => {
    setStyle({
      transform: "perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)",
      transition: "transform 0.5s cubic-bezier(0.22,1,0.36,1)",
    });
    setGlare((g) => ({ ...g, o: 0 }));
  }, []);

  return { ref, style, onMove, onLeave, glare };
}

// Portrait: the top of the card - big photo or initials on a soft gradient.
// Minimal & premium: photo dominates, no text overlay (name goes below).
const Portrait: React.FC<{ person: HallOfFamePerson }> = ({ person }) => {
  const [broken, setBroken] = React.useState(false);
  const showPhoto = person.photo && !broken;
  return (
    <div className="relative h-64 w-full overflow-hidden rounded-t-2xl">
      {showPhoto ? (
        <img
          src={person.photo}
          alt={person.name}
          onError={() => setBroken(true)}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      ) : (
        <>
          {/* soft gradient with a subtle radial highlight */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#f4911a] via-[#ffaa44] to-[#fdba74]" />
          <div
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 35% 30%, rgba(255,255,255,0.35) 0%, transparent 50%)",
            }}
          />
          <div
            className="absolute inset-0 flex items-center justify-center text-5xl font-extrabold tracking-tight text-white"
            style={{ fontFamily: "Lexend Deca, sans-serif" }}
          >
            {initials(person.name)}
          </div>
        </>
      )}
    </div>
  );
};

// PersonCard: minimal & premium. Photo-forward, just name + role + meta.
const PersonCard: React.FC<{ person: HallOfFamePerson }> = ({ person }) => {
  const tilt = useTilt();

  return (
    <div
      ref={tilt.ref}
      onMouseMove={tilt.onMove}
      onMouseLeave={tilt.onLeave}
      className="group relative overflow-hidden rounded-2xl border border-white/60 shadow-[0_12px_40px_-12px_rgba(26,26,46,0.25)] backdrop-blur-2xl"
      style={{
        ...tilt.style,
        background: "rgba(255,255,255,0.6)",
        transformStyle: "preserve-3d",
      }}
    >
      {person.highlight ? (
        <span className="absolute right-3 top-3 z-10 rounded-full bg-white/80 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#f4911a] shadow-sm ring-1 ring-[#f4911a]/20 backdrop-blur">
          {person.highlight}
        </span>
      ) : null}

      <Portrait person={person} />

      {/* Minimal info: name, role, tiny meta row. Nothing else. */}
      <div className="px-6 py-5 text-center">
        <h4
          className="text-lg font-bold tracking-tight text-[#1a1a2e]"
          style={{ fontFamily: "Lexend Deca, sans-serif" }}
        >
          {person.name}
        </h4>
        <p className="mt-0.5 text-sm font-medium text-[#f4911a]">
          {person.role}
        </p>

        <div className="mt-3 flex items-center justify-center gap-2 text-[11px] text-slate-400">
          <span>{person.tenure}</span>
          {person.location ? (
            <>
              <span className="text-slate-300">&middot;</span>
              <span>{person.location}</span>
            </>
          ) : null}
          {person.linkedin ? (
            <>
              <span className="text-slate-300">&middot;</span>
              <a
                href={person.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 font-medium text-[#0a66c2] hover:underline"
              >
                <Linkedin className="h-3 w-3" />
              </a>
            </>
          ) : null}
        </div>
      </div>

      {/* cursor-following glare overlay (glass catching light effect) */}
      <div
        className="pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(circle at " +
            tilt.glare.x +
            "% " +
            tilt.glare.y +
            "%, rgba(255,255,255,0.45), transparent 50%)",
          opacity: tilt.glare.o,
          mixBlendMode: "overlay",
        }}
      />
    </div>
  );
};

export const HallOfFamePage: React.FC = () => {
  // Fetch published members from the API. The admin UI manages what appears
  // here; this page is read-only for visitors.
  const [people, setPeople] = useState<HallOfFamePerson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const data = await hallOfFameApi.list();
        // Map the API shape to the local HallOfFamePerson interface.
        if (!cancelled) {
          setPeople(
            data.map((m) => ({
              name: m.name,
              role: m.role,
              company: m.company,
              photo: m.photo ?? undefined,
              tenure: m.tenure,
              location: m.location ?? undefined,
              linkedin: m.linkedin ?? undefined,
              blurb: m.blurb ?? undefined,
              highlight: m.highlight ?? undefined,
            })),
          );
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="relative min-h-screen overflow-hidden"
      style={{
        background:
          "radial-gradient(circle at 0% 0%, rgba(244,145,26,0.10), transparent 40%)," +
          "radial-gradient(circle at 100% 10%, rgba(56,189,248,0.12), transparent 50%)," +
          "radial-gradient(circle at 50% 100%, rgba(168,85,247,0.08), transparent 45%)," +
          "linear-gradient(180deg, #e7effc 0%, #ffffff 60%, #fff7ed 100%)",
      }}
    >
      <div className="pointer-events-none absolute -left-20 top-32 h-72 w-72 rounded-full bg-[#f4911a]/20 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-64 h-80 w-80 rounded-full bg-[#38bdf8]/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-40 left-1/3 h-72 w-72 rounded-full bg-[#a855f7]/15 blur-3xl" />

      <section className="relative px-4 pt-16 pb-12 sm:pt-24 sm:pb-16">
        <div className="mx-auto max-w-3xl text-center">
          <span
            className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/50 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-[#f4911a] shadow-sm backdrop-blur-xl"
            style={{ fontFamily: "Inter, sans-serif" }}
          >
            <Trophy className="h-3.5 w-3.5" /> Wall of Fame
          </span>
          <h1
            className="mt-6 text-4xl font-extrabold leading-tight text-[#1a1a2e] sm:text-5xl"
            style={{ fontFamily: "Lexend Deca, sans-serif" }}
          >
            Our Honoured{" "}
            <span className="bg-gradient-to-r from-[#f4911a] to-[#ffaa44] bg-clip-text text-transparent">
              Staff
            </span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-slate-600 sm:text-lg">
            Celebrating the dedicated people behind our internship program - the
            founders, managers, and mentors who show up every day.
          </p>
        </div>
      </section>

      {/* Loading state */}
      {loading ? (
        <section className="relative px-4 pb-24">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-[340px] animate-pulse rounded-2xl bg-white/40"
                />
              ))}
            </div>
          </div>
        </section>
      ) : error ? (
        <section className="relative px-4 pb-20">
          <div
            className="mx-auto max-w-md rounded-2xl border border-white/60 bg-white/40 p-12 text-center backdrop-blur-xl"
            data-glass="content"
          >
            <Trophy className="mx-auto h-10 w-10 text-slate-400" />
            <p className="mt-4 text-sm text-slate-600">
              Could not load the Wall of Fame. Please try again later.
            </p>
          </div>
        </section>
      ) : people.length > 0 ? (
        <section className="relative px-4 pb-24">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {people.map((p) => (
                <PersonCard key={p.name} person={p} />
              ))}
            </div>
          </div>
        </section>
      ) : (
        <section className="relative px-4 pb-20">
          <div
            className="mx-auto max-w-md rounded-2xl border border-white/60 bg-white/40 p-12 text-center backdrop-blur-xl"
            data-glass="content"
          >
            <Trophy className="mx-auto h-10 w-10 text-slate-400" />
            <p className="mt-4 text-sm text-slate-600">
              No inductees yet. Check back soon.
            </p>
          </div>
        </section>
      )}
    </div>
  );
};

export default HallOfFamePage;
