import React, { useEffect, useState } from "react";
import { Linkedin, MapPin, Trophy } from "lucide-react";
import { hallOfFameApi } from "@/api/hallOfFame";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

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

const initials = (name: string): string =>
  name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

const MAX_TILT = 6;

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
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setStyle({
      transform:
        "perspective(1000px) rotateX(" +
        (-py * MAX_TILT).toFixed(2) +
        "deg) rotateY(" +
        (px * MAX_TILT).toFixed(2) +
        "deg) scale(1.015)",
      transition: "transform 0.1s ease-out",
    });
    setGlare({ x: (px + 0.5) * 100, y: (py + 0.5) * 100, o: 0.18 });
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

const Portrait: React.FC<{ person: HallOfFamePerson; index: number }> = ({
  person,
  index,
}) => {
  const [broken, setBroken] = React.useState(false);
  const showPhoto = person.photo && !broken;
  return (
    <div className="relative h-64 w-full overflow-hidden border-b border-ink-900/10 bg-ink-950">
      {showPhoto ? (
        <img
          src={person.photo}
          alt={person.name}
          onError={() => setBroken(true)}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      ) : (
        <div className="relative flex h-full w-full items-center justify-center bg-ink-950 blueprint-grid">
          <div className="flex h-24 w-24 items-center justify-center rounded-full border border-copper-500/40 bg-copper-500/10 font-display text-4xl font-light italic text-limestone-50">
            {initials(person.name)}
          </div>
        </div>
      )}
      <span className="absolute left-4 top-4 rounded-pill bg-ink-950/85 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-limestone-100 backdrop-blur-sm">
        HOF—{String(index + 1).padStart(2, "0")}
      </span>
      {person.highlight && (
        <span className="absolute right-4 top-4 rounded-pill bg-copper-500 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-limestone-50">
          {person.highlight}
        </span>
      )}
    </div>
  );
};

const PersonCard: React.FC<{ person: HallOfFamePerson; index: number }> = ({
  person,
  index,
}) => {
  const tilt = useTilt();

  return (
    <div
      ref={tilt.ref}
      onMouseMove={tilt.onMove}
      onMouseLeave={tilt.onLeave}
      className="group sheet-frame relative flex flex-col overflow-hidden bg-limestone-50"
      style={{
        ...tilt.style,
        transformStyle: "preserve-3d",
      }}
    >
      <Portrait person={person} index={index} />

      <div className="flex flex-1 flex-col justify-between p-6">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
            {person.role}
          </span>
          <h3 className="mt-1 font-display text-2xl font-light text-ink-900">
            {person.name}
          </h3>
          <p className="mt-0.5 font-mono text-[11px] text-ink-500">
            {person.company}
          </p>
          {person.blurb && (
            <p className="mt-3 text-sm leading-relaxed text-ink-600">
              {person.blurb}
            </p>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between border-t border-ink-900/10 pt-4 font-mono text-[11px] text-ink-500">
          <div className="flex items-center gap-2">
            <span>{person.tenure}</span>
            {person.location && (
              <>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3 text-copper-500" />
                  {person.location}
                </span>
              </>
            )}
          </div>

          {person.linkedin && (
            <a
              href={person.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${person.name} LinkedIn`}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-ink-900/15 text-ink-700 transition-colors hover:border-copper-500 hover:text-copper-500"
            >
              <Linkedin className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>

      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(circle at " +
            tilt.glare.x +
            "% " +
            tilt.glare.y +
            "%, rgba(255,255,255,0.45), transparent 55%)",
          opacity: tilt.glare.o,
          mixBlendMode: "overlay",
        }}
      />
    </div>
  );
};

export const HallOfFamePage: React.FC = () => {
  const [people, setPeople] = useState<HallOfFamePerson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const data = await hallOfFameApi.list();
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
    <div className="sympho-scope rd-screen rd-screen-hall-of-fame min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—HOF.01"
        category="WALL OF FAME // HONOUR ROLL"
        code="EQUAL RECOGNITION LEDGER"
        title="Our Honoured Staff & Mentors."
        subtitle="Celebrating the dedicated founders, program managers, engineers, and mentors behind our studio courses and internship cohorts — presented as peers on a single architectural plate."
        metrics={[
          {
            value: String(people.length || HALL_OF_FAME.length),
            unit: "inductees",
            label: "Honoured Staff & Mentors",
            code: "HOF—01",
          },
          {
            value: "EQUAL",
            unit: "standing",
            label: "Unranked Peer Recognition",
            code: "HOF—02",
          },
          {
            value: "3D TILT",
            unit: "plates",
            label: "Interactive Portrait Cards",
            code: "HOF—03",
          },
        ]}
      />

      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="HOF—01"
            category="PORTRAIT ARCHIVE"
            code={`${people.length} INDUCTEES`}
            title="Wall of Fame Directory"
            subtitle="Every member is honoured equally — hover any portrait plate to inspect their tenure, station, and mentorship record."
          />

          <div className="mt-12">
            {loading ? (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="sheet-frame h-[380px] animate-pulse bg-limestone-50 p-6"
                  />
                ))}
              </div>
            ) : error ? (
              <div className="sheet-frame mx-auto max-w-xl bg-limestone-50 p-12 text-center">
                <Trophy className="mx-auto h-10 w-10 text-copper-500" />
                <p className="mt-4 font-display text-2xl font-light text-ink-900">
                  Could not load the Wall of Fame. Please try again later.
                </p>
              </div>
            ) : people.length > 0 ? (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {people.map((p, idx) => (
                  <PersonCard key={p.name} person={p} index={idx} />
                ))}
              </div>
            ) : (
              <div className="sheet-frame mx-auto max-w-xl bg-limestone-50 p-12 text-center">
                <Trophy className="mx-auto h-10 w-10 text-copper-500" />
                <p className="mt-4 font-display text-2xl font-light text-ink-900">
                  No inductees yet. Check back soon.
                </p>
                <div className="mt-6 flex justify-center">
                  <SymphoButton to="/internships" variant="primary">
                    Explore Internships
                  </SymphoButton>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—HOF // 02"
        eyebrow="WORK WITH OUR MENTORS"
        title="Ready to learn with our faculty & mentors?"
        description="Join an upcoming internship cohort or enroll in a studio course taught by our honoured practitioners."
        primaryLabel="Explore Internships"
        primaryTo="/internships"
        secondaryLabel="Browse All Courses"
        secondaryTo="/courses"
      />
    </div>
  );
};

export default HallOfFamePage;
