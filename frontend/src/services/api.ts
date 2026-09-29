// frontend/src/services/api.ts

// Automatically normalizes base URL so /api is never duplicated
const rawBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const cleanBase = rawBase.replace(/\/api\/?$/, "").replace(/\/$/, "");
const API_BASE = `${cleanBase}/api`;

export interface SensorDto {
  id: string;
  device_type: string;
  display_name: string;
  default_config: Record<string, unknown>;
}

export interface CreateSensorPayload {
  type: "moisture" | "light";
  display_name?: string;
}

export type DeviceFamily = "simulation" | "edge";
export type DeviceRole = "sensor" | "actuator";

export interface DeviceDto {
  id: string;
  device_type: string;
  role: DeviceRole;
  device_family: DeviceFamily;
  display_name: string;
  default_config: Record<string, unknown>;
  zone_id: string | null;
  location_id: string | null;
}

export interface LocationDto {
  id: string;
  name: string;
}

export interface ZoneDto {
  id: string;
  location_id: string;
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule: Record<string, unknown>;
}

export interface LocationConfigDto {
  location: LocationDto;
  zones: ZoneDto[];
}

export interface ZoneCreatePayload {
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule?: Record<string, unknown>;
}

export interface CreateLocationPayload {
  location_name: string;
  zones: ZoneCreatePayload[];
}

export interface ZoneAssignmentPayload {
  zone_id: string | null;
}

// Phase 2 - Sensors API
export async function getSensors(): Promise<SensorDto[]> {
  const res = await fetch(`${API_BASE}/sensors`);
  if (!res.ok) throw new Error("Failed to fetch sensors");
  return res.json();
}

export const fetchSensors = getSensors;

export async function createSensor(
  payload: CreateSensorPayload | string,
  displayName?: string,
): Promise<SensorDto> {
  const request = typeof payload === "string"
    ? { type: payload, display_name: displayName }
    : payload;
  const res = await fetch(`${API_BASE}/sensors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create sensor");
  }
  return res.json();
}

// Phase 3 - Devices API
export async function getDevices(family?: string, role?: string): Promise<DeviceDto[]> {
  const params = new URLSearchParams();
  if (family) params.append("family", family);
  if (role) params.append("role", role);

  const queryStr = params.toString();
  const url = queryStr ? `${API_BASE}/devices?${queryStr}` : `${API_BASE}/devices`;

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch devices");
  return res.json();
}

export async function fetchDevices(options: {
  family?: DeviceFamily;
  role?: DeviceRole;
} = {}): Promise<DeviceDto[]> {
  return getDevices(options.family, options.role);
}

export async function provisionFamily(family: string): Promise<DeviceDto[]> {
  const res = await fetch(`${API_BASE}/devices/provision?family=${family}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to provision device family");
  return res.json();
}

export const provisionDeviceFamily = provisionFamily;

export async function listLocations(): Promise<LocationDto[]> {
  const res = await fetch(`${API_BASE}/locations`);
  if (!res.ok) throw new Error("Failed to fetch locations");
  return res.json();
}

export async function createLocation(payload: CreateLocationPayload): Promise<LocationConfigDto> {
  const res = await fetch(`${API_BASE}/locations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create location");
  }
  return res.json();
}

export async function getLocationConfig(locationId: string): Promise<LocationConfigDto> {
  const res = await fetch(`${API_BASE}/locations/${locationId}/config`);
  if (!res.ok) throw new Error("Failed to fetch location configuration");
  return res.json();
}

export async function deleteLocation(locationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/locations/${locationId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete location");
}

export async function addZone(locationId: string, zone: ZoneCreatePayload): Promise<ZoneDto> {
  const res = await fetch(`${API_BASE}/locations/${locationId}/zones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(zone),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to add zone");
  }
  return res.json();
}

export async function updateZone(locationId: string, zoneId: string, zone: ZoneCreatePayload): Promise<ZoneDto> {
  const res = await fetch(`${API_BASE}/locations/${locationId}/zones/${zoneId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(zone),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update zone");
  }
  return res.json();
}

export async function deleteZone(locationId: string, zoneId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/locations/${locationId}/zones/${zoneId}`, { method: "DELETE" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to delete zone");
  }
}

export async function assignDeviceZone(deviceId: string, zoneId: string | null): Promise<DeviceDto> {
  const res = await fetch(`${API_BASE}/devices/${deviceId}/zone`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zone_id: zoneId }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to assign device zone");
  }
  return res.json();
}

export async function getZoneDevices(locationId: string, zoneId: string): Promise<DeviceDto[]> {
  const res = await fetch(`${API_BASE}/locations/${locationId}/zones/${zoneId}/devices`);
  if (!res.ok) throw new Error("Failed to load zone devices");
  return res.json();
}