import { assert, Weak } from '../../../../helpers'
import {
  PropsUITable,
  PropsUITableBody,
  PropsUITableCell,
  PropsUITableHead,
  PropsUITableRow,
  TableWithContext,
  TableContext
} from '../../../../types/elements'
import { PropsUIPromptConsentForm, PropsUIPromptConsentFormTable } from '../../../../types/prompts'
import { LabelButton, PrimaryButton } from '../elements/button'
import { BodyLarge } from '../elements/text'
import TextBundle from '../../../../text_bundle'
import { Translator } from '../../../../translator'
import { ReactFactoryContext } from '../../factory'
import { useCallback, useEffect, useState } from 'react'
import _ from 'lodash'

import useUnloadWarning from '../hooks/useUnloadWarning'

import { TableContainer } from '../elements/table_container'

type Props = Weak<PropsUIPromptConsentForm> & ReactFactoryContext

export const ConsentForm = (props: Props): JSX.Element => {
  useUnloadWarning()
  const [tables, setTables] = useState<TableWithContext[]>(() => parseTables(props.tables))
  const [metaTables, setMetaTables] = useState<TableWithContext[]>(() =>
    parseTables(props.metaTables)
  )

  // const { visualizationSettings, locale, resolve } = props
  const { locale, resolve } = props
  // const visualizationSettings = testVisualizations

  const { description, donateQuestion, donateButton, cancelButton } = prepareCopy(props)

  useEffect(() => {
    setTables(parseTables(props.tables))
    setMetaTables(parseTables(props.metaTables))
  }, [props.tables])

  const updateTable = useCallback((tableId: string, table: TableWithContext) => {
    setTables((tables) => {
      const index = tables.findIndex((table) => table.id === tableId)
      if (index === -1) return tables

      const newTables = [...tables]
      newTables[index] = table
      return newTables
    })
  }, [])

  function rowCell (dataFrame: any, column: string, row: number): PropsUITableCell {
    const text = String(dataFrame[column][`${row}`])
    return { __type__: 'PropsUITableCell', text: text }
  }

  function headCell (dataFrame: any, column: string): PropsUITableCell {
    return { __type__: 'PropsUITableCell', text: column }
  }

  function columnNames (dataFrame: any): string[] {
    return Object.keys(dataFrame)
  }

  function columnCount (dataFrame: any): number {
    return columnNames(dataFrame).length
  }

  function rowCount (dataFrame: any): number {
    if (columnCount(dataFrame) === 0) {
      return 0
    } else {
      const firstColumn = dataFrame[columnNames(dataFrame)[0]]
      return Object.keys(firstColumn).length - 1
    }
  }

  function rows (data: any): PropsUITableRow[] {
    const result: PropsUITableRow[] = []
    const n = rowCount(data)
    for (let row = 0; row <= n; row++) {
      const id = `${row}`
      const cells = columnNames(data).map((column: string) => rowCell(data, column, row))
      result.push({ __type__: 'PropsUITableRow', id, cells })
    }
    return result
  }

  function parseTables (
    tablesData: PropsUIPromptConsentFormTable[]
  ): Array<PropsUITable & TableContext> {
    return tablesData.map((table) => parseTable(table))
  }

  function parseTable (tableData: PropsUIPromptConsentFormTable): PropsUITable & TableContext {
    const id = tableData.id
    const title = Translator.translate(tableData.title, props.locale)
    const description =
      tableData.description !== undefined
        ? Translator.translate(tableData.description, props.locale)
        : ''
    const deletedRowCount = 0
    const dataFrame = JSON.parse(tableData.data_frame)
    const headCells = columnNames(dataFrame).map((column: string) => headCell(dataFrame, column))
    const head: PropsUITableHead = { __type__: 'PropsUITableHead', cells: headCells }
    const body: PropsUITableBody = { __type__: 'PropsUITableBody', rows: rows(dataFrame) }

    return {
      __type__: 'PropsUITable',
      id,
      head,
      body,
      title,
      description,
      deletedRowCount,
      annotations: [],
      originalBody: body,
      deletedRows: [],
      visualizations: tableData.visualizations
    }
  }

  function handleDonate (): void {
    const value = serializeConsentData()
    resolve?.({ __type__: 'PayloadJSON', value })
  }

  function handleCancel (): void {
    resolve?.({ __type__: 'PayloadFalse', value: false })
  }

  function serializeConsentData (): string {
    const array = serializeTables().concat(serializeMetaData())
    return JSON.stringify(array)
  }

  function serializeMetaData (): any[] {
    return serializeMetaTables().concat(serializeDeletedMetaData())
  }

  function serializeTables (): any[] {
    return tables.map((table) => serializeTable(table))
  }

  function serializeMetaTables (): any[] {
    return metaTables.map((table) => serializeTable(table))
  }

  function serializeDeletedMetaData (): any {
    const rawData = tables
      .filter(({ deletedRowCount }) => deletedRowCount > 0)
      .map(({ id, deletedRowCount }) => `User deleted ${deletedRowCount} rows from table: ${id}`)

    const data = JSON.stringify(rawData)
    return { user_omissions: data }
  }

  function serializeTable ({ id, head, body: { rows } }: PropsUITable): any {
    const data = rows.map((row) => serializeRow(row, head))
    return { [id]: data }
  }

  function serializeRow (row: PropsUITableRow, head: PropsUITableHead): any {
    assert(
      row.cells.length === head.cells.length,
      `Number of cells in row (${row.cells.length}) should be equals to number of cells in head (${head.cells.length})`
    )
    const keys = head.cells.map((cell) => cell.text)
    const values = row.cells.map((cell) => cell.text)
    return _.fromPairs(_.zip(keys, values))
  }

  return (
    <>
      <div className='max-w-3xl'>
        <BodyLarge text={description} />
      </div>
      <div className='flex flex-col gap-16 w-full'>
        <div className='grid gap-4 md:gap-8 max-w-full'>
          {tables.map((table) => {
            return (
              <TableContainer
                key={table.id}
                id={table.id}
                table={table}
                updateTable={updateTable}
                locale={locale}
              />
            )
          })}
        </div>
        <div>
          <BodyLarge margin='' text={donateQuestion} />

          <div className='flex flex-row gap-4 mt-4 mb-4'>
            <PrimaryButton
              label={donateButton}
              onClick={handleDonate}
              color='bg-success text-white'
            />
            <LabelButton label={cancelButton} onClick={handleCancel} color='text-grey1' />
          </div>
        </div>
      </div>
    </>
  )
}

interface Copy {
  description: string
  donateQuestion: string
  donateButton: string
  cancelButton: string
}

function prepareCopy ({ locale }: Props): Copy {
  return {
    description: Translator.translate(description, locale),
    donateQuestion: Translator.translate(donateQuestionLabel, locale),
    donateButton: Translator.translate(donateButtonLabel, locale),
    cancelButton: Translator.translate(cancelButtonLabel, locale)
  }
}

const donateQuestionLabel = new TextBundle()
  .add('en', 'Do you want to donate the above data?')
  .add('nl', 'Wilt u de bovenstaande gegevens doneren?')

const donateButtonLabel = new TextBundle().add('en', 'Yes, share for research').add('nl', 'Ja, deel voor onderzoek')

const cancelButtonLabel = new TextBundle().add('en', 'No').add('nl', 'Nee')

const description = new TextBundle()
  .add(
    'en',
    'Below, you will find information about your own Netflix viewing history. Examine the data carefully, and remove the information you do not wish to share. If you wish to share this data, click on the \'Yes, share for research\' button at the bottom of this page. By sharing this information, you contribute to research on viewing behavior on Netflix. Thank you very much in advance!'
  )
  .add(
    'nl',
    'Hieronder ziet u gegevens over uw eigen Netflix kijkgeschiedenis. Bekijk de gegevens zorgvuldig, en verwijder de gegevens die u niet wilt delen. Als u deze gegevens wilt delen, klik dan op de knop ‘Ja, deel voor onderzoek’ onderaan deze pagina. Door deze gegevens te delen draagt u bij aan onderzoek over kijkgedrag op Netflix, alvast heel erg bedankt!'
  )
