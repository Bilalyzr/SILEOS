import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  ClipboardList,
  FileCheck2,
  GraduationCap,
  ListFilter,
  Plus,
  Search,
  Sparkles,
  UserCheck,
  UserPlus,
  Users,
} from "lucide-react";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import {
  ADMISSION_STAGES,
  campusOsApi,
  campusOsKeys,
  type AdmissionApplicationListItem,
  type AdmissionApplicationsPage,
  type CampusOsRole,
  useAdmissionApplications,
  useAdmissionIntakes,
  useAdmissionPrograms,
  useAdmissionSummary,
} from "@/api/campus-os";
import { PageBanner } from "@/components/design-system/PageBanner";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatDate,
  initials,
  readable,
} from "./CampusOsPrimitives";
import "@/styles/campus-os.css";

export interface CampusAdmissionsProps {
  data: InstitutionOverview;
  role?: CampusOsRole;
  demo?: boolean;
}

const PAGE_SIZE = 25;

function stageTone(stage: string) {
  if (stage === "enrolled" || stage === "admitted") return "success" as const;
  if (stage === "rejected" || stage === "withdrawn") return "danger" as const;
  if (stage === "documents" || stage === "waitlisted") return "warning" as const;
  return "orange" as const;
}

function applicationStageOptions(current: string) {
  return Array.from(new Set([current, ...ADMISSION_STAGES]));
}

export function CampusAdmissions({
  data,
  role,
  demo = false,
}: CampusAdmissionsProps) {
  const viewerRole = role ?? data.institution.role;
  const canManage = viewerRole === "owner" || viewerRole === "admin";
  const institutionId = canManage ? data.institution.id : 0;
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [stage, setStage] = useState("");
  const [intakeId, setIntakeId] = useState(0);
  const [offset, setOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState(0);
  const [formError, setFormError] = useState("");

  const summary = useAdmissionSummary(institutionId, demo);
  const programs = useAdmissionPrograms(institutionId, demo);
  const intakes = useAdmissionIntakes(institutionId, demo);
  const filters = useMemo(
    () => ({
      search: deferredSearch || undefined,
      stage: stage || undefined,
      intake_id: intakeId || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [deferredSearch, intakeId, offset, stage],
  );
  const applications = useAdmissionApplications(institutionId, filters, demo);

  const createApplication = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const fields = new FormData(form);
      const programId = Number(fields.get("program_id"));
      const selectedIntakeId = Number(fields.get("intake_id"));
      if (!programId || !selectedIntakeId) throw new Error("Choose a programme and an open intake.");
      if (demo) return null;
      return campusOsApi.createAdmissionApplication(data.institution.id, {
        full_name: String(fields.get("full_name") || "").trim(),
        email: String(fields.get("email") || "").trim(),
        phone: String(fields.get("phone") || "").trim(),
        program_id: programId,
        intake_id: selectedIntakeId,
        date_of_birth: String(fields.get("date_of_birth") || "") || null,
        address: String(fields.get("address") || "").trim(),
        prior_institution: String(fields.get("prior_institution") || "").trim(),
        source: "manual",
      });
    },
    onSuccess: async () => {
      if (!demo) {
        await queryClient.invalidateQueries({ queryKey: campusOsKeys.admissions(data.institution.id) });
      }
      setCreateOpen(false);
      setFormError("");
      toast.success(demo ? "Preview form checked" : "Application created");
    },
    onError: (cause) => setFormError(errorMessage(cause, "We couldn’t create this application.")),
  });

  const updateStage = useMutation({
    mutationFn: ({ application, nextStage }: { application: AdmissionApplicationListItem; nextStage: string }) =>
      demo
        ? Promise.resolve({ ...application, stage: nextStage })
        : campusOsApi.updateAdmissionStage(
            data.institution.id,
            application.id,
            nextStage,
            application.version,
          ),
    onSuccess: (updated, variables) => {
      queryClient.setQueriesData<AdmissionApplicationsPage>(
        { queryKey: [...campusOsKeys.admissions(data.institution.id), "applications"] },
        (current) =>
          current
            ? {
                ...current,
                items: current.items.map((item) =>
                  item.id === variables.application.id
                    ? { ...item, ...updated, stage: variables.nextStage }
                    : item,
                ),
              }
            : current,
      );
      if (!demo) void queryClient.invalidateQueries({ queryKey: campusOsKeys.admissions(data.institution.id) });
      toast.success(`Moved to ${readable(variables.nextStage)}`);
    },
    onError: (cause) => toast.error(errorMessage(cause, "The application changed elsewhere. Refresh and try again.")),
  });

  function changeStage(value: string) {
    setStage(value);
    setOffset(0);
  }

  if (!canManage) {
    return (
      <section className="campus-os" aria-label="Admissions workspace">
        <div className="campus-os-banner">
          <PageBanner
            eyebrow="Admissions workspace"
            title="Admissions records are managed by your campus office."
            description="Applicants’ personal information and decisions are limited to authorised owners and administrators."
          />
        </div>
        <div className="campus-os-panel">
          <CampusOsEmpty
            icon={FileCheck2}
            title="Private admissions workspace"
            description="Ask an institution owner or administrator if you need access for admissions work."
          />
        </div>
      </section>
    );
  }

  const stageCounts = summary.data?.stage_counts ?? [];
  const filteredIntakes = (intakes.data ?? []).filter(
    (intake) => !selectedProgram || intake.program_id === selectedProgram,
  );
  const pageStart = applications.data?.total ? offset + 1 : 0;
  const pageEnd = Math.min(offset + PAGE_SIZE, applications.data?.total ?? 0);

  return (
    <section className="campus-os" aria-label="Admissions workspace">
      <div className="campus-os-banner">
        <PageBanner
          eyebrow="Admissions · Applicant to learner"
          title="Turn every enquiry into a confident first day."
          description="Guide applicants through documents, review, offers and enrolment with a clear record of every decision."
          share
          shareTitle={`${data.institution.name} admissions`}
          shareDescription={`Explore programmes and admissions at ${data.institution.name}.`}
          actions={
            <Button leftIcon={<UserPlus size={16} />} onClick={() => setCreateOpen(true)}>
              Add application
            </Button>
          }
        />
      </div>

      {summary.isPending && <CampusOsLoading label="Loading admissions overview" />}
      {summary.isError && (
        <CampusOsError
          message="The admissions overview couldn’t be loaded."
          retry={() => void summary.refetch()}
        />
      )}

      {summary.data && (
        <>
          <div className="campus-os-metric-grid" aria-label="Admissions key numbers">
            {[
              { label: "Active applications", value: summary.data.counts.active, detail: `${summary.data.counts.total} received`, icon: Users, tone: "orange" },
              { label: "Offers issued", value: summary.data.counts.offered, detail: `${summary.data.counts.admitted} accepted`, icon: FileCheck2, tone: "success" },
              { label: "Enrolled", value: summary.data.counts.enrolled, detail: "Converted to learners", icon: GraduationCap, tone: "success" },
              { label: "Tasks overdue", value: summary.data.tasks.overdue, detail: `${summary.data.tasks.open} open tasks`, icon: ClipboardList, tone: summary.data.tasks.overdue ? "danger" : "neutral" },
            ].map((item) => (
              <article className="campus-os-metric" data-tone={item.tone} key={item.label}>
                <div className="campus-os-metric-head">
                  <span>{item.label}</span>
                  <span className="campus-os-metric-icon"><item.icon size={17} aria-hidden="true" /></span>
                </div>
                <strong>{item.value}</strong>
                <footer>{item.detail}</footer>
              </article>
            ))}
          </div>

          <section aria-labelledby="admissions-pipeline-title">
            <div className="campus-os-row-between mb-3">
              <div>
                <span className="campus-os-section-label">Live funnel</span>
                <h2 id="admissions-pipeline-title" className="mt-1 text-lg font-semibold text-stone-800">Applicant pipeline</h2>
              </div>
              {stage && (
                <Button size="sm" variant="ghost" onClick={() => changeStage("")}>Clear stage</Button>
              )}
            </div>
            <div className="campus-os-pipeline" aria-label="Filter applications by stage">
              <button className="campus-os-stage" type="button" aria-pressed={!stage} onClick={() => changeStage("")}>
                <span>All active</span>
                <strong>{summary.data.counts.active}</strong>
              </button>
              {stageCounts.map((item) => (
                <button className="campus-os-stage" type="button" key={item.stage} aria-pressed={stage === item.stage} onClick={() => changeStage(item.stage)}>
                  <span>{readable(item.stage)}</span>
                  <strong>{item.count}</strong>
                </button>
              ))}
            </div>
          </section>

          <div className="campus-os-columns">
            <section className="campus-os-panel" aria-labelledby="applications-title">
              <header className="campus-os-panel-head">
                <div>
                  <span className="campus-os-section-label">Applicant records</span>
                  <h2 id="applications-title">Applications</h2>
                  <p>Search, filter and move each applicant to their next step.</p>
                </div>
                <CampusOsBadge>{applications.data?.total ?? 0} results</CampusOsBadge>
              </header>
              <div className="campus-os-panel-body">
                <div className="campus-os-toolbar my-3">
                  <div className="campus-os-filters">
                    <label className="campus-os-field-wrap">
                      <span className="sr-only">Search applications</span>
                      <Search size={16} aria-hidden="true" />
                      <input
                        className="campus-os-control"
                        type="search"
                        value={search}
                        placeholder="Search name, email or application number"
                        onChange={(event) => { setSearch(event.target.value); setOffset(0); }}
                      />
                    </label>
                    <label>
                      <span className="sr-only">Filter by intake</span>
                      <select className="campus-os-control" value={intakeId} onChange={(event) => { setIntakeId(Number(event.target.value)); setOffset(0); }}>
                        <option value={0}>Every intake</option>
                        {intakes.data?.map((intake) => <option key={intake.id} value={intake.id}>{intake.program_name} · {intake.name}</option>)}
                      </select>
                    </label>
                    <span className="campus-os-badge"><ListFilter size={13} aria-hidden="true" /> {stage ? readable(stage) : "Every stage"}</span>
                  </div>
                </div>

                {applications.isPending && <CampusOsLoading label="Loading applications" />}
                {applications.isError && (
                  <CampusOsError message="Applications couldn’t be loaded." retry={() => void applications.refetch()} />
                )}
                {applications.data && !applications.data.items.length && (
                  <CampusOsEmpty
                    icon={UserCheck}
                    title={search || stage || intakeId ? "No applications match" : "Your first application starts here"}
                    description={search || stage || intakeId ? "Change the search or filters to see more applicants." : "Capture an application and guide it from submission to enrolment."}
                    action={!search && !stage && !intakeId ? <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Add application</Button> : undefined}
                  />
                )}
                {!!applications.data?.items.length && (
                  <div className="campus-table-wrap">
                    <table className="campus-table campus-os-table">
                      <caption className="sr-only">Admissions applications</caption>
                      <thead><tr><th>Applicant</th><th className="campus-os-hide-mobile">Programme</th><th>Stage</th><th className="campus-os-hide-mobile">Updated</th></tr></thead>
                      <tbody>
                        {applications.data.items.map((application) => (
                          <tr key={application.id}>
                            <td>
                              <div className="campus-os-person">
                                <span className="campus-os-avatar" aria-hidden="true">{initials(application.full_name)}</span>
                                <span>
                                  <strong>{application.full_name}</strong>
                                  <small>{application.application_number} · {application.email}</small>
                                </span>
                              </div>
                            </td>
                            <td className="campus-os-hide-mobile">{application.program_name}<small>{application.intake_name}</small></td>
                            <td>
                              <label>
                                <span className="sr-only">Stage for {application.full_name}</span>
                                <select
                                  className="campus-os-stage-select"
                                  aria-label={`Stage for ${application.full_name}`}
                                  value={application.stage}
                                  disabled={updateStage.isPending}
                                  onChange={(event) => updateStage.mutate({ application, nextStage: event.target.value })}
                                >
                                  {applicationStageOptions(application.stage).map((option) => <option key={option} value={option}>{readable(option)}</option>)}
                                </select>
                              </label>
                              {application.offer_status !== "none" && <small><CampusOsBadge tone={stageTone(application.stage)}>Offer {readable(application.offer_status)}</CampusOsBadge></small>}
                            </td>
                            <td className="campus-os-hide-mobile">{formatDate(application.updated_at)}<small>{readable(application.source)}</small></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="campus-os-pagination" aria-label="Application pages">
                      <span>{pageStart}–{pageEnd} of {applications.data.total}</span>
                      <button className="campus-os-icon-button" type="button" aria-label="Previous applications page" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><ArrowLeft size={15} /></button>
                      <button className="campus-os-icon-button" type="button" aria-label="Next applications page" disabled={pageEnd >= applications.data.total} onClick={() => setOffset(offset + PAGE_SIZE)}><ArrowRight size={15} /></button>
                    </div>
                  </div>
                )}
              </div>
            </section>

            <aside className="campus-os-panel" aria-labelledby="intake-capacity-title">
              <header className="campus-os-panel-head">
                <div>
                  <span className="campus-os-section-label">Seat planning</span>
                  <h2 id="intake-capacity-title">Intake capacity</h2>
                  <p>Enrolment against available seats.</p>
                </div>
              </header>
              <div className="campus-os-panel-body pt-4">
                {!summary.data.intakes.length ? (
                  <CampusOsEmpty icon={GraduationCap} title="No intake yet" description="Create a programme intake to start accepting applications." />
                ) : (
                  <div className="campus-os-capacity-list">
                    {summary.data.intakes.map((intake) => {
                      const percent = intake.capacity ? Math.min(100, Math.round((intake.enrolled / intake.capacity) * 100)) : 0;
                      return (
                        <article className="campus-os-capacity" key={intake.id}>
                          <div className="campus-os-row-between">
                            <h3>{intake.program_name}</h3>
                            <CampusOsBadge tone={percent >= 90 ? "warning" : "neutral"}>{intake.available} open</CampusOsBadge>
                          </div>
                          <p>{intake.enrolled} enrolled · {intake.applications} applications</p>
                          <div className="campus-os-capacity-track" role="progressbar" aria-label={`${intake.program_name} seats filled`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}><span style={{ width: `${percent}%` }} /></div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
            </aside>
          </div>
        </>
      )}

      <GlassDialog
        open={createOpen}
        onOpenChange={(open) => { setCreateOpen(open); if (!open) setFormError(""); }}
        title="Add an application"
        eyebrow="Admissions"
        description="Capture the applicant once. Their generated application number and complete history stay with this record."
        size="lg"
      >
        <form
          className="campus-form"
          onSubmit={(event) => { event.preventDefault(); setFormError(""); createApplication.mutate(event.currentTarget); }}
        >
          {demo && <p className="campus-notice"><Sparkles size={14} className="mr-2 inline" />Preview mode checks the form without creating a real record.</p>}
          {formError && <p className="campus-error" role="alert">{formError}</p>}
          <div className="campus-form-grid">
            <label>Full name<input name="full_name" required maxLength={160} autoComplete="name" /></label>
            <label>Email address<input name="email" type="email" required maxLength={254} autoComplete="email" /></label>
          </div>
          <div className="campus-form-grid">
            <label>Phone number<input name="phone" type="tel" maxLength={32} autoComplete="tel" /></label>
            <label>Date of birth<input name="date_of_birth" type="date" /></label>
          </div>
          <div className="campus-form-grid">
            <label>Programme<select name="program_id" required value={selectedProgram} onChange={(event) => setSelectedProgram(Number(event.target.value))}><option value={0}>Choose programme</option>{programs.data?.filter((program) => program.status === "active").map((program) => <option key={program.id} value={program.id}>{program.name}</option>)}</select></label>
            <label>Intake<select name="intake_id" required defaultValue={0} key={selectedProgram}><option value={0}>Choose intake</option>{filteredIntakes.filter((intake) => intake.status === "open" || intake.status === "draft").map((intake) => <option key={intake.id} value={intake.id}>{intake.name} · {intake.available} seats open</option>)}</select></label>
          </div>
          <label>Previous institution<input name="prior_institution" maxLength={200} /></label>
          <label>Address<textarea name="address" maxLength={1000} rows={3} /></label>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createApplication.isPending}>Create application</Button>
          </div>
        </form>
      </GlassDialog>
    </section>
  );
}

export default CampusAdmissions;
