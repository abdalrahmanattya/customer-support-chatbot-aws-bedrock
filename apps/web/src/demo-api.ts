import type { ChatJob, Citation, Session, Ticket, TicketDraft, TicketStatus } from "./types";

const TICKETS_KEY = "northstar-demo-tickets";
const wait = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms));
const uuid = () => crypto.randomUUID();

function tickets(): Ticket[] { return JSON.parse(localStorage.getItem(TICKETS_KEY) || "[]"); }
function saveTickets(items: Ticket[]) { localStorage.setItem(TICKETS_KEY, JSON.stringify(items)); }

export const demoApi = {
  async createSession(): Promise<Session> {
    await wait(80);
    return { sessionId: uuid(), sessionToken: uuid(), expiresAt: new Date(Date.now() + 7_200_000).toISOString() };
  },
  async sendMessage(_session: Session, message: string): Promise<ChatJob> {
    await wait();
    const lower = message.toLowerCase();
    let response = "I couldn't find that in the store policies. You can create a support ticket and an operator can review it.";
    let citations: Citation[] = [];
    if (lower.includes("return") || lower.includes("refund")) {
      response = "Most unused items can be returned within 30 days of delivery in their original packaging. Refunds are sent to the original payment method after inspection.";
      citations = [{ id: "returns", title: "Returns & refunds policy", score: 0.94 }];
    } else if (lower.includes("ship") || lower.includes("delivery") || lower.includes("track")) {
      response = "Orders are processed within 1–2 business days. Once dispatched, a tracking link appears in My Orders and is sent by email.";
      citations = [{ id: "shipping", title: "Shipping & delivery policy", score: 0.92 }];
    } else if (lower.includes("broken") || lower.includes("error") || lower.includes("checkout")) {
      response = "I can help document this issue. Use “Create a ticket” to review the description, reproduction steps, and environment before anything is submitted.";
    }
    return { request_id: uuid(), status: "COMPLETE", response, citations };
  },
  async createDraft(_session: Session, values: Omit<TicketDraft, "draft_id" | "expires_at">): Promise<TicketDraft> {
    await wait(120);
    return { ...values, draft_id: uuid(), expires_at: new Date(Date.now() + 1_800_000).toISOString() };
  },
  async confirmDraft(_session: Session, draft: TicketDraft): Promise<Ticket> {
    await wait(150);
    const now = new Date().toISOString();
    const ticket: Ticket = { ticket_id: `SUP-${uuid().slice(0, 8).toUpperCase()}`, description: draft.description, steps_to_reproduce: draft.steps_to_reproduce, environment: draft.environment, status: "OPEN", created_at: now, updated_at: now };
    saveTickets([ticket, ...tickets()]);
    return ticket;
  },
  async listTickets(status?: TicketStatus): Promise<Ticket[]> {
    await wait(100);
    return status ? tickets().filter((ticket) => ticket.status === status) : tickets();
  },
  async updateTicket(id: string, status: TicketStatus): Promise<Ticket> {
    await wait(100);
    const items = tickets();
    const index = items.findIndex((ticket) => ticket.ticket_id === id);
    if (index < 0) throw new Error("Ticket not found");
    items[index] = { ...items[index], status, updated_at: new Date().toISOString() };
    saveTickets(items);
    return items[index];
  },
};
