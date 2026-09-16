import * as React from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Boxes,
  Briefcase,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Code2,
  CreditCard,
  FlaskConical,
  GraduationCap,
  HeartHandshake,
  LayoutDashboard,
  MessageCircle,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users,
  Video,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { GlassDialog } from "@/components/ui/dialog";
import { isImpersonating, useAuthStore } from "@/store/auth";
import { normalizeRole } from "@/utils/role-routing";

const TOUR_VERSION = "2026.09.14-1";

type TourRole =
  | "student"
  | "instructor"
  | "admin"
  | "superadmin"
  | "company"
  | "spoc"
  | "parent";

interface TourStep {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  features: [string, string, string];
  icon: LucideIcon;
  to?: string;
  actionLabel?: string;
  pillars?: boolean;
}

interface StoredTourProgress {
  version: string;
  status: "started" | "dismissed" | "completed";
  lastStep: number;
  updatedAt: string;
}

interface ProductTourContextValue {
  openTour: () => void;
}

const ProductTourContext = React.createContext<ProductTourContextValue | null>(
  null,
);

const ROLE_LABELS: Record<TourRole, string> = {
  student: "Learner",
  instructor: "Instructor",
  admin: "Administrator",
  superadmin: "SuperAdmin",
  company: "Company partner",
  spoc: "Institution SPOC",
  parent: "Parent or guardian",
};

const PILLARS = [
  {
    name: "Meiporul",
    label: "Immersive learning",
    detail: "3D objects, AR, VR and virtual labs",
    icon: Boxes,
  },
  {
    name: "Seyappaduporul",
    label: "School learning",
    detail: "Live classes, notes, eBooks and campus tools",
    icon: Building2,
  },
  {
    name: "Utporul",
    label: "Skills and careers",
    detail: "Courses, assessments, coding and certificates",
    icon: Code2,
  },
] as const;

function welcomeStep(role: TourRole): TourStep {
  return {
    id: "welcome",
    eyebrow: `SashaInfinity for ${ROLE_LABELS[role]}`,
    title: "One learning OS. Three connected pillars.",
    description:
      "Everything in SashaInfinity is organised around learning by seeing, doing and proving what you know.",
    features: [
      "Move between learning, practice and real-world experience",
      "Keep progress, communication and outcomes connected",
      "Use one account across the complete SashaInfinity experience",
    ],
    icon: Sparkles,
    pillars: true,
  };
}

const ROLE_STEPS: Record<TourRole, TourStep[]> = {
  student: [
    {
      id: "learning-home",
      eyebrow: "Your learning home",
      title: "Know exactly what to learn next",
      description:
        "Your dashboard brings courses, upcoming work and personal recommendations into one clear starting point.",
      features: [
        "Continue courses without losing your place",
        "Follow your learning plan and suggested support steps",
        "See grades, mastery and progress in one place",
      ],
      icon: LayoutDashboard,
      to: "/dashboard",
      actionLabel: "Open my dashboard",
    },
    {
      id: "learn-by-doing",
      eyebrow: "Meiporul",
      title: "Learn by doing, not only by watching",
      description:
        "Explore interactive experiments, 3D models, games, AR and VR experiences connected to your curriculum.",
      features: [
        "Run virtual experiments and record observations",
        "Explore course-linked 3D and immersive objects",
        "Practise concepts through games and coding activities",
      ],
      icon: FlaskConical,
      to: "/labs",
      actionLabel: "Explore learning labs",
    },
    {
      id: "classes-and-support",
      eyebrow: "Seyappaduporul",
      title: "Stay connected to teaching and support",
      description:
        "Join live classes, read shared resources and receive the right support when a concept needs more work.",
      features: [
        "Join scheduled classes and revisit recordings",
        "Use notes, eBooks and lesson resources",
        "Receive instructor interventions and AI suggestions",
      ],
      icon: Video,
      to: "/student/live-classes",
      actionLabel: "View live classes",
    },
    {
      id: "proof-and-progress",
      eyebrow: "Utporul",
      title: "Turn progress into skills and proof",
      description:
        "Complete assessments, build practical ability and collect evidence of achievement as you learn.",
      features: [
        "Take quizzes, assignments and coding assessments",
        "Earn certificates and achievement rewards",
        "Build toward internships and practical opportunities",
      ],
      icon: Trophy,
      to: "/dashboard/analytics",
      actionLabel: "See my progress",
    },
  ],
  instructor: [
    {
      id: "create-curriculum",
      eyebrow: "Course creation",
      title: "Build the complete learning journey",
      description:
        "Create structured courses and combine teaching, interaction, assessment and certification inside one curriculum.",
      features: [
        "Organise sections, lessons and learning outcomes",
        "Attach videos, readings, labs, games and 3D tasks",
        "Preview, publish and update from one workspace",
      ],
      icon: BookOpen,
      to: "/instructor/courses",
      actionLabel: "Manage my courses",
    },
    {
      id: "immersive-studio",
      eyebrow: "Meiporul",
      title: "Create experiences students can explore",
      description:
        "Use the content studios to build reusable experiments, immersive objects and interactive learning activities.",
      features: [
        "Create virtual labs and curriculum investigations",
        "Use GLB models, 3D tasks, games and H5P content",
        "Attach the same asset across courses and lessons",
      ],
      icon: FlaskConical,
      to: "/instructor/lab-studio",
      actionLabel: "Open Lab Studio",
    },
    {
      id: "assessment",
      eyebrow: "Utporul",
      title: "Assess knowledge and practical ability",
      description:
        "Create formative checks, full assessments and coding tasks, then review evidence from one teaching workflow.",
      features: [
        "Build quizzes, assignments and question papers",
        "Run coding tests and practical assessments",
        "Grade, give feedback and issue certificates",
      ],
      icon: GraduationCap,
      to: "/instructor/assessment-studio",
      actionLabel: "Open Assessment Studio",
    },
    {
      id: "learner-support",
      eyebrow: "Sasha Monitor",
      title: "See where learners really need help",
      description:
        "Use risk signals and concept-level evidence to act before a learner falls too far behind.",
      features: [
        "Find at-risk students and weak concepts",
        "Create a support step in the learner's plan",
        "Monitor interventions, progress and engagement",
      ],
      icon: BarChart3,
      to: "/instructor/insights",
      actionLabel: "Open Sasha Monitor",
    },
  ],
  admin: [
    {
      id: "control-center",
      eyebrow: "Unified command",
      title: "Run all three pillars from one control center",
      description:
        "The control center separates each business vertical while keeping platform health, reporting and governance unified.",
      features: [
        "Review Meiporul, Seyappaduporul and Utporul separately",
        "Track operational outcomes across the whole OS",
        "Move from a signal directly to the responsible workspace",
      ],
      icon: LayoutDashboard,
      to: "/admin/operations",
      actionLabel: "Open Control Center",
    },
    {
      id: "people-control",
      eyebrow: "People and access",
      title: "Support every role without losing control",
      description:
        "Manage students, instructors, institutions and partners, with audited view-as tools for resolving user issues.",
      features: [
        "Approve and manage role-based access",
        "Monitor instructors and learner progress",
        "Use audited impersonation to reproduce problems",
      ],
      icon: Users,
      to: "/admin/manage",
      actionLabel: "Manage people",
    },
    {
      id: "content-governance",
      eyebrow: "Content governance",
      title: "Control every learning asset",
      description:
        "Review courses, lectures, eBooks, laboratories, interactive objects and certificates from the admin console.",
      features: [
        "Host, review, edit, publish or remove content",
        "Manage shared libraries and reusable assets",
        "Maintain quality across all business verticals",
      ],
      icon: Boxes,
      to: "/admin/content-libraries",
      actionLabel: "Open content libraries",
    },
    {
      id: "commerce-and-comms",
      eyebrow: "Business operations",
      title: "Connect revenue, communication and AI operations",
      description:
        "Operate multiple revenue models while keeping delivery, provider health and user communication visible.",
      features: [
        "Review orders, memberships, bundles and payouts",
        "Manage communications and notification preferences",
        "Configure fallback-ready AI provider keys",
      ],
      icon: CreditCard,
      to: "/admin/operations?view=revenue",
      actionLabel: "View business reporting",
    },
  ],
  superadmin: [
    {
      id: "platform-overview",
      eyebrow: "Platform governance",
      title: "See the whole SashaInfinity operating system",
      description:
        "Use the supervisory dashboards to understand platform activity without mixing daily administration with governance.",
      features: [
        "Monitor students, instructors and administrators",
        "Review platform-level trends and exceptions",
        "Enter the admin console when action is required",
      ],
      icon: ShieldCheck,
      to: "/superadmin/dashboard",
      actionLabel: "Open platform overview",
    },
    {
      id: "accountability",
      eyebrow: "Audit and accountability",
      title: "Keep powerful actions traceable",
      description:
        "Review impersonation and administrative access so support work remains controlled and accountable.",
      features: [
        "See who viewed another role and when",
        "Review administrator activity and access",
        "Investigate exceptions with a clear audit trail",
      ],
      icon: Users,
      to: "/superadmin/audit",
      actionLabel: "Review the audit trail",
    },
    {
      id: "business-pillars",
      eyebrow: "Business resilience",
      title: "Monitor three independent growth pillars",
      description:
        "Compare the immersive, school and skills verticals while maintaining one reporting and control structure.",
      features: [
        "Inspect each vertical independently",
        "Compare revenue and operational contribution",
        "Identify concentration risks before they grow",
      ],
      icon: BarChart3,
      to: "/admin/operations",
      actionLabel: "View pillar performance",
    },
    {
      id: "admin-console",
      eyebrow: "Operational control",
      title: "Move from oversight to action",
      description:
        "Open the admin console to control content, people, commerce, providers and communications when intervention is needed.",
      features: [
        "Manage platform content and access",
        "Review commerce and service operations",
        "Coordinate communications and configuration",
      ],
      icon: LayoutDashboard,
      to: "/admin/dashboard",
      actionLabel: "Open the admin console",
    },
  ],
  company: [
    {
      id: "company-overview",
      eyebrow: "Company workspace",
      title: "Manage talent activity in one place",
      description:
        "Your company dashboard connects learners, internships, attendance, work evidence and reporting.",
      features: [
        "Review active learners and opportunities",
        "Track attendance, work logs and outcomes",
        "Share announcements with the right audience",
      ],
      icon: Briefcase,
      to: "/company/dashboard",
      actionLabel: "Open company overview",
    },
    {
      id: "internships",
      eyebrow: "Practical experience",
      title: "Turn learning into supervised work",
      description:
        "Create and manage practical opportunities, then review learner activity throughout the experience.",
      features: [
        "Publish internship opportunities",
        "Manage applications and participating students",
        "Review work logs, attendance and performance",
      ],
      icon: HeartHandshake,
      to: "/company/dashboard",
      actionLabel: "Manage internships",
    },
    {
      id: "company-reports",
      eyebrow: "Evidence and reporting",
      title: "Keep outcomes measurable",
      description:
        "Use reports and reviews to turn day-to-day participation into clear evidence for institutions and learners.",
      features: [
        "Export attendance and activity reports",
        "Record structured performance reviews",
        "Monitor program participation and completion",
      ],
      icon: BarChart3,
      to: "/company/dashboard",
      actionLabel: "View company reports",
    },
    {
      id: "billing-and-seats",
      eyebrow: "Access and billing",
      title: "Control purchased access and team administration",
      description:
        "Manage company invoices, learning seats and manager access without losing the operational trail.",
      features: [
        "Review invoices and billing details",
        "Assign purchased course seats",
        "Invite or revoke company managers",
      ],
      icon: CreditCard,
      to: "/company/dashboard",
      actionLabel: "Open billing controls",
    },
  ],
  spoc: [
    {
      id: "spoc-overview",
      eyebrow: "Institution coordination",
      title: "Keep learners and opportunities connected",
      description:
        "Your SPOC workspace brings institution cohorts, internship activity and communication into one view.",
      features: [
        "Review assigned cohorts and learners",
        "Coordinate available internship opportunities",
        "Track pending actions and participation",
      ],
      icon: Building2,
      to: "/spoc/dashboard",
      actionLabel: "Open SPOC dashboard",
    },
    {
      id: "cohort-support",
      eyebrow: "Learner coordination",
      title: "Guide each cohort toward the next action",
      description:
        "Use cohort-level records to understand eligibility, activity and the support learners need.",
      features: [
        "Review learner and cohort details",
        "Coordinate applications and practical work",
        "Follow progress without exposing unrelated records",
      ],
      icon: Users,
      to: "/spoc/dashboard",
      actionLabel: "Review cohorts",
    },
    {
      id: "spoc-communication",
      eyebrow: "Communication",
      title: "Keep information clear and timely",
      description:
        "Publish useful updates and choose how SashaInfinity should contact you about important activity.",
      features: [
        "Share institution and opportunity updates",
        "Use the SPOC publishing workspace",
        "Control your communication preferences",
      ],
      icon: MessageCircle,
      to: "/communication-preferences",
      actionLabel: "Set communication preferences",
    },
  ],
  parent: [
    {
      id: "children-overview",
      eyebrow: "Family overview",
      title: "Understand each child's learning day",
      description:
        "The parent portal brings approved school and online-learning information into a single, protected view.",
      features: [
        "Link a child through an approved access request",
        "Review attendance, fees, results and notices",
        "See learning progress and support signals",
      ],
      icon: HeartHandshake,
      to: "/parent",
      actionLabel: "Open my children",
    },
    {
      id: "campus-life",
      eyebrow: "Seyappaduporul",
      title: "Stay informed about campus activity",
      description:
        "Follow the records families need without switching between disconnected systems or message threads.",
      features: [
        "Check transport and hostel information",
        "Review notices, published results and attendance",
        "Complete available fee actions securely",
      ],
      icon: Building2,
      to: "/parent",
      actionLabel: "View campus information",
    },
    {
      id: "learning-digest",
      eyebrow: "Learning support",
      title: "Know when encouragement or support is needed",
      description:
        "Weekly learning digests show course progress and important risk signals in family-friendly language.",
      features: [
        "Review course completion and current status",
        "See important learning-support signals",
        "Use timely information for better conversations",
      ],
      icon: BarChart3,
      to: "/parent",
      actionLabel: "View learning digests",
    },
  ],
};

function resolveTourRole(rawRole: string | null | undefined): TourRole {
  const role = normalizeRole(rawRole);
  if (role === "company_manager") return "company";
  if (
    role === "instructor" ||
    role === "admin" ||
    role === "superadmin" ||
    role === "company" ||
    role === "spoc" ||
    role === "parent"
  ) {
    return role;
  }
  return "student";
}

function storageKey(userId: number, role: TourRole): string {
  return `sasha-product-tour:${userId}:${role}`;
}

function readProgress(key: string): StoredTourProgress | null {
  try {
    const value = window.localStorage.getItem(key);
    if (!value) return null;
    const parsed = JSON.parse(value) as Partial<StoredTourProgress>;
    if (
      typeof parsed.version !== "string" ||
      typeof parsed.status !== "string" ||
      typeof parsed.lastStep !== "number"
    ) {
      return null;
    }
    return parsed as StoredTourProgress;
  } catch {
    return null;
  }
}

function isTourRoute(pathname: string): boolean {
  return [
    "/dashboard",
    "/my-courses",
    "/my-plan",
    "/my-grades",
    "/my-mastery",
    "/learn-with-sasha",
    "/labs",
    "/coding",
    "/leaderboard",
    "/instructor",
    "/admin",
    "/superadmin",
    "/company",
    "/spoc",
    "/parent",
    "/profile",
    "/settings",
    "/communication-preferences",
  ].some((prefix) =>
    pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function hasLegacyImpersonationFlag(): boolean {
  try {
    return Boolean(
      sessionStorage.getItem("mock_view_as_company") ||
        sessionStorage.getItem("mock_view_as_spoc"),
    );
  } catch {
    return false;
  }
}

export function ProductTourProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = useAuthStore((state) => state.user);
  const profile = useAuthStore((state) => state.profile);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const role = resolveTourRole(user?.role);
  const steps = React.useMemo(
    () => [welcomeStep(role), ...ROLE_STEPS[role]],
    [role],
  );
  const [open, setOpen] = React.useState(false);
  const [stepIndex, setStepIndex] = React.useState(0);
  const activeStep = steps[Math.min(stepIndex, steps.length - 1)];
  const eligible = Boolean(
    isAuthenticated && user && isTourRoute(pathname),
  );

  // The floating "How it works" launcher is fixed to the bottom-right corner;
  // while it is visible, page containers reserve clearance (see
  // body.has-tour-fab in globals.css) so it never covers a card's actions.
  React.useEffect(() => {
    document.body.classList.toggle("has-tour-fab", eligible && !open);
    return () => document.body.classList.remove("has-tour-fab");
  }, [eligible, open]);

  const key = user ? storageKey(user.id, role) : "";

  const saveProgress = React.useCallback(
    (status: StoredTourProgress["status"], index: number) => {
      if (!key) return;
      try {
        const progress: StoredTourProgress = {
          version: TOUR_VERSION,
          status,
          lastStep: index,
          updatedAt: new Date().toISOString(),
        };
        window.localStorage.setItem(key, JSON.stringify(progress));
      } catch {
        // The tour remains usable when storage is blocked by the browser.
      }
    },
    [key],
  );

  React.useEffect(() => {
    setOpen(false);
    setStepIndex(0);
  }, [key]);

  React.useEffect(() => {
    if (!eligible || !user || !key) return;
    if (isImpersonating() || hasLegacyImpersonationFlag()) return;
    // Let the mandatory mobile-number gate finish first for learner accounts.
    if (role === "student" && profile && !profile.phone?.trim()) return;

    const progress = readProgress(key);
    const shouldOpen =
      !progress ||
      progress.version !== TOUR_VERSION ||
      progress.status === "started";
    if (!shouldOpen) return;

    const initialStep =
      progress?.version === TOUR_VERSION
        ? Math.min(Math.max(progress.lastStep, 0), steps.length - 1)
        : 0;
    const timer = window.setTimeout(() => {
      setStepIndex(initialStep);
      setOpen(true);
      saveProgress("started", initialStep);
    }, 650);
    return () => window.clearTimeout(timer);
  }, [eligible, key, profile, role, saveProgress, steps.length, user]);

  const openTour = React.useCallback(() => {
    setStepIndex(0);
    setOpen(true);
    saveProgress("started", 0);
  }, [saveProgress]);

  const dismiss = React.useCallback(() => {
    saveProgress("dismissed", stepIndex);
    setOpen(false);
  }, [saveProgress, stepIndex]);

  const complete = React.useCallback(() => {
    saveProgress("completed", steps.length - 1);
    setOpen(false);
  }, [saveProgress, steps.length]);

  const move = (nextIndex: number) => {
    const safeIndex = Math.min(Math.max(nextIndex, 0), steps.length - 1);
    setStepIndex(safeIndex);
    saveProgress("started", safeIndex);
  };

  const explore = () => {
    if (!activeStep.to) return;
    saveProgress("dismissed", stepIndex);
    setOpen(false);
    navigate(activeStep.to);
  };

  const contextValue = React.useMemo(() => ({ openTour }), [openTour]);
  const StepIcon = activeStep.icon;
  const isLast = stepIndex === steps.length - 1;
  const firstName =
    profile?.first_name?.trim() ||
    user?.display_name?.trim().split(/\s+/)[0] ||
    "there";

  return (
    <ProductTourContext.Provider value={contextValue}>
      {children}

      {eligible && !open && (
        <button
          type="button"
          onClick={openTour}
          aria-label="Open SashaInfinity product tour"
          className="fixed bottom-5 right-4 sm:right-6 z-40 inline-flex items-center gap-2 rounded-full border border-orange-200/80 bg-white/90 p-2.5 lg:px-3.5 lg:py-2.5 text-sm font-semibold text-slate-800 shadow-[0_14px_40px_rgba(249,115,22,0.22)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-orange-300 hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2"
        >
          <span className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-orange-500 to-amber-400 text-white shadow-sm">
            <HelpCircle className="h-4 w-4" />
          </span>
          {/* Icon-only below lg: the wide pill covered the bottom-right card
              corner of the dashboard grid at tablet widths. */}
          <span className="hidden lg:inline">How it works</span>
        </button>
      )}

      <GlassDialog
        open={open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dismiss();
        }}
        size="lg"
        eyebrow={`${activeStep.eyebrow} · Step ${stepIndex + 1} of ${steps.length}`}
        title={
          stepIndex === 0
            ? `Welcome, ${firstName}`
            : "How SashaInfinity works for you"
        }
        description={
          stepIndex === 0
            ? "Take a two-minute tour of the tools available to you."
            : undefined
        }
        data-testid="product-tour"
        className="overflow-hidden border border-orange-100/80"
        actions={
          <>
            <button
              type="button"
              onClick={dismiss}
              className="si-btn-ghost mr-auto"
            >
              Skip for now
            </button>
            {stepIndex > 0 && (
              <button
                type="button"
                onClick={() => move(stepIndex - 1)}
                className="si-btn-secondary"
              >
                <ChevronLeft className="h-4 w-4" /> Back
              </button>
            )}
            <button
              type="button"
              onClick={() => (isLast ? complete() : move(stepIndex + 1))}
              className="si-btn-primary"
            >
              {isLast ? "Finish tour" : "Next"}
              {isLast ? (
                <Check className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-orange-600 via-orange-500 to-amber-400 p-5 text-white shadow-[0_18px_45px_rgba(249,115,22,0.24)] sm:p-6">
            <div
              aria-hidden
              className="absolute -right-12 -top-16 h-44 w-44 rounded-full border-[28px] border-white/10"
            />
            <div
              aria-hidden
              className="absolute -bottom-20 left-1/3 h-40 w-40 rounded-full bg-white/10 blur-2xl"
            />
            <div className="relative flex items-start gap-4">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-white/25 bg-white/15 shadow-inner backdrop-blur">
                <StepIcon className="h-6 w-6" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-orange-100">
                  {ROLE_LABELS[role]} walkthrough
                </p>
                <h2 className="mt-1 text-xl font-bold leading-tight sm:text-2xl">
                  {activeStep.title}
                </h2>
                {stepIndex === 0 && (
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-orange-50">
                    {activeStep.description}
                  </p>
                )}
              </div>
            </div>
          </div>

          {activeStep.pillars ? (
            <div className="grid gap-3 sm:grid-cols-3" aria-label="SashaInfinity pillars">
              {PILLARS.map((pillar) => {
                const PillarIcon = pillar.icon;
                return (
                  <article
                    key={pillar.name}
                    className="rounded-2xl border border-orange-100 bg-gradient-to-b from-orange-50/90 to-white p-4 shadow-sm"
                  >
                    <div className="mb-3 grid h-9 w-9 place-items-center rounded-xl bg-orange-100 text-orange-700">
                      <PillarIcon className="h-4.5 w-4.5" />
                    </div>
                    <h3 className="font-bold text-slate-900">{pillar.name}</h3>
                    <p className="text-xs font-semibold text-orange-700">
                      {pillar.label}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-slate-600">
                      {pillar.detail}
                    </p>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-4 sm:p-5">
              <p className="text-sm leading-6 text-slate-600">
                {activeStep.description}
              </p>
              <ul className="mt-4 grid gap-3 sm:grid-cols-3">
                {activeStep.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-2 rounded-xl bg-orange-50/70 p-3 text-sm leading-5 text-slate-700"
                  >
                    <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-orange-500 text-white">
                      <Check className="h-3 w-3" />
                    </span>
                    {feature}
                  </li>
                ))}
              </ul>
              {activeStep.to && (
                <button
                  type="button"
                  onClick={explore}
                  className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-orange-700 transition hover:text-orange-800"
                >
                  <PlayCircle className="h-4 w-4" />
                  {activeStep.actionLabel || "Explore this feature"}
                  <ArrowRight className="h-4 w-4" />
                </button>
              )}
            </div>
          )}

          <div className="flex items-center justify-between gap-4">
            <div className="flex gap-1.5" aria-label="Tour progress">
              {steps.map((step, index) => (
                <button
                  key={step.id}
                  type="button"
                  onClick={() => move(index)}
                  aria-label={`Go to tour step ${index + 1}: ${step.title}`}
                  aria-current={index === stepIndex ? "step" : undefined}
                  className={`h-2 rounded-full transition-all ${
                    index === stepIndex
                      ? "w-7 bg-orange-500"
                      : index < stepIndex
                        ? "w-2 bg-orange-300"
                        : "w-2 bg-slate-200 hover:bg-orange-200"
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-slate-500">
              You can reopen this tour anytime using
              <span className="font-semibold text-slate-700"> How it works</span>.
            </p>
          </div>
        </div>
      </GlassDialog>
    </ProductTourContext.Provider>
  );
}

export function useProductTour(): ProductTourContextValue {
  const context = React.useContext(ProductTourContext);
  if (!context) {
    throw new Error("useProductTour must be used inside ProductTourProvider");
  }
  return context;
}

export const productTourVersion = TOUR_VERSION;
export const productTourStorageKey = storageKey;
