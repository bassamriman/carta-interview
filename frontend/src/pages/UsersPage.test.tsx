import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import UsersPage from "./UsersPage";
import { mockFetch } from "@/test/mockFetch";

function Where() {
  return <p>at {useLocation().pathname}</p>;
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<UsersPage />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );

describe("UsersPage", () => {
  it("lists users sorted by username with formatted counts", async () => {
    const f = mockFetch([
      { id: 2, username: "zed", email: "z@x.io", transaction_count: 1234 },
      { id: 1, username: "amy", email: "a@x.io", transaction_count: 5 },
    ]);
    renderPage();
    await screen.findByText("amy");
    expect(f).toHaveBeenCalledWith("/api/users");
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("amy");
    expect(rows[1]).toHaveTextContent("zed");
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("navigates to the user's accounts on row click", async () => {
    mockFetch([{ id: 7, username: "amy", email: "a@x.io", transaction_count: 1 }]);
    renderPage();
    await userEvent.click(await screen.findByText("amy"));
    expect(await screen.findByText("at /users/7/accounts")).toBeInTheDocument();
  });

  it("shows an error on HTTP failure", async () => {
    mockFetch(null, false, 500);
    renderPage();
    expect(await screen.findByText("Error: HTTP 500")).toBeInTheDocument();
  });
});
