import { LoginForm } from "@/components/auth/login-form"

/** Separate Campus sign-in. LMS admin/superadmin accounts are refused here. */
export default function CampusLoginPage() {
  return <LoginForm portal="campus" />
}
