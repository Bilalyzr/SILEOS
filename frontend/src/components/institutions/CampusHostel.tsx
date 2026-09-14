import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import { hostelApi, type BlockInput, type HostelPass, type PassStatus, type RoomInput } from "@/api/campus-hostel";
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
  formatDate,
  formatMoney,
  formatTime,
  readable,
} from "./CampusOsPrimitives";

const PASS_TONE: Record<PassStatus, "warning" | "success" | "danger" | "neutral"> = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
  returned: "neutral",
};
const emptyRoom = (): RoomInput => ({ number: "", floor: "", room_type: "double", capacity: 2, active: true });

export function CampusHostel({ data, studentUserId }: { data: InstitutionOverview; studentUserId?: number }) {
  const { institution: inst } = data;
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  if (!staff) return <ResidentHostel institutionId={inst.id} studentUserId={studentUserId} />;
  return <StaffHostel data={data} />;
}

function StaffHostel({ data }: { data: InstitutionOverview }) {
  const { institution: inst, members } = data;
  const manager = ["owner", "admin"].includes(inst.role);
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["campus-hostel", inst.id] });
  const [tab, setTab] = useState<"rooms" | "passes" | "visitors">("rooms");
  return (
    <>
      <BrandBanner compact title="A safe place to stay." description="Blocks, rooms and residents, with out-passes and a visitor register the warden can trust." />
      <div className="campus-tabs" role="tablist">
        {(["rooms", "passes", "visitors"] as const).map((key) => (
          <button key={key} role="tab" type="button" aria-selected={tab === key} className="campus-chip" onClick={() => setTab(key)}>
            {{ rooms: "Rooms", passes: "Out-passes", visitors: "Visitors" }[key]}
          </button>
        ))}
      </div>
      {tab === "rooms" && <Rooms institutionId={inst.id} members={members} manager={manager} invalidate={invalidate} />}
      {tab === "passes" && <Passes institutionId={inst.id} invalidate={invalidate} />}
      {tab === "visitors" && <Visitors institutionId={inst.id} members={members} invalidate={invalidate} />}
    </>
  );
}

function Rooms({ institutionId, members, manager, invalidate }: { institutionId: number; members: InstitutionOverview["members"]; manager: boolean; invalidate: () => Promise<void> }) {
  const occupancy = useQuery({ queryKey: ["campus-hostel", institutionId, "occupancy"], queryFn: () => hostelApi.occupancy(institutionId) });
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [rooms, setRooms] = useState<RoomInput[]>([emptyRoom()]);
  const [allocating, setAllocating] = useState<number>(0);
  const [memberId, setMemberId] = useState(0);
  const staffMembers = members.filter((m) => ["owner", "admin", "teacher"].includes(m.role) && m.status === "active");
  const residents = new Set(occupancy.data?.allocations.map((a) => a.member_id));
  const candidates = members.filter((m) => m.role === "student" && m.status === "active" && !residents.has(m.id));
  const create = useMutation({
    mutationFn: (input: BlockInput) => hostelApi.createBlock(institutionId, input),
    onSuccess: (row) => {
      setOpen(false);
      setError("");
      setRooms([emptyRoom()]);
      toast.success(row.fee_plan_id ? "Block created with its fee plan" : "Block created");
      void invalidate();
    },
    onError: (cause) => setError(errorMessage(cause, "The block couldn’t be created.")),
  });
  const allocate = useMutation({
    mutationFn: () => hostelApi.allocate(institutionId, allocating, memberId),
    onSuccess: (row) => {
      toast.success(`${row.student_name} allocated to ${row.block_name} ${row.room_number}`);
      setAllocating(0);
      setMemberId(0);
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The room couldn’t be allocated.")),
  });
  const checkout = useMutation({
    mutationFn: (allocationId: number) => hostelApi.checkout(institutionId, allocationId),
    onSuccess: () => {
      toast.success("Checked out");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Check-out failed.")),
  });
  return (
    <>
      <div className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <h2>Occupancy</h2>
            <p className="campus-muted">
              {occupancy.data ? `${occupancy.data.occupied} of ${occupancy.data.capacity} beds in use` : "Blocks and rooms with live occupancy."}
            </p>
          </div>
          <div className="campus-actions">
            <Button
              variant="outline"
              onClick={() =>
                hostelApi
                  .occupancyCsv(institutionId)
                  .then((blob) => openBlob(blob, "hostel-occupancy.csv"))
                  .catch((e) => toast.error(errorMessage(e, "The report couldn’t be downloaded.")))
              }
            >
              Download CSV
            </Button>
            {manager && <Button onClick={() => setOpen(true)}>New block</Button>}
          </div>
        </div>
        {occupancy.isLoading && <CampusOsLoading label="Loading hostel" />}
        {occupancy.isError && <CampusOsError message="Hostel data couldn’t be loaded." retry={() => void occupancy.refetch()} />}
        {occupancy.data && !occupancy.data.blocks.length && <CampusOsEmpty title="No hostel blocks yet" description="Create a block with its rooms to start allocating residents." />}
      </div>
      {occupancy.data?.blocks.map((block) => (
        <section className="campus-panel" key={block.id}>
          <div className="campus-panel-heading">
            <div>
              <h2>{block.name}</h2>
              <p className="campus-muted">
                {[block.warden_name && `Warden ${block.warden_name}`, readable(block.gender), block.fee_amount ? `${formatMoney(block.fee_amount, block.currency)} per year` : null].filter(Boolean).join(" · ")}
              </p>
            </div>
            <CampusOsBadge tone={block.occupied >= block.capacity ? "danger" : "success"}>
              {block.occupied} / {block.capacity} beds
            </CampusOsBadge>
          </div>
          <div className="campus-table-wrap">
            <table className="campus-table">
              <thead>
                <tr>
                  <th>Room</th>
                  <th>Type</th>
                  <th>Beds</th>
                  <th>Residents</th>
                  {manager && <th />}
                </tr>
              </thead>
              <tbody>
                {block.rooms.map((room) => {
                  const here = occupancy.data!.allocations.filter((a) => a.room_id === room.id);
                  return (
                    <tr key={room.id}>
                      <td>
                        {room.number}
                        {room.floor && <small>Floor {room.floor}</small>}
                      </td>
                      <td>{readable(room.room_type)}</td>
                      <td>
                        {room.occupied} / {room.capacity}
                      </td>
                      <td>
                        {here.length ? (
                          <ul className="campus-activity">
                            {here.map((a) => (
                              <li key={a.id}>
                                {a.student_name}{" "}
                                {manager && (
                                  <Button size="sm" variant="ghost" loading={checkout.isPending} onClick={() => checkout.mutate(a.id)}>
                                    Check out
                                  </Button>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          "—"
                        )}
                      </td>
                      {manager && (
                        <td>
                          <Button size="sm" disabled={room.occupied >= room.capacity || !room.active} onClick={() => setAllocating(room.id)}>
                            Allocate
                          </Button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ))}
      <GlassDialog open={open} onOpenChange={setOpen} title="New hostel block">
        <form
          className="campus-form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const fee = String(form.get("fee_amount") || "").trim();
            create.mutate({
              name: String(form.get("name") || "").trim(),
              warden_member_id: Number(form.get("warden_member_id")) || null,
              gender: String(form.get("gender") || "any") as BlockInput["gender"],
              fee_amount: fee ? fee : null,
              currency: "INR",
              rooms: rooms.filter((r) => r.number.trim()),
            });
          }}
        >
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <label className="campus-form">
            Block name
            <input className="campus-select" name="name" required maxLength={120} placeholder="Block A" />
          </label>
          <label className="campus-form">
            Warden
            <select className="campus-select" name="warden_member_id" defaultValue="">
              <option value="">Not assigned</option>
              {staffMembers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <label className="campus-form">
            For
            <select className="campus-select" name="gender" defaultValue="any">
              <option value="any">Everyone</option>
              <option value="male">Boys</option>
              <option value="female">Girls</option>
            </select>
          </label>
          <label className="campus-form">
            Hostel fee (per year, optional)
            <input className="campus-select" name="fee_amount" type="number" min={0} step="0.01" placeholder="0.00" />
          </label>
          <fieldset className="campus-panel p-4">
            <legend className="px-2 text-sm font-bold text-stone-800">Rooms</legend>
            {rooms.map((room, index) => (
              <div className="campus-form-grid" key={index}>
                <label>
                  Room number
                  <input aria-label={`Room ${index + 1} number`} value={room.number} maxLength={20} onChange={(e) => setRooms(rooms.map((r, i) => (i === index ? { ...r, number: e.target.value } : r)))} />
                </label>
                <label>
                  Type
                  <select aria-label={`Room ${index + 1} type`} value={room.room_type} onChange={(e) => setRooms(rooms.map((r, i) => (i === index ? { ...r, room_type: e.target.value as RoomInput["room_type"] } : r)))}>
                    <option value="single">Single</option>
                    <option value="double">Double</option>
                    <option value="triple">Triple</option>
                    <option value="dormitory">Dormitory</option>
                  </select>
                </label>
                <label>
                  Beds
                  <input aria-label={`Room ${index + 1} beds`} type="number" min={1} max={20} value={room.capacity} onChange={(e) => setRooms(rooms.map((r, i) => (i === index ? { ...r, capacity: Number(e.target.value) } : r)))} />
                </label>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => setRooms([...rooms, emptyRoom()])}>
              Add room
            </Button>
          </fieldset>
          <Button type="submit" loading={create.isPending}>
            Create block
          </Button>
        </form>
      </GlassDialog>
      <GlassDialog
        open={!!allocating}
        onOpenChange={(v) => {
          if (!v) setAllocating(0);
        }}
        title="Allocate a room"
      >
        <form
          className="campus-form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            if (memberId) allocate.mutate();
          }}
        >
          <label className="campus-form">
            Student
            <select className="campus-select" aria-label="Resident" value={memberId} onChange={(e) => setMemberId(Number(e.target.value))}>
              <option value={0}>Choose…</option>
              {candidates.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={!memberId} loading={allocate.isPending}>
            Allocate
          </Button>
        </form>
      </GlassDialog>
    </>
  );
}

function PassTable({ rows, actions }: { rows: HostelPass[]; actions?: (row: HostelPass) => React.ReactNode }) {
  return (
    <div className="campus-table-wrap">
      <table className="campus-table">
        <thead>
          <tr>
            <th>Resident</th>
            <th>Kind</th>
            <th>Leaves</th>
            <th>Returns</th>
            <th>Reason</th>
            <th>Status</th>
            {actions && <th />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.student_name ?? "—"}</td>
              <td>{readable(row.kind)}</td>
              <td>
                {formatDate(row.leaves_at)} {formatTime(row.leaves_at)}
              </td>
              <td>
                {formatDate(row.returns_at)} {formatTime(row.returns_at)}
              </td>
              <td>{row.reason}</td>
              <td>
                <CampusOsBadge tone={PASS_TONE[row.status]}>{readable(row.status)}</CampusOsBadge>
                {row.decision_note && <small>{row.decision_note}</small>}
              </td>
              {actions && <td>{actions(row)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Passes({ institutionId, invalidate }: { institutionId: number; invalidate: () => Promise<void> }) {
  const [status, setStatus] = useState<PassStatus>("pending");
  const list = useQuery({ queryKey: ["campus-hostel", institutionId, "passes", status], queryFn: () => hostelApi.passes(institutionId, { status }) });
  const [rejecting, setRejecting] = useState<HostelPass | null>(null);
  const [note, setNote] = useState("");
  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: number; approve: boolean }) => (approve ? hostelApi.approvePass(institutionId, id) : hostelApi.rejectPass(institutionId, id, note)),
    onSuccess: (row) => {
      setRejecting(null);
      setNote("");
      toast.success(row.status === "approved" ? "Pass approved" : "Pass rejected");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The decision couldn’t be saved.")),
  });
  const back = useMutation({
    mutationFn: (id: number) => hostelApi.returnPass(institutionId, id),
    onSuccess: () => {
      toast.success("Marked returned");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Return couldn’t be recorded.")),
  });
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <h2>Out-passes</h2>
        <label className="campus-form">
          Status
          <select className="campus-select" aria-label="Pass status" value={status} onChange={(e) => setStatus(e.target.value as PassStatus)}>
            {(["pending", "approved", "rejected", "returned"] as PassStatus[]).map((s) => (
              <option key={s} value={s}>
                {readable(s)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {list.isLoading && <CampusOsLoading label="Loading passes" />}
      {list.isError && <CampusOsError message="Passes couldn’t be loaded." retry={() => void list.refetch()} />}
      {list.data && !list.data.length && <CampusOsEmpty title={`No ${status} passes`} description="Residents request passes from their hostel page." />}
      {!!list.data?.length && (
        <PassTable
          rows={list.data}
          actions={(row) =>
            row.status === "pending" ? (
              <div className="campus-actions">
                <Button size="sm" loading={decide.isPending} onClick={() => decide.mutate({ id: row.id, approve: true })}>
                  Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => setRejecting(row)}>
                  Reject
                </Button>
              </div>
            ) : row.status === "approved" ? (
              <Button size="sm" variant="outline" loading={back.isPending} onClick={() => back.mutate(row.id)}>
                Mark returned
              </Button>
            ) : null
          }
        />
      )}
      <GlassDialog
        open={!!rejecting}
        onOpenChange={(v) => {
          if (!v) setRejecting(null);
        }}
        title="Reject pass"
      >
        <form
          className="campus-form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            if (rejecting) decide.mutate({ id: rejecting.id, approve: false });
          }}
        >
          <label className="campus-form">
            Reason
            <input className="campus-select" aria-label="Rejection reason" required maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <Button type="submit" loading={decide.isPending}>
            Reject
          </Button>
        </form>
      </GlassDialog>
    </section>
  );
}

function Visitors({ institutionId, members, invalidate }: { institutionId: number; members: InstitutionOverview["members"]; invalidate: () => Promise<void> }) {
  const list = useQuery({ queryKey: ["campus-hostel", institutionId, "visitors"], queryFn: () => hostelApi.visitors(institutionId) });
  const students = members.filter((m) => m.role === "student" && m.status === "active");
  const log = useMutation({
    mutationFn: (input: { member_id: number; visitor_name: string; relation: string; phone: string }) => hostelApi.logVisitor(institutionId, input),
    onSuccess: () => {
      toast.success("Visitor checked in");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The visitor couldn’t be logged.")),
  });
  const out = useMutation({
    mutationFn: (id: number) => hostelApi.visitorCheckout(institutionId, id),
    onSuccess: () => {
      toast.success("Visitor checked out");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Check-out failed.")),
  });
  return (
    <section className="campus-panel">
      <h2>Visitor register</h2>
      <form
        className="campus-form-grid mt-2"
        onSubmit={(e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          log.mutate({
            member_id: Number(form.get("member_id")),
            visitor_name: String(form.get("visitor_name") || "").trim(),
            relation: String(form.get("relation") || "").trim(),
            phone: String(form.get("phone") || "").trim(),
          });
          e.currentTarget.reset();
        }}
      >
        <label className="campus-form">
          Resident
          <select className="campus-select" name="member_id" required defaultValue="">
            <option value="">Choose…</option>
            {students.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <label className="campus-form">
          Visitor name
          <input className="campus-select" name="visitor_name" required maxLength={120} />
        </label>
        <label className="campus-form">
          Relation
          <input className="campus-select" name="relation" maxLength={60} />
        </label>
        <label className="campus-form">
          Phone
          <input className="campus-select" name="phone" maxLength={20} />
        </label>
        <Button type="submit" loading={log.isPending}>
          Check in visitor
        </Button>
      </form>
      {list.isLoading && <CampusOsLoading label="Loading visitors" />}
      {list.data && !list.data.length && <p className="campus-muted mt-4">No visitors logged yet.</p>}
      {!!list.data?.length && (
        <div className="campus-table-wrap">
          <table className="campus-table">
            <thead>
              <tr>
                <th>Visitor</th>
                <th>Visiting</th>
                <th>In</th>
                <th>Out</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.data.map((v) => (
                <tr key={v.id}>
                  <td>
                    {v.visitor_name}
                    <small>{[v.relation, v.phone].filter(Boolean).join(" · ")}</small>
                  </td>
                  <td>{v.student_name}</td>
                  <td>
                    {formatDate(v.checked_in_at)} {formatTime(v.checked_in_at)}
                  </td>
                  <td>{v.checked_out_at ? formatTime(v.checked_out_at) : "—"}</td>
                  <td>
                    {!v.checked_out_at && (
                      <Button size="sm" variant="outline" loading={out.isPending} onClick={() => out.mutate(v.id)}>
                        Check out
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ResidentHostel({ institutionId, studentUserId }: { institutionId: number; studentUserId?: number }) {
  const user = useAuthStore((s) => s.user);
  const parent = user?.role === "parent";
  const sid = parent ? studentUserId : undefined;
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["campus-hostel", institutionId, "me", sid], queryFn: () => hostelApi.me(institutionId, sid) });
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const request = useMutation({
    mutationFn: (input: { kind: "outpass" | "leave"; reason: string; leaves_at: string; returns_at: string }) => hostelApi.createPass(institutionId, input),
    onSuccess: () => {
      setOpen(false);
      setError("");
      toast.success("Pass requested");
      void queryClient.invalidateQueries({ queryKey: ["campus-hostel", institutionId] });
    },
    onError: (cause) => setError(errorMessage(cause, "The pass couldn’t be requested.")),
  });
  return (
    <>
      <BrandBanner compact title="Your room and your passes." description="See your allocation, request an out-pass, and track its approval." />
      <section className="campus-panel">
        {me.isLoading && <CampusOsLoading label="Loading hostel" />}
        {me.isError && <CampusOsError message="Hostel details couldn’t be loaded." retry={() => void me.refetch()} />}
        {me.data && !me.data.resident && <CampusOsEmpty title="Not a hostel resident" description="Room allocations are made by the campus office." />}
        {me.data?.resident && me.data.allocation && (
          <div className="campus-panel-heading">
            <div>
              <h2>
                {me.data.allocation.block_name} · Room {me.data.allocation.room_number}
              </h2>
              <p className="campus-muted">Checked in {formatDate(me.data.allocation.checked_in_on)}</p>
            </div>
            {!parent && <Button onClick={() => setOpen(true)}>Request out-pass</Button>}
          </div>
        )}
        {me.data && (
          <>
            <h3 className="mt-4">Passes</h3>
            {!me.data.passes.length ? <p className="campus-muted">No passes yet.</p> : <PassTable rows={me.data.passes} />}
          </>
        )}
      </section>
      <GlassDialog open={open} onOpenChange={setOpen} title="Request an out-pass">
        <form
          className="campus-form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            request.mutate({
              kind: String(form.get("kind") || "outpass") as "outpass" | "leave",
              reason: String(form.get("reason") || "").trim(),
              leaves_at: new Date(String(form.get("leaves_at"))).toISOString(),
              returns_at: new Date(String(form.get("returns_at"))).toISOString(),
            });
          }}
        >
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <label className="campus-form">
            Kind
            <select className="campus-select" name="kind" defaultValue="outpass">
              <option value="outpass">Out-pass (same day)</option>
              <option value="leave">Leave (overnight)</option>
            </select>
          </label>
          <label className="campus-form">
            Leaving
            <input className="campus-select" name="leaves_at" type="datetime-local" required />
          </label>
          <label className="campus-form">
            Returning
            <input className="campus-select" name="returns_at" type="datetime-local" required />
          </label>
          <label className="campus-form">
            Reason
            <input className="campus-select" name="reason" required minLength={3} maxLength={500} />
          </label>
          <Button type="submit" loading={request.isPending}>
            Send request
          </Button>
        </form>
      </GlassDialog>
    </>
  );
}
