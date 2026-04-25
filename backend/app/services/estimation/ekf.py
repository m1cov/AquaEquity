import numpy as np


class ExtendedKalmanFilter:
    """Small reusable EKF for the 1-state soil-water model."""

    def __init__(self, x0, P0, Q, R):
        self.x = np.array(x0, dtype=float)
        self.P = np.array(P0, dtype=float)
        self.Q = np.array(Q, dtype=float)
        self.R = np.array(R, dtype=float)

    def predict(self, f, F_jacobian, u: dict, params):
        F = F_jacobian(self.x, u, params)
        self.x = f(self.x, u, params)
        self.P = F @ self.P @ F.T + self.Q
        return self.x, self.P, F

    def update(self, z, h, H_jacobian, params=None):
        z = np.array(z, dtype=float)
        H = H_jacobian(self.x, params)
        z_pred = h(self.x, params)

        innovation = z - z_pred
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ innovation
        I = np.eye(self.P.shape[0])
        self.P = (I - K @ H) @ self.P

        return self.x, self.P, K, innovation, S
