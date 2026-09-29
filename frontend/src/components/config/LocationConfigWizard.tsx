import React, { useEffect, useState } from "react";
import {
  addZone,
  createLocation,
  deleteLocation,
  deleteZone,
  getLocationConfig,
  listLocations,
  type CreateLocationPayload,
  type LocationConfigDto,
  type LocationDto,
  type ZoneCreatePayload,
  type ZoneDto,
  updateZone,
} from "../../services/api";

const emptyZone = (): ZoneCreatePayload => ({
  name: "",
  moisture_threshold_low: 0.2,
  moisture_threshold_high: 0.8,
  schedule: { mode: "auto" },
});

export const LocationConfigWizard: React.FC = () => {
  const [locations, setLocations] = useState<LocationDto[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<LocationConfigDto | null>(null);
  const [locationName, setLocationName] = useState("New location");
  const [draftZones, setDraftZones] = useState<ZoneCreatePayload[]>([emptyZone()]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadLocations = async () => {
    try {
      const data = await listLocations();
      setLocations(data);
      if (!selectedLocationId && data.length > 0) {
        setSelectedLocationId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load locations");
    }
  };

  useEffect(() => {
    void loadLocations();
  }, []);

  useEffect(() => {
    if (!selectedLocationId) return;
    void (async () => {
      try {
        const config = await getLocationConfig(selectedLocationId);
        setSelectedLocation(config);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load location");
      }
    })();
  }, [selectedLocationId]);

  const handleCreateLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      const payload: CreateLocationPayload = {
        location_name: locationName,
        zones: draftZones.map((zone) => ({
          ...zone,
          schedule: zone.schedule ?? { mode: "auto" },
        })),
      };
      const created = await createLocation(payload);
      setSelectedLocationId(created.location.id);
      setSelectedLocation(created);
      setDraftZones([emptyZone()]);
      setLocationName("New location");
      await loadLocations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create location");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteLocation = async (locationId: string) => {
    if (!window.confirm("Delete this location?")) return;
    try {
      setError(null);
      await deleteLocation(locationId);
      const nextLocations = locations.filter((location) => location.id !== locationId);
      setLocations(nextLocations);
      if (selectedLocationId === locationId) {
        setSelectedLocationId(nextLocations[0]?.id ?? null);
        setSelectedLocation(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete location");
    }
  };

  const updateDraftZone = (index: number, field: keyof ZoneCreatePayload, value: string | number | Record<string, unknown>) => {
    setDraftZones((current) => current.map((zone, currentIndex) => currentIndex === index ? { ...zone, [field]: value } : zone));
  };

  const addDraftZone = () => setDraftZones((current) => [...current, emptyZone()]);
  const removeDraftZone = (index: number) => setDraftZones((current) => current.length === 1 ? current : current.filter((_, idx) => idx !== index));

  const handleAddZone = async () => {
    if (!selectedLocationId) return;
    try {
      setError(null);
      const newZone = await addZone(selectedLocationId, {
        name: "New zone",
        moisture_threshold_low: 0.2,
        moisture_threshold_high: 0.8,
        schedule: { mode: "auto" },
      });
      setSelectedLocation((current) => current ? { ...current, zones: [...current.zones, newZone] } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add zone");
    }
  };

  const handleDeleteZone = async (zoneId: string) => {
    if (!selectedLocationId) return;
    try {
      setError(null);
      await deleteZone(selectedLocationId, zoneId);
      setSelectedLocation((current) => current ? { ...current, zones: current.zones.filter((zone) => zone.id !== zoneId) } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete zone");
    }
  };

  const handleUpdateZone = async (zone: ZoneDto) => {
    if (!selectedLocationId) return;
    try {
      setError(null);
      const updated = await updateZone(selectedLocationId, zone.id, {
        name: zone.name,
        moisture_threshold_low: zone.moisture_threshold_low,
        moisture_threshold_high: zone.moisture_threshold_high,
        schedule: zone.schedule,
      });
      setSelectedLocation((current) => current ? { ...current, zones: current.zones.map((item) => item.id === zone.id ? updated : item) } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update zone");
    }
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Location config</h2>
          <p className="text-sm text-slate-500">Create and maintain greenhouse locations and zones.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1.8fr]">
        <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="font-semibold text-slate-700">Saved locations</h3>
          {locations.length === 0 && <p className="text-sm text-slate-500">No saved locations yet.</p>}
          <ul className="space-y-2">
            {locations.map((location) => (
              <li key={location.id} className="flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-white p-2">
                <button
                  type="button"
                  onClick={() => setSelectedLocationId(location.id)}
                  className={`text-left text-sm font-medium ${selectedLocationId === location.id ? "text-emerald-700" : "text-slate-700"}`}
                >
                  {location.name}
                </button>
                <button type="button" onClick={() => void handleDeleteLocation(location.id)} className="text-xs text-red-600">Delete</button>
              </li>
            ))}
          </ul>

          <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
            <label className="block text-sm font-medium text-slate-700">Location name</label>
            <input
              value={locationName}
              onChange={(event) => setLocationName(event.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />

            {draftZones.map((zone, index) => (
              <div key={`${index}-${zone.name}`} className="space-y-2 rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-700">Zone {index + 1}</span>
                  {draftZones.length > 1 && (
                    <button type="button" onClick={() => removeDraftZone(index)} className="text-xs text-red-600">Remove</button>
                  )}
                </div>
                <input
                  value={zone.name}
                  onChange={(event) => updateDraftZone(index, "name", event.target.value)}
                  placeholder="Zone name"
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input type="number" step="0.1" min="0" max="1" value={zone.moisture_threshold_low} onChange={(event) => updateDraftZone(index, "moisture_threshold_low", Number(event.target.value))} className="rounded border border-slate-300 px-3 py-2 text-sm" />
                  <input type="number" step="0.1" min="0" max="1" value={zone.moisture_threshold_high} onChange={(event) => updateDraftZone(index, "moisture_threshold_high", Number(event.target.value))} className="rounded border border-slate-300 px-3 py-2 text-sm" />
                </div>
              </div>
            ))}

            <div className="flex gap-2">
              <button type="button" onClick={addDraftZone} className="rounded bg-slate-200 px-3 py-2 text-sm font-medium text-slate-700">Add zone</button>
              <button type="button" onClick={() => void handleCreateLocation()} disabled={loading} className="rounded bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
                {loading ? "Saving..." : "Create location"}
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="font-semibold text-slate-700">Selected configuration</h3>
          {selectedLocation ? (
            <>
              <div className="rounded border border-slate-200 bg-white p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Location</p>
                <p className="mt-1 text-lg font-semibold text-slate-800">{selectedLocation.location.name}</p>
                <p className="mt-1 text-xs text-slate-500">{selectedLocation.location.id}</p>
              </div>

              <div className="space-y-3">
                {selectedLocation.zones.map((zone) => (
                  <div key={zone.id} className="rounded border border-slate-200 bg-white p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold text-slate-700">{zone.name}</p>
                      <button type="button" onClick={() => void handleDeleteZone(zone.id)} className="text-xs text-red-600">Delete</button>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <span>Low: {zone.moisture_threshold_low}</span>
                      <span>High: {zone.moisture_threshold_high}</span>
                    </div>
                    <button type="button" onClick={() => void handleUpdateZone(zone)} className="mt-3 rounded bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700">Save zone values</button>
                  </div>
                ))}
                <button type="button" onClick={() => void handleAddZone()} className="rounded bg-emerald-600 px-3 py-2 text-sm font-medium text-white">Add zone to selection</button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">Select a location to view its zones.</p>
          )}

          {error && <p className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        </div>
      </div>
    </section>
  );
};
