import { jsx as _jsx } from "react/jsx-runtime";
export const SearchBar = ({ search, onSearch, placeholder }) => {
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
        }
    }
    return (_jsx("form", Object.assign({ className: 'max-w-[33%]' }, { children: _jsx("div", Object.assign({ className: 'flex flex-row w-full' }, { children: _jsx("input", { className: `text-grey1 text-sm md:text-base font-body w-full
          pl-3 pr-3 py-[1px] md:py-1 border-2 border-solid border-grey3 
          focus:outline-none focus:border-primary rounded-full `, placeholder: placeholder !== null && placeholder !== void 0 ? placeholder : '', 
                // name="query"  // autcomplete popup is annoying
                type: 'search', value: search, onChange: (e) => onSearch(e.target.value), onKeyPress: handleKeyPress }) })) })));
};
