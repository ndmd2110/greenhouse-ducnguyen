// frontend/src/components/devices/DeviceList.tsx
import React, { useCallback, useEffect, useState } from "react";
import { DeviceFamilySwitcher } from "./DeviceFamilySwitcher";
import {
  assignDeviceZone,
  fetchDevices,
  getLocationConfig,
  listLocations,
  provisionDeviceFamily,
} from "../../services/api";
import type { DeviceDto, DeviceFamily } from "../../services/api";

type ZoneOption = {
  zoneId: string;
  label: string;
};

export const DeviceList: React.FC = () => {
  const [selectedFamily, setSelectedFamily] = useState<DeviceFamily>("simulation");
  const [devices, setDevices] = useState<DeviceDto[]>([]);
  const [zoneOptions, setZoneOptions] = useState<ZoneOption[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [provisioning, setProvisioning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadZoneOptions = useCallback(async () => {
    try {
      const locations = await listLocations();
      const options: ZoneOption[] = [];
      for (const location of locations) {
        const config = await getLocationConfig(location.id);
        for (const zone of config.zones) {
          options.push({
            zoneId: zone.id,
            label: `${location.name} — ${zone.name}`,
          });
        }
      }
      setZoneOptions(options);
    } catch {
      setZoneOptions([]);
    }
  }, []);

  const loadDevices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDevices({ family: selectedFamily });
      setDevices(data);
      await loadZoneOptions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load devices");
    } finally {
      setLoading(false);
    }
  }, [loadZoneOptions, selectedFamily]);

  useEffect(() => {
    void Promise.resolve().then(loadDevices);
  }, [loadDevices]);

  const handleProvision = async () => {
    try {
      setProvisioning(true);
      setError(null);
      await provisionDeviceFamily(selectedFamily);
      await loadDevices();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Provisioning failed");
    } finally {
      setProvisioning(false);
    }
  };

  const handleZoneChange = async (deviceId: string, zoneId: string | null) => {
    try {
      setError(null);
      await assignDeviceZone(deviceId, zoneId);
      await loadDevices();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to assign zone");
    }
  };

  return (
    <section id="devices" className="p-6 bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Phase 3: Devices (Abstract Factory)</h2>
          <p className="text-sm text-gray-500">Provision complete device kits with sensors and actuators</p>
        </div>

        <div className="flex items-center gap-3">
          <DeviceFamilySwitcher
            selectedFamily={selectedFamily}
            onSelectFamily={setSelectedFamily}
          />

          <button
            onClick={handleProvision}
            disabled={provisioning}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {provisioning ? "Provisioning..." : `Provision ${selectedFamily} Kit`}
          </button>
        </div>
      </div>

      {loading && <p className="text-gray-400 text-sm py-4">Loading devices...</p>}
      {error && <p className="text-red-500 text-sm py-2">Error: {error}</p>}

      {!loading && !error && devices.length === 0 && (
        <p className="text-gray-400 text-sm italic py-4">
          No devices provisioned for "{selectedFamily}". Click provision to generate a kit.
        </p>
      )}

      {!loading && devices.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
          {devices.map((d) => {
            const currentZoneLabel = d.zone_id ? zoneOptions.find((option) => option.zoneId === d.zone_id)?.label ?? "Assigned zone" : "Unassigned";
            return (
              <div
                key={d.id}
                className="p-4 border border-gray-200 rounded-lg bg-gray-50 flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="font-semibold text-gray-800 text-sm truncate" title={d.display_name}>
                      {d.display_name}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                        d.role === "sensor"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-purple-100 text-purple-800"
                      }`}
                    >
                      {d.role}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-gray-400 font-mono">{d.device_type}</span>
                    <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded uppercase font-semibold">
                      {d.device_family}
                    </span>
                  </div>

                  <label className="mt-3 block text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                    Zone assignment
                  </label>
                  <select
                    value={d.zone_id ?? ""}
                    onChange={(event) => void handleZoneChange(d.id, event.target.value ? event.target.value : null)}
                    className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-700"
                  >
                    <option value="">Unassigned</option>
                    {zoneOptions.map((option) => (
                      <option key={option.zoneId} value={option.zoneId}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="mt-2 text-xs text-slate-500">Current: {currentZoneLabel}</p>
                </div>

                <div className="mt-3">
                  <span className="text-xs font-semibold text-gray-500 uppercase">Default Config</span>
                  <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-x-auto text-gray-600 font-mono">
                    {JSON.stringify(d.default_config, null, 2)}
                  </pre>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};