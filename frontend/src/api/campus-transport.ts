import { api } from "./axios";

const root = (id: number) => `/institutions/${id}/transport`;

export interface TransportStop {
  id: number;
  sequence: number;
  name: string;
  pickup_time: string;
  drop_time: string;
  landmark: string;
}

export interface TransportRoute {
  id: number;
  name: string;
  vehicle_number: string;
  driver_name: string;
  driver_phone: string;
  capacity: number;
  occupied: number;
  fee_amount: number | null;
  currency: string;
  fee_plan_id: number | null;
  active: boolean;
  stops: TransportStop[];
}

export interface StopInput {
  name: string;
  pickup_time: string;
  drop_time: string;
  landmark: string;
}

export interface RouteInput {
  name: string;
  vehicle_number: string;
  driver_name: string;
  driver_phone: string;
  capacity: number;
  fee_amount: string | null;
  currency: string;
  stops: StopInput[];
}

export interface TransportAssignment {
  id: number;
  route_id: number;
  stop_id: number;
  stop_name: string | null;
  member_id: number;
  student_name: string | null;
  fee_assignment_id: number | null;
  status: "active" | "ended";
  started_on: string;
  ended_on: string | null;
  boarded: boolean | null;
  dropped: boolean | null;
}

export interface TransportRoster {
  route: TransportRoute;
  day: string;
  students: TransportAssignment[];
}

export interface TransportMe {
  assigned: boolean;
  route: { id: number; name: string; vehicle_number: string; driver_name: string; driver_phone: string } | null;
  stop: TransportStop | null;
  today: { day: string; boarded: boolean; dropped: boolean } | null;
}

export const transportApi = {
  routes: async (id: number) => (await api.get<TransportRoute[]>(`${root(id)}/routes`)).data,
  createRoute: async (id: number, data: RouteInput) => (await api.post<TransportRoute>(`${root(id)}/routes`, data)).data,
  updateRoute: async (id: number, routeId: number, data: Partial<RouteInput> & { active?: boolean }) =>
    (await api.patch<TransportRoute>(`${root(id)}/routes/${routeId}`, data)).data,
  roster: async (id: number, routeId: number, day?: string) =>
    (await api.get<TransportRoster>(`${root(id)}/routes/${routeId}/roster`, { params: { day } })).data,
  rosterCsv: async (id: number, routeId: number) =>
    (await api.get<Blob>(`${root(id)}/routes/${routeId}/roster.csv`, { responseType: "blob" })).data,
  boarding: async (id: number, routeId: number, day: string, entries: { member_id: number; boarded: boolean; dropped: boolean }[]) =>
    (await api.put<TransportRoster>(`${root(id)}/routes/${routeId}/boarding`, { day, entries })).data,
  assign: async (id: number, routeId: number, memberId: number, stopId: number) =>
    (await api.post<TransportAssignment>(`${root(id)}/routes/${routeId}/assignments`, { member_id: memberId, stop_id: stopId })).data,
  end: async (id: number, assignmentId: number) =>
    (await api.post<TransportAssignment>(`${root(id)}/assignments/${assignmentId}/end`)).data,
  me: async (id: number, studentUserId?: number) =>
    (await api.get<TransportMe>(`${root(id)}/me`, { params: { student_user_id: studentUserId } })).data,
};
