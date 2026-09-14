import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Mail,
  Phone,
  MapPin,
  Globe,
  Facebook,
  Twitter,
  Linkedin,
  AlertCircle,
  Users,
  Ticket,
  ClipboardList,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ShareButton } from "@/components/ui/share-button";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/auth";
import { getAvatarUrl } from "@/utils/media";
import { ViewAsSpocBanner } from "@/components/spoc/ViewAsSpocBanner";

interface UserProfile {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  description: string;
  designation: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  profile_photo: string;
  cover_photo: string;
  facebook: string;
  twitter: string;
  linkedin: string;
  website: string;
}

interface UserStats {
  my_internships?: number;
  vouchers_redeemed?: number;
  pending_interns?: number;
}

export function SpocProfilePage() {
  const { spocId } = useParams<{ spocId: string }>();
  const navigate = useNavigate();
  const currentUser = useAuthStore((s) => s.user);
  const profile = useAuthStore((s) => s.profile);
  const [fetchedProfile, setProfile] = useState<Partial<UserProfile> | null>(
    null,
  );
  const getImpersonationType = useAuthStore((s) => s.getImpersonationType);
  const [stats, setStats] = useState<UserStats>({});
  const [loading, setLoading] = useState(true);
  const [isImpersonating, setIsImpersonating] = useState(false);

  useEffect(() => {
    setIsImpersonating(getImpersonationType() === "spoc");
  }, [getImpersonationType]);

  // Fetch stats only - profile data comes from auth store during impersonation
  useEffect(() => {
    const idToFetch = isImpersonating
      ? currentUser?.id
      : spocId
        ? parseInt(spocId)
        : null;
    if (idToFetch) {
      fetchSpocStats(idToFetch).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [spocId, isImpersonating, currentUser?.id]);

  const fetchSpocStats = async (id: number) => {
    try {
      const response = await api.get(`/admin/users/${id}/stats`);
      setStats(response.data || {});
    } catch (error) {
      console.error("Error fetching SPOC stats:", error);
      setStats({});
    }
  };

  // During impersonation, use current user's profile from auth store
  // Otherwise fetch from API
  useEffect(() => {
    if (!isImpersonating && spocId) {
      fetchSpocProfile(parseInt(spocId));
    } else {
      setLoading(false);
    }
  }, [spocId, isImpersonating]);

  const fetchSpocProfile = async (id: number) => {
    try {
      const response = await api.get(`/admin/users/${id}`);
      setProfile(response.data);
    } catch (error) {
      console.error("Error fetching SPOC profile:", error);
      toast.error("Failed to load SPOC profile");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading SPOC p...</p>
        </div>
      </div>
    );
  }

  // Use auth store profile during impersonation, otherwise fetched profile
  const displayProfile: Partial<UserProfile> | null = isImpersonating
    ? { ...profile, email: currentUser?.user_email }
    : fetchedProfile;
  if (!displayProfile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-slate-600">SPOC profile not found</p>
          <Button onClick={() => navigate(-1)} className="mt-4">
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const p: Partial<UserProfile> = displayProfile || {};
  const fullName =
    `${p.first_name || ""} ${p.last_name || ""}`.trim() ||
    currentUser?.display_name ||
    "SPOC";
  const avatarUrl = getAvatarUrl(displayProfile || currentUser);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* View As Banner */}
      <ViewAsSpocBanner />

      {/* Cover Photo */}
      <div className="h-48 bg-gradient-to-r from-emerald-500 to-teal-600 relative">
        {p.cover_photo && (
          <img
            src={p.cover_photo}
            alt="Cover"
            className="w-full h-full object-cover"
          />
        )}
      </div>

      {/* Profile Header */}
      <div className="max-w-5xl mx-auto px-4 -mt-16 relative z-10">
        <PageLayout
          header={
            <PageHeader>
              <div className="flex flex-col md:flex-row gap-6">
                {/* Avatar */}
                <div className="relative">
                  <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 overflow-hidden ring-4 ring-white shadow-lg">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={fullName}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-white text-4xl font-bold">
                        {fullName[0]?.toUpperCase()}
                      </div>
                    )}
                  </div>
                </div>

                {/* Basic Info */}
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-slate-900">
                    {fullName}
                  </h1>
                  {p.designation && (
                    <p className="text-slate-600 mt-1">{p.designation}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-slate-600">
                    {p.email && (
                      <div className="flex items-center gap-1">
                        <Mail className="w-4 h-4" />
                        <span>{p.email}</span>
                      </div>
                    )}
                    {p.phone && (
                      <div className="flex items-center gap-1">
                        <Phone className="w-4 h-4" />
                        <span>{p.phone}</span>
                      </div>
                    )}
                    <ShareButton
                      url={
                        typeof window !== "undefined"
                          ? window.location.href
                          : undefined
                      }
                      title={`SPOC Profile: ${fullName}`}
                      description={
                        p.description ||
                        p.designation ||
                        "SPOC at SashaInfinity"
                      }
                      size="sm"
                    />
                  </div>
                </div>

                {/* View As Badge */}
                {isImpersonating && (
                  <div className="md:text-right">
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                      <Eye className="w-4 h-4" />
                      Viewing as SPOC
                    </span>
                  </div>
                )}
              </div>
            </PageHeader>
          }
          className="rd-screen rd-screen-spoc-profile"
        >
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-6 border-b border-slate-100">
            <div className="bg-emerald-50 rounded-xl p-4 text-center">
              <Users className="w-6 h-6 text-emerald-600 mx-auto mb-2" />
              <div className="text-2xl font-bold text-emerald-700">
                {stats.my_internships || 0}
              </div>
              <div className="text-sm text-emerald-600">My Internships</div>
            </div>
            <div className="bg-teal-50 rounded-xl p-4 text-center">
              <Ticket className="w-6 h-6 text-teal-600 mx-auto mb-2" />
              <div className="text-2xl font-bold text-teal-700">
                {stats.vouchers_redeemed || 0}
              </div>
              <div className="text-sm text-teal-600">Vouchers Redeemed</div>
            </div>
            <div className="bg-cyan-50 rounded-xl p-4 text-center col-span-2 md:col-span-1">
              <ClipboardList className="w-6 h-6 text-cyan-600 mx-auto mb-2" />
              <div className="text-2xl font-bold text-cyan-700">
                {stats.pending_interns || 0}
              </div>
              <div className="text-sm text-cyan-600">Pending Interns</div>
            </div>
          </div>
          <div className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">About</h2>
            {p.description ? (
              <p className="text-slate-600">{p.description}</p>
            ) : (
              <p className="text-slate-400 italic">No description provided</p>
            )}

            {p.address && (
              <div className="mt-4 flex items-center gap-2 text-slate-600">
                <MapPin className="w-4 h-4" />
                <span>
                  {[p.address, p.city, p.state, p.country]
                    .filter(Boolean)
                    .join(", ")}
                </span>
              </div>
            )}
          </div>
          {(p.facebook || p.twitter || p.linkedin || p.website) && (
            <div className="px-6 pb-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                Connect
              </h2>
              <div className="flex gap-3">
                {p.linkedin && (
                  <a
                    href={p.linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition"
                  >
                    <Linkedin className="w-5 h-5" />
                  </a>
                )}
                {p.facebook && (
                  <a
                    href={p.facebook}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition"
                  >
                    <Facebook className="w-5 h-5" />
                  </a>
                )}
                {p.twitter && (
                  <a
                    href={p.twitter}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 bg-sky-50 text-sky-600 rounded-lg hover:bg-sky-100 transition"
                  >
                    <Twitter className="w-5 h-5" />
                  </a>
                )}
                {p.website && (
                  <a
                    href={p.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 bg-slate-50 text-slate-600 rounded-lg hover:bg-slate-100 transition"
                  >
                    <Globe className="w-5 h-5" />
                  </a>
                )}
              </div>
            </div>
          )}
        </PageLayout>
      </div>
    </div>
  );
}

export default SpocProfilePage;
