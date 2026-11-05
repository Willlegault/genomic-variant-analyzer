"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
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
  CHART_THEME,
  EFFECT_COLORS,
  EFFECT_LABELS,
  PATHOGENICITY_COLORS,
  PATHOGENICITY_LABELS,
} from "../lib/style";

const TOOLTIP = {
  contentStyle: {
    background: CHART_THEME.tooltipBg,
    border: `1px solid ${CHART_THEME.tooltipBorder}`,
    borderRadius: 8,
    fontSize: 12,
  },
  itemStyle: { color: CHART_THEME.tooltipText },
  labelStyle: { color: CHART_THEME.text },
  cursor: { fill: CHART_THEME.cursor },
};

const TICK = { fontSize: 11, fill: CHART_THEME.text };

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
            cy="45%"
            innerRadius={52}
            outerRadius={80}
            paddingAngle={data.length > 1 ? 3 : 0}
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={PATHOGENICITY_COLORS[entry.key] ?? "#94a3b8"} />
            ))}
          </Pie>
          <Tooltip {...TOOLTIP} />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value: string) => (
              <span style={{ color: CHART_THEME.text, fontSize: 12 }}>{value}</span>
            )}
          />
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
        <BarChart data={data} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={CHART_THEME.grid} />
          <XAxis
            dataKey="name"
            tick={TICK}
            interval={0}
            axisLine={{ stroke: CHART_THEME.grid }}
            tickLine={false}
          />
          <YAxis allowDecimals={false} tick={TICK} axisLine={false} tickLine={false} />
          <Tooltip {...TOOLTIP} />
          <Bar dataKey="value" name="Variants" radius={[6, 6, 0, 0]} maxBarSize={56}>
            {data.map((entry) => (
              <Cell key={entry.key} fill={EFFECT_COLORS[entry.key] ?? "#94a3b8"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="mt-2 flex h-64 w-full items-center justify-center rounded-lg border border-dashed border-line text-sm text-muted">
      {label}
    </div>
  );
}
