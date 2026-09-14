import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { Briefcase, User } from "lucide-react";
import { internshipApi, PublicInternship } from "@/api/internship";

export const InternshipsPage: React.FC = () => {
  const [items, setItems] = useState<PublicInternship[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await internshipApi.list();
        setItems(data || []);
      } catch (err: any) {
        toast.error(
          err?.response?.data?.detail || "Failed to load internships",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = items.filter(
    (i) =>
      i.title.toLowerCase().includes(search.toLowerCase()) ||
      (i.spoc_name || "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <PageLayout
      header={
        <PageBanner
          eyebrow="Mentor-led experiences"
          title="Turn learning into experience"
          description="Explore paid internship programs, learn with a mentor and receive a voucher you can redeem on a course at checkout."
          share
          shareTitle="Explore internship programs on SashaInfinity"
        />
      }
      className="rd-screen rd-screen-internships"
    >
      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by program or mentor..."
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
        />
      </div>
      {loading ? (
        <div className="text-center text-gray-500 py-12">
          Loading programs...
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <Briefcase className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500">
            No internship programs available right now. Check back soon.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((i) => (
            <Link
              key={i.id}
              to={`/internships/${i.slug}`}
              className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-yellow-400 hover:shadow-md transition flex flex-col"
            >
              {i.cover_image ? (
                <img
                  src={i.cover_image}
                  alt={i.title}
                  className="w-full h-40 object-cover"
                />
              ) : (
                <div className="w-full h-40 bg-gradient-to-br from-yellow-100 to-yellow-300 flex items-center justify-center">
                  <Briefcase className="w-10 h-10 text-yellow-700" />
                </div>
              )}
              <div className="p-5 flex-1 flex flex-col">
                <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                  {i.title}
                </h3>
                {i.spoc_name && (
                  <div className="mt-1 flex items-center gap-1.5 text-sm text-gray-600">
                    <User className="w-4 h-4" />
                    {i.spoc_name}
                  </div>
                )}
                {i.description && (
                  <p className="mt-3 text-sm text-gray-600 line-clamp-3 flex-1">
                    {i.description}
                  </p>
                )}
                <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-end">
                  <span className="inline-flex items-center gap-1 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold px-4 py-2 rounded-md text-sm">
                    Enroll Now
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageLayout>
  );
};

export default InternshipsPage;
