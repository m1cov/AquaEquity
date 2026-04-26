export const REGION_COORDS: Record<string, { lat: number; lon: number }> = {
  "Pelagonia": { lat: 41.03, lon: 21.33 },
  "Polog": { lat: 41.99, lon: 20.97 },
  "Vardar Valley": { lat: 41.55, lon: 22.20 },
  "Tikveš": { lat: 41.55, lon: 22.20 },
  "Strumica Valley": { lat: 41.43, lon: 22.64 },
  "Ovče Pole": { lat: 41.78, lon: 22.20 },
  "Kumanovo Region": { lat: 42.13, lon: 21.71 },
  "Prespa": { lat: 40.98, lon: 21.10 },
  "Skopje Valley": { lat: 41.99, lon: 21.43 },
  "Bregalnica Region": { lat: 41.88, lon: 22.20 },
};

const REGION_ALIASES: Record<string, string> = {
  "Pelagonija": "Pelagonia",
  "pelagonija": "Pelagonia",
};

export const DEFAULT_REGION_COORD = { lat: 41.99, lon: 21.43 };

export function canonicalRegionName(region: string) {
  return REGION_ALIASES[region] ?? region;
}

export function regionCoord(region: string) {
  return REGION_COORDS[canonicalRegionName(region)] ?? DEFAULT_REGION_COORD;
}
