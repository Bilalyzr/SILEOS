import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import { transportApi, type RouteInput, type StopInput, type TransportRoute } from "@/api/campus-transport";
import { openBlob } from "@/api/campus-exams";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatMoney,
} from "./CampusOsPrimitives";

const emptyStop = (): StopInput => ({ name: "", pickup_time: "", drop_time: "", landmark: "" });

export function CampusTransport({ data, studentUserId }: { data: InstitutionOverview; studentUserId?: number }) {
  const { institution: inst } = data;
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  if (!staff) return <LearnerTransport institutionId={inst.id} studentUserId={studentUserId} />;
  return <StaffTransport data={data} />;
}

function StaffTransport({ data }: { data: InstitutionOverview }) {
  const { institution: inst, members } = data;
  const manager = ["owner", "admin"].includes(inst.role);
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["campus-transport", inst.id] });
  const routes = useQuery({ queryKey: ["campus-transport", inst.id, "routes"], queryFn: () => transportApi.routes(inst.id) });
  const [selected, setSelected] = useState<number>();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [stops, setStops] = useState<StopInput[]>([emptyStop()]);
  const current = routes.data?.find((r) => r.id === selected) ?? routes.data?.[0];
  const create = useMutation({
    mutationFn: (input: RouteInput) => transportApi.createRoute(inst.id, input),
    onSuccess: (row) => {
      setOpen(false);
      setError("");
      setStops([emptyStop()]);
      setSelected(row.id);
      toast.success(row.fee_plan_id ? "Route created with its fee plan" : "Route created");
      void invalidate();
    },
    onError: (cause) => setError(errorMessage(cause, "The route couldn’t be created.")),
  });
  return (
    <>
      <BrandBanner
        compact
        title="Every child on the right bus."
        description="Plan routes and stops, assign students, and record boarding so families can see today’s status."
      />
      <div className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <h2>Routes</h2>
            <p className="campus-muted">Capacity is enforced when students are assigned.</p>
          </div>
          {manager && <Button onClick={() => setOpen(true)}>New route</Button>}
        </div>
        {routes.isLoading && <CampusOsLoading label="Loading routes" />}
        {routes.isError && <CampusOsError message="Routes couldn’t be loaded." retry={() => void routes.refetch()} />}
        {routes.data && !routes.data.length && <CampusOsEmpty title="No routes yet" description="Create a route with its stops to start assigning students." />}
        <div className="campus-actions">
          {routes.data?.map((r) => (
            <button key={r.id} type="button" className="campus-chip" aria-pressed={current?.id === r.id} onClick={() => setSelected(r.id)}>
              {r.name} · {r.occupied}/{r.capacity}
            </button>
          ))}
        </div>
      </div>
      {current && <RouteDetail institutionId={inst.id} route={current} members={members} manager={manager} invalidate={invalidate} />}
      <GlassDialog open={open} onOpenChange={setOpen} title="New route">
        <form
          className="campus-form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const fee = String(form.get("fee_amount") || "").trim();
            create.mutate({
              name: String(form.get("name") || "").trim(),
              vehicle_number: String(form.get("vehicle_number") || "").trim(),
              driver_name: String(form.get("driver_name") || "").trim(),
              driver_phone: String(form.get("driver_phone") || "").trim(),
              capacity: Number(form.get("capacity") || 40),
              fee_amount: fee ? fee : null,
              currency: "INR",
              stops: stops.filter((s) => s.name.trim()),
            });
          }}
        >
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <label className="campus-form">
            Route name
            <input className="campus-select" name="name" required maxLength={120} placeholder="North loop" />
          </label>
          <label className="campus-form">
            Vehicle number
            <input className="campus-select" name="vehicle_number" maxLength={40} />
          </label>
          <label className="campus-form">
            Driver name
            <input className="campus-select" name="driver_name" maxLength={120} />
          </label>
          <label className="campus-form">
            Driver phone
            <input className="campus-select" name="driver_phone" maxLength={20} />
          </label>
          <label className="campus-form">
            Capacity
            <input className="campus-select" name="capacity" type="number" min={1} max={200} defaultValue={40} />
          </label>
          <label className="campus-form">
            Transport fee (per year, optional)
            <input className="campus-select" name="fee_amount" type="number" min={0} step="0.01" placeholder="0.00" />
          </label>
          <fieldset className="campus-panel p-4">
            <legend className="px-2 text-sm font-bold text-stone-800">Stops in order</legend>
            {stops.map((stop, index) => (
              <div className="campus-form-grid" key={index}>
                <label>
                  Stop {index + 1}
                  <input aria-label={`Stop ${index + 1} name`} value={stop.name} maxLength={120} onChange={(e) => setStops(stops.map((s, i) => (i === index ? { ...s, name: e.target.value } : s)))} />
                </label>
                <label>
                  Pickup
                  <input aria-label={`Stop ${index + 1} pickup`} value={stop.pickup_time} placeholder="07:10" maxLength={5} onChange={(e) => setStops(stops.map((s, i) => (i === index ? { ...s, pickup_time: e.target.value } : s)))} />
                </label>
                <label>
                  Drop
                  <input aria-label={`Stop ${index + 1} drop`} value={stop.drop_time} placeholder="16:20" maxLength={5} onChange={(e) => setStops(stops.map((s, i) => (i === index ? { ...s, drop_time: e.target.value } : s)))} />
                </label>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => setStops([...stops, emptyStop()])}>
              Add stop
            </Button>
          </fieldset>
          <Button type="submit" loading={create.isPending}>
            Create route
          </Button>
        </form>
      </GlassDialog>
    </>
  );
}

function RouteDetail({
  institutionId,
  route,
  members,
  manager,
  invalidate,
}: {
  institutionId: number;
  route: TransportRoute;
  members: InstitutionOverview["members"];
  manager: boolean;
  invalidate: () => Promise<void>;
}) {
  const roster = useQuery({ queryKey: ["campus-transport", institutionId, "roster", route.id], queryFn: () => transportApi.roster(institutionId, route.id) });
  const [flags, setFlags] = useState<Record<number, { boarded: boolean; dropped: boolean }>>({});
  const [memberId, setMemberId] = useState(0);
  const [stopId, setStopId] = useState(route.stops[0]?.id ?? 0);
  const assigned = new Set(roster.data?.students.map((s) => s.member_id));
  const candidates = members.filter((m) => m.role === "student" && m.status === "active" && !assigned.has(m.id));
  const assign = useMutation({
    mutationFn: () => transportApi.assign(institutionId, route.id, memberId, stopId),
    onSuccess: (row) => {
      toast.success(`${row.student_name} added at ${row.stop_name}`);
      setMemberId(0);
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The student couldn’t be assigned.")),
  });
  const end = useMutation({
    mutationFn: (assignmentId: number) => transportApi.end(institutionId, assignmentId),
    onSuccess: () => {
      toast.success("Student removed from the route");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The assignment couldn’t be ended.")),
  });
  const save = useMutation({
    mutationFn: () =>
      transportApi.boarding(
        institutionId,
        route.id,
        roster.data!.day,
        roster.data!.students.map((s) => ({
          member_id: s.member_id,
          boarded: flags[s.member_id]?.boarded ?? s.boarded ?? false,
          dropped: flags[s.member_id]?.dropped ?? s.dropped ?? false,
        })),
      ),
    onSuccess: () => {
      toast.success("Boarding recorded");
      setFlags({});
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Boarding couldn’t be saved.")),
  });
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>{route.name}</h2>
          <p className="campus-muted">
            {[route.vehicle_number, route.driver_name, route.driver_phone].filter(Boolean).join(" · ") || "No vehicle details"}
            {route.fee_amount ? ` · ${formatMoney(route.fee_amount, route.currency)} per year` : ""}
          </p>
        </div>
        <CampusOsBadge tone={route.occupied >= route.capacity ? "danger" : "success"}>
          {route.occupied} / {route.capacity} seats
        </CampusOsBadge>
      </div>
      <h3 className="mt-2">Stops</h3>
      <div className="campus-actions">
        {route.stops.map((s) => (
          <span className="campus-chip" key={s.id}>
            {s.sequence}. {s.name}
            {s.pickup_time && ` · ${s.pickup_time}`}
          </span>
        ))}
        {!route.stops.length && <p className="campus-muted">No stops yet.</p>}
      </div>
      {manager && route.stops.length > 0 && (
        <form
          className="campus-form-grid mt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (memberId && stopId) assign.mutate();
          }}
        >
          <label className="campus-form">
            Student
            <select className="campus-select" aria-label="Student to assign" value={memberId} onChange={(e) => setMemberId(Number(e.target.value))}>
              <option value={0}>Choose…</option>
              {candidates.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <label className="campus-form">
            Stop
            <select className="campus-select" aria-label="Stop for assignment" value={stopId} onChange={(e) => setStopId(Number(e.target.value))}>
              {route.stops.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={!memberId || route.occupied >= route.capacity} loading={assign.isPending}>
            Assign to route
          </Button>
        </form>
      )}
      <h3 className="mt-4">Today’s boarding{roster.data ? ` · ${roster.data.day}` : ""}</h3>
      {roster.isLoading && <CampusOsLoading label="Loading roster" />}
      {roster.isError && <CampusOsError message="The roster couldn’t be loaded." retry={() => void roster.refetch()} />}
      {roster.data && !roster.data.students.length && <p className="campus-muted">No students assigned yet.</p>}
      {!!roster.data?.students.length && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <div className="campus-table-wrap">
            <table className="campus-table">
              <thead>
                <tr>
                  <th>Stop</th>
                  <th>Student</th>
                  <th>Boarded</th>
                  <th>Dropped</th>
                  {manager && <th />}
                </tr>
              </thead>
              <tbody>
                {roster.data.students.map((s) => {
                  const state = flags[s.member_id] ?? { boarded: s.boarded ?? false, dropped: s.dropped ?? false };
                  return (
                    <tr key={s.id}>
                      <td>{s.stop_name}</td>
                      <td>{s.student_name}</td>
                      <td>
                        <input type="checkbox" className="campus-check" aria-label={`Boarded ${s.student_name}`} checked={state.boarded} onChange={(e) => setFlags({ ...flags, [s.member_id]: { ...state, boarded: e.target.checked } })} />
                      </td>
                      <td>
                        <input type="checkbox" className="campus-check" aria-label={`Dropped ${s.student_name}`} checked={state.dropped} onChange={(e) => setFlags({ ...flags, [s.member_id]: { ...state, dropped: e.target.checked } })} />
                      </td>
                      {manager && (
                        <td>
                          <Button size="sm" variant="ghost" loading={end.isPending} onClick={() => end.mutate(s.id)}>
                            Remove
                          </Button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="campus-actions mt-4">
            <Button type="submit" loading={save.isPending}>
              Save boarding
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                transportApi
                  .rosterCsv(institutionId, route.id)
                  .then((blob) => openBlob(blob, `transport-${route.name}.csv`))
                  .catch((e) => toast.error(errorMessage(e, "The roster couldn’t be downloaded.")))
              }
            >
              Download roster
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

function LearnerTransport({ institutionId, studentUserId }: { institutionId: number; studentUserId?: number }) {
  const user = useAuthStore((s) => s.user);
  const sid = user?.role === "parent" ? studentUserId : undefined;
  const me = useQuery({ queryKey: ["campus-transport", institutionId, "me", sid], queryFn: () => transportApi.me(institutionId, sid) });
  return (
    <>
      <BrandBanner compact title="Your bus, your stop." description="Route, stop and today’s boarding status at a glance." />
      <section className="campus-panel">
        {me.isLoading && <CampusOsLoading label="Loading transport" />}
        {me.isError && <CampusOsError message="Transport details couldn’t be loaded." retry={() => void me.refetch()} />}
        {me.data && !me.data.assigned && <CampusOsEmpty title="No transport assigned" description="Ask the campus office to assign a route and stop." />}
        {me.data?.assigned && me.data.route && (
          <>
            <h2>{me.data.route.name}</h2>
            <p className="campus-muted">
              {[me.data.route.vehicle_number, me.data.route.driver_name, me.data.route.driver_phone].filter(Boolean).join(" · ")}
            </p>
            {me.data.stop && (
              <p className="mt-2">
                Stop: <strong>{me.data.stop.name}</strong>
                {me.data.stop.pickup_time && ` · pickup ${me.data.stop.pickup_time}`}
                {me.data.stop.drop_time && ` · drop ${me.data.stop.drop_time}`}
              </p>
            )}
            <p className="mt-2">
              Today:{" "}
              {me.data.today ? (
                <>
                  <CampusOsBadge tone={me.data.today.boarded ? "success" : "warning"}>{me.data.today.boarded ? "Boarded" : "Not boarded"}</CampusOsBadge>{" "}
                  <CampusOsBadge tone={me.data.today.dropped ? "success" : "neutral"}>{me.data.today.dropped ? "Dropped" : "Not dropped yet"}</CampusOsBadge>
                </>
              ) : (
                <CampusOsBadge tone="neutral">Not recorded yet</CampusOsBadge>
              )}
            </p>
          </>
        )}
      </section>
    </>
  );
}
