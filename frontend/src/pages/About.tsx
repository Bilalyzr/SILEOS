import { useEffect, useState } from "react";
import {
  Award,
  BookOpen,
  Compass,
  Cpu,
  Globe,
  Layers,
  ShieldCheck,
  Star,
} from "lucide-react";
import { api } from "@/api/axios";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

interface Instructor {
  id: number;
  name: string;
  email: string;
  profile_photo: string;
  description: string;
  expertise: string | null;
  course_count: number;
  rating: number;
}

const CORE_OFFERINGS = [
  {
    code: "OFR—01",
    icon: Cpu,
    title: "Spatial 3D & AR Learning Labs",
    detail:
      "Interactive WebGL simulations and Meiporul 3D AR models that turn abstract STEM and classical concepts into manipulable spatial architectures.",
  },
  {
    code: "OFR—02",
    icon: BookOpen,
    title: "Studio-Grade Course Tracks",
    detail:
      "Mentor-led courses across full-stack engineering, AI systems, data analytics, and classical Tamil literature (Meiporul, Utporul, Seyappaduporul).",
  },
  {
    code: "OFR—03",
    icon: Layers,
    title: "SashaInfinity Campus OS",
    detail:
      "A unified operating system for K-12 schools, colleges, and universities connecting admissions, fee ledgers, live classes, and family communication.",
  },
  {
    code: "OFR—04",
    icon: Compass,
    title: "Verified Industry Internships",
    detail:
      "SPOC-mentored corporate cohorts with daily work logs, attendance telemetry, and direct placement pipelines for partner companies.",
  },
];

const MISSION_PILLARS = [
  {
    code: "MSN—01",
    label: "OUR MISSION",
    title: "Democratizing deep, first-principles mastery.",
    body: "To bridge classical epistemological rigor with modern spatial computing and engineering craft — making world-class instruction accessible to every learner from Salem to the global stage.",
  },
  {
    code: "MSN—02",
    label: "OUR VISION",
    title: "An architectural standard for digital education.",
    body: "We envision learning environments that feel like precision studios rather than passive video feeds — where every concept is inspected, built, and verified through real deliverables.",
  },
  {
    code: "MSN—03",
    label: "OUR PEDAGOGY",
    title: "Clarity of essence (மெய்ப்பொருள்).",
    body: "Rooted in the Tamil philosophical tradition of discerning foundational truth, our curriculum strips away superficial rote memorization in favor of structural understanding.",
  },
];

export function AboutPage() {
  const [instructors, setInstructors] = useState<Instructor[]>([]);
  const [isLoadingInstructors, setIsLoadingInstructors] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchTopInstructors = async () => {
      try {
        setIsLoadingInstructors(true);
        const response = await api.get("/users/instructors/top?limit=5");
        if (!cancelled) {
          setInstructors(Array.isArray(response.data) ? response.data : []);
        }
      } catch (error) {
        console.error("Failed to fetch top instructors:", error);
        if (!cancelled) setInstructors([]);
      } finally {
        if (!cancelled) setIsLoadingInstructors(false);
      }
    };

    fetchTopInstructors();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="sympho-scope rd-screen rd-screen-about min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—ABT.01"
        category="INSTITUTIONAL MONOGRAPH // WHO WE ARE"
        code="SALEM · TAMIL NADU · INDIA"
        title="Architecting the future of spatial & studio learning."
        subtitle="SashaInfinity is an educational technology studio reimagining K-12, collegiate, and professional mastery through interactive 3D WebGL laboratories, classical Tamil scholarship, and mentor-guided engineering cohorts."
        metrics={[
          {
            value: "4",
            unit: "verticals",
            label: "Courses · Labs · Campus · Internships",
            code: "ABT—01",
          },
          {
            value: "3D / AR",
            unit: "spatial",
            label: "WebGL Interactive Engine",
            code: "ABT—02",
          },
          {
            value: "11.66°N",
            unit: "78.14°E",
            label: "Salem Studio Headquarters",
            code: "ABT—03",
          },
        ]}
        actions={
          <>
            <SymphoButton to="/courses" variant="copper">
              Explore Courses
            </SymphoButton>
            <SymphoButton to="/contact" variant="ghost-dark">
              Contact Our Studio
            </SymphoButton>
          </>
        }
      />

      {/* Who We Are — Editorial Split Plate */}
      <section className="border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="ABT—01"
            category="STUDIO MANIFESTO"
            code="FOUNDATION & IDENTITY"
            title="The leading studio for deep learning & instruction."
            subtitle="Where modern software engineering, interactive 3D simulation, and classical Indian intellectual traditions converge."
          />

          <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-12">
            <div className="flex flex-col justify-between space-y-6 lg:col-span-7">
              <div className="sheet-frame bg-limestone-50 p-8">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-500">
                  ARCHITECTURAL OVERVIEW
                </span>
                <h3 className="mt-3 font-display text-3xl font-light leading-snug text-ink-900">
                  Built for learners and institutions that refuse generic templates.
                </h3>
                <p className="mt-4 text-base leading-relaxed text-ink-600">
                  SashaInfinity combines studio-recorded technical courses, browser-native 3D science and geometry laboratories, a complete Digital Library, and an institutional Campus OS into a single cohesive platform.
                </p>
                <p className="mt-4 text-base leading-relaxed text-ink-600">
                  Whether a student is inspecting a 3D crystal lattice in our Learning Lab, studying Sangam poetics under the Tamil Triad, or logging production commits in a mentor-led internship, every interaction is designed for permanent comprehension.
                </p>

                <div className="mt-8 grid grid-cols-2 gap-4 border-t border-ink-900/10 pt-6 sm:grid-cols-3">
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                      PEDAGOGY
                    </span>
                    <p className="mt-1 font-display text-xl font-light text-ink-900">
                      First-Principles
                    </p>
                  </div>
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                      CREDENTIALING
                    </span>
                    <p className="mt-1 font-display text-xl font-light text-ink-900">
                      Cryptographic QR
                    </p>
                  </div>
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                      DEPLOYMENT
                    </span>
                    <p className="mt-1 font-display text-xl font-light text-ink-900">
                      Web · Mobile · AR
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-5">
              <div className="sheet-frame flex h-full flex-col justify-between overflow-hidden bg-ink-950 p-8 text-limestone-100 blueprint-grid">
                <div className="flex items-center justify-between border-b border-limestone-100/10 pb-4">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-400">
                    PLATE // SI—STUDIO
                  </span>
                  <Globe className="h-4 w-4 text-copper-400" />
                </div>

                <div className="my-8 flex items-center justify-center">
                  <img
                    src="/assets/images/Untitled_design__2__1_-removebg-preview-1.png"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src =
                        "https://sashainfinity.com/wp-content/uploads/2025/06/Copy_of_sasha_SISF_PITCH-removebg-preview-e1751282895734.png";
                    }}
                    alt="Children happily learning with VR headsets"
                    className="max-h-64 w-auto object-contain"
                  />
                </div>

                <div className="border-t border-limestone-100/10 pt-4">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-400">
                    IMMERSIVE LEARNING DIVISION
                  </span>
                  <p className="mt-1 text-xs leading-relaxed text-limestone-200/75">
                    Bridging physical classrooms and spatial 3D visualization for K-12 and collegiate cohorts across India.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Offerings */}
      <section className="border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="ABT—02"
            category="PLATFORM ARCHITECTURE"
            code="4 CORE SUBSYSTEMS"
            title="Core Offerings"
            subtitle="Every subsystem is engineered in-house to work as one continuous educational record."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {CORE_OFFERINGS.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.code}
                  className="sheet-frame flex flex-col justify-between bg-limestone-50 p-7 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/40"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                        {item.code}
                      </span>
                      <Icon className="h-4 w-4 text-copper-500" />
                    </div>
                    <h3 className="mt-5 font-display text-2xl font-light text-ink-900">
                      {item.title}
                    </h3>
                    <p className="mt-3 text-sm leading-relaxed text-ink-600">
                      {item.detail}
                    </p>
                  </div>
                  <div className="mt-6 border-t border-ink-900/10 pt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                    SashaInfinity Core // Active
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Mission & Vision Dark Blueprint Section */}
      <section className="on-dark relative overflow-hidden border-b border-limestone-100/10 bg-ink-950 py-section-sm text-limestone-100 blueprint-grid">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            dark
            index="ABT—03"
            category="CHARTER & PRINCIPLES"
            code="INSTITUTIONAL ETHOS"
            title="Mission, Vision & Pedagogy"
            subtitle="Guided by structural clarity, empirical verification, and respect for the learner's attention."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {MISSION_PILLARS.map((m) => (
              <div
                key={m.code}
                className="sheet-frame flex flex-col justify-between bg-ink-900/90 p-8"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-limestone-100/10 pb-4">
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-400">
                      {m.code}
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-limestone-300/60">
                      {m.label}
                    </span>
                  </div>
                  <h3 className="mt-6 font-display text-2xl font-light text-limestone-50">
                    {m.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-limestone-200/75">
                    {m.body}
                  </p>
                </div>
                <div className="mt-8 flex items-center gap-2 border-t border-limestone-100/10 pt-4 font-mono text-[10px] uppercase tracking-[0.14em] text-copper-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Charter Verified
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Top Class Mentors (Dynamic from API, only shown if instructors exist or loading) */}
      {(isLoadingInstructors || instructors.length > 0) && (
        <section className="py-section-sm">
          <div className="mx-auto max-w-[1680px] px-gutter">
            <SymphoSectionHeader
              index="ABT—04"
              category="FACULTY ROSTER"
              code="VERIFIED INSTRUCTORS"
              title="Top Class Mentors"
              subtitle="Practitioners, researchers, and educators leading SashaInfinity studio cohorts."
            />

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
              {isLoadingInstructors
                ? [1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="sheet-frame h-72 animate-pulse bg-limestone-50 p-6"
                    />
                  ))
                : instructors.map((instructor, idx) => (
                    <div
                      key={instructor.id}
                      className="sheet-frame flex flex-col items-center bg-limestone-50 p-6 text-center transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/40"
                    >
                      <span className="self-start font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                        FAC—0{idx + 1}
                      </span>
                      <img
                        src={instructor.profile_photo}
                        alt={`Profile of ${instructor.name}`}
                        className="mt-4 h-20 w-20 rounded-full border border-ink-900/15 object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${instructor.name.replace(
                            " ",
                            "+",
                          )}&background=16181a&color=f4efe6&size=200`;
                        }}
                      />
                      <h3 className="mt-4 font-display text-xl font-light text-ink-900">
                        {instructor.name}
                      </h3>
                      <p className="mt-1 line-clamp-2 text-xs text-ink-600">
                        {instructor.expertise || instructor.description}
                      </p>
                      <div className="mt-4 inline-flex items-center gap-1.5 rounded-pill border border-copper-500/30 bg-copper-500/10 px-3 py-1 font-mono text-xs text-copper-600">
                        <Star size={12} className="fill-current" />
                        {instructor.rating.toFixed(1)}
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        </section>
      )}

      {/* Recognition & Wall of Fame Callout */}
      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <div className="sheet-frame flex flex-col items-start justify-between gap-6 bg-limestone-50 p-8 sm:flex-row sm:items-center">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-ink-900/15 bg-limestone-100 text-copper-500">
                <Award className="h-5 w-5" />
              </div>
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                  HONOUR ROLL // LEADERSHIP & STAFF
                </span>
                <h3 className="mt-1 font-display text-2xl font-light text-ink-900">
                  Meet the people behind SashaInfinity on our Wall of Fame.
                </h3>
              </div>
            </div>
            <SymphoButton to="/hall-of-fame" variant="primary">
              Open Wall of Fame
            </SymphoButton>
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—ABT // 05"
        eyebrow="BEGIN YOUR COHORT"
        title="Join thousands of learners building real mastery."
        description="Explore our catalog of studio courses, interactive 3D learning labs, and verified internship tracks."
        primaryLabel="Browse All Courses"
        primaryTo="/courses"
        secondaryLabel="Get in Touch"
        secondaryTo="/contact"
      />
    </div>
  );
}
