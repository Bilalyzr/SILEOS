import { api } from "./axios";

const root = (id: number) => `/institutions/${id}/hostel`;

export type RoomType = "single" | "double" | "triple" | "dormitory";
export type PassStatus = "pending" | "approved" | "rejected" | "returned";

export interface HostelRoom {
  id: number;
  block_id: number;
  number: string;
  floor: string;
  room_type: RoomType;
  capacity: number;
  occupied: number;
  active: boolean;
}

export interface HostelBlock {
  id: number;
  name: string;
  warden_member_id: number | null;
  warden_name: string | null;
  gender: "any" | "male" | "female";
  fee_amount: number | null;
  currency: string;
  fee_plan_id: number | null;
  active: boolean;
  capacity: number;
  occupied: number;
  rooms: HostelRoom[];
}

export interface RoomInput {
  number: string;
  floor: string;
  room_type: RoomType;
  capacity: number;
  active: boolean;
}

export interface BlockInput {
  name: string;
  warden_member_id: number | null;
  gender: "any" | "male" | "female";
  fee_amount: string | null;
  currency: string;
  rooms: RoomInput[];
}

export interface HostelAllocation {
  id: number;
  room_id: number;
  room_number: string | null;
  block_id: number | null;
  block_name: string | null;
  member_id: number;
  student_name: string | null;
  fee_assignment_id: number | null;
  status: "active" | "ended";
  checked_in_on: string;
  checked_out_on: string | null;
}

export interface HostelOccupancy {
  blocks: HostelBlock[];
  allocations: HostelAllocation[];
  capacity: number;
  occupied: number;
}

export interface HostelPass {
  id: number;
  member_id: number;
  student_name: string | null;
  kind: "outpass" | "leave";
  reason: string;
  leaves_at: string;
  returns_at: string;
  status: PassStatus;
  decided_by: number | null;
  decided_at: string | null;
  decision_note: string;
  returned_at: string | null;
  created_at: string | null;
}

export interface HostelVisitor {
  id: number;
  member_id: number;
  student_name: string | null;
  visitor_name: string;
  relation: string;
  phone: string;
  checked_in_at: string;
  checked_out_at: string | null;
}

export interface HostelMe {
  resident: boolean;
  allocation: HostelAllocation | null;
  passes: HostelPass[];
}

export const hostelApi = {
  blocks: async (id: number) => (await api.get<HostelBlock[]>(`${root(id)}/blocks`)).data,
  createBlock: async (id: number, data: BlockInput) => (await api.post<HostelBlock>(`${root(id)}/blocks`, data)).data,
  updateBlock: async (id: number, blockId: number, data: Partial<Pick<BlockInput, "name" | "warden_member_id" | "gender">> & { active?: boolean }) =>
    (await api.patch<HostelBlock>(`${root(id)}/blocks/${blockId}`, data)).data,
  saveRooms: async (id: number, blockId: number, rooms: RoomInput[]) =>
    (await api.put<HostelBlock>(`${root(id)}/blocks/${blockId}/rooms`, { rooms })).data,
  occupancy: async (id: number) => (await api.get<HostelOccupancy>(`${root(id)}/occupancy`)).data,
  occupancyCsv: async (id: number) => (await api.get<Blob>(`${root(id)}/occupancy.csv`, { responseType: "blob" })).data,
  allocate: async (id: number, roomId: number, memberId: number) =>
    (await api.post<HostelAllocation>(`${root(id)}/rooms/${roomId}/allocations`, { member_id: memberId })).data,
  checkout: async (id: number, allocationId: number) =>
    (await api.post<HostelAllocation>(`${root(id)}/allocations/${allocationId}/checkout`)).data,
  passes: async (id: number, params: { status?: PassStatus; student_user_id?: number } = {}) =>
    (await api.get<HostelPass[]>(`${root(id)}/passes`, { params })).data,
  createPass: async (id: number, data: { kind: "outpass" | "leave"; reason: string; leaves_at: string; returns_at: string }) =>
    (await api.post<HostelPass>(`${root(id)}/passes`, data)).data,
  approvePass: async (id: number, passId: number, note = "") =>
    (await api.post<HostelPass>(`${root(id)}/passes/${passId}/approve`, { note })).data,
  rejectPass: async (id: number, passId: number, note: string) =>
    (await api.post<HostelPass>(`${root(id)}/passes/${passId}/reject`, { note })).data,
  returnPass: async (id: number, passId: number) => (await api.post<HostelPass>(`${root(id)}/passes/${passId}/return`)).data,
  visitors: async (id: number, day?: string) => (await api.get<HostelVisitor[]>(`${root(id)}/visitors`, { params: { day } })).data,
  logVisitor: async (id: number, data: { member_id: number; visitor_name: string; relation: string; phone: string }) =>
    (await api.post<HostelVisitor>(`${root(id)}/visitors`, data)).data,
  visitorCheckout: async (id: number, visitorId: number) =>
    (await api.post<HostelVisitor>(`${root(id)}/visitors/${visitorId}/checkout`)).data,
  me: async (id: number, studentUserId?: number) =>
    (await api.get<HostelMe>(`${root(id)}/me`, { params: { student_user_id: studentUserId } })).data,
};
