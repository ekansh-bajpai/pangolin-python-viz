"""
examples/multi_viewport_alternative_layout.py

One Pangolin window split into multiple sub-displays/viewports:

+--------------------------------+----------------+----------------+
|                                |    image_0     |    image_1     |
|                                |                |                |
|          trajectory            +----------------+----------------+
|                                |    image_2     |    image_3     |
|                                |                |                |
+--------------------------------+----------------+----------------+

Left side:
    - trajectory scene

Right side:
    - 2x2 image grid
    - each image viewport has its own independent ImagePlane

Requirements:
    - Updated PangolinVisualizer with multi-viewport support
    - ImagePlane object available in visualization.objects
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import pypangolin as pango

# Allow running example directly from repository root.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from visualization import PangolinVisualizer, load_tum_trajectory


# =============================================================================
# Demo Pose Generation
# =============================================================================

def generate_demo_poses(num_poses: int = 500):
    """
    Generate synthetic circular camera/robot poses.

    Returns
    -------
    list[np.ndarray]
        List of 4x4 homogeneous transformation matrices.
    """
    poses = []

    for i in range(num_poses):
        t = i * 0.025

        x = np.cos(t)
        y = np.sin(t)
        z = 0.15 * np.sin(2.0 * t)

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


# =============================================================================
# Demo Image Generation
# =============================================================================

def create_demo_image(
    width: int = 320,
    height: int = 180,
    frame_index: int = 0,
    mode: int = 0,
) -> np.ndarray:
    """
    Create a synthetic RGB image.

    Parameters
    ----------
    width:
        Image width.
    height:
        Image height.
    frame_index:
        Animation frame index.
    mode:
        Determines the generated pattern.

    Returns
    -------
    np.ndarray
        RGB uint8 image with shape HxWx3.
    """
    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, height),
        np.linspace(0.0, 1.0, width),
        indexing="ij",
    )

    phase = frame_index * 0.04

    image = np.zeros((height, width, 3), dtype=np.uint8)

    if mode == 0:
        # Red/green gradient with moving blue wave.
        image[..., 0] = np.clip(255.0 * xx, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * yy, 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(
            127.0 + 127.0 * np.sin(10.0 * xx + phase),
            0,
            255,
        ).astype(np.uint8)

    elif mode == 1:
        # Blue/yellow diagonal wave.
        wave = 0.5 + 0.5 * np.sin(12.0 * (xx + yy) + phase)

        image[..., 0] = np.clip(255.0 * wave, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * (1.0 - yy), 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(255.0 * (1.0 - wave), 0, 255).astype(np.uint8)

    elif mode == 2:
        # Animated circular/ring pattern.
        cx = 0.5 + 0.25 * np.sin(phase)
        cy = 0.5 + 0.25 * np.cos(phase)

        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.sin(40.0 * dist - phase * 3.0)

        image[..., 0] = np.clip(127.0 + 127.0 * ring, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * xx, 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(255.0 * yy, 0, 255).astype(np.uint8)

    else:
        # Checkerboard with animated blue brightness.
        checker = (
            (
                np.floor(xx * 12.0).astype(np.int32)
                + np.floor(yy * 8.0).astype(np.int32)
            )
            % 2
        )

        brightness = 0.5 + 0.5 * np.sin(phase)

        image[..., 0] = np.where(checker == 0, 255, 40).astype(np.uint8)
        image[..., 1] = np.where(checker == 0, 80, 255).astype(np.uint8)
        image[..., 2] = np.clip(255.0 * brightness, 0, 255).astype(np.uint8)

    # Add moving white square to every image.
    square_size = 24

    sx = int((0.5 + 0.4 * np.sin(phase + mode)) * width)
    sy = int((0.5 + 0.4 * np.cos(phase + mode)) * height)

    x0 = max(0, sx - square_size // 2)
    x1 = min(width, sx + square_size // 2)
    y0 = max(0, sy - square_size // 2)
    y1 = min(height, sy + square_size // 2)

    image[y0:y1, x0:x1] = np.array([255, 255, 255], dtype=np.uint8)

    return image


# =============================================================================
# Pose Helpers
# =============================================================================

def make_image_pose() -> np.ndarray:
    """
    Pose for an ImagePlane centered in its own image viewport.

    Each image viewport camera looks from +Z toward the origin.
    The image plane lies in the XY plane at z=0.
    """
    return np.eye(4, dtype=np.float64)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    # -------------------------------------------------------------------------
    # Create one window with no default viewport.
    # We will create custom sub-displays manually.
    # -------------------------------------------------------------------------

    viz = PangolinVisualizer(
        title="Trajectory + 2x2 Image Grid Viewports",
        width=1600,
        height=900,
        background_color=(0.05, 0.05, 0.05, 1.0),
        create_default_viewport=False,
    )

    # -------------------------------------------------------------------------
    # Viewport Layout
    #
    # Normalized coordinates:
    #
    # left/right/bottom/top are fractions in [0, 1].
    #
    # Layout:
    #
    # +--------------------------------+----------------+----------------+
    # |                                |    image_0     |    image_1     |
    # |                                |                |                |
    # |          trajectory            +----------------+----------------+
    # |                                |    image_2     |    image_3     |
    # |                                |                |                |
    # +--------------------------------+----------------+----------------+
    #
    # Left 65% of window:
    #   trajectory viewport
    #
    # Right 35% of window:
    #   2x2 image viewports
    # -------------------------------------------------------------------------

    trajectory_bounds = {
        "left": 0.0,
        "right": 0.65,
        "bottom": 0.0,
        "top": 1.0,
    }

    image_layouts = {
        "image_0": {
            "left": 0.65,
            "right": 0.825,
            "bottom": 0.5,
            "top": 1.0,
        },
        "image_1": {
            "left": 0.825,
            "right": 1.0,
            "bottom": 0.5,
            "top": 1.0,
        },
        "image_2": {
            "left": 0.65,
            "right": 0.825,
            "bottom": 0.0,
            "top": 0.5,
        },
        "image_3": {
            "left": 0.825,
            "right": 1.0,
            "bottom": 0.0,
            "top": 0.5,
        },
    }

    # -------------------------------------------------------------------------
    # Add trajectory viewport
    # -------------------------------------------------------------------------

    viz.add_viewport(
        name="trajectory",
        left=trajectory_bounds["left"],
        right=trajectory_bounds["right"],
        bottom=trajectory_bounds["bottom"],
        top=trajectory_bounds["top"],
        camera_eye=(0.0, -3.0, 2.0),
        camera_target=(0.0, 0.0, 0.0),
        camera_up=pango.AxisZ,
    )

    # -------------------------------------------------------------------------
    # Add 4 image viewports
    #
    # Each image viewport has its own camera looking straight at the image plane.
    # -------------------------------------------------------------------------

    image_viewport_names = []

    for name, bounds in image_layouts.items():
        image_viewport_names.append(name)

        viz.add_viewport(
            name=name,
            left=bounds["left"],
            right=bounds["right"],
            bottom=bounds["bottom"],
            top=bounds["top"],
            camera_eye=(0.0, 0.0, 2.0),
            camera_target=(0.0, 0.0, 0.0),
            camera_up=pango.AxisY,
        )

    # -------------------------------------------------------------------------
    # Add objects to trajectory viewport
    # -------------------------------------------------------------------------

    viz.add_axis(
        name="world_axis",
        viewport="trajectory",
        scale=0.5,
        line_width=2.5,
    )

    viz.add_grid(
        name="xy_grid",
        viewport="trajectory",
        size=4.0,
        step=0.2,
        centered=True,
        draw_xy=True,
        draw_xz=False,
        draw_yz=False,
        color=(0.75, 0.75, 0.75, 1.0),
        line_width=1.0,
    )

    estimated_trajectory = viz.add_trajectory(
        name="estimated_trajectory",
        viewport="trajectory",
        color=(1.0, 0.0, 0.0, 1.0),
        line_width=2.0,
        draw_latest_axis=True,
        axis_scale=0.15,
    )

    ground_truth_trajectory = viz.add_trajectory(
        name="ground_truth_trajectory",
        viewport="trajectory",
        color=(0.0, 0.7, 0.0, 1.0),
        line_width=2.0,
        draw_latest_axis=False,
    )

    latest_camera = viz.add_camera_frustum(
        name="latest_camera",
        viewport="trajectory",
        scale=0.12,
        color=(0.1, 0.1, 1.0, 1.0),
        line_width=1.5,
    )

    moving_sphere = viz.add_sphere(
        name="moving_sphere",
        viewport="trajectory",
        position=(0.0, 0.0, 0.0),
        radius=0.04,
        color=(1.0, 0.3, 0.0, 1.0),
    )

    landmarks = viz.add_point_cloud(
        name="landmarks",
        viewport="trajectory",
        color=(0.0, 0.4, 1.0, 1.0),
        point_size=4.0,
    )

    np.random.seed(4)
    map_points = np.random.uniform(low=-1.5, high=1.5, size=(500, 3))
    map_points[:, 2] *= 0.25
    landmarks.set_points(map_points)

    # -------------------------------------------------------------------------
    # Add image planes to image viewports
    # -------------------------------------------------------------------------

    image_planes = []

    for i, viewport_name in enumerate(image_viewport_names):
        image = create_demo_image(
            width=320,
            height=180,
            frame_index=0,
            mode=i,
        )

        plane = viz.add_image_plane(
            name=f"panel_{i}",
            viewport=viewport_name,
            image=image,
            pose=make_image_pose(),
            width=1.7,
            height=None,
            alpha=1.0,
            flip_y=True,
        )

        image_planes.append(plane)

    # -------------------------------------------------------------------------
    # Load trajectory if available, otherwise generate synthetic poses
    # -------------------------------------------------------------------------

    trajectory_path = "trajectory.txt"

    if os.path.exists(trajectory_path):
        poses = load_tum_trajectory(trajectory_path)
        print(f"Loaded {len(poses)} poses from {trajectory_path}")
    else:
        poses = generate_demo_poses(500)
        print("No trajectory file found. Using generated demo poses.")

    # -------------------------------------------------------------------------
    # Update loop
    # -------------------------------------------------------------------------

    for frame_index, T in enumerate(poses):
        if viz.should_quit():
            return

        # Update trajectory scene.
        estimated_trajectory.append_pose(T)

        T_gt = T.copy()
        T_gt[:3, 3] += np.array([0.05, -0.05, 0.0])
        ground_truth_trajectory.append_pose(T_gt)

        latest_camera.set_pose(T)
        moving_sphere.set_position(T[:3, 3])

        # Update image panels.
        for i, plane in enumerate(image_planes):
            image = create_demo_image(
                width=320,
                height=180,
                frame_index=frame_index,
                mode=i,
            )
            plane.set_image(image)

        # Render all viewports.
        viz.render()

        time.sleep(0.005)

    # -------------------------------------------------------------------------
    # Keep window alive after animation finishes
    # -------------------------------------------------------------------------

    viz.spin(target_fps=60)


if __name__ == "__main__":
    main()