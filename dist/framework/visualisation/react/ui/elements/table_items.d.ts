/// <reference types="react" />
import { TableWithContext } from '../../../../types/elements';
interface Props {
    table: TableWithContext;
    searchedTable: TableWithContext;
    handleUndo: () => void;
    locale: string;
}
export declare const TableItems: ({ table, searchedTable, handleUndo, locale }: Props) => JSX.Element;
export {};
