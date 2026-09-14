import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import {
  Camera,
  User,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Edit3,
  Globe,
  Facebook,
  Twitter,
  Linkedin,
  AlertCircle,
  BookOpen,
  Award,
  GraduationCap,
  Users,
  Briefcase,
  Building2,
  Ticket,
  ClipboardList,
  ShieldCheck,
  LifeBuoy,
  Trash2,
  Trophy,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { ShareButton } from "@/components/ui/share-button";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth";
import { useSEO } from "@/hooks/use-seo";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Greeting,
  StatCard,
  FadeUp,
  StaggerGrid,
  SectionCard,
  type StatTone,
} from "@/components/dashboard/primitives";
import { getAvatarUrl } from "@/utils/media";
import { internshipApi } from "@/api/internship";
import { BadgeGrid } from "@/components/gamification/BadgeGrid";
import {
  gamificationAPI,
  type GamificationMeResponse,
} from "@/api/gamification";

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
  enrolled_courses?: number;
  completed_courses?: number;
  in_progress_courses?: number;
  certificates_earned?: number;
  total_learning_time?: number;
  total_courses?: number;
  published_courses?: number;
  total_students?: number;
  // Admin
  total_users?: number;
  open_tickets?: number;
  // SPOC
  my_internships?: number;
  vouchers_redeemed?: number;
  pending_interns?: number;
  // Company
  active_interns?: number;
  internships?: number;
  pending_requests?: number;
}

type RoleStat = {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  tone: StatTone;
};

export function ProfilePage() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const setAuthProfile = useAuthStore((state) => state.setProfile);
  const role = useAuthStore((s) => s.user?.role) || user?.role || "student";
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<UserStats>({});
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<UserProfile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [gamification, setGamification] =
    useState<GamificationMeResponse | null>(null);
  const [visibilitySaving, setVisibilitySaving] = useState(false);

  // Check if user was redirected here for profile completion
  const requiresCompletion =
    location.state?.requiresCompletion || !user?.profile_completed;

  // SEO hook - must be called at top level, not inside useEffect
  const fullName = profile
    ? `${profile.first_name || ""} ${profile.last_name || ""}`.trim()
    : "";
  useSEO(
    profile
      ? {
          title: fullName ? `${fullName} - Profile` : "User Profile",
          description:
            profile.description ||
            `View ${fullName || "user"} profile on SashaInfinity LMS`,
          image: profile.profile_photo,
          url: window.location.href,
        }
      : {},
  );

  const fetchStats = useCallback(async () => {
    try {
      // For SPOC users, fetch internships directly to match the dashboard
      if (role === "spoc") {
        const internships = await internshipApi.spocMyInternships();
        const my_internships = internships.length;
        const vouchers_redeemed = internships.reduce(
          (sum, i) => sum + (i.vouchers_redeemed ?? 0),
          0,
        );
        const vouchers_issued = internships.reduce(
          (sum, i) => sum + (i.vouchers_issued ?? 0),
          0,
        );
        // Pending interns are those with issued but not yet redeemed vouchers
        const pending_interns = vouchers_issued - vouchers_redeemed;

        setStats({
          my_internships,
          vouchers_redeemed,
          pending_interns,
        });
      } else {
        const response = await api.get("/users/stats");
        setStats(response.data || {});
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  }, [role]);
  useEffect(() => {
    fetchProfile();
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    if (role !== "student") return;
    // Best-effort, same as the dashboard widgets — never blocks the rest
    // of the profile page.
    gamificationAPI
      .getMe()
      .then(setGamification)
      .catch(() => {});
  }, [role]);

  const handleToggleLeaderboardVisibility = async () => {
    if (!gamification) return;
    const next = !gamification.stats.leaderboard_visible;
    setVisibilitySaving(true);
    try {
      const updatedStats = await gamificationAPI.updateSettings(next);
      setGamification((prev) =>
        prev ? { ...prev, stats: updatedStats } : prev,
      );
      toast.success(
        next
          ? "You are now visible on the leaderboard"
          : "You are now hidden from the leaderboard",
      );
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail ||
          "Failed to update leaderboard visibility",
      );
    } finally {
      setVisibilitySaving(false);
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await api.get("/users/profile");
      setProfile(response.data);
      setEditForm(response.data);

      // Check if profile is incomplete and auto-enable edit mode
      const isIncomplete =
        !response.data.first_name || !response.data.last_name;
      if (isIncomplete) {
        setIsEditing(true);
        toast("Please complete your profile information", { icon: <AstraSymbol value="ℹ️" /> });
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editForm) return;

    if (!editForm.first_name || !editForm.last_name) {
      toast.error("First name and last name are required");
      return;
    }

    if (requiresCompletion && !editForm.phone) {
      toast.error("Phone number is required to complete your profile");
      return;
    }

    try {
      const response = await api.put("/users/profile", editForm);
      setProfile(response.data);
      setIsEditing(false);

      await useAuthStore.getState().checkAuth();
      setAuthProfile(response.data);

      if (requiresCompletion && response.data.profile_completed) {
        toast.success(
          "Profile completed successfully! Redirecting to dashboard...",
          {
            duration: 3000,
            icon: <AstraSymbol value="✅" />,
          },
        );

        setTimeout(() => {
          const userRole = user?.role || "student";
          const dashboardPath =
            userRole === "admin"
              ? "/admin"
              : userRole === "instructor"
                ? "/instructor/courses"
                : "/courses";
          navigate(dashboardPath, { replace: true });
        }, 1000);
      } else {
        toast.success("Profile updated successfully!");
      }
    } catch (error: any) {
      console.error("Error updating profile:", error);
      toast.error(error.response?.data?.detail || "Failed to update profile");
    }
  };

  const handleCancel = () => {
    setEditForm(profile);
    setIsEditing(false);
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setEditForm((prev) => (prev ? { ...prev, [name]: value } : null));
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 15 * 1024 * 1024) {
      toast.error("File size must be less than 15MB");
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post("/users/avatar", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const newAvatarUrl = response.data.avatar_url;
      if (profile) setProfile({ ...profile, profile_photo: newAvatarUrl });
      if (editForm) setEditForm({ ...editForm, profile_photo: newAvatarUrl });

      setAuthProfile({ profile_photo: newAvatarUrl });
      toast.success("Avatar uploaded successfully!");
    } catch (error: any) {
      console.error("Error uploading avatar:", error);
      toast.error(error.response?.data?.detail || "Failed to upload avatar");
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveAvatar = async () => {
    try {
      setUploading(true);
      await api.delete("/users/avatar");

      const emptyUrl = "";
      if (profile) setProfile({ ...profile, profile_photo: emptyUrl });
      if (editForm) setEditForm({ ...editForm, profile_photo: emptyUrl });

      setAuthProfile({ profile_photo: emptyUrl });
      toast.success("Avatar removed successfully!");
    } catch (error: any) {
      console.error("Error removing avatar:", error);
      toast.error(error.response?.data?.detail || "Failed to remove avatar");
    } finally {
      setUploading(false);
    }
  };

  if (loading || !profile) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  const isProfileIncomplete = !profile?.first_name || !profile?.last_name;

  // -----------------------------------------------------------------------
  // Build role-specific stat block
  // -----------------------------------------------------------------------
  const roleBlock: { title: string; subtitle?: string; cards: RoleStat[] } =
    (() => {
      if (role === "instructor") {
        return {
          title: "Teaching stats",
          subtitle: "Your courses and student reach",
          cards: [
            {
              title: "Total Courses",
              value: stats.total_courses ?? 0,
              icon: BookOpen,
              tone: "orange",
            },
            {
              title: "Published",
              value: stats.published_courses ?? 0,
              icon: Award,
              tone: "emerald",
            },
            {
              title: "Total Students",
              value: stats.total_students ?? 0,
              icon: Users,
              tone: "sky",
            },
          ],
        };
      }
      if (role === "admin") {
        return {
          title: "Platform overview",
          subtitle: "Live numbers across the platform",
          cards: [
            {
              title: "Total Users",
              value: stats.total_users ?? 0,
              icon: Users,
              tone: "sky",
            },
            {
              title: "Total Courses",
              value: stats.total_courses ?? 0,
              icon: BookOpen,
              tone: "orange",
            },
            {
              title: "Open Tickets",
              value: stats.open_tickets ?? 0,
              icon: LifeBuoy,
              tone: "rose",
            },
          ],
        };
      }
      if (role === "spoc") {
        return {
          title: "Cohort overview",
          subtitle: "Internships under your stewardship",
          cards: [
            {
              title: "My Internships",
              value: stats.my_internships ?? 0,
              icon: Briefcase,
              tone: "orange",
            },
            {
              title: "Vouchers Redeemed",
              value: stats.vouchers_redeemed ?? 0,
              icon: Ticket,
              tone: "purple",
            },
            {
              title: "Pending Interns",
              value: stats.pending_interns ?? 0,
              icon: ClipboardList,
              tone: "amber",
            },
          ],
        };
      }
      if (role === "company" || role === "company_manager") {
        return {
          title: "Company at a glance",
          subtitle: "Team activity and pending approvals",
          cards: [
            {
              title: "Active Interns",
              value: stats.active_interns ?? 0,
              icon: Users,
              tone: "emerald",
            },
            {
              title: "Internships",
              value: stats.internships ?? 0,
              icon: Building2,
              tone: "navy",
            },
            {
              title: "Pending Requests",
              value: stats.pending_requests ?? 0,
              icon: ShieldCheck,
              tone: "amber",
            },
          ],
        };
      }
      // Default: student
      return {
        title: "Learning at a glance",
        subtitle: "Your courses, completions, and certificates",
        cards: [
          {
            title: "Enrolled",
            value: stats.enrolled_courses ?? 0,
            icon: BookOpen,
            tone: "orange",
          },
          {
            title: "Completed",
            value: stats.completed_courses ?? 0,
            icon: GraduationCap,
            tone: "emerald",
          },
          {
            title: "Certificates",
            value: stats.certificates_earned ?? 0,
            icon: Award,
            tone: "purple",
          },
        ],
      };
    })();

  return (
    <PageLayout
      header={
        <Greeting
          name={
            `${profile.first_name} ${profile.last_name}`.trim() || user?.email
          }
          chip="MY PROFILE"
          subtitle="Manage your account information and personal details."
          className="mb-6"
        />
      }
    >
      {(requiresCompletion || isProfileIncomplete) && (
        <FadeUp className="mb-6">
          <div className="dash-card-solid p-4 border-l-4 border-yellow-400 rounded-r-2xl flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-yellow-900">
                Complete Your Profile
              </h3>
              <p className="mt-1 text-sm text-yellow-800">
                {requiresCompletion
                  ? "Please fill in all required fields: First Name, Last Name, and Phone Number to access other features."
                  : "Your profile is incomplete. Please fill in your first name and last name."}
              </p>
            </div>
          </div>
        </FadeUp>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Identity card */}
        <div className="lg:col-span-1">
          <FadeUp>
            <div className="dash-card p-6 text-center">
              <div className="relative inline-block mb-4">
                <Avatar className="w-24 h-24 mx-auto ring-4 ring-orange-100/60">
                  {getAvatarUrl(profile) ? (
                    <img
                      src={getAvatarUrl(profile)}
                      alt={`${profile.first_name} ${profile.last_name}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-orange-100 flex items-center justify-center">
                      <User className="h-12 w-12 text-orange-600" />
                    </div>
                  )}
                </Avatar>
                <div className="absolute -bottom-1 -right-1 flex gap-1">
                  <label
                    htmlFor="avatar-upload"
                    className="bg-orange-500 text-white rounded-full p-2 hover:bg-orange-600 transition-colors cursor-pointer shadow-md"
                  >
                    <Camera className="h-4 w-4" />
                    <input
                      id="avatar-upload"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleAvatarUpload}
                      disabled={uploading}
                    />
                  </label>
                  {getAvatarUrl(profile) && (
                    <button
                      onClick={handleRemoveAvatar}
                      disabled={uploading}
                      className="bg-rose-500 text-white rounded-full p-2 hover:bg-rose-600 transition-colors cursor-pointer shadow-md"
                      title="Remove avatar"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              <h2 className="text-xl font-semibold text-secondary-900 mb-1">
                {profile.first_name} {profile.last_name}
              </h2>
              <p className="text-slate-500 text-sm mb-2">{user?.email}</p>
              {profile.designation && (
                <p className="text-orange-600 text-xs font-semibold uppercase tracking-wider mb-3">
                  {profile.designation}
                </p>
              )}

              {profile.description && (
                <p className="text-slate-600 text-sm mb-4 italic">
                  "{profile.description}"
                </p>
              )}

              <ShareButton
                url={
                  typeof window !== "undefined"
                    ? window.location.href
                    : undefined
                }
                title={`Profile: ${profile.first_name} ${profile.last_name}`}
                description={
                  profile.description ||
                  profile.designation ||
                  "Student at SashaInfinity"
                }
                size="sm"
                className="mx-auto"
              />

              <div className="space-y-2 text-sm text-slate-600">
                {(profile.city || profile.country) && (
                  <div className="flex items-center justify-center">
                    <MapPin className="h-4 w-4 mr-1" />
                    <span>
                      {[profile.city, profile.country]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                  </div>
                )}
                {user?.created_at && (
                  <div className="flex items-center justify-center">
                    <Calendar className="h-4 w-4 mr-1" />
                    <span>
                      Joined {new Date(user.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </FadeUp>
        </div>

        {/* Profile details (form) */}
        <div className="lg:col-span-2">
          <FadeUp>
            <div className="dash-card-solid p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-secondary-900">
                  Personal Information
                </h3>
                {!isEditing ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditing(true)}
                  >
                    <Edit3 className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="space-x-2">
                    <Button size="sm" onClick={handleSave}>
                      Save
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleCancel}>
                      Cancel
                    </Button>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                {/* Basic Information */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      First Name <span className="text-red-500">*</span>
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="first_name"
                        value={editForm?.first_name || ""}
                        onChange={handleInputChange}
                        required
                        className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      />
                    ) : (
                      <p className="text-secondary-900">
                        {profile.first_name || "-"}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Last Name <span className="text-red-500">*</span>
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="last_name"
                        value={editForm?.last_name || ""}
                        onChange={handleInputChange}
                        required
                        className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      />
                    ) : (
                      <p className="text-secondary-900">
                        {profile.last_name || "-"}
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      <Mail className="h-4 w-4 inline mr-1" />
                      Email Address
                    </label>
                    <p className="text-secondary-900">{user?.email}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Email cannot be changed here
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      <Phone className="h-4 w-4 inline mr-1" />
                      Phone Number
                    </label>
                    {isEditing ? (
                      <input
                        type="tel"
                        name="phone"
                        value={editForm?.phone || ""}
                        onChange={handleInputChange}
                        placeholder="+1 (555) 123-4567"
                        className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      />
                    ) : (
                      <p className="text-secondary-900">
                        {profile.phone || "-"}
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Designation / Job Title
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      name="designation"
                      value={editForm?.designation || ""}
                      onChange={handleInputChange}
                      placeholder="e.g. Software Engineer, Student, etc."
                      className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  ) : (
                    <p className="text-secondary-900">
                      {profile.designation || "-"}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Bio / About Me
                  </label>
                  {isEditing ? (
                    <textarea
                      name="description"
                      value={editForm?.description || ""}
                      onChange={handleInputChange}
                      rows={4}
                      placeholder="Tell us about yourself..."
                      className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  ) : (
                    <p className="text-secondary-900">
                      {profile.description || "-"}
                    </p>
                  )}
                </div>

                {/* Address Information */}
                <div className="border-t border-slate-200/70 pt-6">
                  <h4 className="text-md font-semibold text-secondary-900 mb-4">
                    Address Information
                  </h4>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        Street Address
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          name="address"
                          value={editForm?.address || ""}
                          onChange={handleInputChange}
                          placeholder="123 Main Street, Apt 4B"
                          className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                        />
                      ) : (
                        <p className="text-secondary-900">
                          {profile.address || "-"}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          City
                        </label>
                        {isEditing ? (
                          <input
                            type="text"
                            name="city"
                            value={editForm?.city || ""}
                            onChange={handleInputChange}
                            placeholder="San Francisco"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.city || "-"}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          State / Province
                        </label>
                        {isEditing ? (
                          <input
                            type="text"
                            name="state"
                            value={editForm?.state || ""}
                            onChange={handleInputChange}
                            placeholder="California"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.state || "-"}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          Country
                        </label>
                        {isEditing ? (
                          <input
                            type="text"
                            name="country"
                            value={editForm?.country || ""}
                            onChange={handleInputChange}
                            placeholder="United States"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.country || "-"}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          Postal Code
                        </label>
                        {isEditing ? (
                          <input
                            type="text"
                            name="postal_code"
                            value={editForm?.postal_code || ""}
                            onChange={handleInputChange}
                            placeholder="94102"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.postal_code || "-"}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Social Links */}
                <div className="border-t border-slate-200/70 pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-md font-semibold text-secondary-900">
                      Social Links
                    </h4>
                    <span className="text-xs text-slate-500">(Optional)</span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        <Globe className="h-4 w-4 inline mr-1" />
                        Website
                      </label>
                      {isEditing ? (
                        <input
                          type="url"
                          name="website"
                          value={editForm?.website || ""}
                          onChange={handleInputChange}
                          placeholder="https://yourwebsite.com"
                          className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                        />
                      ) : profile.website ? (
                        <a
                          href={profile.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-orange-600 hover:text-orange-700"
                        >
                          {profile.website}
                        </a>
                      ) : (
                        <p className="text-secondary-900">-</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          <Facebook className="h-4 w-4 inline mr-1" />
                          Facebook
                        </label>
                        {isEditing ? (
                          <input
                            type="url"
                            name="facebook"
                            value={editForm?.facebook || ""}
                            onChange={handleInputChange}
                            placeholder="https://facebook.com/username"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.facebook || "-"}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          <Twitter className="h-4 w-4 inline mr-1" />
                          Twitter
                        </label>
                        {isEditing ? (
                          <input
                            type="url"
                            name="twitter"
                            value={editForm?.twitter || ""}
                            onChange={handleInputChange}
                            placeholder="https://twitter.com/username"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.twitter || "-"}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          <Linkedin className="h-4 w-4 inline mr-1" />
                          LinkedIn
                        </label>
                        {isEditing ? (
                          <input
                            type="url"
                            name="linkedin"
                            value={editForm?.linkedin || ""}
                            onChange={handleInputChange}
                            placeholder="https://linkedin.com/in/username"
                            className="w-full px-3 py-2 border border-slate-200/70 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                          />
                        ) : (
                          <p className="text-secondary-900">
                            {profile.linkedin || "-"}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </FadeUp>
        </div>
      </div>
      <details className="rd-panel rd-profile-activity">
        <summary>Activity, achievements and visibility</summary>
        <FadeUp className="mb-6">
          <div className="mb-3">
            <h2 className="dash-h2">{roleBlock.title}</h2>
            {roleBlock.subtitle && (
              <p className="text-xs text-slate-500 mt-0.5">
                {roleBlock.subtitle}
              </p>
            )}
          </div>
          <StaggerGrid className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {roleBlock.cards.map((card) => (
              <StatCard
                key={card.title}
                title={card.title}
                value={card.value}
                icon={card.icon as any}
                tone={card.tone}
              />
            ))}
          </StaggerGrid>
        </FadeUp>
        {role === "student" && gamification && (
          <FadeUp className="mb-6">
            <SectionCard
              title="Badges & leaderboard"
              description={`${gamification.badges.length} badge${gamification.badges.length === 1 ? "" : "s"} earned`}
              icon={Trophy}
            >
              <div className="flex items-center justify-between gap-4 mb-4 p-3 rounded-xl border border-slate-200 bg-slate-50/40">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-secondary-900 flex items-center gap-1.5">
                    {gamification.stats.leaderboard_visible ? (
                      <Eye className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <EyeOff className="w-4 h-4 text-slate-400" />
                    )}
                    Show me on the leaderboard
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {gamification.stats.leaderboard_visible
                      ? "Other students can see your name, level, and XP on the leaderboard."
                      : "You are hidden from the leaderboard. You can still see your own rank."}
                  </p>
                </div>
                <button
                  role="switch"
                  aria-checked={gamification.stats.leaderboard_visible}
                  onClick={handleToggleLeaderboardVisibility}
                  disabled={visibilitySaving}
                  className={`relative flex-shrink-0 w-11 h-6 rounded-full transition-colors ${
                    gamification.stats.leaderboard_visible
                      ? "bg-orange-500"
                      : "bg-slate-300"
                  } disabled:opacity-60`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                      gamification.stats.leaderboard_visible
                        ? "translate-x-5"
                        : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              <BadgeGrid badges={gamification.badges} />
            </SectionCard>
          </FadeUp>
        )}
      </details>
    </PageLayout>
  );
}
