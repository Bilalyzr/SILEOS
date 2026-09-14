import { api } from './axios'

export interface ImmersiveDevice {
  id: number
  asset_tag: string
  serial_number: string
  device_type: 'headset' | 'controller' | 'workstation' | 'router' | 'haptic' | 'other'
  vendor: string
  model: string
  status: 'inventory' | 'provisioning' | 'ready' | 'deployed' | 'maintenance' | 'quarantined' | 'retired'
  assigned_room: string
  last_seen_at: string | null
}

export interface DeploymentMilestone {
  id: number
  sequence: number
  title: string
  status: 'not_started' | 'in_progress' | 'blocked' | 'completed' | 'skipped'
  due_on: string | null
  completed_at: string | null
  evidence_urls: string[]
  notes: string
}

export interface SafetyInspection {
  id: number
  inspection_type: string
  status: 'scheduled' | 'passed' | 'failed' | 'conditional'
  scheduled_for: string
  completed_at: string | null
  findings: string
  corrective_actions: string
  next_due_on: string | null
}

export interface ServiceTicket {
  id: number
  reference: string
  device_id: number | null
  category: string
  priority: 'low' | 'normal' | 'high' | 'critical'
  status: 'open' | 'triaged' | 'in_progress' | 'waiting_customer' | 'resolved' | 'closed'
  subject: string
  description: string
  resolution: string
  sla_due_at: string | null
  assignee_id: number | null
  resolved_at: string | null
  created_at: string
}

export interface ImmersiveSiteSummary {
  id: number
  tenant_id: number
  institution_id: number | null
  contract_id: number | null
  code: string
  name: string
  status: 'planned' | 'installing' | 'active' | 'paused' | 'retired'
  address: Record<string, string>
  room_count: number
  headset_capacity: number
  network_readiness: 'unknown' | 'failed' | 'conditional' | 'ready'
  safety_status: 'pending' | 'failed' | 'conditional' | 'passed'
  go_live_on: string | null
  notes: string
  counts: { devices: number; deployed_devices: number; open_tickets: number }
}

export interface ImmersiveSite extends ImmersiveSiteSummary {
  devices: ImmersiveDevice[]
  milestones: DeploymentMilestone[]
  inspections: SafetyInspection[]
  tickets: ServiceTicket[]
}

export const meiporulOperationsAPI = {
  sites: async (tenantId?: number) =>
    (await api.get<ImmersiveSiteSummary[]>('/meiporul/operations/sites', { params: tenantId ? { tenant_id: tenantId } : undefined })).data,
  site: async (siteId: number) =>
    (await api.get<ImmersiveSite>(`/meiporul/operations/sites/${siteId}`)).data,
  createSite: async (body: Record<string, unknown>) =>
    (await api.post<ImmersiveSite>('/meiporul/operations/sites', body)).data,
  updateSite: async (siteId: number, body: Record<string, unknown>) =>
    (await api.patch<ImmersiveSite>(`/meiporul/operations/sites/${siteId}`, body)).data,
  addDevice: async (siteId: number, body: Record<string, unknown>) =>
    (await api.post<ImmersiveDevice>(`/meiporul/operations/sites/${siteId}/devices`, body)).data,
  updateDevice: async (deviceId: number, body: Record<string, unknown>) =>
    (await api.patch<ImmersiveDevice>(`/meiporul/operations/devices/${deviceId}`, body)).data,
  inspect: async (siteId: number, body: Record<string, unknown>) =>
    (await api.post<ImmersiveSite>(`/meiporul/operations/sites/${siteId}/inspections`, body)).data,
  updateMilestone: async (milestoneId: number, body: Record<string, unknown>) =>
    (await api.patch<ImmersiveSite>(`/meiporul/operations/milestones/${milestoneId}`, body)).data,
  createTicket: async (siteId: number, body: Record<string, unknown>) =>
    (await api.post<ImmersiveSite>(`/meiporul/operations/sites/${siteId}/tickets`, body)).data,
  updateTicket: async (ticketId: number, body: Record<string, unknown>) =>
    (await api.patch<ImmersiveSite>(`/meiporul/operations/tickets/${ticketId}`, body)).data,
}
