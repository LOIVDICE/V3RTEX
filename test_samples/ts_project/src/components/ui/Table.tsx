import React from "react";
import type { PaginatedResponse } from "../../types/api";
import { formatNumber } from "../../utils/formatters";

interface Column<T> {
  key: keyof T;
  header: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface TableProps<T> {
  data: PaginatedResponse<T> | null;
  columns: Column<T>[];
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

export function Table<T extends { id: number }>({ data, columns, onPageChange, isLoading }: TableProps<T>) {
  if (isLoading) return <div className="loading">Loading…</div>;
  if (!data) return null;

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={String(c.key)}>{c.header}</th>)}</tr>
        </thead>
        <tbody>
          {data.items.map((row) => (
            <tr key={row.id}>
              {columns.map((c) => (
                <td key={String(c.key)}>
                  {c.render ? c.render(row[c.key], row) : String(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination">
        <span>{formatNumber(data.total)} total</span>
        <button disabled={!data.hasPrev} onClick={() => onPageChange(data.page - 1)}>Prev</button>
        <span>{data.page} / {data.totalPages}</span>
        <button disabled={!data.hasNext} onClick={() => onPageChange(data.page + 1)}>Next</button>
      </div>
    </div>
  );
}

export default Table;
