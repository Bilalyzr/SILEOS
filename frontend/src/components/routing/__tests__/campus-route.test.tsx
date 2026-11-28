import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { CampusRoute } from "../campus-route"

let auth: any
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => auth }))
vi.mock("@/components/loading/InfinityTrace", () => ({ InfinityTrace: () => <div>loading</div> }))

const renderAt = () =>
  render(
    <MemoryRouter initialEntries={["/institutions"]}>
      <Routes>
        <Route path="/institutions" element={<CampusRoute><div>campus workspace</div></CampusRoute>} />
        <Route path="/campus/login" element={<div>campus sign in</div>} />
        <Route path="/admin/dashboard" element={<div>lms admin dashboard</div>} />
        <Route path="/superadmin/dashboard" element={<div>lms superadmin dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
const as = (role?: string) => {
  auth = { isAuthenticated: !!role, isLoading: false, hasResolvedAuth: true, user: role ? { role } : null }
}

describe("CampusRoute", () => {
  it("sends signed-out visitors to the Campus sign-in, not the LMS one", () => {
    as(); renderAt()
    expect(screen.getByText("campus sign in")).toBeInTheDocument()
  })
  it("keeps LMS admin out of Campus and returns them to their own dashboard", () => {
    as("admin"); renderAt()
    expect(screen.getByText("lms admin dashboard")).toBeInTheDocument()
    expect(screen.queryByText("campus workspace")).toBeNull()
  })
  it("keeps LMS superadmin out of Campus", () => {
    as("superadmin"); renderAt()
    expect(screen.getByText("lms superadmin dashboard")).toBeInTheDocument()
  })
  it.each(["student", "instructor", "campus_admin"])("lets %s in", (role) => {
    as(role); renderAt()
    expect(screen.getByText("campus workspace")).toBeInTheDocument()
  })
  it("waits while the session resolves", () => {
    auth = { isAuthenticated: false, isLoading: true, hasResolvedAuth: false, user: null }
    renderAt()
    expect(screen.getByText("loading")).toBeInTheDocument()
  })
})
