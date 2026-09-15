import React, { useEffect, useState } from 'react';
import { fetchSensors, createSensor, SensorDto } from '../../services/api';

export const SensorList: React.FC = () => {
  const [sensors, setSensors] = useState<SensorDto[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string>('');
  const [sensorType, setSensorType] = useState<'moisture' | 'light'>('moisture');

  const loadSensors = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSensors();
      setSensors(data);
    } catch (err: any) {
      setError(err.message || 'Error loading sensors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSensors();
  }, []);

  const handleAddSensor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createSensor({ type: sensorType, display_name: displayName || undefined });
      setDisplayName('');
      await loadSensors();
    } catch (err: any) {
      setError(err.message || 'Error creating sensor');
    }
  };

  return (
    <div id="sensors" className="p-4 bg-white rounded-lg shadow border border-slate-200">
      <h2 className="text-xl font-bold text-slate-800 mb-4">Sensors Management</h2>

      <form onSubmit={handleAddSensor} className="flex flex-wrap gap-2 mb-6">
        <input
          type="text"
          placeholder="Display Name (optional)"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded text-sm flex-1 min-w-[200px]"
        />
        <select
          value={sensorType}
          onChange={(e) => setSensorType(e.target.value as 'moisture' | 'light')}
          className="px-3 py-2 border border-slate-300 rounded text-sm bg-white"
        >
          <option value="moisture">Moisture Sensor</option>
          <option value="light">Light Sensor</option>
        </select>
        <button
          type="submit"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded shadow transition"
        >
          Add Sensor
        </button>
      </form>

      {loading && <p className="text-slate-500 text-sm">Loading sensors...</p>}
      {error && <p className="text-red-500 text-sm mb-4">Error: {error}</p>}

      {!loading && sensors.length === 0 && (
        <p className="text-slate-500 text-sm italic">No sensors registered yet.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sensors.map((sensor) => (
          <div key={sensor.id} className="p-3 border border-slate-100 rounded bg-slate-50">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold text-slate-700">{sensor.display_name}</span>
              <span className="text-xs px-2 py-0.5 bg-slate-200 text-slate-600 rounded-full">
                {sensor.device_type}
              </span>
            </div>
            <pre className="text-xs bg-slate-800 text-slate-100 p-2 rounded overflow-x-auto">
              {JSON.stringify(sensor.default_config, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
};