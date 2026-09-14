import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CloudCog,
  Database,
  Download,
  ExternalLink,
  Globe2,
  KeyRound,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import toast from "react-hot-toast";

import {
  campusControlPlaneApi,
  type IntegrationKind,
  type RetentionPolicy,
} from "@/api/campus-control-plane";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { Button } from "@/components/ui/button";
import { apiError } from "./InstitutionDialog";

const integrations: { kind: IntegrationKind; name: string; detail: string }[] = [
  { kind: "google_workspace", name: "Google Workspace", detail: "Institution sign-in and account lifecycle" },
  { kind: "microsoft_entra", name: "Microsoft Entra ID", detail: "Federated identity and group mapping" },
  { kind: "saml", name: "SAML 2.0", detail: "Enterprise identity provider configuration" },
  { kind: "scim", name: "SCIM 2.0", detail: "Automated user provisioning configuration" },
  { kind: "oneroster", name: "OneRoster 1.2", detail: "Portable roster, class and enrollment exchange" },
  { kind: "lti_1_3", name: "LTI 1.3 Advantage", detail: "Learning tool and grade-return configuration" },
  { kind: "digilocker_nad", name: "DigiLocker / NAD", detail: "Academic credential publishing readiness" },
];

const defaults: RetentionPolicy = {
  inactive_account_days: 730,
  learning_record_days: 2555,
  financial_record_days: 2920,
  application_record_days: 730,
  legal_hold: false,
};

export function CampusControlPlane({ id }: { id: number }) {
  const cache = useQueryClient();
  const query = useQuery({ queryKey: ["campus-control-plane", id], queryFn: () => campusControlPlaneApi.get(id) });
  const [hostname, setHostname] = useState("");
  const [editing, setEditing] = useState<IntegrationKind>();
  const [displayName, setDisplayName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [clientId, setClientId] = useState("");
  const [secretRef, setSecretRef] = useState("");
  const [retention, setRetention] = useState<RetentionPolicy>();
  const [busy, setBusy] = useState(false);
  const policy = retention || query.data?.retention || defaults;

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    try {
      await action();
      await cache.invalidateQueries({ queryKey: ["campus-control-plane", id] });
      toast.success(message);
    } catch (error) {
      toast.error(apiError(error));
    } finally {
      setBusy(false);
    }
  }

  async function addDomain(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await campusControlPlaneApi.addDomain(id, hostname);
      setHostname("");
    }, "Verification record created");
  }

  function openIntegration(kind: IntegrationKind, name: string) {
    const current = query.data?.integrations.find((item) => item.kind === kind);
    setEditing(kind);
    setDisplayName(current?.display_name || name);
    setIssuer(String(current?.config.issuer || current?.config.base_url || ""));
    setClientId(String(current?.config.client_id || current?.config.tenant_id || ""));
    setSecretRef("");
  }

  async function saveIntegration(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    await run(
      () => campusControlPlaneApi.saveIntegration(id, {
        kind: editing,
        display_name: displayName,
        status: issuer || editing === "oneroster" ? "ready" : "draft",
        config: { issuer, client_id: clientId },
        secret_reference: secretRef,
      }),
      "Integration settings saved",
    );
    setEditing(undefined);
  }

  async function downloadRoster() {
    await run(async () => {
      const blob = await campusControlPlaneApi.oneRosterExport(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "sashainfinity-oneroster-1.2.zip";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "OneRoster export downloaded");
  }

  if (query.isPending) return <div className="campus-skeleton" role="status" aria-label="Loading trust centre" />;
  if (query.isError || !query.data) return <div className="campus-error" role="alert">We couldn’t load the trust centre. <button onClick={() => void query.refetch()}>Try again</button></div>;

  return (
    <div className="campus-control-plane">
      <BrandBanner
        compact
        eyebrow="Trust, identity and interoperability"
        title="Your campus data. Connected with control."
        description="Prepare secure identity, standards-based exchange and privacy operations from one accountable workspace."
      />

      <div className="campus-columns">
        <section className="campus-panel">
          <div className="campus-panel-heading"><div><h2>Custom domains</h2><p className="campus-muted">Use your institution’s own web address.</p></div><Globe2 size={20} /></div>
          <form className="campus-form" onSubmit={addDomain}>
            <label>Domain<input required placeholder="learn.yourschool.edu" value={hostname} onChange={(event) => setHostname(event.target.value)} /></label>
            <Button type="submit" loading={busy}>Add domain</Button>
          </form>
          {query.data.domains.map((domain) => (
            <article className="campus-control-row" key={domain.id}>
              <span className="campus-icon"><Globe2 size={18} /></span>
              <div><strong>{domain.hostname}</strong><small>{domain.status === "verified" ? "Verified" : `Add ${domain.verification.record_name} as a TXT record`}</small>{domain.status !== "verified" && <code>{domain.verification.record_value}</code>}</div>
              <span className="campus-chip" data-tone={domain.status === "verified" ? "success" : "muted"}>{domain.status}</span>
            </article>
          ))}
          {!query.data.domains.length && <p className="campus-notice">Add a domain to receive its unique DNS verification record.</p>}
        </section>

        <section className="campus-panel">
          <div className="campus-panel-heading"><div><h2>Open standards</h2><p className="campus-muted">Exchange data without locking it into one platform.</p></div><Database size={20} /></div>
          {query.data.standards.map((standard) => <div className="campus-control-row" key={standard.key}><span className="campus-icon"><CheckCircle2 size={18} /></span><div><strong>{standard.key.toUpperCase()} {standard.version}</strong><small>{standard.capability}</small></div></div>)}
          <Button variant="outline" leftIcon={<Download size={16} />} loading={busy} onClick={() => void downloadRoster()}>Download OneRoster package</Button>
        </section>
      </div>

      <section className="campus-panel">
        <div className="campus-panel-heading"><div><h2>Identity and integrations</h2><p className="campus-muted">Store public configuration here and keep credentials in your secret manager.</p></div><CloudCog size={20} /></div>
        <div className="campus-control-grid">
          {integrations.map((integration) => {
            const saved = query.data.integrations.find((item) => item.kind === integration.kind);
            return <button className="campus-control-integration" key={integration.kind} onClick={() => openIntegration(integration.kind, integration.name)}><span className="campus-icon"><KeyRound size={18} /></span><span><strong>{integration.name}</strong><small>{integration.detail}</small></span><span className="campus-chip" data-tone={saved?.status === "active" ? "success" : "muted"}>{saved?.status || "Set up"}</span></button>;
          })}
        </div>
        {editing && (
          <form className="campus-form campus-control-editor" onSubmit={saveIntegration}>
            <div className="campus-panel-heading"><h3>Configure {integrations.find((item) => item.kind === editing)?.name}</h3><Button type="button" variant="ghost" onClick={() => setEditing(undefined)}>Close</Button></div>
            <div className="campus-form-grid">
              <label>Display name<input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
              <label>Issuer or base URL<input value={issuer} onChange={(event) => setIssuer(event.target.value)} placeholder="https://identity.example.edu" /></label>
              <label>Client or tenant ID<input value={clientId} onChange={(event) => setClientId(event.target.value)} /></label>
              <label>Secret manager reference<input value={secretRef} onChange={(event) => setSecretRef(event.target.value)} placeholder="vault://campus/provider" /></label>
            </div>
            <p className="campus-notice"><LockKeyhole size={15} /> Never paste a client secret here. Save its reference after an administrator provisions it in the deployment secret store.</p>
            <Button type="submit" loading={busy}>Save configuration</Button>
          </form>
        )}
      </section>

      <section className="campus-panel">
        <div className="campus-panel-heading"><div><h2>Retention and privacy requests</h2><p className="campus-muted">Keep an explicit record of retention decisions and rights requests.</p></div><ShieldCheck size={20} /></div>
        <form className="campus-form" onSubmit={(event) => { event.preventDefault(); void run(() => campusControlPlaneApi.saveRetention(id, policy), "Retention policy saved"); }}>
          <div className="campus-form-grid">
            {([ ["inactive_account_days", "Inactive accounts"], ["learning_record_days", "Learning records"], ["financial_record_days", "Financial records"], ["application_record_days", "Applications"] ] as const).map(([field, label]) => <label key={field}>{label} (days)<input type="number" min={field === "financial_record_days" ? 365 : 30} max={field === "financial_record_days" || field === "learning_record_days" ? 7300 : 3650} value={policy[field]} onChange={(event) => setRetention({ ...policy, [field]: Number(event.target.value) })} /></label>)}
          </div>
          <label className="campus-check"><input type="checkbox" checked={policy.legal_hold} onChange={(event) => setRetention({ ...policy, legal_hold: event.target.checked })} /><span>Legal hold is active; automated deletion must remain paused.</span></label>
          <Button type="submit" loading={busy}>Save policy</Button>
        </form>
        <div className="campus-control-requests">
          {query.data.privacy_requests.map((request) => <article className="campus-control-row" key={request.id}><span className="campus-icon"><ShieldCheck size={18} /></span><div><strong>{request.kind} request · account {request.subject_user_id}</strong><small>Due {new Date(request.due_at).toLocaleDateString()} · {request.status}</small></div>{!["completed", "rejected", "cancelled"].includes(request.status) && <Button size="sm" variant="outline" leftIcon={<RefreshCw size={14} />} onClick={() => void run(() => campusControlPlaneApi.updatePrivacyRequest(id, request.id, "processing"), "Request moved to processing")}>Process</Button>}</article>)}
          {!query.data.privacy_requests.length && <p className="campus-notice">No privacy requests are waiting for action.</p>}
        </div>
      </section>
      <a className="campus-control-doc-link" href="https://www.1edtech.org/standards" target="_blank" rel="noreferrer">Read the interoperability standards <ExternalLink size={14} /></a>
    </div>
  );
}

