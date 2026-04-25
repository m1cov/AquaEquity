import numpy as np

from app.services.estimation.crop_parameters import list_crop_parameters
from app.services.estimation.data_inputs import get_estimator_inputs
from app.services.estimation.ekf import ExtendedKalmanFilter
from app.services.estimation.evapotranspiration import clamp, compute_daily_et0_from_weather
from app.services.estimation.measurement_model import H_direct_soil_moisture, h_direct_soil_moisture
from app.services.estimation.parameters import DEFAULT_CROPS, DEFAULT_SOIL_TYPES, SoilCropParams, get_crop_params
from app.services.estimation.state_model import (
    F_jacobian,
    f_state,
    irrigation_control,
    relative_available_water,
    stress_level,
)


DEFAULT_SITE = {"elevation_m": 245.0}

DEFAULT_WEATHER = {
    "T_mean_c": 24.5,
    "T_min_c": 17.0,
    "T_max_c": 32.0,
    "u2_m_s": 2.1,
    "RH_min": 35.0,
    "RH_max": 80.0,
    "Rn_MJ_m2_day": 13.5,
    "rain_mm": 0.0,
    "G_MJ_m2_day": 0.0,
}

MEASUREMENT_SCHEDULE = {
    2: 107.0,
    7: 96.0,
}


class FarmEstimatorService:
    """
    High-level wrapper around the EKF.

    For the demo endpoint, the filter is run from a known initial condition so the
    frontend can display a deterministic scenario.
    """

    def __init__(self):
        self.live_filters: dict[str, ExtendedKalmanFilter] = {}
        self.base_process_noise = 9.0
        self.base_measurement_noise = 16.0

    def create_filter(self, initial_soil_water_mm: float = 110.0) -> ExtendedKalmanFilter:
        ekf = ExtendedKalmanFilter(
            x0=np.array([initial_soil_water_mm], dtype=float),
            P0=np.array([[25.0]], dtype=float),
            Q=np.array([[self.base_process_noise]], dtype=float),
            R=np.array([[self.base_measurement_noise]], dtype=float),
        )
        ekf.Q_base = self.base_process_noise
        return ekf

# nigde ne se koristi
    def initialize_live_filter(self, farm_id: str, initial_soil_water_mm: float = 110.0):
        self.live_filters[farm_id] = self.create_filter(initial_soil_water_mm)

# nigde ne se koristi
    def get_live_estimate(self, farm_id: str):
        if farm_id not in self.live_filters:
            self.initialize_live_filter(farm_id)

        ekf = self.live_filters[farm_id]
        return {
            "farm_id": farm_id,
            "soil_water_estimate_mm": round(float(ekf.x[0]), 2),
            "uncertainty": round(float(ekf.P[0, 0]), 2),
        }

    def run_daily_step(
        self,
        ekf: ExtendedKalmanFilter,
        params: SoilCropParams,
        weather: dict | None = None,
        satellite: dict | None = None,
        inputs: dict | None = None,
        field_geometry: dict | None = None,
        date: str | None = None,
        auto_irrigate: bool = True,
        explicit_irrigation_mm: float | None = None,
    ):
        inputs = self._prepare_daily_inputs(
            params=params,
            weather=weather,
            satellite=satellite,
            inputs=inputs,
            field_geometry=field_geometry,
            date=date,
        )

        theta_now = float(ekf.x[0])
        if explicit_irrigation_mm is not None:
            irrigation_mm = float(explicit_irrigation_mm)
        elif auto_irrigate:
            irrigation_mm = irrigation_control(theta_now, params)
        else:
            irrigation_mm = 0.0

        u = {
            "rain_mm": float(inputs["rain_mm"]),
            "irrigation_mm": irrigation_mm,
            "et0_mm": float(inputs["et0_mm"]),
            "ndvi": float(params.default_ndvi if inputs["ndvi_mean"] is None else inputs["ndvi_mean"]),
        }

        q_base = float(getattr(ekf, "Q_base", self.base_process_noise))
        ekf.Q = np.array([[q_base + float(inputs["Q_weather"])]], dtype=float)

        x_pred, P_pred, _ = ekf.predict(
            f=f_state,
            F_jacobian=F_jacobian,
            u=u,
            params=params,
        )

        updated = False
        kalman_gain = None
        innovation = None
        effective_r_satellite = inputs.get("R_satellite")

        measurement = inputs.get("moisture_mean_mm")
        if inputs["satellite_available"] and measurement is not None:
            if effective_r_satellite is None:
                moisture_std = inputs.get("moisture_std_mm")
                effective_r_satellite = max(float(moisture_std or 0.0) ** 2, 4.0)

            ekf.R = np.array([[float(effective_r_satellite)]], dtype=float)
            x_upd, P_upd, K, y, _ = ekf.update(
                z=np.array([float(measurement)], dtype=float),
                h=h_direct_soil_moisture,
                H_jacobian=H_direct_soil_moisture,
                params=params,
            )
            x_upd[0] = clamp(float(x_upd[0]), params.theta_min, params.theta_max)
            ekf.x = x_upd
            ekf.P = P_upd
            updated = True
            kalman_gain = float(K[0, 0])
            innovation = float(y[0])
        else:
            x_upd = x_pred
            P_upd = P_pred

        return {
            "rain_mm": float(inputs["rain_mm"]),
            "rain_std_mm": float(inputs["rain_std_mm"]),
            "et0_mm": float(inputs["et0_mm"]),
            "et0_std_mm": float(inputs["et0_std_mm"]),
            "weather_source": inputs.get("weather_source"),
            "ndvi_mean": inputs["ndvi_mean"],
            "ndvi_std": inputs["ndvi_std"],
            "moisture_mean_mm": inputs["moisture_mean_mm"],
            "moisture_std_mm": inputs["moisture_std_mm"],
            "satellite_available": bool(inputs["satellite_available"]),
            "irrigation_mm": float(irrigation_mm),
            "x_pred": float(x_pred[0]),
            "P_pred": float(P_pred[0, 0]),
            "x_upd": float(x_upd[0]),
            "P_upd": float(P_upd[0, 0]),
            "measurement_mm": None if measurement is None else float(measurement),
            "updated": updated,
            "kalman_gain": kalman_gain,
            "innovation": innovation,
            "Q_weather": float(inputs["Q_weather"]),
            "R_satellite": effective_r_satellite,
        }

    def _prepare_daily_inputs(
        self,
        params: SoilCropParams,
        weather: dict | None,
        satellite: dict | None,
        inputs: dict | None,
        field_geometry: dict | None,
        date: str | None,
    ) -> dict:
        if inputs is not None:
            return inputs

        if field_geometry is not None:
            if date is None:
                raise ValueError("date is required when field_geometry is provided.")
            return get_estimator_inputs(
                field_geometry=field_geometry,
                date=date,
                weather=weather,
                params=params,
            )

        return self._inputs_from_demo_data(params=params, weather=weather, satellite=satellite)

    def _inputs_from_demo_data(
        self,
        params: SoilCropParams,
        weather: dict | None,
        satellite: dict | None,
    ) -> dict:
        weather = dict(weather or {})
        if "et0_mm" not in weather:
            weather["et0_mm"] = compute_daily_et0_from_weather(weather, DEFAULT_SITE)

        satellite = satellite or {}
        z_meas = satellite.get("z_meas")
        moisture_std_mm = satellite.get("moisture_std_mm")
        r_satellite = None
        if moisture_std_mm is not None:
            r_satellite = max(float(moisture_std_mm) ** 2, 4.0)

        inputs = get_estimator_inputs(
            field_geometry=None,
            date="1970-01-01",
            weather=weather,
            params=params,
        )
        inputs.update({
            "satellite_available": z_meas is not None,
            "ndvi_mean": satellite.get("ndvi", params.default_ndvi),
            "ndvi_std": satellite.get("ndvi_std"),
            "moisture_mean_mm": None if z_meas is None else float(z_meas),
            "moisture_std_mm": moisture_std_mm,
            "R_satellite": r_satellite,
        })
        return inputs

    def run_demo_for_crop(
        self,
        crop_name: str,
        soil_type: str = "loam",
        days: int = 10,
        auto_irrigate: bool = True,
    ):
        params = get_crop_params(crop_name, soil_type)
        ekf = self.create_filter(initial_soil_water_mm=110.0)

        history = []
        ndvi = params.default_ndvi
        irrigation_trigger_mm = params.theta_fc - params.depletion_fraction_p * (params.theta_fc - params.theta_wp)

        for day in range(1, days + 1):
            weather = dict(DEFAULT_WEATHER)
            weather["rain_mm"] = 0.0

            satellite = {
                "ndvi": ndvi,
                "z_meas": MEASUREMENT_SCHEDULE.get(day),
            }

            result = self.run_daily_step(
                ekf=ekf,
                params=params,
                weather=weather,
                satellite=satellite,
                auto_irrigate=auto_irrigate,
            )

            theta = result["x_upd"]
            history.append({
                "day": day,
                "crop": params.crop_name,
                "display_name": params.display_name,
                "soil_type": params.soil_type,
                "rain_mm": round(float(weather["rain_mm"]), 2),
                "ndvi": round(float(ndvi if result["ndvi_mean"] is None else result["ndvi_mean"]), 2),
                "et0_mm": round(result["et0_mm"], 2),
                "et0_std_mm": round(result["et0_std_mm"], 2),
                "irrigation_mm": round(result["irrigation_mm"], 2),
                "x_pred_mm": round(result["x_pred"], 2),
                "P_pred": round(result["P_pred"], 2),
                "measurement_mm": None if result["measurement_mm"] is None else round(result["measurement_mm"], 2),
                "moisture_std_mm": None if result["moisture_std_mm"] is None else round(result["moisture_std_mm"], 2),
                "satellite_available": result["satellite_available"],
                "updated": result["updated"],
                "soil_water_estimate_mm": round(theta, 2),
                "uncertainty": round(result["P_upd"], 2),
                "relative_available_water": round(relative_available_water(theta, params), 3),
                "stress_level": stress_level(theta, params),
                "kalman_gain": None if result["kalman_gain"] is None else round(result["kalman_gain"], 3),
                "innovation": None if result["innovation"] is None else round(result["innovation"], 2),
            })

        return {
            "crop": params.crop_name,
            "display_name": params.display_name,
            "soil_type": params.soil_type,
            "days": days,
            "auto_irrigate": auto_irrigate,
            "parameters": {
                "theta_fc_mm": round(params.theta_fc, 2),
                "theta_wp_mm": round(params.theta_wp, 2),
                "theta_max_mm": round(params.theta_max, 2),
                "irrigation_trigger_mm": round(irrigation_trigger_mm, 2),
                "max_irrigation_mm_day": round(params.max_irrigation_mm_day, 2),
            },
            "crop_parameters": {
                "kc_initial": round(params.kc_initial, 2),
                "kc_mid": round(params.kc_mid, 2),
                "kc_late": round(params.kc_late, 2),
                "depletion_fraction_p": round(params.depletion_fraction_p, 2),
                "root_depth_m": round(params.root_depth_m, 2),
                "default_ndvi": round(params.default_ndvi, 2),
                "notes": params.notes,
                "source_url": params.source_url,
            },
            "history": history,
            "final": history[-1] if history else None,
        }

    def run_all_crop_demo(self, days: int = 10, soil_type: str = "loam"):
        scenarios = [
            self.run_demo_for_crop(crop, soil_type=soil_type, days=days)
            for crop in DEFAULT_CROPS
        ]

        return {
            "title": "Skopje crop EKF demo with FAO-style crop coefficients",
            "unit_note": "All water depths are mm over the field surface/root zone, not mm^2.",
            "weather_assumption": "No rain for the demo period; ET0 is computed from fixed Skopje-like summer weather.",
            "method_note": "Crop Kc and depletion fraction p come from FAO-style crop defaults. Root-zone storage limits and irrigation control remain simplified estimator assumptions.",
            "available_crops": list_crop_parameters(),
            "available_soil_types": DEFAULT_SOIL_TYPES,
            "measurement_days": sorted(MEASUREMENT_SCHEDULE.keys()),
            "scenarios": scenarios,
        }


estimator_service = FarmEstimatorService()
