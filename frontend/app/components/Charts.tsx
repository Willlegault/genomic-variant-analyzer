"use client";

import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Pathogenicity, VariantEffect } from "../lib/types";
import {
  EFFECT_COLORS,
  EFFECT_LABELS,
  PATHOGENICITY_COLORS,
  PATHOGENICITY_LABELS,
} from "../lib/style";

interface PathogenicityChartProps {
  counts: Record<string, number>;
}

export function PathogenicityChart({ counts }: PathogenicityChartProps) {
  const data = Object.entries(counts).map(([key, value]) => ({
    key: key as Pathogenicity,
    name: PATHOGENICITY_LABELS[key as Pathogenicity] ?? key,
    value,
  }));

  if (data.length === 0) {
    return <EmptyChart label="No variants to chart." />;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={({ name, value }) => `${name ?? ""}: ${value ?? 0}`}
          >
            {data.map((entry) => (
              <Cell
                key={entry.key}
                fill={PATHOGENICITY_COLORS[entry.key] ?? "#94a3b8"}
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

interface EffectChartProps {
  counts: Record<string, number>;
}

export function EffectChart({ counts }: EffectChartProps) {
  const data = Object.entries(counts).map(([key, value]) => ({
    key: key as VariantEffect,
    name: EFFECT_LABELS[key as VariantEffect] ?? key,
    value,
  }));

  if (data.length === 0) {
    return <EmptyChart label="No variants to chart." />;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value">
            {data.map((entry) => (
              <Cell
                key={entry.key}
                fill={EFFECT_COLORS[entry.key] ?? "#94a3b8"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="flex h-64 w-full items-center justify-center rounded-md border border-dashed border-zinc-300 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
      {label}
    </div>
  );
}
