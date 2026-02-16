import React from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

type DonutCompletionProps = {
  finished: number
  pending: number
}

const COLORS = ['#2563eb', '#bfdbfe']

export function DonutCompletion({ finished, pending }: DonutCompletionProps) {
  const safeFinished = Math.max(0, finished)
  const safePending = Math.max(0, pending)
  const total = Math.max(1, safeFinished + safePending)

  const data = [
    { name: 'Finalizadas', value: safeFinished, pct: Math.round((safeFinished / total) * 100) },
    { name: 'Pendentes', value: safePending, pct: Math.round((safePending / total) * 100) },
  ]

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={62} outerRadius={86} paddingAngle={3}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.name === 'Finalizadas' ? COLORS[0] : COLORS[1]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number, _name: unknown, props: any) => [`${value} (${props?.payload?.pct ?? 0}%)`, 'Quantidade']} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
