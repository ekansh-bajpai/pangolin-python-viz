from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, List, Optional

import numpy as np
import pypangolin as pango
from OpenGL.GL import *
import OpenGL.GLUT as glut

from .utils import (
    ArrayLike,
    ColorLike,
    as_color,
    ensure_points,
    ensure_pose,
    ensure_vec3,
    set_gl_color,
)


class Drawable(ABC):
    """
    Base class for all drawable scene objects.
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
        self.visible = bool(visible)
        self.color = color
        self.line_width = float(line_width)
        self.point_size = float(point_size)
        self.properties: Dict[str, Any] = properties or {}

    @abstractmethod
    def draw(self) -> None:
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


class Grid(Drawable):
    """
    Configurable grid drawn on XY, XZ, and/or YZ planes.
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
            if self.draw_xy:
                glVertex3d(ox + v, oy + start, oz)
                glVertex3d(ox + v, oy + end, oz)

                glVertex3d(ox + start, oy + v, oz)
                glVertex3d(ox + end, oy + v, oz)

            if self.draw_xz:
                glVertex3d(ox + v, oy, oz + start)
                glVertex3d(ox + v, oy, oz + end)

                glVertex3d(ox + start, oy, oz + v)
                glVertex3d(ox + end, oy, oz + v)

            if self.draw_yz:
                glVertex3d(ox, oy + v, oz + start)
                glVertex3d(ox, oy + v, oz + end)

                glVertex3d(ox, oy + start, oz + v)
                glVertex3d(ox, oy + end, oz + v)

        glEnd()


class Axis(Drawable):
    """
    Draw pose coordinate axis.

    Color convention:
    - X: red
    - Y: green
    - Z: blue
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

        glColor3f(1.0, 0.0, 0.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(x_end[0], x_end[1], x_end[2])

        glColor3f(0.0, 1.0, 0.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(y_end[0], y_end[1], y_end[2])

        glColor3f(0.0, 0.0, 1.0)
        glVertex3d(origin[0], origin[1], origin[2])
        glVertex3d(z_end[0], z_end[1], z_end[2])

        glEnd()


class Trajectory(Drawable):
    """
    Drawable trajectory from poses or positions.
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
        return self.poses[-1] if self.poses else None

    def latest_position(self) -> Optional[np.ndarray]:
        return self.positions[-1] if self.positions else None

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

        if self.draw_latest_axis and self.poses:
            Axis(
                pose=self.poses[-1],
                scale=self.axis_scale,
                line_width=self.line_width,
            ).draw()


class PointCloud(Drawable):
    """
    Draw Nx3 point cloud or landmarks.
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

            if (
                colors.ndim != 2
                or colors.shape[0] != self.points.shape[0]
                or colors.shape[1] not in (3, 4)
            ):
                raise ValueError("colors must have shape Nx3 or Nx4")

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
            return self.set_points(points, colors)

        self.points = np.vstack([self.points, points])

        if colors is not None:
            colors = np.asarray(colors, dtype=np.float64)

            if colors.ndim != 2 or colors.shape[0] != points.shape[0] or colors.shape[1] not in (3, 4):
                raise ValueError("colors must have shape Nx3 or Nx4")

            if colors.shape[1] == 3:
                colors = np.c_[colors, np.ones(colors.shape[0])]

            if self.colors is None:
                base = np.tile(np.asarray(as_color(self.color)), (self.points.shape[0] - points.shape[0], 1))
                self.colors = np.vstack([base, colors])
            else:
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
            if len(c) == 3:
                glColor3f(float(c[0]), float(c[1]), float(c[2]))
            else:
                glColor4f(float(c[0]), float(c[1]), float(c[2]), float(c[3]))

            glVertex3d(float(p[0]), float(p[1]), float(p[2]))

        glEnd()


class Sphere(Drawable):
    """
    Drawable solid sphere.
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
        glut.glutSolidSphere(self.radius, self.slices, self.stacks)
        glPopMatrix()


class CameraFrustum(Drawable):
    """
    Simple camera frustum visualization.
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

    def set_scale(self, scale: float) -> "CameraFrustum":
        self.scale = float(scale)
        return self

    def draw(self) -> None:
        if not self.visible:
            return

        s = self.scale

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

        for c in [c1, c2, c3, c4]:
            glVertex3d(o[0], o[1], o[2])
            glVertex3d(c[0], c[1], c[2])

        for a, b in [(c1, c2), (c2, c3), (c3, c4), (c4, c1)]:
            glVertex3d(a[0], a[1], a[2])
            glVertex3d(b[0], b[1], b[2])

        glEnd()


class CustomDrawable(Drawable):
    """
    Callback-based custom drawable.
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


class Scene:
    """
    Ordered drawable object container.
    """

    def __init__(self) -> None:
        self.objects: Dict[str, Drawable] = {}
        self.draw_order: List[str] = []

    def add(
        self,
        obj: Drawable,
        name: Optional[str] = None,
        replace: bool = True,
    ) -> Drawable:
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
                
class ImagePlane(Drawable):
    """
    Draws an image as a textured plane in the 3D scene.

    The image is rendered on a rectangular plane centered at the local origin.

    Local plane coordinates:

        (-w/2, -h/2, 0) ----- ( w/2, -h/2, 0)
                |                     |
                |       image         |
                |                     |
        (-w/2,  h/2, 0) ----- ( w/2,  h/2, 0)

    The plane is transformed into the world using a 4x4 pose.

    Parameters
    ----------
    image:
        Optional image as numpy array.
        Supported shapes:
            HxW
            HxWx3
            HxWx4

        Supported dtypes:
            uint8
            float32 / float64 in range [0, 1]

    pose:
        4x4 homogeneous pose of the image plane in world coordinates.

    width:
        Width of the image plane in world units.

    height:
        Height of the image plane in world units.
        If None, height is computed from image aspect ratio.

    alpha:
        Global opacity multiplier.

    flip_y:
        If True, flips texture coordinates vertically.
        This is often needed because image coordinates and OpenGL texture
        coordinates have opposite vertical direction.

    name:
        Scene object name.

    Notes
    -----
    This class uses an OpenGL texture internally.
    The texture is created lazily the first time draw() is called.
    """

    def __init__(
        self,
        image: Optional[np.ndarray] = None,
        pose: Optional[ArrayLike] = None,
        width: float = 1.0,
        height: Optional[float] = None,
        alpha: float = 1.0,
        flip_y: bool = True,
        visible: bool = True,
        name: str = "image_plane",
    ) -> None:
        super().__init__(
            name=name,
            visible=visible,
            color=(1.0, 1.0, 1.0, float(alpha)),
        )

        self.pose = np.eye(4, dtype=np.float64) if pose is None else ensure_pose(pose)

        self.width = float(width)
        self.height = None if height is None else float(height)
        self.alpha = float(alpha)
        self.flip_y = bool(flip_y)

        self.image: Optional[np.ndarray] = None

        self.texture_id: Optional[int] = None
        self.texture_width: int = 0
        self.texture_height: int = 0
        self.texture_channels: int = 0
        self.texture_dirty: bool = False

        if image is not None:
            self.set_image(image)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_pose(self, pose: ArrayLike) -> "ImagePlane":
        """
        Update image plane pose.

        Parameters
        ----------
        pose:
            4x4 homogeneous matrix.
        """
        self.pose = ensure_pose(pose)
        return self

    def set_size(
        self,
        width: float,
        height: Optional[float] = None,
    ) -> "ImagePlane":
        """
        Update plane size.

        If height is None, height is computed from image aspect ratio.
        """
        self.width = float(width)
        self.height = None if height is None else float(height)
        return self

    def set_alpha(self, alpha: float) -> "ImagePlane":
        """
        Set global image opacity.
        """
        self.alpha = float(alpha)
        self.color = (
            float(self.color[0]),
            float(self.color[1]),
            float(self.color[2]),
            self.alpha,
        )
        return self

    def set_image(self, image: np.ndarray) -> "ImagePlane":
        """
        Set or update image.

        Parameters
        ----------
        image:
            Image as numpy array with shape:
                HxW
                HxWx3
                HxWx4
        """
        image = self._prepare_image(image)

        self.image = image
        self.texture_height = int(image.shape[0])
        self.texture_width = int(image.shape[1])

        if image.ndim == 2:
            self.texture_channels = 1
        else:
            self.texture_channels = int(image.shape[2])

        self.texture_dirty = True
        return self

    def clear_image(self) -> "ImagePlane":
        """
        Remove current image.
        """
        self.image = None
        self.texture_dirty = True
        return self

    def delete_texture(self) -> None:
        """
        Delete OpenGL texture.
        """
        if self.texture_id is not None:
            glDeleteTextures([self.texture_id])
            self.texture_id = None

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _prepare_image(self, image: np.ndarray) -> np.ndarray:
        """
        Convert image to uint8 OpenGL-compatible image.
        """
        image = np.asarray(image)

        if image.ndim not in (2, 3):
            raise ValueError("image must have shape HxW, HxWx3, or HxWx4")

        if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
            raise ValueError("image channels must be 1, 3, or 4")

        if image.dtype == np.uint8:
            out = image.copy()
        elif np.issubdtype(image.dtype, np.floating):
            out = np.clip(image, 0.0, 1.0)
            out = (out * 255.0).astype(np.uint8)
        else:
            out = image.astype(np.uint8)

        # Ensure contiguous memory for glTexImage2D.
        out = np.ascontiguousarray(out)

        return out

    def _get_gl_formats(self):
        """
        Return OpenGL internal format and data format.
        """
        if self.texture_channels == 1:
            return GL_LUMINANCE, GL_LUMINANCE

        if self.texture_channels == 3:
            return GL_RGB, GL_RGB

        if self.texture_channels == 4:
            return GL_RGBA, GL_RGBA

        raise ValueError("Invalid texture channel count")

    def _create_texture_if_needed(self) -> None:
        """
        Create OpenGL texture lazily.
        """
        if self.texture_id is None:
            self.texture_id = glGenTextures(1)

            glBindTexture(GL_TEXTURE_2D, self.texture_id)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)

            glBindTexture(GL_TEXTURE_2D, 0)

    def _upload_texture_if_needed(self) -> None:
        """
        Upload image to GPU texture if dirty.
        """
        if self.image is None:
            return

        if not self.texture_dirty:
            return

        self._create_texture_if_needed()

        internal_format, data_format = self._get_gl_formats()

        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            internal_format,
            self.texture_width,
            self.texture_height,
            0,
            data_format,
            GL_UNSIGNED_BYTE,
            self.image,
        )

        glBindTexture(GL_TEXTURE_2D, 0)

        self.texture_dirty = False

    def _computed_size(self):
        """
        Compute final plane width and height.
        """
        width = self.width

        if self.height is not None:
            height = self.height
        else:
            if self.texture_width > 0 and self.texture_height > 0:
                aspect = self.texture_height / self.texture_width
                height = width * aspect
            else:
                height = width

        return width, height

    # -------------------------------------------------------------------------
    # Draw
    # -------------------------------------------------------------------------

    def draw(self) -> None:
        if not self.visible:
            return

        if self.image is None:
            return

        self._upload_texture_if_needed()

        if self.texture_id is None:
            return

        width, height = self._computed_size()

        half_w = width * 0.5
        half_h = height * 0.5

        # Texture coordinates.
        if self.flip_y:
            t00 = (0.0, 1.0)
            t10 = (1.0, 1.0)
            t11 = (1.0, 0.0)
            t01 = (0.0, 0.0)
        else:
            t00 = (0.0, 0.0)
            t10 = (1.0, 0.0)
            t11 = (1.0, 1.0)
            t01 = (0.0, 1.0)

        glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_TEXTURE_BIT)

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        # Enable alpha blending for transparent images / global alpha.
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glColor4f(1.0, 1.0, 1.0, self.alpha)

        glPushMatrix()

        # OpenGL expects column-major matrix.
        glMultMatrixd(self.pose.T)

        glBegin(GL_QUADS)

        glTexCoord2f(*t00)
        glVertex3f(-half_w, -half_h, 0.0)

        glTexCoord2f(*t10)
        glVertex3f(half_w, -half_h, 0.0)

        glTexCoord2f(*t11)
        glVertex3f(half_w, half_h, 0.0)

        glTexCoord2f(*t01)
        glVertex3f(-half_w, half_h, 0.0)

        glEnd()

        glPopMatrix()

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

        glPopAttrib()