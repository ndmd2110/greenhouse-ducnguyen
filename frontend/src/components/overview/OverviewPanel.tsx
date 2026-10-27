import { useEffect, useState } from 'react';
import { fetchOverview, listLocations } from '../../services/api';
import type { LocationDto, LocationOverviewDto, OverviewZoneDto } from '../../services/api';

function ZoneCard({ zone }: { zone: OverviewZoneDto }) {
  const readingByDevice = new Map(zone.latest_readings.map((r) => [r.device_id, r]));
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-semibold text-slate-800">{zone.name}</h3>
      <p className="text-xs text-slate-500">
        Moisture {zone.moisture_threshold_low} – {zone.moisture_threshold_high}
      </p>
      {zone.devices.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No devices assigned.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {zone.devices.map((d) => {
            const r = readingByDevice.get(d.id);
            return (
              <li key={d.id} className="rounded border border-slate-100 bg-slate-50 p-2 text-sm">
                <div className="font-medium text-slate-800">{d.display_name ?? d.device_type}</div>
                <div className="text-xs text-slate-500">
                  {d.role} · {d.device_type}
                </div>
                {r ? (
                  <div className="mt-1 text-xs text-slate-700">
                    <span className="font-semibold">
                      {r.value} {r.unit}
                    </span>{' '}
                    · tracking {r.tracking_enabled ? 'on' : 'off'} · every {r.sampling_interval_seconds}s ·{' '}
                    {new Date(r.recorded_at).toLocaleString()}
                  </div>
                ) : (
                  <div className="mt-1 text-xs italic text-slate-400">No reading yet</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function OverviewPanel() {
  const [locations, setLocations] = useState<LocationDto[]>([]);
  const [locationId, setLocationId] = useState('');
  const [overview, setOverview] = useState<LocationOverviewDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  // Locations list for the dropdown (existing endpoint).
  useEffect(() => {
    let cancelled = false;
    listLocations()
      .then((locs) => {
        if (cancelled) return;
        setLocations(locs);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load locations');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The ONLY data call for the cards: selecting a location or pressing Refresh = one fetchOverview.
  useEffect(() => {
    if (!locationId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchOverview(locationId)
      .then((data) => {
        if (!cancelled) setOverview(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setOverview(null);
          setError(e instanceof Error ? e.message : 'Failed to load overview');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [locationId, refreshTick]);

  const rec = overview?.last_recommendation ?? null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Overview</h2>
          <p className="text-sm text-slate-600">One snapshot per location.</p>
        </div>
        <div className="flex items-end gap-2">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
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
          <button
            type="button"
            onClick={() => setRefreshTick((t) => t + 1)}
            disabled={!locationId || loading}
            className="rounded border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {locations.length === 0 && <p className="text-sm text-slate-500">Create a location in the configuration wizard first.</p>}
      {error && (
        <p role="alert" className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {overview && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs uppercase text-slate-500">Assigned sensors</div>
              <div className="text-2xl font-bold">{overview.device_counts.sensor}</div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs uppercase text-slate-500">Assigned actuators</div>
              <div className="text-2xl font-bold">{overview.device_counts.actuator}</div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs uppercase text-slate-500">Strategy</div>
              <div className="text-lg font-semibold">
                {overview.strategy_key ?? <span className="text-sm font-normal italic text-slate-400">None saved</span>}
              </div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-xs uppercase text-slate-500">Recommendation</div>
              {rec ? (
                <>
                  <div className={`text-lg font-semibold ${rec.action === 'irrigate' ? 'text-sky-700' : 'text-slate-800'}`}>
                    {rec.action}
                  </div>
                  <div className="text-xs text-slate-600">{rec.reason}</div>
                </>
              ) : (
                <div className="text-sm italic text-slate-400">No strategy saved, nothing to evaluate</div>
              )}
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {overview.zones.map((z) => (
              <ZoneCard key={z.id} zone={z} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}