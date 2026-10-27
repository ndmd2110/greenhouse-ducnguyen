import { useEffect, useState } from 'react';
import {
  evaluateAutomation,
  getAutomation,
  listLocations,
  listStrategies,
  saveAutomation,
} from '../../services/api';
import type { LocationDto, RecommendationDto, StrategyInfoDto } from '../../services/api';

type Notice = { kind: 'success' | 'error'; text: string };

export function StrategyPanel() {
  const [locations, setLocations] = useState<LocationDto[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfoDto[]>([]);
  const [locationId, setLocationId] = useState('');
  const [strategyKey, setStrategyKey] = useState('');
  const [savedKey, setSavedKey] = useState('');
  const [result, setResult] = useState<RecommendationDto | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState<'save' | 'evaluate' | null>(null);

  // Initial load: locations + known strategy keys.
  useEffect(() => {
    let cancelled = false;
    Promise.all([listLocations(), listStrategies()])
      .then(([locs, strats]) => {
        if (cancelled) return;
        setLocations(locs);
        setStrategies(strats);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch((err: unknown) => {
        if (!cancelled) setNotice({ kind: 'error', text: err instanceof Error ? err.message : 'Failed to load automation data' });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the persisted key whenever the location changes.
  useEffect(() => {
    if (!locationId) return;
    let cancelled = false;
    getAutomation(locationId)
      .then((rule) => {
        if (cancelled) return;
        setStrategyKey(rule.strategy_key);
        setSavedKey(rule.is_default ? '' : rule.strategy_key);
        setResult(null);
        setNotice(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setNotice({ kind: 'error', text: err instanceof Error ? err.message : 'Failed to load strategy' });
      });
    return () => {
      cancelled = true;
    };
  }, [locationId]);

  const dirty = strategyKey !== savedKey;

  const handleSave = async () => {
    setBusy('save');
    setNotice(null);
    try {
      const rule = await saveAutomation(locationId, strategyKey);
      setSavedKey(rule.strategy_key);
      setNotice({ kind: 'success', text: `Saved "${rule.strategy_key}" for this location.` });
    } catch (err: unknown) {
      setNotice({ kind: 'error', text: err instanceof Error ? err.message : 'Failed to save strategy' });
    } finally {
      setBusy(null);
    }
  };

  const handleEvaluate = async () => {
    setBusy('evaluate');
    setNotice(null);
    try {
      setResult(await evaluateAutomation(locationId));
    } catch (err: unknown) {
      setResult(null);
      setNotice({ kind: 'error', text: err instanceof Error ? err.message : 'Failed to evaluate' });
    } finally {
      setBusy(null);
    }
  };

  const description = strategies.find((s) => s.key === strategyKey)?.description;
  const irrigate = result?.action === 'irrigate';

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
      <h2 className="mb-1 text-xl font-bold text-slate-800">Automation strategy</h2>
      <p className="mb-4 text-sm text-slate-600">
        Pick how irrigation is decided for a location, save it, then evaluate against the latest sensor readings.
      </p>

      {locations.length === 0 ? (
        <p className="text-sm text-slate-500">Create a location in the configuration wizard first.</p>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm font-medium text-slate-700">
              Location
              <select
                value={locationId}
                onChange={(e) => setLocationId(e.target.value)}
                className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-normal"
              >
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm font-medium text-slate-700">
              Strategy
              <select
                value={strategyKey}
                onChange={(e) => setStrategyKey(e.target.value)}
                className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-normal"
              >
                {strategies.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.key}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={handleSave}
              disabled={busy !== null || !strategyKey || !dirty}
              className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy === 'save' ? 'Saving...' : 'Save'}
            </button>
            <button
              type="button"
              onClick={handleEvaluate}
              disabled={busy !== null || !locationId}
              className="rounded border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy === 'evaluate' ? 'Evaluating...' : 'Evaluate'}
            </button>
          </div>

          {description && <p className="mt-2 text-sm text-slate-500">{description}</p>}
          {dirty && savedKey !== '' && (
            <p className="mt-1 text-sm text-amber-700">Unsaved change: evaluate still uses "{savedKey}" until you save.</p>
          )}
          {dirty && savedKey === '' && (
            <p className="mt-1 text-sm text-amber-700">Nothing saved yet: evaluate uses the default until you save.</p>
          )}
        </>
      )}

      {notice && (
        <p
          role={notice.kind === 'error' ? 'alert' : 'status'}
          className={`mt-3 rounded border px-3 py-2 text-sm ${
            notice.kind === 'error'
              ? 'border-red-200 bg-red-50 text-red-800'
              : 'border-emerald-200 bg-emerald-50 text-emerald-800'
          }`}
        >
          {notice.text}
        </p>
      )}

      {result && (
        <div className={`mt-4 rounded border p-4 ${irrigate ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-slate-50'}`}>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-sm font-semibold ${
                irrigate ? 'bg-sky-600 text-white' : 'bg-slate-200 text-slate-800'
              }`}
            >
              {result.action}
            </span>
            <span className="text-sm text-slate-600">using "{result.strategy_key}"</span>
          </div>
          <p className="mt-2 text-sm text-slate-800">{result.reason}</p>
          {result.zones.length > 1 && (
            <ul className="mt-3 space-y-1 border-t border-slate-200 pt-3 text-sm">
              {result.zones.map((z) => (
                <li key={z.zone_id} className="flex flex-wrap gap-x-2">
                  <span className="font-medium text-slate-800">{z.zone_name}</span>
                  <span className={z.action === 'irrigate' ? 'font-semibold text-sky-700' : 'text-slate-600'}>{z.action}</span>
                  <span className="text-slate-500">{z.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}