import { Text } from './elements';
export interface VisualizationProps {
    title: Text;
    height?: number;
}
export declare type AggregationFunction = 'count' | 'mean' | 'sum' | 'count_pct' | 'pct';
export interface Axis {
    label?: string;
    column: string;
}
export interface AggregationGroup {
    label?: string;
    column: string;
    dateFormat?: DateFormat;
    range?: [number, number];
    levels?: string[];
}
export interface AggregationValue {
    label?: string;
    column: string;
    aggregate?: AggregationFunction;
    group_by?: string;
    secondAxis?: boolean;
    z?: string;
    zAggregate?: AggregationFunction;
    addZeroes?: boolean;
}
export interface ChartVisualization extends VisualizationProps {
    type: 'line' | 'bar' | 'area';
    group: AggregationGroup;
    values: AggregationValue[];
}
export interface TextVisualization extends VisualizationProps {
    type: 'wordcloud';
    textColumn: string;
    valueColumn?: string;
    valueAggregation?: 'sum' | 'mean';
    tokenize?: boolean;
    extract?: 'url_domain';
}
export interface ScoredTerm {
    text: string;
    value: number;
    importance: number;
    rowIds?: string[];
}
export declare type VisualizationType = ChartVisualization | TextVisualization;
export interface AxisSettings {
    label: string;
    secondAxis?: boolean;
    tickerFormat?: TickerFormat;
}
export declare type TickerFormat = 'percent' | 'default';
export declare type XType = 'string' | 'date';
export interface ChartVisualizationData {
    type: 'line' | 'bar' | 'area';
    data: Array<Record<string, any>>;
    xKey: AxisSettings;
    yKeys: Record<string, AxisSettings>;
}
export interface TextVisualizationData {
    type: 'wordcloud';
    topTerms: ScoredTerm[];
}
export declare type VisualizationData = ChartVisualizationData | TextVisualizationData;
export declare type DateFormat = 'auto' | 'year' | 'quarter' | 'month' | 'day' | 'hour' | 'month_cycle' | 'weekday_cycle' | 'hour_cycle';
