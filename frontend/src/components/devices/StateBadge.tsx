const STYLES: Record<string, string> = {
  idle: "bg-slate-200 text-slate-700",
  running: "bg-emerald-100 text-emerald-800",
  error: "bg-red-100 text-red-800",
  maintenance: "bg-amber-100 text-amber-800",
  off: "bg-gray-800 text-gray-100",
};

type Props = {
  state: string;
  allowedCommands: string[];
};

export function StateBadge({ state, allowedCommands }: Props) {
  const tooltip =
    allowedCommands.length > 0
      ? `Allowed commands: ${allowedCommands.join(", ")}`
      : "No commands allowed in this state";
  return (
    <span
      title={tooltip}
      className={`inline-block cursor-help rounded-full px-2 py-0.5 text-xs font-semibold ${
        STYLES[state] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {state}
    </span>
  );
}