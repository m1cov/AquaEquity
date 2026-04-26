import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { type EnrichedFarm } from "@/hooks/useFarmData";
import { farmPolygon, stressColor } from "@/lib/irrigation";

// Fix default icon path issues (defensive — we use polygons, not markers)
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;

interface Props {
  farms: EnrichedFarm[];
  onSelect?: (farm: EnrichedFarm) => void;
  height?: string;
}

const MK_CENTER: L.LatLngExpression = [41.6, 21.7];

export function FarmMap({ farms, onSelect, height = "520px" }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const farmsLayerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: MK_CENTER,
      zoom: 8,
      scrollWheelZoom: false,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    const farmsLayer = L.layerGroup().addTo(map);
    mapRef.current = map;
    farmsLayerRef.current = farmsLayer;

    const resizeTimer = window.setTimeout(() => map.invalidateSize(), 150);

    return () => {
      window.clearTimeout(resizeTimer);
      map.remove();
      mapRef.current = null;
      farmsLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const layer = farmsLayerRef.current;
    const map = mapRef.current;
    if (!layer || !map) return;

    layer.clearLayers();

    const bounds = L.latLngBounds([]);

    farms.forEach((farm) => {
      const color = stressColor(farm.stress);
      const hasCorners =
        farm.top_left_x != null && farm.top_left_y != null &&
        farm.top_right_x != null && farm.top_right_y != null &&
        farm.bottom_right_x != null && farm.bottom_right_y != null &&
        farm.bottom_left_x != null && farm.bottom_left_y != null;
      const positions: L.LatLngExpression[] = hasCorners
        ? [
            [farm.top_left_x!, farm.top_left_y!],
            [farm.top_right_x!, farm.top_right_y!],
            [farm.bottom_right_x!, farm.bottom_right_y!],
            [farm.bottom_left_x!, farm.bottom_left_y!],
          ]
        : farmPolygon(farm.latitude, farm.longitude, farm.size_ha) as L.LatLngExpression[];

      const polygon = L.polygon(positions, {
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: 0.45,
      });

      polygon.bindTooltip(
        `<div class="text-xs">
          <div class="font-semibold">${farm.name}</div>
          <div>NDVI: ${farm.ndvi?.toFixed(2) ?? "—"}</div>
          <div>Soil: ${farm.soilMoisture?.toFixed(0) ?? "—"}%</div>
          <div class="capitalize">Stress: ${farm.stress}</div>
        </div>`,
        { direction: "top", offset: [0, -4], opacity: 1 },
      );

      polygon.on("click", () => onSelectRef.current?.(farm));
      polygon.addTo(layer);
      bounds.extend(polygon.getBounds());
    });

    if (bounds.isValid()) map.fitBounds(bounds.pad(0.45), { maxZoom: 8 });
  }, [farms]);

  return (
    <div className="rounded-xl overflow-hidden border shadow-elev-md" style={{ height }}>
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

// Force Leaflet to recompute size when container becomes visible
export function useFixLeafletSize() {
  useEffect(() => {
    const t = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 200);
    return () => window.clearTimeout(t);
  }, []);
}
