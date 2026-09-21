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

    The projection-rebuild fields (orthographic/ortho_width/fx/fy/cx/cy/
    near/far) let PangolinVisualizer.render() recompute this viewport's
    projection matrix against its *current* live pixel size every frame --
    display.GetBounds() tracks window resizes automatically (Pangolin's own
    layout system), but a projection matrix baked once at add_viewport()
    time does not, so without this a resized window leaves stale-sized
    content with whitespace/empty space around it instead of filling the
    (correctly resized) box.
    """

    name: str
    display: object
    render_state: object
    handler: object
    scene: Scene
    orthographic: bool = False
    ortho_width: Optional[float] = None
    fx: Optional[float] = None
    fy: Optional[float] = None
    cx: Optional[float] = None
    cy: Optional[float] = None
    near: float = 0.1
    far: float = 1000.0
    _last_px_size: Optional[tuple] = None


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

    @staticmethod
    def _build_projection(
        vp_px_w: int,
        vp_px_h: int,
        orthographic: bool,
        ortho_width: Optional[float],
        fx: Optional[float],
        fy: Optional[float],
        cx: Optional[float],
        cy: Optional[float],
        near: float,
        far: float,
        default_fx: float = 420.0,
        default_fy: float = 420.0,
    ):
        vp_px_w = max(1, vp_px_w)
        vp_px_h = max(1, vp_px_h)

        if orthographic:
            half_w = (2.0 if ortho_width is None else float(ortho_width)) / 2.0
            half_h = half_w * (vp_px_h / vp_px_w)
            return pango.ProjectionMatrixOrthographic(-half_w, half_w, -half_h, half_h, near, far)

        return pango.ProjectionMatrix(
            vp_px_w,
            vp_px_h,
            default_fx if fx is None else float(fx),
            default_fy if fy is None else float(fy),
            vp_px_w / 2.0 if cx is None else float(cx),
            vp_px_h / 2.0 if cy is None else float(cy),
            near,
            far,
        )

    def _refresh_viewport_projection(self, viewport: Viewport) -> None:
        """Rebuild this viewport's projection matrix if its live pixel size
        (tracked by Pangolin's own resize-responsive layout, via
        display.GetBounds()) has changed since the last check -- keeps
        content correctly scaled to the panel instead of stale-sized with
        whitespace around it after the main window is resized."""
        bounds = viewport.display.GetBounds()
        px_size = (max(1, int(bounds.w)), max(1, int(bounds.h)))

        if px_size == viewport._last_px_size:
            return

        projection = self._build_projection(
            px_size[0], px_size[1],
            viewport.orthographic, viewport.ortho_width,
            viewport.fx, viewport.fy, viewport.cx, viewport.cy,
            viewport.near, viewport.far,
            default_fx=self.fx, default_fy=self.fy,
        )
        viewport.render_state.SetProjectionMatrix(projection)
        viewport._last_px_size = px_size

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
        orthographic: bool = False,
        ortho_width: Optional[float] = None,
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

        The projection is scaled to this viewport's own pixel size (not the
        full window's) -- otherwise content is framed as if seen through a
        camera calibrated for the whole window and renders far too small
        inside a smaller viewport. It's also recomputed every render() call
        against the viewport's *current* pixel size, so resizing the main
        window rescales each panel's content to fill it instead of leaving
        stale-sized content with growing whitespace around it.

        Pass `orthographic=True` for pure 2D content (e.g. an image plane
        meant to exactly fill its panel): the projection becomes a
        parallel-projection box sized to `ortho_width` world units wide,
        with height derived from the viewport's own pixel aspect ratio so a
        plane of that same aspect fills it exactly, with no FOV/distance
        tuning needed.
        """
        if not replace and name in self.viewports:
            raise KeyError(f"Viewport '{name}' already exists")

        if not (0.0 <= left < right <= 1.0):
            raise ValueError("Expected 0 <= left < right <= 1")

        if not (0.0 <= bottom < top <= 1.0):
            raise ValueError("Expected 0 <= bottom < top <= 1")

        near = self.near if near is None else float(near)
        far = self.far if far is None else float(far)

        camera_eye = ensure_vec3(camera_eye, "camera_eye")
        camera_target = ensure_vec3(camera_target, "camera_target")

        viewport_width = max(1e-8, right - left)
        viewport_height = max(1e-8, top - bottom)
        vp_px_w = max(1, int(round(self.width * viewport_width)))
        vp_px_h = max(1, int(round(self.height * viewport_height)))

        projection = self._build_projection(
            vp_px_w, vp_px_h, orthographic, ortho_width, fx, fy, cx, cy, near, far,
            default_fx=self.fx, default_fy=self.fy,
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

        # No aspect argument -- the box exactly fills its Attach-fraction
        # bounds with no internal Pangolin letterboxing; `_build_projection`
        # (recomputed per-frame in render()) is what keeps content correctly
        # scaled to that box's live pixel size instead.
        display = (
            pango.CreateDisplay()
            .SetBounds(
                pango.Attach(bottom),
                pango.Attach(top),
                pango.Attach(left),
                pango.Attach(right),
            )
            .SetHandler(handler)
        )

        viewport = Viewport(
            name=name,
            display=display,
            render_state=render_state,
            handler=handler,
            scene=Scene(),
            orthographic=orthographic,
            ortho_width=ortho_width,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
            near=near,
            far=far,
            _last_px_size=(vp_px_w, vp_px_h),
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
            self._refresh_viewport_projection(viewport)
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
        self._refresh_viewport_projection(vp)
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
        bounds = pango.DisplayBase().GetBounds()
        width = max(1, int(bounds.w))
        height = max(1, int(bounds.h))

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