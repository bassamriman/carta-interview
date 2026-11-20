import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Named {
  id: number;
  name: string;
}

interface RecurringGroup {
  id: number;
  account_id: number;
  merchant: Named | null;
  category: Named | null;
  amount: string;
  type: string;
  interval: string;
  first_date: string;
  last_date: string;
  count: number;
}

interface GroupTransaction {
  id: number;
  date: string;
  amount: string;
  category: Named | null;
  merchant: Named | null;
  type: string;
  account: { id: number; name: string; account_type: string };
}

interface TransactionPage {
  items: GroupTransaction[];
  next_cursor: string | null;
  previous_cursor: string | null;
}

type Cursor = { direction: "after" | "before"; value: string } | null;

const PAGE_SIZE = 20;

const money = (amount: string) =>
  `$${parseFloat(amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function groupTransactionsUrl(groupId: number, cursor: Cursor) {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
  if (cursor) params.set(cursor.direction, cursor.value);
  return `/api/recurring-groups/${groupId}/transactions?${params}`;
}

function GroupTransactions({ group }: { group: RecurringGroup }) {
  // The cursor belongs to one group; the parent remounts this per group.
  const [cursor, setCursor] = useState<Cursor>(null);
  const [data, setData] = useState<{ url: string; page: TransactionPage } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const url = groupTransactionsUrl(group.id, cursor);

  useEffect(() => {
    let ignore = false;
    getJson<TransactionPage>(url)
      .then((page) => {
        if (!ignore) setData({ url, page });
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      });
    return () => {
      ignore = true;
    };
  }, [url]);

  if (error) return <p className="text-red-500">Error: {error}</p>;
  const page = data?.page;
  const loading = data?.url !== url;

  return (
    <div>
      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Type</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(page?.items ?? []).map((t) => (
              <TableRow key={t.id}>
                <TableCell>{t.date}</TableCell>
                <TableCell className="text-right">{money(t.amount)}</TableCell>
                <TableCell className="capitalize">{t.type}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-center gap-4 mt-4">
        <Button
          variant="outline"
          size="sm"
          disabled={loading || !page?.previous_cursor}
          onClick={() => page?.previous_cursor && setCursor({ direction: "before", value: page.previous_cursor })}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || !page?.next_cursor}
          onClick={() => page?.next_cursor && setCursor({ direction: "after", value: page.next_cursor })}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

export default function RecurringGroupsPage() {
  const { userId } = useParams<{ userId: string }>();
  const [groups, setGroups] = useState<RecurringGroup[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    getJson<RecurringGroup[]>(`/api/users/${userId}/recurring-groups`)
      .then((data) => {
        if (!ignore) setGroups(data);
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      });
    return () => {
      ignore = true;
    };
  }, [userId]);

  if (error) return <p className="p-8 text-red-500">Error: {error}</p>;

  const selected = groups?.find((g) => g.id === selectedId) ?? null;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <Link to={`/users/${userId}/accounts`} className="text-sm text-blue-600 hover:underline">
        &larr; Back to accounts
      </Link>
      <h1 className="text-2xl font-bold mt-4 mb-6">Recurring transactions</h1>
      {groups?.length === 0 && (
        <p className="text-gray-500">No recurring transactions found.</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-[22rem_1fr] gap-6">
        <ul className="space-y-2">
          {(groups ?? []).map((g) => (
            <li key={g.id}>
              <button
                type="button"
                aria-pressed={g.id === selectedId}
                onClick={() => setSelectedId(g.id)}
                className={`w-full rounded-md border bg-white p-3 text-left hover:shadow-md ${
                  g.id === selectedId ? "border-blue-600 ring-1 ring-blue-600" : ""
                }`}
              >
                <span className="block font-medium">{g.merchant?.name ?? "No merchant"}</span>
                <span className="block text-sm text-gray-500">
                  {g.category?.name ?? "No category"} · {money(g.amount)} · <span className="capitalize">{g.interval}</span>
                </span>
                <span className="block text-xs text-gray-400">
                  {g.count} transactions, {g.first_date} to {g.last_date}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <div>
          {selected ? (
            <GroupTransactions key={selected.id} group={selected} />
          ) : (
            groups !== null &&
            groups.length > 0 && <p className="text-gray-500">Select a group to see its transactions.</p>
          )}
        </div>
      </div>
    </div>
  );
}
