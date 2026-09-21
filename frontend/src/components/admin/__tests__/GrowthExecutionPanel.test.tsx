import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GrowthExecutionPanel } from '../GrowthExecutionPanel';
import { growthAPI } from '@/api/growth';
vi.mock('@/api/growth', () => ({ growthAPI: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
vi.mock('@/api/planner', () => ({ plannerError: () => 'Request failed' }));
describe('Growth execution', () => {
  beforeEach(() => { vi.resetAllMocks(); vi.mocked(growthAPI.get).mockResolvedValue({ unified_cash: [{ currency: 'INR', captured: 1200, refunded: 200, net_cash: 1000 }], recommendations: [{ id: 1, tenant_id: 2, status: 'approved' }], analytics: { campaigns: [{ source: 'direct', campaign: '', net_revenue: 500, spend: 0, new_customers: 0, cac: null }] } }); });
  it('separates cash from profit and unknown acquisition cost', async () => {
    render(<GrowthExecutionPanel />);
    expect(await screen.findByText(/1,000 net cash/)).toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument();
    expect(screen.getByText(/Cash is not profit/)).toBeInTheDocument();
  });
  it('reports actual notification count after explicit publishing', async () => {
    vi.mocked(growthAPI.post).mockResolvedValue({ notified: 0 });
    render(<GrowthExecutionPanel />);
    await screen.findByText(/#1 · Workspace 2/);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Publish reviewed offer' }));
    await waitFor(() => expect(growthAPI.post).toHaveBeenCalledWith('/recommendations/1/publish'));
    expect(await screen.findByRole('status')).toHaveTextContent('0 opted-in member(s) notified');
  });
  it('does not report a failed publish as delivered', async () => {
    vi.mocked(growthAPI.post).mockRejectedValue(new Error('provider failed'));
    render(<GrowthExecutionPanel />);
    await screen.findByText(/#1 · Workspace 2/);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Publish reviewed offer' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
  it('links an imported lead using the current version', async () => {
    vi.mocked(growthAPI.get).mockResolvedValue({ unified_cash: [], recommendations: [], analytics: { campaigns: [] }, leads: [{ id: 4, name: 'Prospect', company: 'School', version: 2 }] });
    vi.mocked(growthAPI.put).mockResolvedValue({});
    render(<GrowthExecutionPanel />);
    await screen.findByText('#4 · School');
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Customer workspace ID' }), { target: { value: '9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Link workspace' }));
    await waitFor(() => expect(growthAPI.put).toHaveBeenCalledWith('/leads/4/workspace', { tenant_id: 9, version: 2 }));
  });
});
