import { demoApi } from "./demo-api";
import type { ChatJob, Session, Ticket, TicketDraft, TicketStatus } from "./types";

const baseUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
export const isDemo = !baseUrl || import.meta.env.VITE_DEMO_MODE === "true";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The request could not be completed.");
  return body;
}

async function completeChat(session: Session, job: ChatJob): Promise<ChatJob> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const current = await request<ChatJob>(`/sessions/${session.sessionId}/messages/${job.request_id}`, { headers: { Authorization: `Bearer ${session.sessionToken}` } });
    if (current.status !== "PENDING") return current;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("The response took too long. Please try again.");
}

export const api = {
  createSession: (): Promise<Session> => isDemo ? demoApi.createSession() : request("/sessions", { method: "POST" }),
  async sendMessage(session: Session, message: string): Promise<ChatJob> {
    if (isDemo) return demoApi.sendMessage(session, message);
    const job = await request<ChatJob>(`/sessions/${session.sessionId}/messages`, { method: "POST", headers: { Authorization: `Bearer ${session.sessionToken}`, "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ message }) });
    return completeChat(session, job);
  },
  createDraft: (session: Session, values: Omit<TicketDraft, "draft_id" | "expires_at">): Promise<TicketDraft> => isDemo ? demoApi.createDraft(session, values) : request(`/sessions/${session.sessionId}/ticket-drafts`, { method: "POST", headers: { Authorization: `Bearer ${session.sessionToken}` }, body: JSON.stringify({ description: values.description, stepsToReproduce: values.steps_to_reproduce, environment: values.environment }) }),
  confirmDraft: (session: Session, draft: TicketDraft): Promise<Ticket> => isDemo ? demoApi.confirmDraft(session, draft) : request(`/sessions/${session.sessionId}/ticket-drafts/${draft.draft_id}/confirm`, { method: "POST", headers: { Authorization: `Bearer ${session.sessionToken}`, "Idempotency-Key": crypto.randomUUID() } }),
  listTickets: (token: string, status?: TicketStatus): Promise<{ tickets: Ticket[] }> => isDemo ? demoApi.listTickets(status).then((tickets) => ({ tickets })) : request(`/operator/tickets${status ? `?status=${status}` : ""}`, { headers: { Authorization: `Bearer ${token}` } }),
  updateTicket: (token: string, id: string, status: TicketStatus): Promise<Ticket> => isDemo ? demoApi.updateTicket(id, status) : request(`/operator/tickets/${id}`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ status }) }),
};
