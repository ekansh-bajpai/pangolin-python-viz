from __future__ import annotations

import os
import sys
import time

import numpy as np
import pypangolin as pango
from OpenGL.GL import *

# Optional, only needed if you want to load image files.
try:
    import cv2
except ImportError:
    cv2 = None

# Allow running example directly from repository root.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from visualization import (
    PangolinVisualizer,
    CustomDrawable,
    load_tum_trajectory,
    set_gl_color,
)


def draw_custom_triangle(obj: CustomDrawable) -> None:
    """
    Example user-defined custom OpenGL object.
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


def generate_demo_poses(num_poses: int = 300):
    """
    Generate synthetic circular poses.
    """
    poses = []

    for i in range(num_poses):
        t = i * 0.03

        x = np.cos(t)
        y = np.sin(t)
        z = 0.2 * np.sin(2.0 * t)

        T = np.eye(4, dtype=np.float64)
        T[:3, 3] = [x, y, z]

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

    return poses


def create_demo_image(
    width: int = 320,
    height: int = 180,
    frame_index: int = 0,
) -> np.ndarray:
    """
    Create a synthetic RGB image for ImagePlane testing.

    Returns
    -------
    np.ndarray
        uint8 image with shape HxWx3.
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)

    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, height),
        np.linspace(0.0, 1.0, width),
        indexing="ij",
    )

    phase = frame_index * 0.03

    image[..., 0] = np.clip(255.0 * xx, 0, 255).astype(np.uint8)
    image[..., 1] = np.clip(255.0 * yy, 0, 255).astype(np.uint8)
    image[..., 2] = np.clip(
        127.0 + 127.0 * np.sin(8.0 * xx + phase),
        0,
        255,
    ).astype(np.uint8)

    # Add a moving bright square.
    square_size = 32
    cx = int((0.5 + 0.4 * np.sin(phase)) * width)
    cy = int((0.5 + 0.4 * np.cos(phase)) * height)

    x0 = max(0, cx - square_size // 2)
    x1 = min(width, cx + square_size // 2)
    y0 = max(0, cy - square_size // 2)
    y1 = min(height, cy + square_size // 2)

    image[y0:y1, x0:x1] = np.array([255, 255, 255], dtype=np.uint8)

    return image


def load_or_create_image(path: str = "viz/image.png") -> np.ndarray:
    """
    Load an RGB image from disk if available, otherwise create a synthetic image.
    """
    if cv2 is not None and os.path.exists(path):
        image_bgr = cv2.imread(path, cv2.IMREAD_COLOR)

        if image_bgr is not None:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            print(f"Loaded image from {path}")
            return image_rgb

    print("No image file found. Using generated demo image.")
    return create_demo_image()


def make_image_pose_from_camera(
    T_wc: np.ndarray,
    distance: float = 0.35,
    vertical_offset: float = 0.25,
) -> np.ndarray:
    """
    Create an image-plane pose near the current camera/robot pose.

    Assumption:
    The ImagePlane lies in its local XY plane, with normal along local +Z.

    This function places the image slightly above and in front of the pose.

    Parameters
    ----------
    T_wc:
        4x4 world-from-camera pose.
    distance:
        Local forward offset.
    vertical_offset:
        Local upward/world-z offset.

    Returns
    -------
    np.ndarray
        4x4 image-plane pose in world frame.
    """
    T_image = T_wc.copy()

    # Place the image near the moving pose.
    # With this synthetic setup, local +X is roughly tangent direction.
    # Here we offset in local +Z and world +Z for visibility.
    local_offset = np.array([0.0, 0.0, distance])
    world_offset = T_wc[:3, :3] @ local_offset

    T_image[:3, 3] = T_wc[:3, 3] + world_offset + np.array(
        [0.0, 0.0, vertical_offset],
        dtype=np.float64,
    )

    return T_image


def main() -> None:
    viz = PangolinVisualizer(
        title="Visualization Usage Example with ImagePlane",
        width=1280,
        height=720,
        fx=420,
        fy=420,
        camera_eye=(0.0, -3.0, 2.0),
        camera_target=(0.0, 0.0, 0.0),
        camera_up=pango.AxisZ,
        background_color=(1.0, 1.0, 1.0, 1.0),
    )

    # -------------------------------------------------------------------------
    # Add static objects
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Add dynamic objects
    # -------------------------------------------------------------------------

    estimated_trajectory = viz.add_trajectory(
        name="estimated_trajectory",
        color=(1.0, 0.0, 0.0, 1.0),
        line_width=2.0,
        draw_latest_axis=True,
        axis_scale=0.15,
    )

    ground_truth_trajectory = viz.add_trajectory(
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

    latest_camera = viz.add_camera_frustum(
        name="latest_camera",
        scale=0.12,
        color=(0.1, 0.1, 1.0, 1.0),
        line_width=1.5,
    )

    # -------------------------------------------------------------------------
    # Add image plane object
    # -------------------------------------------------------------------------

    initial_image = load_or_create_image("viz/image.png")

    image_pose = np.eye(4, dtype=np.float64)
    image_pose[:3, 3] = np.array([0.0, 0.0, 0.6], dtype=np.float64)

    image_plane = viz.add_image_plane(
        name="debug_image",
        image=initial_image,
        pose=image_pose,
        width=0.8,
        height=None,     # keep aspect ratio
        alpha=0.95,
        flip_y=True,
    )

    viz.add_custom(
        draw_callback=draw_custom_triangle,
        name="custom_triangle",
        color=(1.0, 0.7, 0.0, 0.8),
        line_width=1.0,
        properties={
            "scale": 0.25,
            "z": 0.05,
        },
    )

    # -------------------------------------------------------------------------
    # Landmarks
    # -------------------------------------------------------------------------

    np.random.seed(0)
    points = np.random.uniform(low=-1.5, high=1.5, size=(300, 3))
    points[:, 2] *= 0.25
    landmarks.set_points(points)

    # -------------------------------------------------------------------------
    # Load trajectory or generate synthetic trajectory
    # -------------------------------------------------------------------------

    trajectory_path = "viz/trajectory.txt"

    if os.path.exists(trajectory_path):
        poses = load_tum_trajectory(trajectory_path)
        print(f"Loaded {len(poses)} poses from {trajectory_path}")
    else:
        poses = generate_demo_poses(300)
        print("No trajectory file found. Using generated demo poses.")

    # -------------------------------------------------------------------------
    # Update loop
    # -------------------------------------------------------------------------

    for i, T in enumerate(poses):
        if viz.should_quit():
            return

        estimated_trajectory.append_pose(T)

        # Example fake ground truth trajectory
        T_gt = T.copy()
        T_gt[:3, 3] += np.array([0.05, -0.05, 0.0])
        ground_truth_trajectory.append_pose(T_gt)

        moving_sphere.set_position(T[:3, 3])
        latest_camera.set_pose(T)

        # ---------------------------------------------------------------------
        # Update ImagePlane
        # ---------------------------------------------------------------------

        # Move image plane with the latest pose.
        T_image = make_image_pose_from_camera(
            T_wc=T,
            distance=0.35,
            vertical_offset=0.25,
        )
        image_plane.set_pose(T_image)

        # Dynamically update image content every frame.
        dynamic_image = create_demo_image(
            width=320,
            height=180,
            frame_index=i,
        )
        image_plane.set_image(dynamic_image)

        viz.render()

        # Optional slow down
        time.sleep(0.005)

    # Keep rendering after animation completes.
    viz.spin(target_fps=60)


if __name__ == "__main__":
    main()