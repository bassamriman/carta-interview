import { expect, test } from "@playwright/test";

// bob.louis (user 2) has one small account (id 3, ~250 transactions).
// Never open account 1: it has ~1M rows and its transactions call never returns.
const USER = "bob.louis";

test("users page lists users with transaction counts", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Select a User" })).toBeVisible();
  await expect(page.getByRole("row", { name: new RegExp(USER) })).toBeVisible();
});

test("user -> accounts -> transactions navigation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("cell", { name: USER, exact: true }).click();
  await expect(page).toHaveURL(/\/users\/2\/accounts$/);
  await expect(page.getByRole("heading", { name: "Accounts" })).toBeVisible();

  await page.getByRole("link", { name: /Checking/ }).click();
  await expect(page).toHaveURL(/\/users\/2\/accounts\/3\/transactions$/);
  await expect(page.locator("tbody tr")).toHaveCount(20);
});

test("transactions pagination moves between pages", async ({ page }) => {
  await page.goto("/users/2/accounts/3/transactions");
  const firstRow = page.locator("tbody tr").first();
  await expect(firstRow).toBeVisible();
  const first = await firstRow.innerText();
  await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("button", { name: "Previous" })).toBeEnabled();
  await expect(firstRow).not.toHaveText(first);
  await page.getByRole("button", { name: "Previous" }).click();
  await expect(firstRow).toHaveText(first);
  await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
});

test("transactions search filters and clears", async ({ page }) => {
  await page.goto("/users/2/accounts/3/transactions");
  await expect(page.locator("tbody tr")).toHaveCount(20);
  await page.getByPlaceholder(/Search by merchant/).fill("Summit Home Loans");
  await expect(page.locator("tbody tr").first()).toContainText("Summit Home Loans");
  await expect(page.locator("tbody tr").last()).toContainText("Summit Home Loans");
  await page.getByPlaceholder(/Search by merchant/).fill("");
  await expect(page.locator("tbody tr")).toHaveCount(20);
});

test("back links return to previous pages", async ({ page }) => {
  await page.goto("/users/2/accounts/3/transactions");
  await page.getByRole("link", { name: /Back to accounts/ }).click();
  await expect(page).toHaveURL(/\/users\/2\/accounts$/);
  await page.getByRole("link", { name: /Back to users/ }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("accounts page links to recurring transactions", async ({ page }) => {
  await page.goto("/users/2/accounts");
  await page.getByRole("link", { name: /Recurring transactions/ }).click();
  await expect(page).toHaveURL(/\/users\/2\/recurring$/);
  await expect(page.getByRole("heading", { name: "Recurring transactions" })).toBeVisible();
});
