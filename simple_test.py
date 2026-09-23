"""
modular_pangolin_visualizer.py

A modular Pangolin/OpenGL visualization framework.

Features:
- Multiple independent visualizer windows/instances
- Scene/object based design
- Custom drawable objects
- Trajectories from 4x4 poses or 3D positions
- Point clouds / landmarks
- Grids
- Coordinate axes
- Spheres
- Camera frustums
- Image saving

Dependencies:
    pip install numpy PyOpenGL PyOpenGL_accelerate scipy opencv-python
    pypangolin must be installed separately according to your platform.

Example:
    python modular_pangolin_visualizer.py
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union, Any

import numpy as np
import pypangolin as pango
from OpenGL.GL import *
import OpenGL.GLUT as glut


ArrayLike = Union[np.ndarray, Sequence[float]]
ColorLike = Union[Tuple[float, float, float], Tuple[float, float, float, float]]


# =============================================================================
# Utility Functions
# =============================================================================

def as_color(color: ColorLike) -> Tuple[float, float, float, float]:
    """
    Converts RGB/RGBA color into RGBA.

    Parameters
    ----------
    color:
        Tuple/list of length 3 or 4.

    Returns
    -------
    tuple
        RGBA color.
    """
    if len(color) == 3:
        return float(color[0]), float(color[1]), float(color[2]), 1.0
    if len(color) == 4:
        return float(color[0]), float(color[1]), float(color[2]), float(color[3])
    raise ValueError("Color must be RGB or RGBA")


def ensure_vec3(value: ArrayLike, name: str = "vector") -> np.ndarray:
    """
    Ensures an input is a 3D vector.
    """
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.shape[0] != 3:
        raise ValueError(f"{name} must have exactly 3 elements")
    return arr


def ensure_points(points: ArrayLike, name: str = "points") -> np.ndarray:
    """
    Ensures an input is an Nx3 array.
    """
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape Nx3")
    return arr


def ensure_pose(pose: ArrayLike, name: str = "pose") -> np.ndarray:
    """
    Ensures an input is a valid 4x4 homogeneous transformation matrix.
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
    Creates a 4x4 pose from position and optional 3x3 orientation.

    Parameters
    ----------
    position:
        3D translation vector.
    orientation:
        3x3 rotation matrix. If None, identity is used.
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
    Sets OpenGL RGBA color.
    """
    r, g, b, a = as_color(color)
    glColor4f(r, g, b, a)


def draw_line(p1: ArrayLike, p2: ArrayLike, color: ColorLike, line_width: float = 1.0) -> None:
    """
    Draws one OpenGL line segment.
    """
    p1 = ensure_vec3(p1, "p1")
    p2 = ensure_vec3(p2, "p2")

    set_gl_color(color)
    glLineWidth(float(line_width))

    glBegin(GL_LINES)
    glVertex3d(float(p1[0]), float(p1[1]), float(p1[2]))
    glVertex3d(float(p2[0]), float(p2[1]), float(p2[2]))
    glEnd()


# =============================================================================
# Base Drawable
# =============================================================================

class Drawable(ABC):
    """
    Base class for all drawable objects.

    Every drawable has common runtime properties:
    - name
    - visibility
    - color
    - line width
    - point size
    - arbitrary custom properties dictionary
    """

    def __init__(
        self,
        name: Optional[str] = None,
        visible: bool = True,
        color: ColorLike = (1.0, 1.0, 1.0, 1.0),
        line_width: float = 1.0,
        point_size: float = 3.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.visible = visible
        self.color = color
        self.line_width = float(line_width)
        self.point_size = float(point_size)
        self.properties: Dict[str, Any] = properties or {}

    @abstractmethod
    def draw(self) -> None:
        """
        Draw object. Must be implemented by subclasses.
        """
        raise NotImplementedError

    def set_visible(self, visible: bool) -> "Drawable":
        self.visible = bool(visible)
        return self

    def show(self) -> "Drawable":
        self.visible = True
        return self

    def hide(self) -> "Drawable":
        self.visible = False
        return self

    def set_color(self, color: ColorLike) -> "Drawable":
        self.color = color
        return self

    def set_line_width(self, width: float) -> "Drawable":
        self.line_width = float(width)
        return self

    def set_point_size(self, size: float) -> "Drawable":
        self.point_size = float(size)
        return self

    def set_property(self, key: str, value: Any) -> "Drawable":
        self.properties[key] = value
        return self

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)


# =============================================================================
# Grid
# =============================================================================

class Grid(Drawable):
    """
    Draws a configurable 3D grid on XY/XZ/YZ planes.

    By default, the grid starts at origin and extends positively by `size`.
    Set centered=True to create a grid centered around origin.
    """

    def __init__(
        self,
        size: float = 2.0,
        step: float = 0.1,
        origin: ArrayLike = (0.0, 0.0, 0.0),
        centered: bool = False,
        draw_xy: bool = True,
        draw_xz: bool = False,
        draw_yz: bool = False,
        color: ColorLike = (0.5, 0.5, 0.5, 1.0),
        line_width: float = 1.0,
        visible: bool = True,
        name: str = "grid",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
            line_width=line_width,
        )

        if step <= 0:
            raise ValueError("step must be positive")
        if size <= 0:
            raise ValueError("size must be positive")

        self.size = float(size)
        self.step = float(step)
        self.origin = ensure_vec3(origin, "origin")
        self.centered = bool(centered)

        self.draw_xy = bool(draw_xy)
        self.draw_xz = bool(draw_xz)
        self.draw_yz = bool(draw_yz)

    def draw(self) -> None:
        if not self.visible:
            return

        set_gl_color(self.color)
        glLineWidth(self.line_width)

        ox, oy, oz = self.origin

        if self.centered:
            start = -self.size / 2.0
            end = self.size / 2.0
        else:
            start = 0.0
            end = self.size

        values = np.arange(start, end + self.step * 0.5, self.step)

        glBegin(GL_LINES)

        for v in values:
            # XY plane, z fixed
            if self.draw_xy:
                glVertex3d(ox + v, oy + start, oz)
                glVertex3d(ox + v, oy + end, oz)

                glVertex3d(ox + start, oy + v, oz)
                glVertex3d(ox + end, oy + v, oz)

            # XZ plane, y fixed
            if self.draw_xz:
                glVertex3d(ox + v, oy, oz + start)
                glVertex3d(ox + v, oy, oz + end)

                glVertex3d(ox + start, oy, oz + v)
                glVertex3d(ox + end, oy, oz + v)

            # YZ plane, x fixed
            if self.draw_yz:
                glVertex3d(ox, oy + v, oz + start)
                glVertex3d(ox, oy + v, oz + end)

                glVertex3d(ox, oy + start, oz + v)
                glVertex3d(ox, oy + end, oz + v)

        glEnd()


# =============================================================================
# Axis
# =============================================================================

class Axis(Drawable):
    """
    Draws coordinate axes for a given pose.

    Color convention:
    - X: Red
    - Y: Green
    - Z: Blue
    """

    def __init__(
        self,
        pose: Optional[ArrayLike] = None,
        scale: float = 1.0,
        line_width: float = 2.0,
        visible: bool = True,
        name: str = "axis",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=(1.0, 1.0, 1.0, 1.0),
            line_width=line_width,
        )

        self.pose = np.eye(4, dtype=np.float64) if pose is None else ensure_pose(pose)
        self.scale = float(scale)

    def set_pose(self, pose: ArrayLike) -> "Axis":
        self.pose = ensure_pose(pose)
        return self

    def set_scale(self, scale: float) -> "Axis":
        self.scale = float(scale)
        return self

    def draw(self) -> None:
        if not self.visible:
            return

        pose = self.pose
        origin = pose[:3, 3]

        x_end = pose @ np.array([self.scale, 0.0, 0.0, 1.0])
        y_end = pose @ np.array([0.0, self.scale, 0.0, 1.0])
        z_end = pose @ np.array([0.0, 0.0, self.scale, 1.0])

        glLineWidth(self.line_width)

        glBegin(GL_LINES)

        # X axis
        glColor3f(1.0, 0.0, 0.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(x_end[0], x_end[1], x_end[2])

        # Y axis
        glColor3f(0.0, 1.0, 0.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(y_end[0], y_end[1], y_end[2])

        # Z axis
        glColor3f(0.0, 0.0, 1.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(z_end[0], z_end[1], z_end[2])

        glEnd()


# =============================================================================
# Trajectory
# =============================================================================

class Trajectory(Drawable):
    """
    Draws a trajectory from:
    - list of 4x4 poses
    - list of 3D positions

    If 4x4 poses are provided, the latest pose axis can also be drawn.
    """

    def __init__(
        self,
        poses: Optional[Iterable[ArrayLike]] = None,
        positions: Optional[Iterable[ArrayLike]] = None,
        color: ColorLike = (1.0, 0.0, 0.0, 1.0),
        line_width: float = 2.0,
        draw_latest_axis: bool = True,
        axis_scale: float = 0.1,
        visible: bool = True,
        name: str = "trajectory",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
            line_width=line_width,
        )

        self.poses: List[np.ndarray] = []
        self.positions: List[np.ndarray] = []

        self.draw_latest_axis = bool(draw_latest_axis)
        self.axis_scale = float(axis_scale)

        if poses is not None:
            self.set_poses(poses)
        elif positions is not None:
            self.set_positions(positions)

    def set_poses(self, poses: Iterable[ArrayLike]) -> "Trajectory":
        self.poses = [ensure_pose(T).copy() for T in poses]
        self.positions = [T[:3, 3].copy() for T in self.poses]
        return self

    def set_positions(self, positions: Iterable[ArrayLike]) -> "Trajectory":
        self.positions = [ensure_vec3(p, "position").copy() for p in positions]
        self.poses = []
        return self

    def append_pose(self, pose: ArrayLike) -> "Trajectory":
        T = ensure_pose(pose).copy()
        self.poses.append(T)
        self.positions.append(T[:3, 3].copy())
        return self

    def append_position(self, position: ArrayLike) -> "Trajectory":
        p = ensure_vec3(position, "position").copy()
        self.positions.append(p)
        return self

    def clear(self) -> "Trajectory":
        self.poses.clear()
        self.positions.clear()
        return self

    def latest_pose(self) -> Optional[np.ndarray]:
        if not self.poses:
            return None
        return self.poses[-1]

    def latest_position(self) -> Optional[np.ndarray]:
        if not self.positions:
            return None
        return self.positions[-1]

    def draw(self) -> None:
        if not self.visible:
            return

        if len(self.positions) >= 2:
            set_gl_color(self.color)
            glLineWidth(self.line_width)

            glBegin(GL_LINES)
            for p1, p2 in zip(self.positions[:-1], self.positions[1:]):
                glVertex3d(float(p1[0]), float(p1[1]), float(p1[2]))
                glVertex3d(float(p2[0]), float(p2[1]), float(p2[2]))
            glEnd()

        if self.draw_latest_axis and len(self.poses) > 0:
            Axis(
                pose=self.poses[-1],
                scale=self.axis_scale,
                line_width=self.line_width,
                visible=True,
            ).draw()


# =============================================================================
# Point Cloud / Landmarks
# =============================================================================

class PointCloud(Drawable):
    """
    Draws Nx3 points.

    Supports either one color for all points, or Nx3/Nx4 per-point colors
    using manual OpenGL drawing.
    """

    def __init__(
        self,
        points: Optional[ArrayLike] = None,
        colors: Optional[np.ndarray] = None,
        color: ColorLike = (0.0, 1.0, 0.0, 1.0),
        point_size: float = 5.0,
        visible: bool = True,
        name: str = "point_cloud",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
            point_size=point_size,
        )

        self.points = np.empty((0, 3), dtype=np.float64)
        self.colors: Optional[np.ndarray] = None

        if points is not None:
            self.set_points(points, colors=colors)

    def set_points(
        self,
        points: ArrayLike,
        colors: Optional[np.ndarray] = None,
    ) -> "PointCloud":
        self.points = ensure_points(points)

        if colors is not None:
            colors = np.asarray(colors, dtype=np.float64)
            if colors.ndim != 2 or colors.shape[0] != self.points.shape[0] or colors.shape[1] not in (3, 4):
                raise ValueError("colors must have shape Nx3 or Nx4 and match points count")
            self.colors = colors
        else:
            self.colors = None

        return self

    def append_points(
        self,
        points: ArrayLike,
        colors: Optional[np.ndarray] = None,
    ) -> "PointCloud":
        points = ensure_points(points)

        if self.points.size == 0:
            return self.set_points(points, colors=colors)

        self.points = np.vstack([self.points, points])

        if colors is not None:
            colors = np.asarray(colors, dtype=np.float64)
            if colors.ndim != 2 or colors.shape[0] != points.shape[0] or colors.shape[1] not in (3, 4):
                raise ValueError("colors must have shape Nx3 or Nx4 and match new points count")

            if self.colors is None:
                base = np.tile(np.asarray(as_color(self.color)), (self.points.shape[0] - points.shape[0], 1))
                self.colors = np.vstack([base, colors if colors.shape[1] == 4 else np.c_[colors, np.ones(colors.shape[0])]])
            else:
                if colors.shape[1] == 3:
                    colors = np.c_[colors, np.ones(colors.shape[0])]
                if self.colors.shape[1] == 3:
                    self.colors = np.c_[self.colors, np.ones(self.colors.shape[0])]
                self.colors = np.vstack([self.colors, colors])

        return self

    def clear(self) -> "PointCloud":
        self.points = np.empty((0, 3), dtype=np.float64)
        self.colors = None
        return self

    def draw(self) -> None:
        if not self.visible or self.points.size == 0:
            return

        glPointSize(self.point_size)

        if self.colors is None:
            set_gl_color(self.color)
            pango.glDrawPoints(self.points)
            return

        glBegin(GL_POINTS)
        for p, c in zip(self.points, self.colors):
            if c.shape[0] == 3:
                glColor3f(float(c[0]), float(c[1]), float(c[2]))
            else:
                glColor4f(float(c[0]), float(c[1]), float(c[2]), float(c[3]))
            glVertex3d(float(p[0]), float(p[1]), float(p[2]))
        glEnd()


# =============================================================================
# Sphere
# =============================================================================

class Sphere(Drawable):
    """
    Draws a solid sphere.
    """

    def __init__(
        self,
        position: ArrayLike = (0.0, 0.0, 0.0),
        radius: float = 0.05,
        color: ColorLike = (0.0, 0.0, 1.0, 1.0),
        slices: int = 20,
        stacks: int = 20,
        visible: bool = True,
        name: str = "sphere",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
        )

        self.position = ensure_vec3(position, "position")
        self.radius = float(radius)
        self.slices = int(slices)
        self.stacks = int(stacks)

    def set_position(self, position: ArrayLike) -> "Sphere":
        self.position = ensure_vec3(position, "position")
        return self

    def set_radius(self, radius: float) -> "Sphere":
        self.radius = float(radius)
        return self

    def draw(self) -> None:
        if not self.visible:
            return

        set_gl_color(self.color)

        glPushMatrix()
        glTranslatef(
            float(self.position[0]),
            float(self.position[1]),
            float(self.position[2]),
        )
        glut.glutSolidSphere(
            self.radius,
            self.slices,
            self.stacks,
        )
        glPopMatrix()


# =============================================================================
# Camera Frustum
# =============================================================================

class CameraFrustum(Drawable):
    """
    Draws a simple camera frustum from a 4x4 pose.
    """

    def __init__(
        self,
        pose: Optional[ArrayLike] = None,
        scale: float = 0.2,
        color: ColorLike = (0.0, 0.0, 1.0, 1.0),
        line_width: float = 1.5,
        visible: bool = True,
        name: str = "camera_frustum",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
            line_width=line_width,
        )

        self.pose = np.eye(4, dtype=np.float64) if pose is None else ensure_pose(pose)
        self.scale = float(scale)

    def set_pose(self, pose: ArrayLike) -> "CameraFrustum":
        self.pose = ensure_pose(pose)
        return self

    def draw(self) -> None:
        if not self.visible:
            return

        s = self.scale

        # Camera local coordinates
        corners = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [s, s * 0.6, s, 1.0],
                [s, -s * 0.6, s, 1.0],
                [-s, -s * 0.6, s, 1.0],
                [-s, s * 0.6, s, 1.0],
            ],
            dtype=np.float64,
        )

        world = (self.pose @ corners.T).T[:, :3]

        o = world[0]
        c1, c2, c3, c4 = world[1], world[2], world[3], world[4]

        set_gl_color(self.color)
        glLineWidth(self.line_width)

        glBegin(GL_LINES)

        # Rays
        for c in [c1, c2, c3, c4]:
            glVertex3d(o[0], o[1], o[2])
            glVertex3d(c[0], c[1], c[2])

        # Image plane rectangle
        pairs = [(c1, c2), (c2, c3), (c3, c4), (c4, c1)]
        for a, b in pairs:
            glVertex3d(a[0], a[1], a[2])
            glVertex3d(b[0], b[1], b[2])

        glEnd()


# =============================================================================
# Custom Drawable
# =============================================================================

class CustomDrawable(Drawable):
    """
    Generic callback-based drawable.

    The callback receives this object as argument.

    Example
    -------
    def draw_triangle(obj):
        set_gl_color(obj.color)
        glBegin(GL_TRIANGLES)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        glVertex3f(0, 1, 0)
        glEnd()

    triangle = CustomDrawable(draw_triangle, color=(1, 0, 0))
    """

    def __init__(
        self,
        draw_callback: Callable[["CustomDrawable"], None],
        name: str = "custom",
        visible: bool = True,
        color: ColorLike = (1.0, 1.0, 1.0, 1.0),
        line_width: float = 1.0,
        point_size: float = 3.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=color,
            line_width=line_width,
            point_size=point_size,
            properties=properties,
        )

        self.draw_callback = draw_callback

    def draw(self) -> None:
        if not self.visible:
            return

        self.draw_callback(self)


# =============================================================================
# Scene
# =============================================================================

class Scene:
    """
    Container for drawable objects.
    """

    def __init__(self) -> None:
        self.objects: Dict[str, Drawable] = {}
        self.draw_order: List[str] = []

    def add(self, obj: Drawable, name: Optional[str] = None, replace: bool = True) -> Drawable:
        object_name = name or obj.name

        if object_name is None:
            object_name = f"object_{len(self.objects)}"

        if not replace and object_name in self.objects:
            raise KeyError(f"Object '{object_name}' already exists")

        obj.name = object_name

        if object_name not in self.objects:
            self.draw_order.append(object_name)

        self.objects[object_name] = obj
        return obj

    def remove(self, name: str) -> None:
        if name in self.objects:
            del self.objects[name]
        if name in self.draw_order:
            self.draw_order.remove(name)

    def get(self, name: str) -> Optional[Drawable]:
        return self.objects.get(name)

    def require(self, name: str) -> Drawable:
        obj = self.get(name)
        if obj is None:
            raise KeyError(f"Object '{name}' does not exist")
        return obj

    def clear(self) -> None:
        self.objects.clear()
        self.draw_order.clear()

    def names(self) -> List[str]:
        return list(self.draw_order)

    def set_visible(self, name: str, visible: bool) -> None:
        self.require(name).set_visible(visible)

    def draw(self) -> None:
        for name in self.draw_order:
            obj = self.objects.get(name)
            if obj is not None:
                obj.draw()


# =============================================================================
# Pangolin Visualizer
# =============================================================================

class PangolinVisualizer:
    """
    Modular Pangolin visualizer window.

    Each instance owns:
    - one Pangolin window
    - one scene
    - one 3D camera/display
    """

    def __init__(
        self,
        title: str = "Pangolin Visualizer",
        width: int = 1280,
        height: int = 720,
        fx: float = 420.0,
        fy: float = 420.0,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
        near: float = 0.1,
        far: float = 1000.0,
        camera_eye: ArrayLike = (0.0, 0.0, 3.0),
        camera_target: ArrayLike = (0.0, 0.0, 0.0),
        camera_up=pango.AxisY,
        background_color: ColorLike = (1.0, 1.0, 1.0, 1.0),
        enable_depth_test: bool = True,
        initialize_glut: bool = True,
    ) -> None:
        self.title = title
        self.width = int(width)
        self.height = int(height)
        self.background_color = as_color(background_color)

        self.scene = Scene()

        if initialize_glut:
            try:
                glut.glutInit()
            except Exception:
                pass

        self.window = pango.CreateWindowAndBind(
            self.title,
            self.width,
            self.height,
        )

        if enable_depth_test:
            glEnable(GL_DEPTH_TEST)

        cx = self.width / 2.0 if cx is None else float(cx)
        cy = self.height / 2.0 if cy is None else float(cy)

        self.projection = pango.ProjectionMatrix(
            self.width,
            self.height,
            float(fx),
            float(fy),
            cx,
            cy,
            float(near),
            float(far),
        )

        camera_eye = ensure_vec3(camera_eye, "camera_eye")
        camera_target = ensure_vec3(camera_target, "camera_target")

        self.model_view = pango.ModelViewLookAt(
            camera_eye[0],
            camera_eye[1],
            camera_eye[2],
            camera_target[0],
            camera_target[1],
            camera_target[2],
            camera_up,
        )

        self.render_state = pango.OpenGlRenderState(
            self.projection,
            self.model_view,
        )

        self.handler = pango.Handler3D(self.render_state)

        self.display = (
            pango.CreateDisplay()
            .SetBounds(
                pango.Attach(0),
                pango.Attach(1),
                pango.Attach(0),
                pango.Attach(1),
                -float(self.width) / float(self.height),
            )
            .SetHandler(self.handler)
        )

    # -------------------------------------------------------------------------
    # Scene API
    # -------------------------------------------------------------------------

    def add(self, obj: Drawable, name: Optional[str] = None, replace: bool = True) -> Drawable:
        return self.scene.add(obj, name=name, replace=replace)

    def remove(self, name: str) -> None:
        self.scene.remove(name)

    def get(self, name: str) -> Optional[Drawable]:
        return self.scene.get(name)

    def require(self, name: str) -> Drawable:
        return self.scene.require(name)

    def clear_scene(self) -> None:
        self.scene.clear()

    # -------------------------------------------------------------------------
    # Convenience Object Creation
    # -------------------------------------------------------------------------

    def add_grid(self, name: str = "grid", **kwargs) -> Grid:
        obj = Grid(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_axis(self, name: str = "axis", **kwargs) -> Axis:
        obj = Axis(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_trajectory(self, name: str = "trajectory", **kwargs) -> Trajectory:
        obj = Trajectory(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_point_cloud(self, name: str = "point_cloud", **kwargs) -> PointCloud:
        obj = PointCloud(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_sphere(self, name: str = "sphere", **kwargs) -> Sphere:
        obj = Sphere(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_camera_frustum(self, name: str = "camera_frustum", **kwargs) -> CameraFrustum:
        obj = CameraFrustum(name=name, **kwargs)
        self.add(obj, name=name)
        return obj

    def add_custom(
        self,
        draw_callback: Callable[[CustomDrawable], None],
        name: str = "custom",
        **kwargs,
    ) -> CustomDrawable:
        obj = CustomDrawable(
            draw_callback=draw_callback,
            name=name,
            **kwargs,
        )
        self.add(obj, name=name)
        return obj

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def should_quit(self) -> bool:
        return bool(pango.ShouldQuit())

    def render(self, finish_frame: bool = True) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        r, g, b, a = self.background_color
        glClearColor(r, g, b, a)

        self.display.Activate(self.render_state)
        self.scene.draw()

        if finish_frame:
            pango.FinishFrame()

    def spin(self, target_fps: Optional[float] = None) -> None:
        """
        Blocking render loop.

        Parameters
        ----------
        target_fps:
            If provided, sleeps to approximately limit FPS.
        """
        dt = None if target_fps is None else 1.0 / float(target_fps)

        while not self.should_quit():
            t0 = time.time()
            self.render()

            if dt is not None:
                elapsed = time.time() - t0
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    # -------------------------------------------------------------------------
    # Save Screenshot
    # -------------------------------------------------------------------------

    def save_image(self, filename: str) -> None:
        """
        Saves current back buffer to image using OpenCV.
        """
        bounds = self.display.GetBounds()

        width = int(bounds.w)
        height = int(bounds.h)

        buffer = np.empty((height, width, 4), dtype=np.uint8)

        glReadBuffer(GL_BACK)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)

        glReadPixels(
            int(bounds.l),
            int(bounds.b),
            width,
            height,
            GL_BGRA,
            GL_UNSIGNED_BYTE,
            buffer,
        )

        try:
            import cv2
        except ImportError as exc:
            raise ImportError("opencv-python is required for save_image()") from exc

        cv2.imwrite(filename, buffer)


# =============================================================================
# Trajectory File Loader
# =============================================================================

def load_tum_trajectory(path: str) -> List[np.ndarray]:
    """
    Loads a TUM-style trajectory file:

        timestamp tx ty tz qx qy qz qw

    Returns
    -------
    list of 4x4 numpy arrays
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


# =============================================================================
# Example Main
# =============================================================================

def example_custom_triangle(obj: CustomDrawable) -> None:
    """
    Example callback object.
    """
    set_gl_color(obj.color)
    glLineWidth(obj.line_width)

    scale = float(obj.properties.get("scale", 1.0))
    z = float(obj.properties.get("z", 0.0))

    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, 0.0, z)
    glVertex3f(scale, 0.0, z)
    glVertex3f(0.5 * scale, 0.75 * scale, z)
    glEnd()


def main() -> None:
    """
    Demonstration.

    If 'trajectory.txt' exists, it is loaded as a TUM trajectory:
        timestamp tx ty tz qx qy qz qw

    Otherwise an artificial trajectory is generated.
    """

    viz = PangolinVisualizer(
        title="Modular Pangolin Visualizer",
        width=1280,
        height=720,
        fx=420,
        fy=420,
        camera_eye=(0.0, -3.0, 2.0),
        camera_target=(0.0, 0.0, 0.0),
        camera_up=pango.AxisZ,
        background_color=(1.0, 1.0, 1.0, 1.0),
    )

    # Static objects
    viz.add_axis(
        name="world_axis",
        scale=0.5,
        line_width=2.5,
    )

    viz.add_grid(
        name="xy_grid",
        size=4.0,
        step=0.2,
        centered=True,
        draw_xy=True,
        draw_xz=False,
        draw_yz=False,
        color=(0.75, 0.75, 0.75, 1.0),
        line_width=1.0,
    )

    # Dynamic objects
    est_traj = viz.add_trajectory(
        name="estimated_trajectory",
        color=(1.0, 0.0, 0.0, 1.0),
        line_width=2.0,
        draw_latest_axis=True,
        axis_scale=0.15,
    )

    gt_traj = viz.add_trajectory(
        name="ground_truth_trajectory",
        color=(0.0, 0.7, 0.0, 1.0),
        line_width=2.0,
        draw_latest_axis=False,
        axis_scale=0.15,
    )

    landmarks = viz.add_point_cloud(
        name="landmarks",
        color=(0.0, 0.5, 1.0, 1.0),
        point_size=4.0,
    )

    moving_sphere = viz.add_sphere(
        name="moving_sphere",
        position=(0.0, 0.0, 0.0),
        radius=0.04,
        color=(1.0, 0.3, 0.0, 1.0),
    )

    camera_frustum = viz.add_camera_frustum(
        name="latest_camera_frustum",
        scale=0.12,
        color=(0.1, 0.1, 1.0, 1.0),
        line_width=1.5,
    )

    viz.add_custom(
        draw_callback=example_custom_triangle,
        name="custom_triangle",
        color=(1.0, 0.7, 0.0, 0.8),
        properties={"scale": 0.25, "z": 0.05},
    )

    # Load or generate trajectory
    try:
        poses = load_tum_trajectory("trajectory.txt")
        print(f"Loaded {len(poses)} poses from trajectory.txt")
    except FileNotFoundError:
        print("trajectory.txt not found. Generating artificial trajectory.")

        poses = []
        for i in range(300):
            t = i * 0.03
            x = 1.0 * np.cos(t)
            y = 1.0 * np.sin(t)
            z = 0.2 * np.sin(2.0 * t)

            T = np.eye(4, dtype=np.float64)
            T[:3, 3] = [x, y, z]

            # Simple yaw orientation
            yaw = t + np.pi / 2.0
            c, s = np.cos(yaw), np.sin(yaw)
            T[:3, :3] = np.array(
                [
                    [c, -s, 0.0],
                    [s, c, 0.0],
                    [0.0, 0.0, 1.0],
                ],
                dtype=np.float64,
            )

            poses.append(T)

    # Some random landmarks
    np.random.seed(0)
    pts = np.random.uniform(low=-1.5, high=1.5, size=(300, 3))
    pts[:, 2] *= 0.25
    landmarks.set_points(pts)

    # Animate trajectory
    for i, T in enumerate(poses):
        if viz.should_quit():
            return

        est_traj.append_pose(T)

        # Fake GT offset example
        T_gt = T.copy()
        T_gt[:3, 3] += np.array([0.05, -0.05, 0.0])
        gt_traj.append_pose(T_gt)

        moving_sphere.set_position(T[:3, 3])
        camera_frustum.set_pose(T)

        viz.render()

        # Optional slow down
        # time.sleep(0.01)

    # Keep window alive
    viz.spin(target_fps=60)


if __name__ == "__main__":
    main()