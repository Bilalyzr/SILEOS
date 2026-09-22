export type BusinessVerticalKey = "meiporul" | "seyappaduporul" | "utporul";

export type DeliveryState = "live" | "foundation" | "planned";

export interface VerticalWorkspace {
  title: string;
  description: string;
  href: string;
  adminHref?: string;
  state: DeliveryState;
}

export interface RevenueModel {
  key: string;
  label: string;
  model: string;
}

export interface BusinessVertical {
  key: BusinessVerticalKey;
  code: "MA1" | "MA2" | "MA3";
  label: string;
  tamil: string;
  eyebrow: string;
  promise: string;
  description: string;
  route: string;
  subdomain: string;
  color: "violet" | "emerald" | "sky";
  workspaces: VerticalWorkspace[];
  revenueModels: RevenueModel[];
  integrations: string[];
}

export const BUSINESS_VERTICALS: Record<BusinessVerticalKey, BusinessVertical> = {
  meiporul: {
    key: "meiporul",
    code: "MA1",
    label: "Meiporul",
    tamil: "மெய்ப்பொருள்",
    eyebrow: "Immersive learning pillar",
    promise: "Learn with the object, not only its description.",
    description:
      "The home for 3D-integrated curriculum, reusable GLB objects, AR and VR experiences, GeoGebra interactives, and measurable virtual labs.",
    route: "/meiporul",
    subdomain: "meiporul.sashainfinity.com",
    color: "violet",
    workspaces: [
      { title: "Immersive curriculum", description: "Public courses that combine lessons, 3D objects, interactives, and assessment.", href: "/courses?course_type=meiporul", adminHref: "/admin/courses", state: "live" },
      { title: "AR and 3D gallery", description: "Discover reusable models and launch supported objects in augmented reality.", href: "/meiporul-ar", adminHref: "/admin/content-libraries", state: "live" },
      { title: "Experiential labs", description: "Run guided investigations and WebXR-capable virtual lab activities.", href: "/labs", adminHref: "/admin/content-libraries", state: "live" },
      { title: "Lab Studio", description: "Author investigations, attach GLB models, and publish them into curriculum.", href: "/instructor/lab-studio", adminHref: "/admin/lab-studio", state: "live" },
      { title: "Fleet and lab deployment", description: "Headset rooms, safety controls, installation, and AMC operations.", href: "/admin/operations?view=meiporul", state: "live" },
    ],
    revenueModels: [
      { key: "immersive_courses", label: "Immersive course sales", model: "Per course, bundle, or membership" },
      { key: "asset_licensing", label: "3D asset licensing", model: "Per asset, classroom, school, or enterprise" },
      { key: "experience_subscription", label: "Experience subscriptions", model: "Monthly or annual per classroom" },
      { key: "lab_deployment", label: "Lab deployment", model: "Hardware, installation, training, and EMI" },
      { key: "amc_support", label: "AMC and field support", model: "Annual contract and service parts" },
    ],
    integrations: ["Utporul course blocks", "Shared learner identity", "xAPI learning evidence", "Central revenue reporting"],
  },
  seyappaduporul: {
    key: "seyappaduporul",
    code: "MA2",
    label: "Seyappaduporul",
    tamil: "செயப்படுபொருள்",
    eyebrow: "Tutoring and operations pillar",
    promise: "Run every class, fee, resource, and learner handoff under one roof.",
    description:
      "The operating home for schools and tutoring centers: live classes, attendance, fee collection, schedules, notebooks, ebooks, question papers, staff, and parent visibility.",
    route: "/seyappaduporul",
    subdomain: "seyappaduporul.sashainfinity.com",
    color: "emerald",
    workspaces: [
      { title: "Institution operations", description: "Manage campuses, admissions, timetables, attendance, exams, staff, transport, and hostel workflows.", href: "/institutions", state: "live" },
      { title: "Live tutoring", description: "Schedule, deliver, record, and report instructor-led classes.", href: "/student/live-classes", adminHref: "/admin/past-classes", state: "live" },
      { title: "Fees and finance", description: "Publish plans, collect online or offline fees, issue receipts, and reconcile payments.", href: "/campus", adminHref: "/institutions", state: "live" },
      { title: "Digital library", description: "Share and sell books, guides, lecture notes, and course-linked resources.", href: "/library", adminHref: "/admin/content-libraries", state: "live" },
      { title: "Practice paper generator", description: "Create school and entrance-exam question papers with centrally controlled pricing.", href: "/exam-papers", adminHref: "/admin/exam-pricing", state: "live" },
    ],
    revenueModels: [
      { key: "tuition_fees", label: "Tutoring and school fees", model: "Recurring plans and installments" },
      { key: "institution_operations", label: "Institution operations", model: "Subscription, per learner, or managed service" },
      { key: "digital_resources", label: "Books and notes", model: "One-time sale, bundle, or included access" },
      { key: "paper_generation", label: "Assessment papers", model: "Per generated paper or institution plan" },
      { key: "franchise_services", label: "Franchise services", model: "Onboarding, technology fee, and royalty" },
    ],
    integrations: ["Utporul course engine", "Meiporul lab activities", "Shared parent and learner identity", "Central revenue reporting"],
  },
  utporul: {
    key: "utporul",
    code: "MA3",
    label: "Utporul",
    tamil: "உட்பொருள்",
    eyebrow: "Skills and course creation pillar",
    promise: "Turn expertise into assessable skills, credentials, and career outcomes.",
    description:
      "The common academic engine for all three pillars, with course authoring, quizzes, assessment workflows, certificates, creator commerce, and internships.",
    route: "/utporul",
    subdomain: "utporul.sashainfinity.com",
    color: "sky",
    workspaces: [
      { title: "Skill course catalog", description: "Discover public skill programs and outcome-led learning paths.", href: "/courses?course_type=utporul", adminHref: "/admin/courses", state: "live" },
      { title: "Course creation", description: "Build lessons, quizzes, assignments, live sessions, labs, 3D blocks, and credentials.", href: "/instructor/courses/create", adminHref: "/admin/courses/create", state: "live" },
      { title: "Assessment Studio", description: "Create governed question banks, adaptive practice, grading, and intervention flows.", href: "/instructor/assessment-studio", adminHref: "/admin/quizzes", state: "live" },
      { title: "Certificates", description: "Issue and publicly verify course and cohort credentials.", href: "/verify-certificate", adminHref: "/admin/certificates", state: "live" },
      { title: "Career bridge", description: "Connect institutions, cohorts, verified skills, internships, and companies.", href: "/internships", adminHref: "/admin/internships", state: "live" },
      { title: "Live coding assessment", description: "Run sandboxed programming tests with visible and hidden cases.", href: "/coding", state: "live" },
    ],
    revenueModels: [
      { key: "skill_courses", label: "Course sales", model: "One-time, cohort, bundle, or membership" },
      { key: "assessment_services", label: "Assessment services", model: "Per attempt, seat, or institution license" },
      { key: "credentials", label: "Premium credentials", model: "Included or paid verification tier" },
      { key: "creator_commerce", label: "Creator commerce", model: "Revenue share and affiliate commission" },
      { key: "career_services", label: "Career and internship services", model: "Listing, connection, subscription, or success fee" },
    ],
    integrations: ["Shared authoring engine", "Meiporul 3D and lab blocks", "Seyappaduporul live delivery", "Central revenue reporting"],
  },
};

export const BUSINESS_VERTICAL_KEYS = Object.keys(BUSINESS_VERTICALS) as BusinessVerticalKey[];

const ALIASES: Record<string, BusinessVerticalKey> = {
  meiporul: "meiporul",
  ma1: "meiporul",
  seyappaduporul: "seyappaduporul",
  "seyappadu-porul": "seyappaduporul",
  "seyappadu porul": "seyappaduporul",
  seyappadu_porul: "seyappaduporul",
  ma2: "seyappaduporul",
  utporul: "utporul",
  upporul: "utporul",
  ma3: "utporul",
};

export function normalizeBusinessVertical(value?: string | null): BusinessVerticalKey | null {
  if (!value) return null;
  return ALIASES[value.trim().toLowerCase()] ?? null;
}

export function verticalFromHostname(hostname: string): BusinessVerticalKey | null {
  const firstLabel = hostname.trim().toLowerCase().split(".")[0];
  return normalizeBusinessVertical(firstLabel);
}

export function verticalPublicHref(
  key: BusinessVerticalKey,
  hostname = typeof window === "undefined" ? "" : window.location.hostname,
): string {
  const normalizedHost = hostname.trim().toLowerCase();
  if (
    normalizedHost === "sashainfinity.com" ||
    normalizedHost.endsWith(".sashainfinity.com")
  ) {
    return `https://${BUSINESS_VERTICALS[key].subdomain}`;
  }
  return BUSINESS_VERTICALS[key].route;
}
