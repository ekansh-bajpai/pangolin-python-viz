from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import pypangolin as pango
from OpenGL.GL import *
import OpenGL.GLUT as glut

from .objects import (
    Axis,
    CameraFrustum,
    CustomDrawable,
    Drawable,
    Grid,
    ImagePlane,
    PointCloud,
    Scene,
    Sphere,
    Trajectory,
)
from .utils import ArrayLike, ColorLike, as_color, ensure_vec3


@dataclass
class Viewport:
    """
    One Pangolin sub-display/viewport.

    Each viewport owns:
    - a Pangolin display
    - a render state
    - a camera handler
    - a scene
    """

    name: str
    display: object
    render_state: object
    handler: object
    scene: Scene


class PangolinVisualizer:
    """
    Modular Pangolin visualizer with multi-viewport support.

    This class owns:
    - one Pangolin window
    - one or more Pangolin sub-displays/viewports
    - one scene per viewport

    By default, one viewport named "main" is created and occupies the full window.

    You can add more viewports using:

        viz.add_viewport(...)

    Then add objects into a specific viewport using:

        viz.add_grid(viewport="trajectory")
        viz.add_image_plane(viewport="image_0")
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
        create_default_viewport: bool = True,
    ) -> None:
        self.title = title
        self.width = int(width)
        self.height = int(height)
        self.background_color = as_color(background_color)

        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = self.width / 2.0 if cx is None else float(cx)
        self.cy = self.height / 2.0 if cy is None else float(cy)
        self.near = float(near)
        self.far = float(far)

        self.viewports: Dict[str, Viewport] = {}

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

        if create_default_viewport:
            self.add_viewport(
                name="main",
                left=0.0,
                right=1.0,
                bottom=0.0,
                top=1.0,
                fx=self.fx,
                fy=self.fy,
                cx=self.cx,
                cy=self.cy,
                near=self.near,
                far=self.far,
                camera_eye=camera_eye,
                camera_target=camera_target,
                camera_up=camera_up,
            )

    # -------------------------------------------------------------------------
    # Viewport Management
    # -------------------------------------------------------------------------

    def add_viewport(
        self,
        name: str,
        left: float,
        right: float,
        bottom: float,
        top: float,
        fx: Optional[float] = None,
        fy: Optional[float] = None,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
        near: Optional[float] = None,
        far: Optional[float] = None,
        camera_eye: ArrayLike = (0.0, 0.0, 3.0),
        camera_target: ArrayLike = (0.0, 0.0, 0.0),
        camera_up=pango.AxisY,
        replace: bool = True,
    ) -> Viewport:
        """
        Add a Pangolin sub-display/viewport.

        Bounds are normalized window fractions:

            left   in [0, 1]
            right  in [0, 1]
            bottom in [0, 1]
            top    in [0, 1]

        Example
        -------
        Top-left quadrant:

            left=0.0, right=0.5, bottom=0.5, top=1.0

        Bottom-right quadrant:

            left=0.5, right=1.0, bottom=0.0, top=0.5
        """
        if not replace and name in self.viewports:
            raise KeyError(f"Viewport '{name}' already exists")

        if not (0.0 <= left < right <= 1.0):
            raise ValueError("Expected 0 <= left < right <= 1")

        if not (0.0 <= bottom < top <= 1.0):
            raise ValueError("Expected 0 <= bottom < top <= 1")

        fx = self.fx if fx is None else float(fx)
        fy = self.fy if fy is None else float(fy)
        cx = self.cx if cx is None else float(cx)
        cy = self.cy if cy is None else float(cy)
        near = self.near if near is None else float(near)
        far = self.far if far is None else float(far)

        camera_eye = ensure_vec3(camera_eye, "camera_eye")
        camera_target = ensure_vec3(camera_target, "camera_target")

        projection = pango.ProjectionMatrix(
            self.width,
            self.height,
            fx,
            fy,
            cx,
            cy,
            near,
            far,
        )

        model_view = pango.ModelViewLookAt(
            camera_eye[0],
            camera_eye[1],
            camera_eye[2],
            camera_target[0],
            camera_target[1],
            camera_target[2],
            camera_up,
        )

        render_state = pango.OpenGlRenderState(
            projection,
            model_view,
        )

        handler = pango.Handler3D(render_state)

        viewport_width = max(1e-8, right - left)
        viewport_height = max(1e-8, top - bottom)

        aspect = -float(self.width * viewport_width) / float(
            self.height * viewport_height
        )

        display = (
            pango.CreateDisplay()
            .SetBounds(
                pango.Attach(bottom),
                pango.Attach(top),
                pango.Attach(left),
                pango.Attach(right),
                aspect,
            )
            .SetHandler(handler)
        )

        viewport = Viewport(
            name=name,
            display=display,
            render_state=render_state,
            handler=handler,
            scene=Scene(),
        )

        self.viewports[name] = viewport
        return viewport

    def remove_viewport(self, name: str) -> None:
        """
        Remove viewport from internal registry.

        Note:
        Pangolin display destruction is managed internally by Pangolin.
        """
        if name in self.viewports:
            del self.viewports[name]

    def get_viewport(self, name: str = "main") -> Optional[Viewport]:
        return self.viewports.get(name)

    def require_viewport(self, name: str = "main") -> Viewport:
        viewport = self.get_viewport(name)

        if viewport is None:
            raise KeyError(f"Viewport '{name}' does not exist")

        return viewport

    def viewport_names(self):
        return list(self.viewports.keys())

    # -------------------------------------------------------------------------
    # Scene API
    # -------------------------------------------------------------------------

    @property
    def scene(self) -> Scene:
        """
        Backward-compatible shortcut to main viewport scene.
        """
        return self.require_viewport("main").scene

    def add(
        self,
        obj: Drawable,
        name: Optional[str] = None,
        replace: bool = True,
        viewport: str = "main",
    ) -> Drawable:
        vp = self.require_viewport(viewport)
        return vp.scene.add(obj, name=name, replace=replace)

    def remove(self, name: str, viewport: str = "main") -> None:
        vp = self.require_viewport(viewport)
        vp.scene.remove(name)

    def get(self, name: str, viewport: str = "main") -> Optional[Drawable]:
        vp = self.require_viewport(viewport)
        return vp.scene.get(name)

    def require(self, name: str, viewport: str = "main") -> Drawable:
        vp = self.require_viewport(viewport)
        return vp.scene.require(name)

    def clear_scene(self, viewport: str = "main") -> None:
        vp = self.require_viewport(viewport)
        vp.scene.clear()

    def clear_all_scenes(self) -> None:
        for vp in self.viewports.values():
            vp.scene.clear()

    # -------------------------------------------------------------------------
    # Convenience Object Creation API
    # -------------------------------------------------------------------------

    def add_grid(
        self,
        name: str = "grid",
        viewport: str = "main",
        **kwargs,
    ) -> Grid:
        obj = Grid(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_axis(
        self,
        name: str = "axis",
        viewport: str = "main",
        **kwargs,
    ) -> Axis:
        obj = Axis(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_trajectory(
        self,
        name: str = "trajectory",
        viewport: str = "main",
        **kwargs,
    ) -> Trajectory:
        obj = Trajectory(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_point_cloud(
        self,
        name: str = "point_cloud",
        viewport: str = "main",
        **kwargs,
    ) -> PointCloud:
        obj = PointCloud(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_sphere(
        self,
        name: str = "sphere",
        viewport: str = "main",
        **kwargs,
    ) -> Sphere:
        obj = Sphere(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_camera_frustum(
        self,
        name: str = "camera_frustum",
        viewport: str = "main",
        **kwargs,
    ) -> CameraFrustum:
        obj = CameraFrustum(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_image_plane(
        self,
        name: str = "image_plane",
        viewport: str = "main",
        **kwargs,
    ) -> ImagePlane:
        obj = ImagePlane(name=name, **kwargs)
        self.add(obj, name=name, viewport=viewport)
        return obj

    def add_custom(
        self,
        draw_callback: Callable[[CustomDrawable], None],
        name: str = "custom",
        viewport: str = "main",
        **kwargs,
    ) -> CustomDrawable:
        obj = CustomDrawable(
            draw_callback=draw_callback,
            name=name,
            **kwargs,
        )
        self.add(obj, name=name, viewport=viewport)
        return obj

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def should_quit(self) -> bool:
        return bool(pango.ShouldQuit())

    def render(self, finish_frame: bool = True) -> None:
        """
        Render all viewports in this window.
        """
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        r, g, b, a = self.background_color
        glClearColor(r, g, b, a)

        for viewport in self.viewports.values():
            viewport.display.Activate(viewport.render_state)
            viewport.scene.draw()

        if finish_frame:
            pango.FinishFrame()

    def render_viewport(
        self,
        viewport: str,
        clear: bool = False,
        finish_frame: bool = False,
    ) -> None:
        """
        Render only one viewport.

        Usually you should call render() instead.
        """
        if clear:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        vp = self.require_viewport(viewport)
        vp.display.Activate(vp.render_state)
        vp.scene.draw()

        if finish_frame:
            pango.FinishFrame()

    def spin(self, target_fps: Optional[float] = None) -> None:
        """
        Blocking render loop.
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
    # Screenshot
    # -------------------------------------------------------------------------

    def save_image(self, filename: str) -> None:
        """
        Save current framebuffer as image using OpenCV.
        """
        width = self.width
        height = self.height

        buffer = np.empty((height, width, 4), dtype=np.uint8)

        glReadBuffer(GL_BACK)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)

        glReadPixels(
            0,
            0,
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