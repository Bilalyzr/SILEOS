import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import * as React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Upload,
  FileText,
  Loader2,
  Eye,
  EyeOff,
  CheckCircle2,
} from "lucide-react";
import toast from "react-hot-toast";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

import { TagInput } from "@/components/candidate/TagInput";
import { candidateAPI, CandidateProfile } from "@/api/candidate";
import { uploadDocument } from "@/api/upload";

const SKILL_SUGGESTIONS = [
  "React",
  "TypeScript",
  "Python",
  "FastAPI",
  "Node.js",
  "SQL",
  "AWS",
  "Docker",
  "Kubernetes",
  "Figma",
  "Machine Learning",
  "Data Analysis",
];
const ROLE_SUGGESTIONS = [
  "Frontend Intern",
  "Backend Intern",
  "Full-Stack Intern",
  "Data Analyst Intern",
  "Product Intern",
  "Design Intern",
  "ML Engineer Intern",
  "DevOps Intern",
];

export const InternshipProfilePage: React.FC = () => {
  const [profile, setProfile] = React.useState<CandidateProfile | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);

  const [bio, setBio] = React.useState("");
  const [skills, setSkills] = React.useState<string[]>([]);
  const [preferredRoles, setPreferredRoles] = React.useState<string[]>([]);
  const [availabilityDate, setAvailabilityDate] = React.useState("");
  const [linkedinUrl, setLinkedinUrl] = React.useState("");
  const [githubUrl, setGithubUrl] = React.useState("");
  const [portfolioUrl, setPortfolioUrl] = React.useState("");
  const [resumeUrl, setResumeUrl] = React.useState("");

  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const hydrate = React.useCallback((p: CandidateProfile) => {
    setProfile(p);
    setBio(p.bio ?? "");
    setSkills(p.skills ?? []);
    setPreferredRoles(p.preferred_roles ?? []);
    setAvailabilityDate(
      p.availability_date ? p.availability_date.slice(0, 10) : "",
    );
    setLinkedinUrl(p.linkedin_url ?? "");
    setGithubUrl(p.github_url ?? "");
    setPortfolioUrl(p.portfolio_url ?? "");
    setResumeUrl(p.resume_url ?? "");
  }, []);

  React.useEffect(() => {
    candidateAPI
      .getMe()
      .then(hydrate)
      .catch((e: any) => toast.error(e?.message || "Failed to load profile"))
      .finally(() => setLoading(false));
  }, [hydrate]);

  const onResumeSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      toast.error("Resume must be a PDF file");
      return;
    }
    setUploading(true);
    try {
      // Use resume context to allow students to upload
      const res = await uploadDocument(file, undefined, "resume");
      setResumeUrl(res.file_url);
      toast.success("Resume uploaded");
    } catch (err: any) {
      toast.error(err?.message || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const onSave = async () => {
    // Validate LinkedIn is required
    if (!linkedinUrl?.trim()) {
      toast.error("LinkedIn URL is required");
      return;
    }

    // Validate unique links - all three must be different
    const links = [linkedinUrl, githubUrl, portfolioUrl].filter(Boolean);
    const uniqueLinks = new Set(links);
    if (links.length !== uniqueLinks.size) {
      toast.error("LinkedIn, GitHub, and Portfolio URLs must be unique");
      return;
    }

    setSaving(true);
    try {
      const next = await candidateAPI.updateMe({
        bio,
        skills,
        preferred_roles: preferredRoles,
        availability_date: availabilityDate || null,
        linkedin_url: linkedinUrl,
        github_url: githubUrl,
        portfolio_url: portfolioUrl,
        resume_url: resumeUrl,
      });
      hydrate(next);
      toast.success("Profile saved");
    } catch (e: any) {
      toast.error(e?.message || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const onToggleVisibility = async () => {
    if (!profile) return;
    try {
      const next = await candidateAPI.setVisibility(!profile.is_visible);
      hydrate(next);
      toast.success(next.is_visible ? "Visible to companies" : "Hidden");
    } catch (e: any) {
      toast.error(e?.message || "Failed to update");
    }
  };

  if (loading) {
    return (
      <div className="container-custom flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
      </div>
    );
  }

  const completeness = profile?.completeness ?? 0;
  const eligible = !!profile?.eligibility?.eligible;

  return (
    <div className="min-h-screen bg-neutral-50">
      <PageLayout
        header={
          <PageHeader>
            <h1 className="text-2xl sm:text-3xl font-bold text-neutral-900">
              Internship Profile
            </h1>
            <p className="text-sm sm:text-base text-neutral-600">
              Build a profile that helps companies find you for internships.
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-dashboard-internship-profile"
      >
        <Link
          to="/dashboard"
          className="mb-4 sm:mb-6 inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-primary-600 min-h-[44px]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
        <Card className="mb-4 sm:mb-6">
          <CardContent className="p-4 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3 sm:gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    {eligible ? (
                      <Badge variant="success">Eligible</Badge>
                    ) : (
                      <Badge variant="neutral">Not eligible yet</Badge>
                    )}
                    {profile?.eligibility?.source && (
                      <Badge variant="outline" className="text-xs">
                        {profile.eligibility.source === "auto_certificate"
                          ? "via certificate"
                          : "via SPOC"}
                      </Badge>
                    )}
                  </div>
                  {!eligible && (
                    <p className="mt-1 text-xs text-neutral-500 max-w-[280px]">
                      Complete a course to earn your certificate — eligibility
                      is granted automatically.
                    </p>
                  )}
                </div>
              </div>

              <Button
                variant={profile?.is_visible ? "outline" : "default"}
                size="sm"
                onClick={onToggleVisibility}
                disabled={!eligible}
                className="min-h-[44px] w-full sm:w-auto"
              >
                {profile?.is_visible ? (
                  <>
                    <EyeOff className="mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">
                      Hide from companies
                    </span>
                    <span className="sm:hidden">Hide</span>
                  </>
                ) : (
                  <>
                    <Eye className="mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">
                      Go visible to companies
                    </span>
                    <span className="sm:hidden">Go visible</span>
                  </>
                )}
              </Button>
            </div>

            <div className="mt-4">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-neutral-600">Profile completeness</span>
                <span className="font-medium">{completeness}%</span>
              </div>
              <Progress value={completeness} className="h-2" />
              {completeness === 100 && (
                <div className="mt-2 flex items-center gap-1 text-xs text-success-700">
                  <CheckCircle2 className="h-3 w-3" />
                  Your profile is complete!
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        <Card className="mb-4 sm:mb-6">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg sm:text-xl">Resume (PDF)</CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0 space-y-3">
            {resumeUrl ? (
              <div className="flex items-center justify-between rounded-md bg-neutral-50 p-3">
                <a
                  href={resumeUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-sm text-primary-700 hover:underline min-h-[44px] flex items-center"
                >
                  <FileText className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">View uploaded resume</span>
                </a>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setResumeUrl("")}
                  className="min-h-[40px]"
                >
                  Remove
                </Button>
              </div>
            ) : (
              <p className="text-sm text-neutral-500">
                No resume uploaded yet.
              </p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={onResumeSelect}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="min-h-[44px] w-full sm:w-auto"
            >
              {uploading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {resumeUrl ? "Replace resume" : "Upload resume"}
            </Button>
          </CardContent>
        </Card>
        <Card className="mb-4 sm:mb-6">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg sm:text-xl">About you</CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0">
            <textarea
              className="min-h-[120px] w-full rounded-md border border-neutral-300 bg-white p-3 text-base outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
              placeholder="A short intro companies will read first. What are you building? What do you care about?"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={2000}
              style={{ fontSize: "16px" }}
            />
            <div className="mt-1 text-right text-xs text-neutral-400">
              {bio.length}/2000
            </div>
          </CardContent>
        </Card>
        <Card className="mb-4 sm:mb-6">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg sm:text-xl">Skills</CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0">
            <TagInput
              value={skills}
              onChange={setSkills}
              placeholder="Add a skill and press Enter"
              suggestions={SKILL_SUGGESTIONS}
            />
          </CardContent>
        </Card>
        <Card className="mb-4 sm:mb-6">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg sm:text-xl">
              Preferred roles
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0">
            <TagInput
              value={preferredRoles}
              onChange={setPreferredRoles}
              placeholder="e.g. Frontend Intern"
              suggestions={ROLE_SUGGESTIONS}
            />
          </CardContent>
        </Card>
        <Card className="mb-6">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg sm:text-xl">
              Availability & links
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0 grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Available from
              </label>
              <Input
                type="date"
                value={availabilityDate}
                onChange={(e) => setAvailabilityDate(e.target.value)}
                className="h-12"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                LinkedIn URL <span className="text-red-600">*</span>
              </label>
              <Input
                type="url"
                placeholder="https://linkedin.com/in/you"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                required
                className="h-12"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                GitHub URL
              </label>
              <Input
                type="url"
                placeholder="https://github.com/you"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                className="h-12"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Portfolio URL
              </label>
              <Input
                type="url"
                placeholder="https://yourportfolio.com"
                value={portfolioUrl}
                onChange={(e) => setPortfolioUrl(e.target.value)}
                className="h-12"
              />
            </div>
          </CardContent>
        </Card>
        <div className="sticky bottom-0 bg-white border-t border-neutral-200 p-4 flex flex-col sm:flex-row items-center justify-end gap-2 sm:gap-3 shadow-lg">
          <Button
            variant="outline"
            asChild
            className="w-full sm:w-auto min-h-[44px]"
          >
            <Link to="/dashboard">Cancel</Link>
          </Button>
          <Button
            onClick={onSave}
            disabled={saving}
            className="w-full sm:w-auto min-h-[44px]"
          >
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save profile
          </Button>
        </div>
      </PageLayout>
    </div>
  );
};

export default InternshipProfilePage;
