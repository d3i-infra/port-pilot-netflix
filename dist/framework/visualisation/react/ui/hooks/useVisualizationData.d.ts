import { TableWithContext } from '../../../../types/elements';
import { VisualizationType, VisualizationData } from '../../../../types/visualizations';
declare type Status = 'loading' | 'success' | 'error';
export default function useVisualizationData(table: TableWithContext, visualization: VisualizationType): [VisualizationData | undefined, Status];
export {};
