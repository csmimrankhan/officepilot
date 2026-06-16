export default function AdminResponsiveTable({ columns, data, renderRow, keyField = 'id', emptyMessage = 'No data found.', mobileCard = null }) {
  if (!data || data.length === 0) {
    return <div className="empty-state" style={{ padding: '40px 20px' }}><p className="subtle">{emptyMessage}</p></div>
  }

  return (
    <>
      <div className="admin-table-desktop">
        <table className="table" style={{ width: '100%' }}>
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col.key} style={col.width ? { width: col.width } : {}}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map(item => renderRow(item))}
          </tbody>
        </table>
      </div>
      {mobileCard && (
        <div className="admin-table-mobile">
          {data.map(item => (
            <div key={item[keyField]}>{mobileCard(item)}</div>
          ))}
        </div>
      )}
    </>
  )
}
