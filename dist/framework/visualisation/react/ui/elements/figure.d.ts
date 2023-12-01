/// <reference types="react" />
import { TableWithContext } from '../../../../types/elements';
import { VisualizationType, VisualizationData } from '../../../../types/visualizations';
import { ReactFactoryContext } from '../../factory';
declare type Props = VisualizationProps & ReactFactoryContext;
export interface VisualizationProps {
    table: TableWithContext;
    visualization: VisualizationType;
    locale: string;
    handleDelete: (rowIds: string[]) => void;
    handleUndo: () => void;
}
export declare const Figure: ({ table, visualization, locale, handleDelete, handleUndo }: Props) => JSX.Element;
export declare const RenderVisualization: import("react").MemoExoticComponent<({ visualizationData, fallbackMessage, loading }: {
    visualizationData: VisualizationData | undefined;
    fallbackMessage: string;
    loading?: boolean;
}) => JSX.Element | null>;
export {};
