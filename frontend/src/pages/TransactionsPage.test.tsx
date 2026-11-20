import { vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import TransactionsPage from "./TransactionsPage";
import { mockFetch } from "@/test/mockFetch";

const tx = (id: number, merchant: string | null = "Shop") => ({
  id,
  date: "2024-01-01",
  amount: "12.5",
  category: id % 2 ? { id: 1, name: "Food" } : null,
  merchant: merchant ? { id: 1, name: merchant } : null,
  type: "debit",
  account: { id: 1, name: "Checking", account_type: "checking" },
});

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/users/3/accounts/9/transactions"]}>
      <Routes>
        <Route
          path="/users/:userId/accounts/:accountId/transactions"
          element={<TransactionsPage />}
        />
      </Routes>
    </MemoryRouter>,
  );

// The API returns a cursor page, not a bare list.
const page = (items: unknown[], next: string | null = null, prev: string | null = null) => ({
  items,
  next_cursor: next,
  previous_cursor: prev,
});

const respond = (...bodies: unknown[]) => {
  const fn = vi.fn();
  for (const body of bodies)
    fn.mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(body) });
  vi.stubGlobal("fetch", fn);
  return fn;
};

describe("TransactionsPage", () => {
  it("renders rows and the back link from one page request", async () => {
    const f = mockFetch(page([tx(1), tx(2, null)]));
    renderPage();
    await screen.findByText("Shop");
    expect(f).toHaveBeenCalledTimes(1);
    expect(f).toHaveBeenCalledWith("/api/accounts/9/transactions?limit=20");
    expect(screen.getAllByText("$12.50")).toHaveLength(2);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /back to accounts/i })).toHaveAttribute(
      "href",
      "/users/3/accounts",
    );
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("walks next and previous with the server cursors", async () => {
    const f = respond(
      page([tx(1)], "n1"),
      page([tx(2, "Second")], null, "p2"),
      page([tx(1)], "n1"),
    );
    renderPage();
    await screen.findByText("Shop");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Second");
    expect(f).toHaveBeenLastCalledWith("/api/accounts/9/transactions?limit=20&after=n1");
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    await screen.findByText("Shop");
    expect(f).toHaveBeenLastCalledWith("/api/accounts/9/transactions?limit=20&before=p2");
  });

  it("debounces search, sends it to the API and restarts from the first page", async () => {
    const f = respond(page([tx(1)], "n1"), page([tx(2, "Second")], "n1"), page([tx(3, "Hit")]));
    renderPage();
    await screen.findByText("Shop");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Second");
    await userEvent.type(screen.getByPlaceholderText(/search/i), "a&b");
    await screen.findByText("Hit");
    expect(f).toHaveBeenLastCalledWith("/api/accounts/9/transactions?limit=20&search=a%26b");
    expect(f).toHaveBeenCalledTimes(3);
  });

  it("shows an error on HTTP failure", async () => {
    mockFetch(null, false, 500);
    renderPage();
    expect(await screen.findByText("Error: HTTP 500")).toBeInTheDocument();
  });
});
