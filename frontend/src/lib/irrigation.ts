export type StressLevel = "healthy" | "moderate" | "stressed";

export function stressFromNdvi(ndvi: number | null | undefined): StressLevel {
  if (ndvi == null) return "moderate";
  if (ndvi >= 0.6) return "healthy";
  if (ndvi >= 0.4) return "moderate";
  return "stressed";
}

export function stressColor(level: StressLevel): string {
  switch (level) {
    case "healthy": return "hsl(145 60% 42%)";
    case "moderate": return "hsl(38 92% 50%)";
    case "stressed": return "hsl(0 75% 52%)";
  }
}

/**
 * Recommended water in liters.
 * - Target soil moisture = 35%
 * - 1% deficit ≈ 1 mm water needed in top layer ≈ 1 L/m²
 * - Multiply by area, modulate by NDVI (lower NDVI -> +20% recovery)
 */
export function recommendedLiters(
  soilMoisturePct: number | null | undefined,
  ndvi: number | null | undefined,
  sizeHa: number,
): number {
  if (soilMoisturePct == null) return 0;
  const target = 35;
  const deficit = Math.max(0, target - soilMoisturePct);
  const areaM2 = sizeHa * 10000;
  const ndviFactor = ndvi != null && ndvi < 0.4 ? 1.2 : 1.0;
  const liters = deficit * areaM2 * ndviFactor;
  return Math.round(liters);
}

export function recommendedWindow(liters: number): { start: string; end: string } {
  // Flow rate ~ 8000 L/h. Window starts at 04:00.
  const hours = Math.min(4, Math.max(0.5, liters / 8000));
  const startH = 4;
  const endH = startH + hours;
  const fmt = (h: number) => {
    const hh = Math.floor(h).toString().padStart(2, "0");
    const mm = Math.round((h - Math.floor(h)) * 60).toString().padStart(2, "0");
    return `${hh}:${mm}`;
  };
  return { start: fmt(startH), end: fmt(endH) };
}

export function formatLiters(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k L`;
  return `${Math.round(n)} L`;
}

/** Compute a simple polygon (square) around a center point given size in ha. */
export function farmPolygon(lat: number, lng: number, sizeHa: number): [number, number][] {
  const areaM2 = sizeHa * 10000;
  const sideM = Math.sqrt(areaM2);
  const dLat = (sideM / 2) / 111_320;
  const dLng = (sideM / 2) / (111_320 * Math.cos((lat * Math.PI) / 180));
  // Slight parallelogram for visual variety
  const skew = dLng * 0.15;
  return [
    [lat + dLat, lng - dLng + skew],
    [lat + dLat, lng + dLng + skew],
    [lat - dLat, lng + dLng - skew],
    [lat - dLat, lng - dLng - skew],
  ];
}
