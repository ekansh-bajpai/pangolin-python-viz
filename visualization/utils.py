from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
from OpenGL.GL import *


ArrayLike = Union[np.ndarray, Sequence[float]]
ColorLike = Union[
    Tuple[float, float, float],
    Tuple[float, float, float, float],
]


def as_color(color: ColorLike) -> Tuple[float, float, float, float]:
    """
    Convert RGB or RGBA color into RGBA.

    Parameters
    ----------
    color:
        Tuple/list with 3 or 4 values in range [0, 1].

    Returns
    -------
    tuple
        RGBA color tuple.
    """
    if len(color) == 3:
        return float(color[0]), float(color[1]), float(color[2]), 1.0

    if len(color) == 4:
        return (
            float(color[0]),
            float(color[1]),
            float(color[2]),
            float(color[3]),
        )

    raise ValueError("Color must be RGB or RGBA")


def ensure_vec3(value: ArrayLike, name: str = "vector") -> np.ndarray:
    """
    Ensure value is a 3D vector.

    Parameters
    ----------
    value:
        Input array-like object.
    name:
        Name used in error messages.

    Returns
    -------
    np.ndarray
        Shape `(3,)`.
    """
    arr = np.asarray(value, dtype=np.float64).reshape(-1)

    if arr.shape[0] != 3:
        raise ValueError(f"{name} must have exactly 3 elements")

    return arr


def ensure_points(points: ArrayLike, name: str = "points") -> np.ndarray:
    """
    Ensure input points are an Nx3 array.

    Parameters
    ----------
    points:
        Input points.
    name:
        Name used in error messages.

    Returns
    -------
    np.ndarray
        Shape `(N, 3)`.
    """
    arr = np.asarray(points, dtype=np.float64)

    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape Nx3")

    return arr


def ensure_pose(pose: ArrayLike, name: str = "pose") -> np.ndarray:
    """
    Ensure pose is a 4x4 homogeneous matrix.

    Parameters
    ----------
    pose:
        Input pose.
    name:
        Name used in error messages.

    Returns
    -------
    np.ndarray
        Shape `(4, 4)`.
    """
    arr = np.asarray(pose, dtype=np.float64)

    if arr.shape != (4, 4):
        raise ValueError(f"{name} must have shape 4x4")

    return arr


def pose_from_position_orientation(
    position: ArrayLike,
    orientation: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Create a 4x4 pose from position and optional 3x3 orientation.

    Parameters
    ----------
    position:
        3D translation vector.
    orientation:
        Optional 3x3 rotation matrix. If None, identity is used.

    Returns
    -------
    np.ndarray
        4x4 homogeneous transformation matrix.
    """
    position = ensure_vec3(position, "position")

    T = np.eye(4, dtype=np.float64)
    T[:3, 3] = position

    if orientation is not None:
        orientation = np.asarray(orientation, dtype=np.float64)

        if orientation.shape != (3, 3):
            raise ValueError("orientation must have shape 3x3")

        T[:3, :3] = orientation

    return T


def set_gl_color(color: ColorLike) -> None:
    """
    Set OpenGL color from RGB/RGBA tuple.
    """
    r, g, b, a = as_color(color)
    glColor4f(r, g, b, a)


def draw_line(
    p1: ArrayLike,
    p2: ArrayLike,
    color: ColorLike,
    line_width: float = 1.0,
) -> None:
    """
    Draw one OpenGL line segment.

    Parameters
    ----------
    p1:
        Start point.
    p2:
        End point.
    color:
        RGB/RGBA line color.
    line_width:
        OpenGL line width.
    """
    p1 = ensure_vec3(p1, "p1")
    p2 = ensure_vec3(p2, "p2")

    set_gl_color(color)
    glLineWidth(float(line_width))

    glBegin(GL_LINES)
    glVertex3d(float(p1[0]), float(p1[1]), float(p1[2]))
    glVertex3d(float(p2[0]), float(p2[1]), float(p2[2]))
    glEnd()


def load_tum_trajectory(path: str) -> List[np.ndarray]:
    """
    Load a TUM-style trajectory file.

    Expected format:

    ```text
    timestamp tx ty tz qx qy qz qw
    ```

    Parameters
    ----------
    path:
        Path to trajectory file.

    Returns
    -------
    list[np.ndarray]
        List of 4x4 poses.
    """
    from scipy.spatial.transform import Rotation as R

    poses: List[np.ndarray] = []

    with open(path, "r") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) < 8:
                continue

            tx, ty, tz = map(float, parts[1:4])
            qx, qy, qz, qw = map(float, parts[4:8])

            T = np.eye(4, dtype=np.float64)
            T[:3, :3] = R.from_quat([qx, qy, qz, qw]).as_matrix()
            T[:3, 3] = np.array([tx, ty, tz], dtype=np.float64)

            poses.append(T)

    return poses