import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { companyAPI, InterestCandidateView } from "@/api/company";

/**
 * SS3 — Student-side internship inbox.
 * Lists companies that have expressed interest; accept/decline.
 */
export function InternshipInboxPage() {
  const [rows, setRows] = useState<InterestCandidateView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await companyAPI.myInbox();
      setRows(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load inbox");
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const act = async (id: number, verb: "accept" | "decline") => {
    try {
      if (verb === "accept") await companyAPI.acceptInterest(id);
      else await companyAPI.declineInterest(id);
      toast.success(verb === "accept" ? "Accepted" : "Declined");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Action failed");
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-2xl font-bold text-slate-900">
            Internship inbox
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Companies that have expressed interest in hiring you. Accepting
            reveals your email and phone to the company so they can reach out
            directly.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-dashboard-internship-inbox"
    >
      {loading ? (
        <div className="py-10 text-center text-slate-500">Loading…</div>
      ) : error ? (
        <div
          role="alert"
          className="py-10 text-center bg-white rounded-xl border border-rose-200"
        >
          <p className="text-sm text-rose-600">{error}</p>
          <button
            onClick={load}
            className="mt-3 px-4 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-700"
          >
            Try again
          </button>
        </div>
      ) : rows.length === 0 ? (
        <div
          className="py-16 text-center text-slate-500 bg-white rounded-xl border border-slate-200"
          data-glass="content"
        >
          No interest yet. Make sure your candidate profile is visible and
          complete.
        </div>
      ) : (
        <ul className="space-y-4">
          {rows.map((r) => (
            <li
              key={r.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-slate-900">
                    {r.company_name || "A company"}
                    <span
                      className={`ml-2 text-[11px] px-2 py-0.5 rounded ${
                        r.status === "accepted"
                          ? "bg-emerald-100 text-emerald-700"
                          : r.status === "declined"
                            ? "bg-rose-100 text-rose-700"
                            : r.status === "withdrawn"
                              ? "bg-slate-200 text-slate-600"
                              : "bg-indigo-100 text-indigo-700"
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {r.company_industry || "—"}
                    {r.company_website && (
                      <>
                        {" · "}
                        <a
                          href={r.company_website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-600"
                        >
                          {r.company_website}
                        </a>
                      </>
                    )}
                  </div>
                </div>
                {r.status === "interested" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => act(r.id, "accept")}
                      className="px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => act(r.id, "decline")}
                      className="px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 text-sm"
                    >
                      Decline
                    </button>
                  </div>
                )}
              </div>
              {r.company_message && (
                <blockquote className="mt-3 text-sm text-slate-700 italic border-l-4 border-indigo-200 bg-slate-50 px-4 py-2 rounded">
                  {r.company_message}
                </blockquote>
              )}
            </li>
          ))}
        </ul>
      )}
    </PageLayout>
  );
}

export default InternshipInboxPage;
