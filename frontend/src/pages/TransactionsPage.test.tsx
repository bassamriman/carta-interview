import { render, screen, waitFor } from "@testing-library/react";
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
const page = (items: unknown[]) => ({ items, next_cursor: null, previous_cursor: null });

describe("TransactionsPage", () => {
  it("renders rows, total and back link", async () => {
    const f = mockFetch(page([tx(1), tx(2, null)]));
    renderPage();
    await screen.findByText("Shop");
    expect(f).toHaveBeenCalledWith("/api/accounts/9/transactions?limit=200");
    expect(screen.getByText("2 total transactions")).toBeInTheDocument();
    expect(screen.getAllByText("$12.50")).toHaveLength(2);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /back to accounts/i })).toHaveAttribute(
      "href",
      "/users/3/accounts",
    );
    expect(screen.queryByText(/Page \d+ of/)).not.toBeInTheDocument();
  });

  it("paginates 20 per page", async () => {
    mockFetch(page(Array.from({ length: 45 }, (_, i) => tx(i + 1))));
    renderPage();
    await screen.findByText("Page 1 of 3");
    expect(screen.getAllByRole("row")).toHaveLength(21);
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getAllByRole("row")).toHaveLength(6);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("debounces search and refetches with the encoded query", async () => {
    const f = mockFetch(page([tx(1)]));
    renderPage();
    await screen.findByText("Shop");
    await userEvent.type(screen.getByPlaceholderText(/search/i), "a&b");
    await waitFor(() =>
      expect(f).toHaveBeenCalledWith("/api/accounts/9/transactions?limit=200&search=a%26b"),
    );
    expect(f.mock.calls.filter(([u]) => String(u).includes("search="))).toHaveLength(1);
  });

  it("shows an error on HTTP failure", async () => {
    mockFetch(null, false, 500);
    renderPage();
    expect(await screen.findByText("Error: HTTP 500")).toBeInTheDocument();
  });
});
