import * as React from 'react'
import { Link } from 'react-router-dom'
import { Briefcase, Eye, EyeOff, CheckCircle2, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { candidateAPI, CandidateProfile } from '@/api/candidate'
import toast from 'react-hot-toast'

export const InternshipEligibilityWidget: React.FC = () => {
  const [profile, setProfile] = React.useState<CandidateProfile | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [toggling, setToggling] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    candidateAPI
      .getMe()
      .then((p) => {
        if (!cancelled) setProfile(p)
      })
      .catch(() => {
        /* silently ignore — widget is opportunistic */
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const onToggleVisibility = async () => {
    if (!profile) return
    setToggling(true)
    try {
      const next = await candidateAPI.setVisibility(!profile.is_visible)
      setProfile(next)
      toast.success(next.is_visible ? 'Profile now visible to companies' : 'Profile hidden')
    } catch (e: any) {
      toast.error(e?.message || 'Failed to update visibility')
    } finally {
      setToggling(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-neutral-500">Loading internship status...</CardContent>
      </Card>
    )
  }

  const eligible = !!profile?.eligibility?.eligible
  const source = profile?.eligibility?.source

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-primary-600" />
          Internship Marketplace
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {eligible ? (
              <CheckCircle2 className="h-5 w-5 text-success-600" />
            ) : (
              <XCircle className="h-5 w-5 text-neutral-400" />
            )}
            <span className="text-sm font-medium">
              {eligible ? 'Eligible for internships' : 'Not yet eligible'}
            </span>
          </div>
          {source && (
            <Badge variant="outline" className="text-xs">
              {source === 'auto_certificate' ? 'via certificate' : 'via SPOC'}
            </Badge>
          )}
        </div>

        {!eligible && (
          <p className="text-xs text-neutral-500">
            Complete a course to earn your certificate — eligibility is granted automatically.
          </p>
        )}

        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-neutral-500">
            <span>Profile completeness</span>
            <span>{profile?.completeness ?? 0}%</span>
          </div>
          <Progress value={profile?.completeness ?? 0} className="h-2" />
        </div>

        <div className="flex items-center justify-between rounded-md bg-neutral-50 p-3">
          <div className="flex items-center gap-2">
            {profile?.is_visible ? (
              <Eye className="h-4 w-4 text-primary-600" />
            ) : (
              <EyeOff className="h-4 w-4 text-neutral-400" />
            )}
            <span className="text-sm">
              {profile?.is_visible ? 'Visible to companies' : 'Hidden from companies'}
            </span>
          </div>
          <Button
            size="sm"
            variant={profile?.is_visible ? 'outline' : 'default'}
            disabled={toggling || !eligible}
            onClick={onToggleVisibility}
          >
            {profile?.is_visible ? 'Hide' : 'Go visible'}
          </Button>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard/internship-profile">Edit profile</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard/internship-inbox">Inbox</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard/my-vouchers">My Vouchers</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default InternshipEligibilityWidget
