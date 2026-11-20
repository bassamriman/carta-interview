import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AccountsPage from "./AccountsPage";
import { mockFetch } from "@/test/mockFetch";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/users/3/accounts"]}>
      <Routes>
        <Route path="/users/:userId/accounts" element={<AccountsPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("AccountsPage", () => {
  it("renders account cards with balance, truncated notes and links", async () => {
    const f = mockFetch([
      {
        id: 9,
        name: "Checking",
        account_type: "checking",
        notes: "x".repeat(80),
        balance: "1234.5",
      },
      { id: 10, name: "Savings", account_type: "savings", notes: null, balance: "0" },
    ]);
    renderPage();
    await screen.findByText("Checking");
    expect(f).toHaveBeenCalledWith("/api/users/3/accounts");
    expect(screen.getByText("$1,234.50")).toBeInTheDocument();
    expect(screen.getByText("$0.00")).toBeInTheDocument();
    expect(screen.getByText("x".repeat(50))).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Checking/ })).toHaveAttribute(
      "href",
      "/users/3/accounts/9/transactions",
    );
    expect(screen.getByRole("link", { name: /back to users/i })).toHaveAttribute("href", "/");
  });

  it("shows an error on HTTP failure", async () => {
    mockFetch(null, false, 404);
    renderPage();
    expect(await screen.findByText("Error: HTTP 404")).toBeInTheDocument();
  });
});
