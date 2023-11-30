import { Weak } from '../../../../helpers'
import { PropsUISearchBar } from '../../../../types/elements'

export const SearchBar = ({
  search,
  onSearch,
  placeholder
}: Weak<PropsUISearchBar>): JSX.Element => {
  function handleKeyPress (event: React.KeyboardEvent<HTMLInputElement>): void {
    if (event.key === 'Enter') {
      event.preventDefault()
    }
  }

  return (
    <form className='max-w-[33%]'>
      <div className='flex flex-row w-full'>
        <input
          className={`text-grey1 text-sm md:text-base font-body w-full
          pl-3 pr-3 py-[1px] md:py-1 border-2 border-solid border-grey3 
          focus:outline-none focus:border-primary rounded-full `}
          placeholder={placeholder ?? ''}
          // name="query"  // autcomplete popup is annoying
          type='search'
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          onKeyPress={handleKeyPress}
        />
      </div>
    </form>
  )
}
