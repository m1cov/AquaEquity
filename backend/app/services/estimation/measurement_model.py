import numpy as np


def h_direct_soil_moisture(x: np.ndarray, params=None) -> np.ndarray:
    """Direct satellite soil-moisture measurement model: z = theta + noise."""
    return np.array([float(x[0])], dtype=float)


def H_direct_soil_moisture(x: np.ndarray, params=None) -> np.ndarray:
    return np.array([[1.0]], dtype=float)
