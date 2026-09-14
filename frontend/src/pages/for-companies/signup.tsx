import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { companyAPI } from "@/api/company";

/**
 * SS3 — Dual-purpose:
 *  - Self-serve signup (no `?setup_token`)
 *  - Complete-setup for admin-invited companies (`?setup_token=...`)
 */
export function ForCompaniesSignupPage() {
  const [params] = useSearchParams();
  const setupToken = params.get("setup_token") || "";
  const navigate = useNavigate();
  const isSetup = Boolean(setupToken);

  const [form, setForm] = useState({
    name: "",
    contact_email: "",
    contact_phone: "",
    website: "",
    industry: "",
    team_size: "",
    description: "",
    password: "",
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isSetup) {
      // Setup flow only needs password
      setForm((f) => ({ ...f, password: "" }));
    }
  }, [isSetup]);

  const onChange =
    (key: keyof typeof form) =>
    (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >,
    ) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      if (isSetup) {
        await companyAPI.completeSetup(setupToken, form.password);
        toast.success("Account set up — please sign in");
        navigate("/login");
      } else {
        if (!form.name || !form.contact_email) {
          toast.error("Name and email are required");
          setSubmitting(false);
          return;
        }
        await companyAPI.signup({
          name: form.name,
          contact_email: form.contact_email,
          password: form.password,
          contact_phone: form.contact_phone,
          website: form.website,
          industry: form.industry,
          team_size: form.team_size,
          description: form.description,
        });
        toast.success("Signup received — we will notify you once approved");
        navigate("/login");
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || err?.message || "Signup failed";
      toast.error(String(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">
                {isSetup
                  ? "Complete your company account"
                  : "Create a company account"}
              </h1>
              <p className="text-slate-600 text-sm mb-6">
                {isSetup
                  ? "Set a password to finish activating your admin-invited account."
                  : "After you submit, an administrator will review your account. You will be notified by email once approved."}
              </p>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-for-companies-signup"
      >
        <form onSubmit={onSubmit} className="space-y-4">
          {!isSetup && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Company name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={onChange("name")}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Contact email *
                </label>
                <input
                  type="email"
                  value={form.contact_email}
                  onChange={onChange("contact_email")}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    value={form.contact_phone}
                    onChange={onChange("contact_phone")}
                    className="w-full rounded-md border border-slate-300 px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Website
                  </label>
                  <input
                    type="url"
                    value={form.website}
                    onChange={onChange("website")}
                    placeholder="https://..."
                    className="w-full rounded-md border border-slate-300 px-3 py-2"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={form.industry}
                    onChange={onChange("industry")}
                    className="w-full rounded-md border border-slate-300 px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Team size
                  </label>
                  <select
                    value={form.team_size}
                    onChange={onChange("team_size")}
                    className="w-full rounded-md border border-slate-300 px-3 py-2"
                  >
                    <option value="">—</option>
                    <option value="1-10">1-10</option>
                    <option value="11-50">11-50</option>
                    <option value="51-200">51-200</option>
                    <option value="200+">200+</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  About the company
                </label>
                <textarea
                  value={form.description}
                  onChange={onChange("description")}
                  rows={3}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
              </div>
            </>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Password *
            </label>
            <input
              type="password"
              value={form.password}
              onChange={onChange("password")}
              minLength={8}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold px-4 py-2.5 rounded-md"
          >
            {submitting
              ? "Submitting…"
              : isSetup
                ? "Set password & finish"
                : "Create account"}
          </button>
        </form>
        {!isSetup && (
          <p className="text-xs text-slate-500 mt-4 text-center">
            Already have a company account?{" "}
            <Link to="/login" className="text-indigo-600 font-medium">
              Sign in
            </Link>
          </p>
        )}
      </PageLayout>
    </div>
  );
}

export default ForCompaniesSignupPage;
