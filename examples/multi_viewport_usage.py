from __future__ import annotations

import os
import sys
import time

import numpy as np
import pypangolin as pango

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from visualization import PangolinVisualizer, load_tum_trajectory


def generate_demo_poses(num_poses: int = 500):
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


def create_demo_image(
    width: int = 320,
    height: int = 180,
    frame_index: int = 0,
    mode: int = 0,
) -> np.ndarray:
    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, height),
        np.linspace(0.0, 1.0, width),
        indexing="ij",
    )

    phase = frame_index * 0.04

    image = np.zeros((height, width, 3), dtype=np.uint8)

    if mode == 0:
        image[..., 0] = np.clip(255.0 * xx, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * yy, 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(
            127.0 + 127.0 * np.sin(10.0 * xx + phase),
            0,
            255,
        ).astype(np.uint8)

    elif mode == 1:
        wave = 0.5 + 0.5 * np.sin(12.0 * (xx + yy) + phase)
        image[..., 0] = np.clip(255.0 * wave, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * (1.0 - yy), 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(255.0 * (1.0 - wave), 0, 255).astype(np.uint8)

    elif mode == 2:
        cx = 0.5 + 0.25 * np.sin(phase)
        cy = 0.5 + 0.25 * np.cos(phase)

        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.sin(40.0 * dist - phase * 3.0)

        image[..., 0] = np.clip(127.0 + 127.0 * ring, 0, 255).astype(np.uint8)
        image[..., 1] = np.clip(255.0 * xx, 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(255.0 * yy, 0, 255).astype(np.uint8)

    else:
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

    square_size = 24
    sx = int((0.5 + 0.4 * np.sin(phase + mode)) * width)
    sy = int((0.5 + 0.4 * np.cos(phase + mode)) * height)

    x0 = max(0, sx - square_size // 2)
    x1 = min(width, sx + square_size // 2)
    y0 = max(0, sy - square_size // 2)
    y1 = min(height, sy + square_size // 2)

    image[y0:y1, x0:x1] = np.array([255, 255, 255], dtype=np.uint8)

    return image


def make_image_pose() -> np.ndarray:
    """
    Puts an ImagePlane centered at the origin of each image viewport.

    Each image viewport camera looks from +Z toward origin.
    The image plane lies in XY plane at z=0.
    """
    return np.eye(4, dtype=np.float64)


def main() -> None:
    # -------------------------------------------------------------------------
    # One window, multiple viewports
    # -------------------------------------------------------------------------

    viz = PangolinVisualizer(
        title="Trajectory + 4 Image Viewports",
        width=1600,
        height=900,
        background_color=(0.05, 0.05, 0.05, 1.0),
        create_default_viewport=False,
    )

    # -------------------------------------------------------------------------
    # Layout
    #
    # Normalized coordinates:
    #
    # x: 0.0 ------------------------------------------------------------- 1.0
    #
    #    +-------------------------------+-------------------------------+
    #    |                               |            image_0            |
    #    |                               +-------------------------------+
    #    |          trajectory           |            image_1            |
    #    |                               +-------------------------------+
    #    |                               |            image_2            |
    #    |                               +-------------------------------+
    #    |                               |            image_3            |
    #    +-------------------------------+-------------------------------+
    #
    # Left 65%: trajectory viewport
    # Right 35%: four stacked image viewports
    # -------------------------------------------------------------------------

    trajectory_left = 0.0
    trajectory_right = 0.65

    image_left = 0.65
    image_right = 1.0

    viz.add_viewport(
        name="trajectory",
        left=trajectory_left,
        right=trajectory_right,
        bottom=0.0,
        top=1.0,
        camera_eye=(0.0, -3.0, 2.0),
        camera_target=(0.0, 0.0, 0.0),
        camera_up=pango.AxisZ,
    )

    # Four image viewports on right side.
    # Each gets its own camera looking straight at its own image plane.
    image_viewport_names = []

    for i in range(4):
        bottom = 1.0 - float(i + 1) / 4.0
        top = 1.0 - float(i) / 4.0

        name = f"image_{i}"
        image_viewport_names.append(name)

        viz.add_viewport(
            name=name,
            left=image_left,
            right=image_right,
            bottom=bottom,
            top=top,
            camera_eye=(0.0, 0.0, 2.0),
            camera_target=(0.0, 0.0, 0.0),
            camera_up=pango.AxisY,
        )

    # -------------------------------------------------------------------------
    # Trajectory viewport objects
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
    # Image viewport objects
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
    # Load or generate trajectory
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

        estimated_trajectory.append_pose(T)

        T_gt = T.copy()
        T_gt[:3, 3] += np.array([0.05, -0.05, 0.0])
        ground_truth_trajectory.append_pose(T_gt)

        latest_camera.set_pose(T)
        moving_sphere.set_position(T[:3, 3])

        for i, plane in enumerate(image_planes):
            image = create_demo_image(
                width=320,
                height=180,
                frame_index=frame_index,
                mode=i,
            )
            plane.set_image(image)

        viz.render()
        time.sleep(0.005)

    viz.spin(target_fps=60)


if __name__ == "__main__":
    main()