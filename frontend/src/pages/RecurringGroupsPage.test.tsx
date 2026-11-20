import { vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import RecurringGroupsPage from "./RecurringGroupsPage";

const group = (id: number, merchant: string | null, interval = "monthly") => ({
  id,
  account_id: 9,
  merchant: merchant ? { id: id, name: merchant } : null,
  category: { id: 1, name: "Bills" },
  amount: "15.99",
  type: "debit",
  interval,
  first_date: "2024-01-05",
  last_date: "2024-06-05",
  count: 6,
});

const tx = (id: number, date: string) => ({
  id,
  date,
  amount: "15.99",
  category: { id: 1, name: "Bills" },
  merchant: { id: 1, name: "Netflix" },
  type: "debit",
  account: { id: 9, name: "Checking", account_type: "checking" },
});

const page = (items: unknown[], next: string | null = null, prev: string | null = null) => ({
  items,
  next_cursor: next,
  previous_cursor: prev,
});

const ok = (body: unknown) => ({ ok: true, status: 200, json: () => Promise.resolve(body) });

const routes = (table: Record<string, unknown[]>) => {
  const f = vi.fn((url: string) => {
    const queue = table[url];
    if (!queue?.length) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    return Promise.resolve(ok(queue.length > 1 ? queue.shift() : queue[0]));
  });
  vi.stubGlobal("fetch", f);
  return f;
};

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/users/3/recurring"]}>
      <Routes>
        <Route path="/users/:userId/recurring" element={<RecurringGroupsPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("RecurringGroupsPage", () => {
  it("lists groups and loads a group's transactions when it is selected", async () => {
    const f = routes({
      "/api/users/3/recurring-groups": [[group(1, "Netflix"), group(2, null, "weekly")]],
      "/api/recurring-groups/2/transactions?limit=20": [page([tx(7, "2024-02-02")])],
    });
    renderPage();
    await screen.findByRole("button", { name: /Netflix/ });
    expect(screen.getByText(/select a group/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /No merchant/ }));
    await screen.findByText("2024-02-02");
    expect(f).toHaveBeenCalledWith("/api/recurring-groups/2/transactions?limit=20");
    expect(screen.getByRole("button", { name: /No merchant/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("pages a selected group's transactions with cursors", async () => {
    const f = routes({
      "/api/users/3/recurring-groups": [[group(1, "Netflix")]],
      "/api/recurring-groups/1/transactions?limit=20": [page([tx(1, "2024-01-05")], "n1")],
      "/api/recurring-groups/1/transactions?limit=20&after=n1": [page([tx(2, "2024-02-05")], null, "p2")],
    });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Netflix/ }));
    await screen.findByText("2024-01-05");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("2024-02-05");
    expect(f).toHaveBeenCalledWith("/api/recurring-groups/1/transactions?limit=20&after=n1");
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("shows an empty state when the user has no recurring groups", async () => {
    routes({ "/api/users/3/recurring-groups": [[]] });
    renderPage();
    expect(await screen.findByText(/no recurring transactions/i)).toBeInTheDocument();
  });

  it("shows an error on HTTP failure", async () => {
    routes({});
    renderPage();
    expect(await screen.findByText("Error: HTTP 404")).toBeInTheDocument();
  });
});
