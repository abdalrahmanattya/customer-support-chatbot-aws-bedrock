import { beforeEach, describe, expect, it } from "vitest";
import { demoApi } from "./demo-api";

describe("demo API", () => {
  beforeEach(() => localStorage.clear());

  it("returns grounded policy answers with citations", async () => {
    const session = await demoApi.createSession();
    const response = await demoApi.sendMessage(session, "What is the return policy?");
    expect(response.response).toContain("30 days");
    expect(response.citations[0].title).toContain("Returns");
  });

  it("does not persist a ticket until the draft is confirmed", async () => {
    const session = await demoApi.createSession();
    const draft = await demoApi.createDraft(session, {
      description: "Checkout froze", steps_to_reproduce: "Clicked pay", environment: "Chrome",
    });
    expect((await demoApi.listTickets()).length).toBe(0);
    const ticket = await demoApi.confirmDraft(session, draft);
    expect(ticket.status).toBe("OPEN");
    expect((await demoApi.listTickets()).length).toBe(1);
  });
});
