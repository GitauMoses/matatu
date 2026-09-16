const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8123";

export type Stop = {
  id: string;
  name: string;
  lat: number;
  lon: number;
};

export type SearchResult = {
  id: string;
  name: string;
  context: string;
  lat: number;
  lon: number;
  source: "stage" | "place";
  nearest_stage: { id: string; name: string; walk_km: number } | null;
  reachable: boolean;
};

export type PlanLeg = {
  route_id: string;
  route_number: string;
  route_description: string;
  headsign: string;
  board_stop: Stop;
  alight_stop: Stop;
  stops: Stop[];
  num_stages: number;
  distance_km: number;
  alight_on_request: boolean;
  /** Unconfirmed — matched from a government registry, not a rider. Only
   * ever populated when `terminals` has nothing confirmed. */
  likely_saccos: string[];
  terminals: { name: string; lat: number; lon: number; saccos: string[] }[];
  geometry: [number, number][]; // [lon, lat] along the recorded matatu path
};

export type PlanOption = {
  estimated_minutes: number;
  legs: PlanLeg[];
  transfers: number;
  transfer_stop?: Stop;
  transfer_to_stop?: Stop;
  transfer_walk_km?: number;
  walk_to_board_km: number;
  walk_from_alight_km: number;
};

export type Stage = { id: string; name: string; lat: number; lon: number; routes?: string[] };

export type PlanResult = {
  walk_only?: { distance_km: number; minutes: number };
  options: PlanOption[];
  note: string;
};

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export function fetchStops(): Promise<Stop[]> {
  return getJSON("/stops");
}

export function searchPlaces(
  query: string,
  near?: { lat: number; lon: number }
): Promise<SearchResult[]> {
  const qs = new URLSearchParams({ q: query });
  if (near) {
    qs.set("lat", String(near.lat));
    qs.set("lon", String(near.lon));
  }
  return getJSON(`/search?${qs.toString()}`);
}

export function planTrip(
  originLat: number,
  originLon: number,
  destLat: number,
  destLon: number,
  originName?: string,
  destName?: string
): Promise<PlanResult> {
  const qs = new URLSearchParams({
    origin_lat: String(originLat),
    origin_lon: String(originLon),
    dest_lat: String(destLat),
    dest_lon: String(destLon),
  });
  if (originName) qs.set("origin_name", originName);
  if (destName) qs.set("dest_name", destName);
  return getJSON(`/plan?${qs.toString()}`);
}
