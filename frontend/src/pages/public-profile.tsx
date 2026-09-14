import * as React from "react"
import { useParams, Link } from "react-router-dom"
import {
  Globe,
  Facebook,
  Twitter,
  Linkedin,
  Mail,
  MapPin,
  Calendar,
  BookOpen,
  Users,
  Star,
  User as UserIcon,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { api } from "@/api/axios"
import { getMediaUrl } from "@/utils/media"
import { ShareButton } from "@/components/ui/share-button"

interface PublicProfile {
  username: string
  display_name: string
  role: string
  profile_photo: string
  cover_photo: string
  designation: string
  bio: string
  location: string
  email: string
  joined_date: string | null
  social_links: {
    website?: string
    facebook?: string
    twitter?: string
    linkedin?: string
  }
  stats: {
    courses?: number
    students?: number
    rating?: number
  }
}

/**
 * Public, READ-ONLY profile page (route: /u/:username).
 *
 * Completely separate from the protected `/profile` route — it is not wrapped
 * in ProtectedRoute and renders no edit controls, so a shared link opens for
 * anyone and the profile can never be edited from here.
 */
export const PublicProfilePage = () => {
  const { username } = useParams<{ username: string }>()
  const [profile, setProfile] = React.useState<PublicProfile | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let active = true
    const load = async () => {
      if (!username) return
      try {
        setLoading(true)
        setError(null)
        const res = await api.get(`/users/public/${username}`)
        if (active) setProfile(res.data)
      } catch (e) {
        if (active) setError("This profile could not be found.")
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [username])

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading profile…</p>
        </div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <UserIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Profile Not Found</h2>
          <p className="text-gray-600 mb-6">
            {error || "The profile you're looking for doesn't exist."}
          </p>
          <Link to="/" className="text-primary-600 hover:underline">
            Go to SashaInfinity
          </Link>
        </div>
      </div>
    )
  }

  const cover = getMediaUrl(profile.cover_photo)
  const photo = getMediaUrl(profile.profile_photo)
  const isInstructor = profile.role === "instructor" || profile.role === "admin"
  const joined = profile.joined_date
    ? new Date(profile.joined_date).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
      })
    : ""

  const socials = [
    { url: profile.social_links.website, Icon: Globe },
    { url: profile.social_links.facebook, Icon: Facebook },
    { url: profile.social_links.twitter, Icon: Twitter },
    { url: profile.social_links.linkedin, Icon: Linkedin },
  ].filter((s) => s.url)

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Cover banner */}
      <div
        className="relative h-48 md:h-60 bg-gradient-to-br from-primary-600 to-primary-800"
        style={
          cover
            ? { backgroundImage: `url(${cover})`, backgroundSize: "cover", backgroundPosition: "center" }
            : undefined
        }
      >
        <div className="absolute inset-0 bg-black/20" />
      </div>

      <div className="container-custom">
        <div className="max-w-4xl mx-auto -mt-16 relative z-10 px-4">
          {/* Header card */}
          <Card>
            <CardContent className="pt-0">
              <div className="flex flex-col items-center text-center -mt-14">
                <Avatar size="xl" className="w-28 h-28 ring-4 ring-white shadow-lg">
                  {photo && <AvatarImage src={photo} />}
                  <AvatarFallback className="bg-primary-700 text-white text-3xl font-bold">
                    {profile.display_name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>

                <h1 className="text-3xl font-bold text-gray-900 mt-4">
                  {profile.display_name}
                </h1>

                <div className="flex flex-wrap items-center justify-center gap-3 mt-2 text-gray-600">
                  <Badge className="bg-primary-100 text-primary-700 border-0 uppercase tracking-wide">
                    {profile.role}
                  </Badge>
                  {profile.designation && <span className="text-sm">{profile.designation}</span>}
                </div>

                <div className="flex flex-wrap items-center justify-center gap-4 mt-3 text-sm text-gray-500">
                  {profile.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" /> {profile.location}
                    </span>
                  )}
                  {joined && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" /> Joined {joined}
                    </span>
                  )}
                  {profile.email && (
                    <a
                      href={`mailto:${profile.email}`}
                      className="flex items-center gap-1 hover:text-primary-600"
                    >
                      <Mail className="w-4 h-4" /> {profile.email}
                    </a>
                  )}
                </div>

                {profile.bio && (
                  <p className="text-gray-600 mt-4 max-w-2xl leading-relaxed">{profile.bio}</p>
                )}

                <div className="mt-5">
                  <ShareButton
                    url={`${window.location.origin}/u/${profile.username}`}
                    title={`${profile.display_name} on SashaInfinity`}
                    description={
                      profile.bio ||
                      `Discover ${profile.display_name}'s learning profile.`
                    }
                  />
                </div>

                {socials.length > 0 && (
                  <div className="flex items-center justify-center gap-3 mt-5">
                    {socials.map(({ url, Icon }, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-neutral-100 hover:bg-primary-100 text-gray-600 hover:text-primary-600 p-2.5 rounded-full transition-colors"
                      >
                        <Icon className="w-5 h-5" />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6 mb-12">
            <StatCard
              icon={<BookOpen className="w-6 h-6 text-primary-600" />}
              value={profile.stats.courses ?? 0}
              label={isInstructor ? "Courses" : "Enrolled"}
            />
            {isInstructor ? (
              <>
                <StatCard
                  icon={<Users className="w-6 h-6 text-success-600" />}
                  value={(profile.stats.students ?? 0).toLocaleString()}
                  label="Students"
                />
                <StatCard
                  icon={<Star className="w-6 h-6 text-yellow-600" />}
                  value={(profile.stats.rating ?? 0).toFixed(1)}
                  label="Rating"
                />
              </>
            ) : (
              <>
                <StatCard
                  icon={<Star className="w-6 h-6 text-yellow-600" />}
                  value="Learner"
                  label="Member"
                />
                <StatCard
                  icon={<Calendar className="w-6 h-6 text-blue-600" />}
                  value={joined ? joined.split(" ").pop() ?? "" : "—"}
                  label="Since"
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const StatCard = ({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: React.ReactNode
  label: string
}) => (
  <Card className="text-center">
    <CardContent className="pt-6">
      <div className="w-12 h-12 bg-neutral-100 rounded-full flex items-center justify-center mx-auto mb-3">
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <p className="text-gray-600 text-sm">{label}</p>
    </CardContent>
  </Card>
)
