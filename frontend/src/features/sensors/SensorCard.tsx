import React, { useEffect, useState } from 'react';
import { getLatestReading, readSensorNow, updateSampling } from '../../services/api';
import type { ReadingDto, SensorDto } from '../../services/api';

// TEMPORARY: Phase 12 replaces this poll with the dashboard WebSocket (reading.created).
const POLL_MS = 5000;
const MIN_INTERVAL_SECONDS = 5;

const SOURCE_STYLES: Record<string, string> = {
  simulation: 'bg-sky-100 text-sky-800',
  mqtt: 'bg-violet-100 text-violet-800',
  vendor: 'bg-amber-100 text-amber-800',
};

function formatValue(reading: ReadingDto): string {
  const digits = reading.unit === 'lux' ? 1 : 3;
  return `${reading.value.toFixed(digits)} ${reading.unit}`;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export const SensorCard: React.FC<{ sensor: SensorDto }> = ({ sensor }) => {
  const protocol = String(sensor.default_config?.protocol ?? 'simulation');
  const isMqtt = protocol === 'mqtt';

  const [reading, setReading] = useState<ReadingDto | null>(null);
  const [loadingReading, setLoadingReading] = useState<boolean>(true);
  const [pollError, setPollError] = useState<string | null>(null);

  const [readingBusy, setReadingBusy] = useState<boolean>(false);
  const [readError, setReadError] = useState<string | null>(null);

  const [savedInterval, setSavedInterval] = useState<number>(sensor.sampling_interval_seconds);
  const [intervalInput, setIntervalInput] = useState<string>(String(sensor.sampling_interval_seconds));
  const [tracking, setTracking] = useState<boolean>(sensor.tracking_enabled);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Latest stored reading comes from the database, so a page refresh keeps the last value.
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const latest = await getLatestReading(sensor.id);
        if (!cancelled) {
          setReading(latest);
          setPollError(null);
        }
      } catch (err: unknown) {
        if (!cancelled) setPollError(errorMessage(err, 'Could not load latest reading'));
      } finally {
        if (!cancelled) setLoadingReading(false);
      }
    };
    void Promise.resolve().then(load);
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sensor.id]);

  const handleReadNow = async () => {
    try {
      setReadingBusy(true);
      setReadError(null);
      setReading(await readSensorNow(sensor.id));
    } catch (err: unknown) {
      setReadError(errorMessage(err, 'Read failed'));
    } finally {
      setReadingBusy(false);
    }
  };

  const saveSampling = async (interval: number, trackingEnabled: boolean) => {
    if (!Number.isInteger(interval) || interval < MIN_INTERVAL_SECONDS) {
      setSaveError(`Interval must be a whole number of at least ${MIN_INTERVAL_SECONDS} seconds.`);
      return;
    }
    try {
      setSaving(true);
      setSaveError(null);
      const result = await updateSampling(sensor.id, interval, trackingEnabled);
      setSavedInterval(result.sampling_interval_seconds);
      setIntervalInput(String(result.sampling_interval_seconds));
      setTracking(result.tracking_enabled);
    } catch (err: unknown) {
      setSaveError(errorMessage(err, 'Could not save sampling settings'));
    } finally {
      setSaving(false);
    }
  };

  const intervalChanged = intervalInput !== String(savedInterval);

  return (
    <div className="p-3 border border-slate-100 rounded bg-slate-50">
      <div className="flex justify-between items-center mb-2 gap-2">
        <span className="font-semibold text-slate-700 truncate" title={sensor.display_name}>
          {sensor.display_name}
        </span>
        <span className="text-xs px-2 py-0.5 bg-slate-200 text-slate-600 rounded-full shrink-0">
          {sensor.device_type}
        </span>
      </div>

      {/* Latest stored value + source badge */}
      <div className="rounded border border-slate-200 bg-white p-3 mb-3">
        {loadingReading ? (
          <p className="text-sm text-slate-400">Loading latest reading...</p>
        ) : reading ? (
          <>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-2xl font-bold text-slate-900">{formatValue(reading)}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  SOURCE_STYLES[reading.source] ?? 'bg-slate-200 text-slate-700'
                }`}
              >
                {reading.source}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {new Date(reading.recorded_at).toLocaleString()}
            </p>
          </>
        ) : (
          <p className="text-sm italic text-slate-500">
            {isMqtt ? 'Waiting for the device to send data.' : 'No readings yet.'}
          </p>
        )}
        {pollError && <p className="mt-1 text-xs text-red-500">Refresh failed: {pollError}</p>}
      </div>

      <div className="flex items-center gap-2 mb-1">
        <button
          type="button"
          onClick={() => void handleReadNow()}
          disabled={readingBusy || isMqtt}
          title={isMqtt ? 'MQTT devices push their readings; they cannot be read on demand.' : undefined}
          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded disabled:opacity-50 transition"
        >
          {readingBusy ? 'Reading...' : 'Read now'}
        </button>
        <span className="text-xs text-slate-400">Auto-refreshes every {POLL_MS / 1000}s (temporary polling)</span>
      </div>
      {readError && <p className="text-xs text-red-500 mb-2">Error: {readError}</p>}

      {/* Sampling controls */}
      <div className="mt-3 border-t border-slate-200 pt-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Interval (s)
            <input
              type="number"
              min={MIN_INTERVAL_SECONDS}
              step={1}
              value={intervalInput}
              onChange={(e) => setIntervalInput(e.target.value)}
              className="mt-1 block w-24 rounded border border-slate-300 bg-white px-2 py-1 text-sm font-normal normal-case text-slate-700"
            />
          </label>
          <button
            type="button"
            onClick={() => void saveSampling(Number(intervalInput), tracking)}
            disabled={saving || !intervalChanged}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded disabled:opacity-50 transition"
          >
            {saving ? 'Saving...' : 'Apply'}
          </button>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={tracking}
              disabled={saving}
              onChange={(e) => void saveSampling(savedInterval, e.target.checked)}
            />
            Tracking {tracking ? 'on' : 'off'}
          </label>
        </div>
        {isMqtt && (
          <p className="mt-2 text-xs text-slate-400">
            MQTT device: the backend stores this interval, the controller honors it (Phase 12).
          </p>
        )}
        {saveError && <p className="mt-2 text-xs text-red-500">Error: {saveError}</p>}
      </div>

      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-slate-500">Default config</summary>
        <pre className="mt-1 text-xs bg-slate-800 text-slate-100 p-2 rounded overflow-x-auto">
          {JSON.stringify(sensor.default_config, null, 2)}
        </pre>
      </details>
    </div>
  );
};