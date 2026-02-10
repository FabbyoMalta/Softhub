import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

type BillingResponse = {
  summary: { total_open: number; over_20_days: number; oldest_due_date: string | null }
  items: Array<{ external_id: string; id_cliente: string; amount_open: string; due_date: string; open_days: number }>
}

function App() {
  const [data, setData] = useState<BillingResponse | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/billing/open')
      .then((res) => res.json())
      .then(setData)
  }, [])

  return (
    <main style={{ fontFamily: 'sans-serif', margin: '2rem' }}>
      <h1>Softhub Ops Console (MVP)</h1>
      <p>Dashboard diário e rotina de inadimplência.</p>
      {data && (
        <>
          <h2>KPIs</h2>
          <ul>
            <li>Total em aberto: {data.summary.total_open}</li>
            <li>Atrasos +20 dias: {data.summary.over_20_days}</li>
            <li>Vencimento mais antigo: {data.summary.oldest_due_date ?? '-'}</li>
          </ul>
          <h2>Contas em aberto</h2>
          <table border={1} cellPadding={6}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Cliente</th>
                <th>Valor aberto</th>
                <th>Vencimento</th>
                <th>Dias em aberto</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.external_id}>
                  <td>{item.external_id}</td>
                  <td>{item.id_cliente}</td>
                  <td>{item.amount_open}</td>
                  <td>{item.due_date}</td>
                  <td>{item.open_days}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
