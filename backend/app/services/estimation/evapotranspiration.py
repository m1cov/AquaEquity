import math


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def saturation_vapor_pressure(temperature_c: float) -> float:
    """Saturation vapor pressure e^o(T) [kPa]."""
    return 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))


def mean_saturation_vapor_pressure(t_min_c: float, t_max_c: float) -> float:
    return 0.5 * (
        saturation_vapor_pressure(t_min_c) + saturation_vapor_pressure(t_max_c)
    )


def actual_vapor_pressure_from_rh(
    t_min_c: float,
    t_max_c: float,
    rh_min: float | None = None,
    rh_max: float | None = None,
    rh_mean: float | None = None,
) -> float:
    if rh_min is not None and rh_max is not None:
        e_tmin = saturation_vapor_pressure(t_min_c)
        e_tmax = saturation_vapor_pressure(t_max_c)
        return 0.5 * (e_tmin * rh_max / 100.0 + e_tmax * rh_min / 100.0)

    if rh_mean is not None:
        t_mean_c = 0.5 * (t_min_c + t_max_c)
        return saturation_vapor_pressure(t_mean_c) * rh_mean / 100.0

    raise ValueError("Need either rh_min/rh_max or rh_mean.")


def slope_saturation_vapor_pressure_curve(t_mean_c: float) -> float:
    e_t = saturation_vapor_pressure(t_mean_c)
    return (4098.0 * e_t) / ((t_mean_c + 237.3) ** 2)


def atmospheric_pressure_from_elevation(elevation_m: float) -> float:
    return 101.3 * (((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26)


def psychrometric_constant(elevation_m: float) -> float:
    return 0.000665 * atmospheric_pressure_from_elevation(elevation_m)


def fao56_penman_monteith_et0(
    t_mean_c: float,
    t_min_c: float,
    t_max_c: float,
    wind_speed_2m_m_s: float,
    elevation_m: float,
    net_radiation_mj_m2_day: float,
    soil_heat_flux_mj_m2_day: float = 0.0,
    rh_min: float | None = None,
    rh_max: float | None = None,
    rh_mean: float | None = None,
) -> float:
    """
    FAO-56 Penman-Monteith reference evapotranspiration ET0 [mm/day].
    """
    delta = slope_saturation_vapor_pressure_curve(t_mean_c)
    gamma = psychrometric_constant(elevation_m)
    es = mean_saturation_vapor_pressure(t_min_c, t_max_c)
    ea = actual_vapor_pressure_from_rh(t_min_c, t_max_c, rh_min, rh_max, rh_mean)

    numerator = (
        0.408 * delta * (net_radiation_mj_m2_day - soil_heat_flux_mj_m2_day)
        + gamma
        * (900.0 / (t_mean_c + 273.0))
        * wind_speed_2m_m_s
        * (es - ea)
    )
    denominator = delta + gamma * (1.0 + 0.34 * wind_speed_2m_m_s)

    return max(numerator / denominator, 0.0)


def compute_daily_et0_from_weather(weather: dict, site: dict) -> float:
    return fao56_penman_monteith_et0(
        t_mean_c=float(weather["T_mean_c"]),
        t_min_c=float(weather["T_min_c"]),
        t_max_c=float(weather["T_max_c"]),
        wind_speed_2m_m_s=float(weather["u2_m_s"]),
        elevation_m=float(site.get("elevation_m", 245.0)),
        net_radiation_mj_m2_day=float(weather.get("Rn_MJ_m2_day", 10.5)),
        soil_heat_flux_mj_m2_day=float(weather.get("G_MJ_m2_day", 0.0)),
        rh_min=weather.get("RH_min"),
        rh_max=weather.get("RH_max"),
        rh_mean=weather.get("RH_mean"),
    )
