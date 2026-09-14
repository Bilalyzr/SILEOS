import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Radio } from "lucide-react";
import { fetchLiveNow, type LiveClassOut } from "@/api/liveClasses";
import { useAuthStore } from "@/store/auth";

const LiveContext = createContext<LiveClassOut[]>([]);
export const useStudentLiveClasses = () => useContext(LiveContext);

/** One enrollment-gated request shared by all visible course cards. */
export function StudentLiveProvider({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  const enabled = authenticated && user?.role === "student";
  const query = useQuery({
    queryKey: ["student-live-classes", user?.id],
    queryFn: fetchLiveNow,
    enabled,
    staleTime: 10000,
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: 1,
  });
  const classes =
    enabled && !query.isError
      ? (query.data?.classes || []).filter((c) => c.status === "live")
      : [];
  return (
    <LiveContext.Provider value={classes}>{children}</LiveContext.Provider>
  );
}

export function StudentLiveClasses({ courseId }: { courseId?: number }) {
  const classes = useStudentLiveClasses().filter(
    (c) => courseId === undefined || c.course_id === courseId,
  );
  if (!classes.length) return null;
  return (
    <section
      className="astra-live-notice"
      aria-label={
        courseId ? "Live class for this course" : "Live classes in your courses"
      }
    >
      <div className="flex items-center gap-2 font-bold">
        <Radio size={18} />
        <h2>Live now</h2>
      </div>
      <p>Your enrolled course has a class running. Open it to join.</p>
      <div className="flex flex-wrap gap-3">
        {classes.map((c) => (
          <Link
            key={c.id}
            className="sf-primary"
            to={`/student/live-classes/${c.id}/join`}
            aria-label={`Join live class: ${c.title}`}
          >
            <Radio size={15} />
            {c.title}
            <span>Join live</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
