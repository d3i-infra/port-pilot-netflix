import { PropsUITable, TableContext } from '../../../../../types/elements';
import { DateFormat } from '../../../../../types/visualizations';
export declare function formatDate(dateString: string[], format: DateFormat, minValues?: number): [string[], Record<string, number> | null];
export declare function tokenize(text: string): string[];
export declare function getTableColumn(table: PropsUITable & TableContext, column: string): string[];
export declare function rescaleToRange(value: number, min: number, max: number, newMin: number, newMax: number): number;
export declare function extractUrlDomain(x: string): string;
