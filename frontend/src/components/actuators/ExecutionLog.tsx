import { useCallback, useEffect, useState } from "react";
import { applyActuatorCommand, fetchDevices, listExecutions } from "../../services/api";
import type { DeviceDto, ExecutionDto } from "../../services/api";

export function ExecutionLog() {
  const [rows, setRows] = useState<ExecutionDto[]>([]);
  const [actuators, setActuators] = useState<DeviceDto[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [command, setCommand] = useState("start_pump");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [executions, devices] = await Promise.all([
        listExecutions(20),
        fetchDevices({ role: "actuator" }),
      ]);
      setRows(executions);
      setActuators(devices);
      setDeviceId((prev) => prev || devices[0]?.id || "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load execution log");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(refresh);
  }, [refresh]);

  const handleApply = async () => {
    if (!deviceId || !command.trim()) return;
    try {
      setApplying(true);
      setError(null);
      await applyActuatorCommand(deviceId, command.trim());
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to apply command");
    } finally {
      setApplying(false);
    }
  };

  const nameById = new Map(actuators.map((d) => [d.id, d.display_name]));

  return (
    <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Execution log</h2>
          <p className="text-sm text-gray-500">Recent actuator apply attempts (Decorator pattern).</p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="rounded border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <ul className="mb-4 list-disc space-y-1 rounded border border-slate-200 bg-slate-50 p-3 pl-7 text-xs text-slate-600">
        <li>
          Any command succeeds until the actuator has been <code>running</code> for 30 minutes. The command is not
          validated in this phase.
        </li>
        <li>
          A success row has an empty message and the policy <code>logging</code>.
        </li>
        <li>
          A blocked row shows <code>Max run time exceeded</code> with the policies <code>maxRunTime</code> and{" "}
          <code>logging</code>.
        </li>
      </ul>

      <div className="mb-4 flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Actuator
          <select
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            className="rounded border border-slate-300 bg-white px-2 py-2 text-sm font-normal"
          >
            {actuators.map((d) => (
              <option key={d.id} value={d.id}>
                {d.display_name} ({d.state})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Command
          <input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            className="rounded border border-slate-300 px-2 py-2 text-sm font-normal"
          />
        </label>
        <button
          type="button"
          onClick={() => void handleApply()}
          disabled={applying || !deviceId}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {applying ? "Applying..." : "Apply (demo)"}
        </button>
      </div>

      {error && (
        <p role="alert" className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {rows.length === 0 ? (
        <p className="py-4 text-sm italic text-slate-400">No executions yet. Apply a command to create one.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <th className="py-2 pr-4">Time</th>
                <th className="py-2 pr-4">Device</th>
                <th className="py-2 pr-4">Result</th>
                <th className="py-2 pr-4">Policies</th>
                <th className="py-2">Message</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4 whitespace-nowrap text-slate-600">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 text-slate-800">{nameById.get(r.device_id) ?? r.device_id.slice(0, 8)}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                        r.success ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                      }`}
                    >
                      {r.success ? "success" : "blocked"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs text-slate-600">{r.policy_applied.join(", ")}</td>
                  <td className="py-2 text-slate-700">{r.message ?? <span className="text-slate-400">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}