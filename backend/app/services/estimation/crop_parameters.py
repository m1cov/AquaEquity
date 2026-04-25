from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CropParameters:
    """FAO-style crop metadata used to tune the estimator for regional crops."""

    key: str
    display_name: str
    kc_initial: float
    kc_mid: float
    kc_late: float
    depletion_fraction_p: float
    root_depth_m: float
    default_ndvi: float
    notes: str
    source_url: str


CROP_PARAMETERS = {
    "wheat": CropParameters(
        key="wheat",
        display_name="Wheat",
        kc_initial=0.40,
        kc_mid=1.15,
        kc_late=0.25,
        depletion_fraction_p=0.55,
        root_depth_m=1.40,
        default_ndvi=0.60,
        notes="Good default for winter or spring wheat around Skopje.",
        source_url="https://www.fao.org/land-water/databases-and-software/crop-information/wheat/es/",
    ),
    "maize": CropParameters(
        key="maize",
        display_name="Corn",
        kc_initial=0.30,
        kc_mid=1.20,
        kc_late=0.60,
        depletion_fraction_p=0.55,
        root_depth_m=1.00,
        default_ndvi=0.68,
        notes="Good default for summer maize or corn with high water demand in mid-season.",
        source_url="https://www.fao.org/land-water/databases-and-software/crop-information/maize/en/",
    ),
    "tomato": CropParameters(
        key="tomato",
        display_name="Tomato",
        kc_initial=0.60,
        kc_mid=1.15,
        kc_late=0.80,
        depletion_fraction_p=0.45,
        root_depth_m=1.00,
        default_ndvi=0.72,
        notes="Tomato is more sensitive to water stress, so p is lower.",
        source_url="https://www.fao.org/land-water/databases-and-software/crop-information/tomato/en/",
    ),
}

CROP_ALIASES = {
    "tomatoes": "tomato",
    "corn": "maize",
}

DEFAULT_CROPS = ["tomato", "wheat", "maize"]


def normalize_crop_name(crop_name: str) -> str:
    key = crop_name.strip().lower()
    return CROP_ALIASES.get(key, key)


def get_crop_parameters(crop_name: str) -> CropParameters:
    key = normalize_crop_name(crop_name)

    if key not in CROP_PARAMETERS:
        raise ValueError(
            f"Unknown crop '{crop_name}'. Available crops: {', '.join(DEFAULT_CROPS)}"
        )

    return CROP_PARAMETERS[key]


def list_crop_parameters() -> list[dict]:
    return [asdict(CROP_PARAMETERS[key]) for key in DEFAULT_CROPS]


def get_kc_for_stage(crop_name: str, stage: str) -> float:
    crop = get_crop_parameters(crop_name)
    stage_key = stage.strip().lower()

    if stage_key in {"initial", "early"}:
        return crop.kc_initial
    if stage_key in {"mid", "middle", "midseason", "mid-season"}:
        return crop.kc_mid
    if stage_key in {"late", "end"}:
        return crop.kc_late

    raise ValueError("Stage must be one of: initial, mid, late")


def irrigation_trigger(theta_fc: float, theta_wp: float, crop_name: str) -> float:
    """Returns the root-zone water storage threshold below which irrigation should start."""

    crop = get_crop_parameters(crop_name)
    return theta_fc - crop.depletion_fraction_p * (theta_fc - theta_wp)


def is_crop_stressed(theta: float, theta_fc: float, theta_wp: float, crop_name: str) -> bool:
    return theta < irrigation_trigger(theta_fc=theta_fc, theta_wp=theta_wp, crop_name=crop_name)
