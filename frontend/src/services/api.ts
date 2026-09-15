export interface SensorDto {
  id: string;
  device_type: string;
  display_name: string;
  default_config: Record<string, unknown>;
}

export interface CreateSensorPayload {
  type: 'moisture' | 'light';
  display_name?: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchSensors(): Promise<SensorDto[]> {
  const res = await fetch(`${API_BASE}/api/sensors`);
  if (!res.ok) throw new Error('Failed to fetch sensors');
  return res.json();
}

export async function createSensor(payload: CreateSensorPayload): Promise<SensorDto> {
  const res = await fetch(`${API_BASE}/api/sensors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to create sensor');
  }
  return res.json();
}