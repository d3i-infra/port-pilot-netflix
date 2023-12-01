import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { zoomInIcon, zoomOutIcon } from './zoom_icons';
export const Minimizable = ({ children, size = 'h-[15rem] w-[24rem]', fullSize, minimized }) => {
    const [isMinimized, setIsMinimized] = useState(true);
    const containerStyle = isMinimized
        ? `${size} overflow-hidden animate-fadeIn`
        : (fullSize !== null && fullSize !== void 0 ? fullSize : false)
            ? 'w-full'
            : '';
    const childStyle = isMinimized
        ? 'scale-50 origin-top-left z-10 p-5 w-[200%] '
        : 'transition-all duration-500';
    const toggleStyle = isMinimized
        ? 'transition-all absolute top-0 left-0 h-full w-full z-20 bg-primary/0 hover:bg-primary/25 border-solid  cursor-zoom-in'
        : 'w-min mr-auto mt-2 cursor-zoom-out';
    const iconStyle = isMinimized ? 'rounded-tr-sm bg-primary' : 'rounded-sm mb-2 bg-primary';
    const minimizedTruthy = Boolean(minimized);
    const child = minimizedTruthy
        ? (minimized)
        : (_jsx("div", Object.assign({ className: `relative  ${childStyle}` }, { children: minimizedTruthy ? minimized : children })));
    return (_jsxs("div", Object.assign({ className: `overflow-auto relative ${containerStyle}` }, { children: [child, _jsx("div", Object.assign({ className: `flex items-end justify-start rounded-sm border-primary ${toggleStyle}`, onClick: () => setIsMinimized(!isMinimized) }, { children: _jsx("div", Object.assign({ className: `relative font-caption text-xl px-4 py-1 backdrop-blur-[2px] text-white z-30 ${iconStyle}` }, { children: isMinimized ? zoomInIcon : zoomOutIcon })) }))] })));
};
