import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
});

test("customer receives a cited policy answer", async ({ page }) => {
  await page.getByRole("button", { name: "What is your return policy?" }).click();
  await expect(page.getByText(/30 days of delivery/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Returns & refunds policy/ })).toBeVisible();
});

test("operator desk requires sign-in", async ({ page }) => {
  await page.goto("/operator");
  await expect(page.getByRole("heading", { name: "Operator desk" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign in with Cognito/ })).toBeVisible();
});

test("customer reviews a ticket before submitting it", async ({ page }) => {
  await page.getByRole("button", { name: /Create a ticket/ }).click();
  await page.getByLabel("What happened?").fill("The checkout screen froze");
  await page.getByLabel("Steps to reproduce").fill("Open checkout and select Pay");
  await page.getByLabel("Device and browser").fill("Chrome on macOS");
  await page.getByRole("button", { name: /Review ticket/ }).click();
  await expect(page.getByText("Nothing is submitted until you confirm.")).toBeVisible();
  await page.getByRole("button", { name: /Confirm & submit/ }).click();
  await expect(page.getByText("Ticket submitted")).toBeVisible();
});

test("operator progresses a customer ticket to resolved", async ({ page }) => {
  await page.getByRole("button", { name: /Create a ticket/ }).click();
  await page.getByLabel("What happened?").fill("The checkout screen froze");
  await page.getByLabel("Steps to reproduce").fill("Open checkout and select Pay");
  await page.getByLabel("Device and browser").fill("Chrome on macOS");
  await page.getByRole("button", { name: /Review ticket/ }).click();
  await page.getByRole("button", { name: /Confirm & submit/ }).click();
  await expect(page.getByText("Ticket submitted")).toBeVisible();
  await page.goto("/operator");
  await page.getByRole("button", { name: /Sign in with Cognito/ }).click();
  await expect(page.getByText("The checkout screen froze")).toBeVisible();
  await page.getByText("The checkout screen froze").click();
  await page.getByRole("button", { name: "Start progress" }).click();
  await expect(page.locator(".ticket-drawer .status")).toHaveText("IN PROGRESS");
  await page.getByRole("button", { name: "Mark resolved" }).click();
  await expect(page.locator(".ticket-drawer .status")).toHaveText("RESOLVED");
});

test("mobile layout keeps the chat usable", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile");
  await expect(page.getByRole("region", { name: "Support chat" })).toBeVisible();
  await expect(page.getByPlaceholder(/Ask about returns/)).toBeVisible();
});
