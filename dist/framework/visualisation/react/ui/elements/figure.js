import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import TextBundle from '../../../../text_bundle';
import { Translator } from '../../../../translator';
import { memo, useMemo, useState } from 'react';
import useVisualizationData from '../hooks/useVisualizationData';
import { Title6 } from './text';
import Lottie from 'lottie-react';
import spinnerDark from '../../../../../assets/lottie/spinner-dark.json';
import RechartsGraph from './figures/recharts_graph';
import VisxWordcloud from './figures/visx_wordcloud';
import { zoomInIcon, zoomOutIcon } from './zoom_icons';
const doubleTypes = ['wordcloud'];
export const Figure = ({ table, visualization, locale, handleDelete, handleUndo }) => {
    var _a;
    const [visualizationData, status] = useVisualizationData(table, visualization);
    // const [longLoading, setLongLoading] = useState<boolean>(false)
    const [showStatus, setShowStatus] = useState('visible');
    const canDouble = doubleTypes.includes(visualization.type);
    const [resizeLoading, setResizeLoading] = useState(false);
    // useEffect(() => {
    //   if (status !== 'loading') {
    //     setLongLoading(false)
    //     return
    //   }
    //   const timer = setTimeout(() => {
    //     setLongLoading(true)
    //   }, 1000)
    //   return () => clearTimeout(timer)
    // }, [status])
    function toggleDouble() {
        setResizeLoading(true);
        if (showStatus === 'visible') {
            setShowStatus('double');
        }
        else {
            setShowStatus('visible');
        }
        setTimeout(() => {
            setResizeLoading(false);
        }, 150);
    }
    const { title } = useMemo(() => {
        const title = Translator.translate(visualization.title, locale);
        return { title };
    }, [visualization]);
    const { errorMsg, noDataMsg } = useMemo(() => prepareCopy(locale), [locale]);
    if (visualizationData == null && status === 'loading') {
        return (_jsxs("div", Object.assign({ className: 'flex justify-center items-center gap-6' }, { children: [_jsx("div", Object.assign({ className: 'w-10 h-10' }, { children: _jsx(Lottie, { animationData: spinnerDark, loop: true }) })), _jsx("span", Object.assign({ className: 'text-grey1' }, { children: title }))] })));
    }
    if (status === 'error') {
        return _jsx("div", Object.assign({ className: 'flex justify-center items-center text-error' }, { children: errorMsg }));
    }
    let height = (_a = visualization.height) !== null && _a !== void 0 ? _a : 250;
    if (showStatus === 'double')
        height = height * 2;
    return (_jsxs("div", Object.assign({ className: ' max-w overflow-hidden  bg-grey6 rounded-md border-[0.2rem] border-grey4' }, { children: [_jsxs("div", Object.assign({ className: 'flex justify-between' }, { children: [_jsx(Title6, { text: title, margin: 'p-3' }), _jsx("button", Object.assign({ onClick: toggleDouble, className: showStatus !== 'hidden' && canDouble ? 'text-primary px-3' : 'hidden' }, { children: showStatus === 'double' ? zoomOutIcon : zoomInIcon }))] })), _jsx("div", Object.assign({ className: 'w-full overflow-auto' }, { children: _jsx("div", Object.assign({ className: 'flex flex-col ' }, { children: _jsx("div", Object.assign({ 
                        // ref={ref}
                        className: 'grid relative z-50 w-full pr-1  min-w-[500px]', style: { gridTemplateRows: String(height) + 'px' } }, { children: _jsx(RenderVisualization, { visualizationData: visualizationData, fallbackMessage: noDataMsg, loading: resizeLoading }) })) })) }), table.id)] })));
};
export const RenderVisualization = memo(({ visualizationData, fallbackMessage, loading }) => {
    if (visualizationData == null)
        return null;
    const fallback = (_jsx("div", Object.assign({ className: 'm-auto font-bodybold text-4xl text-grey2 ' }, { children: fallbackMessage })));
    if (loading !== null && loading !== void 0 ? loading : false)
        return null;
    if (['line', 'bar', 'area'].includes(visualizationData.type)) {
        const chartVisualizationData = visualizationData;
        if (chartVisualizationData.data.length === 0)
            return fallback;
        return _jsx(RechartsGraph, { visualizationData: chartVisualizationData });
    }
    if (visualizationData.type === 'wordcloud') {
        const textVisualizationData = visualizationData;
        if (textVisualizationData.topTerms.length === 0)
            return fallback;
        return _jsx(VisxWordcloud, { visualizationData: textVisualizationData });
    }
    return null;
});
function prepareCopy(locale) {
    return {
        errorMsg: Translator.translate(errorMsg, locale),
        noDataMsg: Translator.translate(noDataMsg, locale)
    };
}
const noDataMsg = new TextBundle().add('en', 'No data').add('nl', 'Geen data');
const errorMsg = new TextBundle()
    .add('en', 'Could not create visualization')
    .add('nl', 'Kon visualisatie niet maken');
