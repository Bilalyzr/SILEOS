import { useEffect, useId, useState } from "react";
import { api } from "@/api/axios";

export function CourseLinkField({
  value,
  onChange,
  courseId,
}: {
  value: string;
  onChange: (value: string) => void;
  courseId?: number | null;
}) {
  const id = useId();
  const [result, setResult] = useState<{
    value: string;
    available: boolean;
    message: string;
  }>();
  useEffect(() => {
    if (!value) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .get("/courses/slug-availability", {
          params: { slug: value, exclude_course_id: courseId || undefined },
          signal: controller.signal,
        })
        .then(({ data }) => {
          if (!controller.signal.aborted) setResult({ ...data, value });
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setResult({
              value,
              available: false,
              message:
                "Availability could not be checked. Saving will check again.",
            });
        });
    }, 350);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [value, courseId]);
  const current = result?.value === value ? result : undefined;
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block font-medium">
        Custom course link
      </label>
      <input
        id={id}
        className="w-full"
        value={value}
        maxLength={120}
        placeholder="your-course-name"
        onChange={(e) =>
          onChange(e.target.value.toLowerCase().replace(/\s+/g, "-"))
        }
        aria-describedby={`${id}-status`}
        aria-invalid={!!value && current?.available === false}
      />
      <p className="text-sm break-all">
        {window.location.origin}/courses/{value || "automatic-course-link"}
      </p>
      <p
        id={`${id}-status`}
        role="status"
        className={`text-sm ${current?.available === false ? "text-red-700" : "text-slate-600"}`}
      >
        {value
          ? current?.message || "Checking availability…"
          : "Optional. Leave blank to create a link automatically."}
      </p>
    </div>
  );
}
