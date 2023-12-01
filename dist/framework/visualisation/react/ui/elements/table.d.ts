/// <reference types="react" />
import { TableWithContext } from '../../../../types/elements';
export interface Props {
    table: TableWithContext;
    show: boolean;
    locale: string;
    search: string;
    unfilteredRows: number;
    handleDelete?: (rowIds: string[]) => void;
    handleUndo?: () => void;
    pageSize?: number;
}
export declare const Table: ({ table, show, locale, search, unfilteredRows, handleDelete, handleUndo, pageSize }: Props) => JSX.Element;
