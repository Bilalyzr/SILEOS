import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  MessageCircle,
  Megaphone,
  RefreshCw,
  Send,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { whatsappApi } from "@/api/whatsapp";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";

const AUDIENCE_ROLES = [
  ["student", "Students"],
  ["instructor", "Instructors"],
  ["parent", "Parents"],
  ["spoc", "SPOCs"],
  ["company", "Companies"],
  ["company_manager", "Company managers"],
  ["admin", "Admins"],
  ["superadmin", "SuperAdmins"],
] as const;

function readableError(cause: unknown) {
  const error = cause as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return error.response?.data?.detail || error.message || "Please try again.";
}

function friendlyDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function newCampaignRequestKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function AdminCommunicationsPage() {
  const [campaignOpen, setCampaignOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [bannerPreview, setBannerPreview] = useState("");
  const [campaignRequestKey, setCampaignRequestKey] = useState(() =>
    newCampaignRequestKey("platform"),
  );

  const overview = useQuery({
    queryKey: ["whatsapp-admin-overview"],
    queryFn: whatsappApi.adminOverview,
  });
  const contacts = useQuery({
    queryKey: ["whatsapp-admin-contacts", statusFilter, roleFilter, search],
    queryFn: () =>
      whatsappApi.adminContacts({
        status: statusFilter || undefined,
        role: roleFilter || undefined,
        search: search || undefined,
        offset: 0,
        limit: 100,
      }),
  });
  const campaigns = useQuery({
    queryKey: ["whatsapp-admin-campaigns"],
    queryFn: () => whatsappApi.adminCampaigns(100),
  });

  const canSend = Boolean(
    overview.data?.configured &&
      overview.data.webhook_ready &&
      overview.data.approved_templates.length,
  );

  async function createCampaign(form: HTMLFormElement) {
    const fields = new FormData(form);
    const roles = fields.getAll("roles").map(String);
    const parameters = String(fields.get("parameters") || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    if (!roles.length) {
      setError("Choose at least one recipient role.");
      return;
    }
    if (parameters.length > 10 || parameters.some((item) => item.length > 256)) {
      setError(
        "Use at most 10 template parameters, with no more than 256 characters on each line.",
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      await whatsappApi.createAdminCampaign({
        request_key: campaignRequestKey,
        template: String(fields.get("template")),
        language: String(fields.get("language")),
        parameters,
        roles,
        header_image_url: String(fields.get("banner") || "") || null,
      });
      setCampaignRequestKey(newCampaignRequestKey("platform"));
      setCampaignOpen(false);
      setBannerPreview("");
      await Promise.all([campaigns.refetch(), overview.refetch()]);
      toast.success("WhatsApp campaign queued once.");
    } catch (cause) {
      setError(readableError(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="campus mx-auto max-w-7xl py-2">
      <BrandBanner
        headingLevel="h1"
        eyebrow="SashaInfinity · Communications Center"
        title="Reach the right people, with permission."
        description="See provider health, understand your consented audience and send approved WhatsApp templates with delivery results in one place."
      >
        <Button
          leftIcon={<Send size={16} />}
          disabled={!canSend}
          onClick={() => setCampaignOpen(true)}
        >
          New WhatsApp campaign
        </Button>
        <Link className="brand-text-link" to="/communication-preferences">
          My communication preference →
        </Link>
      </BrandBanner>

      {(overview.isError || contacts.isError || campaigns.isError) && (
        <div className="campus-error" role="alert">
          Some communications data could not be loaded. {" "}
          <button
            type="button"
            onClick={() => {
              void overview.refetch();
              void contacts.refetch();
              void campaigns.refetch();
            }}
          >
            Retry
          </button>
        </div>
      )}

      {error && (
        <div className="campus-error" role="alert">
          {error}
        </div>
      )}

      {overview.isLoading ? (
        <div className="campus-skeleton" role="status" aria-label="Loading provider health" />
      ) : overview.data ? (
        <>
          <section className="campus-panel">
            <div className="campus-panel-heading">
              <div>
                <span className="campus-eyebrow">
                  <ShieldCheck size={14} /> Provider health
                </span>
                <h2 className="mt-2 text-xl font-bold text-secondary-900">
                  Official WhatsApp Cloud API
                </h2>
                <p className="campus-muted mt-2">
                  Configuration health for the whole SashaInfinity platform.
                </p>
              </div>
              <span
                className="campus-chip"
                data-tone={overview.data.configured ? "success" : "muted"}
              >
                {overview.data.configured ? "Ready" : "Setup needed"}
              </span>
            </div>
            <div className="campus-stats mt-5">
              <div className="campus-panel campus-stat">
                <div className="campus-stat-top">
                  <span>Business account</span>
                  <Settings2 size={17} />
                </div>
                <strong>
                  {overview.data.business_account_configured ? "Linked" : "Needed"}
                </strong>
                <small>Cloud API {overview.data.api_version}</small>
              </div>
              <div className="campus-panel campus-stat">
                <div className="campus-stat-top">
                  <span>Webhook</span>
                  <RefreshCw size={17} />
                </div>
                <strong>{overview.data.webhook_ready ? "Ready" : "Pending"}</strong>
                <small>Signed inbound and delivery events</small>
              </div>
              <div className="campus-panel campus-stat">
                <div className="campus-stat-top">
                  <span>Sending number</span>
                  <MessageCircle size={17} />
                </div>
                <strong>
                  {overview.data.business_phone_configured ? "Connected" : "Needed"}
                </strong>
                <small>{overview.data.display_phone_number || "Official business number"}</small>
              </div>
              <div className="campus-panel campus-stat">
                <div className="campus-stat-top">
                  <span>Templates</span>
                  <CheckCircle2 size={17} />
                </div>
                <strong>{overview.data.approved_templates.length}</strong>
                <small>Approved names available to send</small>
              </div>
            </div>
            {!canSend && (
              <div className="campus-notice mt-5">
                <strong>Campaign sending is paused.</strong>
                <p className="mt-2">
                  Complete the provider connection and add at least one approved
                  template before sending.
                </p>
                {!!overview.data.missing_fields.length && (
                  <p className="mt-2">
                    Missing: {overview.data.missing_fields.join(", ")}
                  </p>
                )}
              </div>
            )}
          </section>

          <section className="campus-panel">
            <div className="campus-panel-heading">
              <div>
                <span className="campus-eyebrow">
                  <Users size={14} /> Permission overview
                </span>
                <h2 className="mt-2 text-xl font-bold text-secondary-900">
                  Account-wide consent
                </h2>
              </div>
              <span className="campus-chip">
                {overview.data.consent_counts.total_users} accounts
              </span>
            </div>
            <div className="campus-stats mt-5">
              <div className="campus-panel campus-stat">
                <span>Confirmed</span>
                <strong>{overview.data.consent_counts.confirmed}</strong>
                <small>Eligible after role and activity checks</small>
              </div>
              <div className="campus-panel campus-stat">
                <span>Pending</span>
                <strong>{overview.data.consent_counts.pending}</strong>
                <small>Waiting for JOIN confirmation</small>
              </div>
              <div className="campus-panel campus-stat">
                <span>Not started</span>
                <strong>{overview.data.consent_counts.not_started}</strong>
                <small>No WhatsApp preference recorded</small>
              </div>
              <div className="campus-panel campus-stat">
                <span>Withdrawn</span>
                <strong>{overview.data.consent_counts.revoked}</strong>
                <small>Excluded from every campaign</small>
              </div>
            </div>
            {!!Object.keys(overview.data.eligible_by_role).length && (
              <div className="campus-actions mt-5">
                {Object.entries(overview.data.eligible_by_role).map(
                  ([role, count]) => (
                    <span className="campus-chip" key={role}>
                      {role.replace(/_/g, " ")} · {count}
                    </span>
                  ),
                )}
              </div>
            )}
          </section>
        </>
      ) : null}

      <section className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <h2 className="text-xl font-bold text-secondary-900">
              Consent directory
            </h2>
            <p className="campus-muted mt-2">
              Review account choices. Administrators cannot opt in for another person.
            </p>
          </div>
          <span className="campus-chip">{contacts.data?.total || 0} results</span>
        </div>
        <form
          className="campus-toolbar my-5"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(searchDraft.trim());
          }}
        >
          <input
            aria-label="Search consent directory"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Search name or email"
          />
          <select
            aria-label="Filter by consent"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All consent states</option>
            <option value="confirmed">Confirmed</option>
            <option value="pending">Pending</option>
            <option value="not_started">Not started</option>
            <option value="revoked">Withdrawn</option>
          </select>
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(event) => setRoleFilter(event.target.value)}
          >
            <option value="">All roles</option>
            {AUDIENCE_ROLES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <Button type="submit" variant="outline">
            Search
          </Button>
        </form>
        {contacts.isLoading ? (
          <div className="campus-skeleton" role="status" />
        ) : (
          <div className="campus-table-wrap">
            <table className="campus-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Role</th>
                  <th>WhatsApp</th>
                  <th>Permission</th>
                </tr>
              </thead>
              <tbody>
                {contacts.data?.items.map((contact) => (
                  <tr key={contact.user_id}>
                    <td>
                      {contact.name}
                      <small>{contact.email}</small>
                    </td>
                    <td>{contact.role.replace(/_/g, " ")}</td>
                    <td>{contact.phone || "Not added"}</td>
                    <td>
                      <span
                        className="campus-chip"
                        data-tone={contact.status === "confirmed" ? "success" : "muted"}
                      >
                        {contact.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
                {!contacts.data?.items.length && (
                  <tr>
                    <td colSpan={4}>No accounts match these filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <span className="campus-eyebrow">
              <Megaphone size={14} /> Delivery history
            </span>
            <h2 className="mt-2 text-xl font-bold text-secondary-900">
              Platform campaigns
            </h2>
            <p className="campus-muted mt-2">
              Counts update from signed provider delivery receipts.
            </p>
          </div>
          <Button
            disabled={!canSend}
            leftIcon={<Send size={16} />}
            onClick={() => setCampaignOpen(true)}
          >
            New campaign
          </Button>
        </div>
        {campaigns.isLoading ? (
          <div className="campus-skeleton mt-5" role="status" />
        ) : !campaigns.data?.length ? (
          <div className="campus-notice mt-5">
            Your first approved-template campaign and its delivery results will
            appear here.
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            {campaigns.data.map((campaign) => (
              <article className="campus-step" key={campaign.id}>
                <span className="campus-icon">
                  <MessageCircle size={17} />
                </span>
                <div className="campus-step-copy">
                  <strong>{campaign.template}</strong>
                  <p>
                    {friendlyDate(campaign.created_at)} · {campaign.status} · {" "}
                    {campaign.roles.map((role) => role.replace(/_/g, " ")).join(", ")}
                  </p>
                </div>
                <div className="campus-actions">
                  <span className="campus-chip">Recipients {campaign.recipient_count}</span>
                  <span className="campus-chip">Sent {campaign.sent}</span>
                  <span className="campus-chip" data-tone="success">
                    Delivered {campaign.delivered}
                  </span>
                  <span className="campus-chip">Read {campaign.read}</span>
                  {!!campaign.failed && (
                    <span className="campus-chip">Failed {campaign.failed}</span>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <GlassDialog
        open={campaignOpen}
        onOpenChange={setCampaignOpen}
        title="Create a platform WhatsApp campaign"
        description="Only active accounts in the selected roles with confirmed consent are included. Eligibility is checked again before delivery."
      >
        <form
          className="campus-form"
          onSubmit={(event) => {
            event.preventDefault();
            void createCampaign(event.currentTarget);
          }}
        >
          {error && (
            <p className="campus-error" role="alert">
              {error}
            </p>
          )}
          <label>
            Approved template
            <select name="template" required defaultValue="">
              <option value="" disabled>
                Choose an approved template
              </option>
              {overview.data?.approved_templates.map((template) => (
                <option value={template} key={template}>
                  {template}
                </option>
              ))}
            </select>
          </label>
          <label>
            Template language
            <input name="language" required defaultValue="en" maxLength={20} />
          </label>
          <fieldset>
            <legend className="mb-2 font-semibold text-secondary-900">
              Recipient roles
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {AUDIENCE_ROLES.map(([value, label]) => (
                <label className="campus-check" key={value}>
                  <input type="checkbox" name="roles" value={value} />
                  {label} ({overview.data?.eligible_by_role[value] || 0} eligible)
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            Template parameters, one per line
            <textarea
              name="parameters"
              maxLength={2560}
              placeholder={"New learning recommendations are ready\nOpen SashaInfinity today"}
            />
          </label>
          <label>
            Approved header banner URL
            <input
              name="banner"
              type="url"
              maxLength={500}
              value={bannerPreview}
              onChange={(event) => setBannerPreview(event.target.value)}
              placeholder="https://cdn.sashainfinity.com/updates/banner.png"
            />
          </label>
          {bannerPreview && (
            <div className="overflow-hidden rounded-2xl border border-orange-100 bg-orange-50/50 p-2">
              <img
                src={bannerPreview}
                alt="WhatsApp header banner preview"
                className="max-h-44 w-full rounded-xl object-cover"
              />
            </div>
          )}
          <p className="campus-notice">
            Use a light-orange SashaInfinity banner hosted on an HTTPS address
            the provider can fetch.
          </p>
          <Button type="submit" loading={busy} disabled={!canSend}>
            Queue campaign once
          </Button>
        </form>
      </GlassDialog>
    </div>
  );
}

export default AdminCommunicationsPage;
