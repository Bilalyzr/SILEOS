import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { Link } from "react-router-dom";

/**
 * SS3 — public marketing page advertising the company/hiring portal.
 */
export function ForCompaniesPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50">
      <PageLayout
        header={
          <PageHeader>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
                Hire pre-vetted, course-certified talent
              </h1>
              <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-10">
                SashaInfinity LMS graduates complete rigorous, instructor-led
                courses. Get access to students who are ready to contribute from
                day one — filtered by skills, roles, and availability.
              </p>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-for-companies"
      >
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            to="/for-companies/signup"
            className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-8 py-3 rounded-lg shadow"
          >
            Create a company account
          </Link>
          <Link
            to="/login"
            className="inline-block bg-white border border-slate-300 text-slate-700 font-semibold px-8 py-3 rounded-lg hover:bg-slate-50"
          >
            Sign in
          </Link>
        </div>
      </PageLayout>

      <section className="max-w-6xl mx-auto px-6 pb-20 grid md:grid-cols-3 gap-8">
        {[
          {
            title: "Pre-filtered candidates",
            body: "See only students who finished a course and opted in to be hired.",
          },
          {
            title: "Express interest, no spam",
            body: "Send one message. Candidate accepts or declines. Contact revealed on acceptance.",
          },
          {
            title: "No recruiter fees",
            body: "Free to browse. No per-hire placement charges while in beta.",
          },
        ].map((c) => (
          <div
            key={c.title}
            className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm"
            data-glass="content"
          >
            <h3 className="font-semibold text-slate-900 text-lg mb-2">
              {c.title}
            </h3>
            <p className="text-slate-600 text-sm">{c.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export default ForCompaniesPage;
