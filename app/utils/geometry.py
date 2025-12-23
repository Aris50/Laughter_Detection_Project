import numpy as np

def dist(p1, p2):
    """Euclidean distance between two 2D points."""
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))

def eye_aperture(upper, lower, left, right):
    """
    Normalized eye-opening:
    vertical distance / horizontal distance
    Used as proxy for AU6 (cheek raiser).
    """
    v = dist(upper, lower)
    h = dist(left, right)
    return v / h if h > 1e-6 else 0.0
