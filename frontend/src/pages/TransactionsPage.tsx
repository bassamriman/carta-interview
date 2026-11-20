import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Category {
  id: number;
  name: string;
}

interface Merchant {
  id: number;
  name: string;
}

interface TransactionAccount {
  id: number;
  name: string;
  account_type: string;
}

interface Transaction {
  id: number;
  date: string;
  amount: string;
  category: Category | null;
  merchant: Merchant | null;
  type: string;
  account: TransactionAccount;
}

const PAGE_SIZE = 20;

interface TransactionPage {
  items: Transaction[];
  next_cursor: string | null;
  previous_cursor: string | null;
}

type Cursor = { direction: "after" | "before"; value: string } | null;

function pageUrl(accountId: string | undefined, search: string, cursor: Cursor) {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
  if (search) params.set("search", search);
  if (cursor) params.set(cursor.direction, cursor.value);
  return `/api/accounts/${accountId}/transactions?${params}`;
}

export default function TransactionsPage() {
  const { userId, accountId } = useParams<{
    userId: string;
    accountId: string;
  }>();
  const [data, setData] = useState<TransactionPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [cursorState, setCursorState] = useState<{ key: string; cursor: Cursor }>({
    key: "",
    cursor: null,
  });
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // A cursor is only valid for the account and search it came from, so it is
  // dropped (first page) whenever either changes.
  const walkKey = `${accountId ?? ""}::${debouncedSearch}`;
  const cursor = cursorState.key === walkKey ? cursorState.cursor : null;
  const url = pageUrl(accountId, debouncedSearch, cursor);
  const loading = loadedUrl !== url;

  useEffect(() => {
    let ignore = false;
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((page: TransactionPage) => {
        if (ignore) return;
        setData(page);
        setLoadedUrl(url);
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      });
    return () => {
      ignore = true;
    };
  }, [url]);

  if (error) return <p className="p-8 text-red-500">Error: {error}</p>;

  const pageTransactions = data?.items ?? [];
  const go = (direction: "after" | "before", value: string | null) => {
    if (value) setCursorState({ key: walkKey, cursor: { direction, value } });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <Link
        to={`/users/${userId}/accounts`}
        className="text-sm text-blue-600 hover:underline"
      >
        &larr; Back to accounts
      </Link>
      <h1 className="text-2xl font-bold mt-4 mb-4">Transactions</h1>
      <Input
        type="search"
        placeholder="Search by merchant or category..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 max-w-sm"
      />

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Account</TableHead>
              <TableHead>Merchant</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Type</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: PAGE_SIZE }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-4 w-16 ml-auto" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                  </TableRow>
                ))
              : pageTransactions.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>{t.date}</TableCell>
                    <TableCell>{t.account.name}</TableCell>
                    <TableCell>{t.merchant?.name ?? "—"}</TableCell>
                    <TableCell>{t.category?.name ?? "—"}</TableCell>
                    <TableCell className="text-right">
                      ${parseFloat(t.amount).toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                      })}
                    </TableCell>
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
          disabled={loading || !data?.previous_cursor}
          onClick={() => go("before", data?.previous_cursor ?? null)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || !data?.next_cursor}
          onClick={() => go("after", data?.next_cursor ?? null)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
