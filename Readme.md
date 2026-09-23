# Modular Pangolin Visualization

A modular, extensible Python 3D visualization framework built on top of:

- [`pypangolin`](https://github.com/stevenlovegrove/Pangolin)
- `PyOpenGL`
- `numpy`

This package is intended for robotics, SLAM, visual odometry, mapping, bundle adjustment debugging, trajectory comparison, landmark visualization, image debugging, camera-frame visualization, and custom OpenGL-based 3D debugging tools.

The framework provides a clean scene/object abstraction over Pangolin so that you can create visualization windows, create multiple sub-viewports, add objects to each viewport, update object data dynamically, and render interactively.

---

# Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Coordinate System](#coordinate-system)
- [Package API Overview](#package-api-overview)
- [PangolinVisualizer](#pangolinvisualizer)
- [Viewport](#viewport)
- [Multi-Viewport Layouts](#multi-viewport-layouts)
- [Scene](#scene)
- [Drawable](#drawable)
- [Grid](#grid)
- [Axis](#axis)
- [Trajectory](#trajectory)
- [PointCloud](#pointcloud)
- [Sphere](#sphere)
- [CameraFrustum](#camerafrustum)
- [ImagePlane](#imageplane)
- [CustomDrawable](#customdrawable)
- [Utility Functions](#utility-functions)
- [Trajectory File Loading](#trajectory-file-loading)
- [Common Usage Patterns](#common-usage-patterns)
- [Full Example](#full-example)
- [Multi-Viewport Full Example](#multi-viewport-full-example)
- [Multiple Windows](#multiple-windows)
- [Screenshots](#screenshots)
- [Performance Notes](#performance-notes)
- [Troubleshooting](#troubleshooting)
- [Extending the Framework](#extending-the-framework)
- [License](#license)

---

# Features

- Modular visualization class
- Object-oriented scene management
- Multiple drawable object types
- Runtime object updates
- Custom OpenGL object support
- Pangolin interactive 3D camera controls
- Multi-viewport / sub-display support inside one Pangolin window
- Independent scene per viewport
- Independent camera/render state per viewport
- Trajectory visualization from poses or positions
- Latest pose coordinate axis visualization
- Point cloud / landmark visualization
- Per-point color support
- Grid visualization on XY, XZ, and YZ planes
- Sphere visualization
- Camera frustum visualization
- Image visualization as textured 3D planes using `ImagePlane`
- Dynamic image/frame updates
- Screenshot saving
- TUM trajectory file loading
- Clean separation between:
  - visualizer window
  - viewports
  - scenes
  - drawable objects
  - utilities

---

# Project Structure

Recommended project layout:

```text
project_root/
├── visualization/
│   ├── __init__.py
│   ├── utils.py
│   ├── objects.py
│   └── visualizer.py
│
├── examples/
│   ├── usage.py
│   └── multi_viewport_alternative_layout.py
│
└── README.md
```

## File Responsibilities

### `visualization/__init__.py`

Exports the main public API.

You can import most classes directly:

```python
from visualization import PangolinVisualizer, Trajectory, PointCloud, ImagePlane
```

### `visualization/utils.py`

Contains helper functions for:

- color conversion
- input validation
- OpenGL line drawing
- pose construction
- TUM trajectory loading

### `visualization/objects.py`

Contains all drawable objects:

- `Drawable`
- `Grid`
- `Axis`
- `Trajectory`
- `PointCloud`
- `Sphere`
- `CameraFrustum`
- `ImagePlane`
- `CustomDrawable`
- `Scene`

### `visualization/visualizer.py`

Contains the main `PangolinVisualizer` window class and multi-viewport support.

### `examples/usage.py`

Demonstrates typical single-scene usage.

### `examples/multi_viewport_alternative_layout.py`

Demonstrates one Pangolin window divided into:

- one trajectory viewport
- four image viewports in a 2x2 grid

---

# Installation

## Python Version

Recommended:

```bash
Python >= 3.8
```

---

## Python Dependencies

Install from `requirements.txt` (in this repo):

```bash
pip install -r requirements.txt
```

This is `numpy`, `scipy`, `PyOpenGL`, `PyOpenGL_accelerate`, and `opencv-python` — everything this
package needs on its own, so it can be used standalone in any project that needs 3D visualization.
`pypangolin` is intentionally not in `requirements.txt` — see below, it has to be built rather than
`pip install`-ed.

`opencv-python` is only required if you want to use:

```python
viz.save_image("image.png")
```

or load images using OpenCV:

```python
cv2.imread(...)
```

`scipy` is only required if you want to use:

```python
load_tum_trajectory(...)
```

because it uses:

```python
scipy.spatial.transform.Rotation
```

---

## Pangolin / pypangolin

You need Pangolin's Python bindings (`pypangolin`). `pip install pypangolin` is unreliable — there
isn't a maintained prebuilt wheel for most platforms, and several upstream/fork combinations were
tried against this library and failed to build or link correctly against a real Python 3.10 + GL
stack.

**Use this exact, verified-working fork and commit** — a frozen fork of
[stevenlovegrove/Pangolin](https://github.com/stevenlovegrove/Pangolin) at
[ekansh-bajpai/Pangolin](https://github.com/ekansh-bajpai/Pangolin), branch `frozen-working` (also
tagged `working-v1`), kept as a stable backup independent of upstream's moving `master`:

```bash
git clone --recursive -b frozen-working https://github.com/ekansh-bajpai/Pangolin.git
cd Pangolin
```

Install build dependencies (Ubuntu):

```bash
./scripts/install_prerequisites.sh -m apt recommended
```

Build Pangolin and its Python bindings, with your project's venv/conda env **active** (so the
bindings build against the same Python/`pip` this package will run under):

```bash
cmake -B build
cmake --build build
cmake --build build -t pypangolin_pip_install
```

This installs `pypangolin` directly into your active environment. Verify with:

```bash
python -c "import pypangolin; print('pypangolin OK')"
```

---

# Quick Start

Run the basic example:

```bash
python examples/usage.py
```

Run the multi-viewport example:

```bash
python examples/multi_viewport_alternative_layout.py
```

If this file exists:

```text
trajectory.txt
```

the examples can load it as a TUM-style trajectory.

Otherwise, they generate a synthetic circular trajectory.

If an example includes `ImagePlane`, it may also try to load or generate image data.

---

# Core Concepts

The framework is based on four main concepts:

## 1. Visualizer

The `PangolinVisualizer` represents one Pangolin window.

It owns:

- Pangolin window
- one or more Pangolin sub-displays / viewports
- one render state per viewport
- one camera handler per viewport
- one `Scene` per viewport

Example:

```python
viz = PangolinVisualizer(title="Viewer")
```

---

## 2. Viewport

A viewport is a rectangular sub-region of a Pangolin window.

Each viewport has:

- normalized bounds inside the window
- its own camera
- its own Pangolin display
- its own render state
- its own scene

Example:

```python
viz.add_viewport(
    name="trajectory",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)
```

Objects are added to a viewport by passing:

```python
viewport="trajectory"
```

Example:

```python
viz.add_grid(viewport="trajectory")
```

---

## 3. Scene

A `Scene` is an ordered container of drawable objects.

Each viewport has its own scene.

For backward compatibility, `viz.scene` refers to the scene of the default viewport named:

```text
main
```

if it exists.

Normally, you use convenience methods:

```python
trajectory = viz.add_trajectory(name="trajectory", viewport="trajectory")
grid = viz.add_grid(name="grid", viewport="trajectory")
image = viz.add_image_plane(name="debug_image", viewport="image_0")
```

---

## 4. Drawable Objects

Every visual object inherits from `Drawable`.

Examples:

- `Grid`
- `Axis`
- `Trajectory`
- `PointCloud`
- `Sphere`
- `CameraFrustum`
- `ImagePlane`
- `CustomDrawable`

Each drawable object implements:

```python
draw()
```

The visualizer does not know how each object is drawn. It simply activates a viewport and calls:

```python
viewport.scene.draw()
```

This makes the framework modular and easy to extend.

---

# Coordinate System

The framework itself does not enforce a strict world convention.

However, all poses are expected to be 4x4 homogeneous transformations:

```python
T = np.eye(4)
T[:3, :3] = R
T[:3, 3] = t
```

where:

- `R` is a 3x3 rotation matrix
- `t` is a 3D translation vector

A point in local coordinates can be transformed to world coordinates as:

```python
p_world_h = T @ p_local_h
```

The `Axis` object uses the following color convention:

| Axis | Color |
|---|---|
| X | Red |
| Y | Green |
| Z | Blue |

The `ImagePlane` object lies in its local XY plane and has its local normal along local positive Z.

The Pangolin camera up-axis can be configured:

```python
camera_up=pango.AxisY
```

or:

```python
camera_up=pango.AxisZ
```

For robotics/SLAM, `pango.AxisZ` is often convenient when Z is up.

---

# Package API Overview

Typical imports:

```python
from visualization import (
    PangolinVisualizer,
    Drawable,
    Grid,
    Axis,
    Trajectory,
    PointCloud,
    Sphere,
    CameraFrustum,
    ImagePlane,
    CustomDrawable,
    Scene,
    as_color,
    ensure_vec3,
    ensure_points,
    ensure_pose,
    pose_from_position_orientation,
    set_gl_color,
    draw_line,
    load_tum_trajectory,
)
```

---

# PangolinVisualizer

Main class for creating and managing a Pangolin visualization window.

```python
from visualization import PangolinVisualizer
```

---

## Constructor

```python
PangolinVisualizer(
    title="Pangolin Visualizer",
    width=1280,
    height=720,
    fx=420.0,
    fy=420.0,
    cx=None,
    cy=None,
    near=0.1,
    far=1000.0,
    camera_eye=(0.0, 0.0, 3.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisY,
    background_color=(1.0, 1.0, 1.0, 1.0),
    enable_depth_test=True,
    initialize_glut=True,
    create_default_viewport=True,
)
```

---

## Parameters

### `title: str`

Window title.

```python
title="Trajectory Viewer"
```

### `width: int`

Window width in pixels.

### `height: int`

Window height in pixels.

### `fx, fy: float`

Camera projection focal lengths.

Used internally by:

```python
pango.ProjectionMatrix(...)
```

### `cx, cy: Optional[float]`

Camera projection principal point.

If `None`, defaults to:

```python
cx = width / 2
cy = height / 2
```

### `near: float`

Near clipping plane.

### `far: float`

Far clipping plane.

### `camera_eye: tuple`

Initial camera position for the default viewport.

Example:

```python
camera_eye=(0.0, -3.0, 2.0)
```

### `camera_target: tuple`

Initial look-at target for the default viewport.

Example:

```python
camera_target=(0.0, 0.0, 0.0)
```

### `camera_up`

Pangolin camera up axis for the default viewport.

Examples:

```python
camera_up=pango.AxisY
camera_up=pango.AxisZ
```

### `background_color`

RGBA background color in range `[0, 1]`.

Example:

```python
background_color=(1.0, 1.0, 1.0, 1.0)
```

### `enable_depth_test`

Enables OpenGL depth test:

```python
glEnable(GL_DEPTH_TEST)
```

### `initialize_glut`

Attempts to initialize GLUT. Required for `Sphere`, because it uses:

```python
glut.glutSolidSphere(...)
```

### `create_default_viewport`

If `True`, creates a default viewport named:

```text
main
```

covering the full window.

For custom multi-viewport layouts, set:

```python
create_default_viewport=False
```

Example:

```python
viz = PangolinVisualizer(
    title="Dashboard",
    create_default_viewport=False,
)
```

---

## Viewport Methods

### `add_viewport(...)`

Create a sub-display/viewport inside the window.

```python
viz.add_viewport(
    name="trajectory",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)
```

Bounds are normalized fractions in `[0, 1]`.

```text
left   = 0.0 means left edge of window
right  = 1.0 means right edge of window
bottom = 0.0 means bottom edge of window
top    = 1.0 means top edge of window
```

### `remove_viewport(name)`

Remove a viewport from the visualizer registry.

```python
viz.remove_viewport("image_0")
```

### `get_viewport(name="main")`

Return a viewport or `None`.

```python
vp = viz.get_viewport("trajectory")
```

### `require_viewport(name="main")`

Return a viewport or raise `KeyError`.

```python
vp = viz.require_viewport("trajectory")
```

### `viewport_names()`

Return all viewport names.

```python
print(viz.viewport_names())
```

---

## Scene Methods

All scene methods accept a `viewport` argument.

If omitted, they use:

```text
main
```

### `add(obj, name=None, replace=True, viewport="main")`

Add a drawable object to a viewport scene.

```python
from visualization import Grid

grid = Grid(size=5.0)
viz.add(grid, name="main_grid", viewport="trajectory")
```

Returns the added object.

---

### `remove(name, viewport="main")`

Remove object from a viewport scene.

```python
viz.remove("main_grid", viewport="trajectory")
```

---

### `get(name, viewport="main")`

Get object by name.

Returns object or `None`.

```python
traj = viz.get("trajectory", viewport="trajectory")
if traj is not None:
    traj.clear()
```

---

### `require(name, viewport="main")`

Get object by name.

Raises `KeyError` if it does not exist.

```python
traj = viz.require("trajectory", viewport="trajectory")
```

---

### `clear_scene(viewport="main")`

Remove all objects from one viewport scene.

```python
viz.clear_scene(viewport="trajectory")
```

---

### `clear_all_scenes()`

Remove all objects from all viewport scenes.

```python
viz.clear_all_scenes()
```

---

## Convenience Object Creation Methods

These methods create the object, add it to a viewport scene, and return it.

All methods accept:

```python
viewport="main"
```

For example:

```python
viz.add_grid(viewport="trajectory")
viz.add_image_plane(viewport="image_0")
```

### `add_grid`

```python
grid = viz.add_grid(
    name="grid",
    viewport="trajectory",
    size=4.0,
    step=0.2,
    centered=True,
)
```

### `add_axis`

```python
axis = viz.add_axis(
    name="world_axis",
    viewport="trajectory",
    scale=1.0,
)
```

### `add_trajectory`

```python
trajectory = viz.add_trajectory(
    name="trajectory",
    viewport="trajectory",
    color=(1.0, 0.0, 0.0, 1.0),
)
```

### `add_point_cloud`

```python
cloud = viz.add_point_cloud(
    name="landmarks",
    viewport="trajectory",
    point_size=3.0,
)
```

### `add_sphere`

```python
sphere = viz.add_sphere(
    name="robot",
    viewport="trajectory",
    position=(0, 0, 0),
    radius=0.05,
)
```

### `add_camera_frustum`

```python
camera = viz.add_camera_frustum(
    name="camera",
    viewport="trajectory",
    scale=0.15,
)
```

### `add_image_plane`

Creates an `ImagePlane`, adds it to the selected viewport scene, and returns it.

```python
image_plane = viz.add_image_plane(
    name="debug_image",
    viewport="image_0",
    image=image_rgb,
    width=1.0,
    height=None,
    alpha=1.0,
)
```

### `add_custom`

```python
custom = viz.add_custom(
    draw_callback=my_draw_function,
    name="custom_object",
    viewport="trajectory",
)
```

---

## Rendering Methods

### `render(finish_frame=True)`

Render all viewports in the window.

```python
viz.render()
```

Use this in an update loop:

```python
while not viz.should_quit():
    update_objects()
    viz.render()
```

---

### `render_viewport(viewport, clear=False, finish_frame=False)`

Render only one viewport.

Usually, use `render()` instead.

```python
viz.render_viewport("image_0")
```

---

### `spin(target_fps=None)`

Start a blocking render loop.

```python
viz.spin()
```

With approximate FPS limit:

```python
viz.spin(target_fps=60)
```

Use `spin()` when your scene is static or after your animation/update loop has finished.

---

### `should_quit()`

Returns `True` if Pangolin window should close.

```python
if viz.should_quit():
    break
```

---

### `save_image(filename)`

Save the current full framebuffer to an image file.

```python
viz.render()
viz.save_image("screenshot.png")
```

Requires:

```bash
pip install opencv-python
```

---

# Viewport

A `Viewport` represents one Pangolin sub-display.

Each viewport owns:

- name
- Pangolin display
- OpenGL render state
- camera handler
- scene

Internally, it is represented by a dataclass:

```python
@dataclass
class Viewport:
    name: str
    display: object
    render_state: object
    handler: object
    scene: Scene
```

You usually do not instantiate `Viewport` manually. Use:

```python
viz.add_viewport(...)
```

---

## Viewport Bounds

Viewport bounds use normalized window coordinates:

```text
left, right, bottom, top in [0, 1]
```

Examples:

### Full Window

```python
left=0.0
right=1.0
bottom=0.0
top=1.0
```

### Left Half

```python
left=0.0
right=0.5
bottom=0.0
top=1.0
```

### Top Right Quadrant

```python
left=0.5
right=1.0
bottom=0.5
top=1.0
```

### Bottom Right Quadrant

```python
left=0.5
right=1.0
bottom=0.0
top=0.5
```

---

# Multi-Viewport Layouts

Multi-viewport support is useful for dashboards.

For example, one window can contain:

- a large 3D trajectory view
- four camera/debug image views
- a map view
- a local object view

---

## Create a Multi-Viewport Window

```python
viz = PangolinVisualizer(
    title="Dashboard",
    width=1600,
    height=900,
    background_color=(0.05, 0.05, 0.05, 1.0),
    create_default_viewport=False,
)
```

---

## Add a Trajectory Viewport

```python
viz.add_viewport(
    name="trajectory",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)
```

---

## Add Four Image Viewports in a 2x2 Grid

```python
image_layouts = {
    "image_0": dict(left=0.65, right=0.825, bottom=0.5, top=1.0),
    "image_1": dict(left=0.825, right=1.0, bottom=0.5, top=1.0),
    "image_2": dict(left=0.65, right=0.825, bottom=0.0, top=0.5),
    "image_3": dict(left=0.825, right=1.0, bottom=0.0, top=0.5),
}

for name, bounds in image_layouts.items():
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
```

This creates:

```text
+--------------------------------+----------------+----------------+
|                                |    image_0     |    image_1     |
|                                |                |                |
|          trajectory            +----------------+----------------+
|                                |    image_2     |    image_3     |
|                                |                |                |
+--------------------------------+----------------+----------------+
```

---

## Add Objects to Specific Viewports

```python
traj = viz.add_trajectory(
    name="estimated",
    viewport="trajectory",
    color=(1, 0, 0, 1),
)

img0 = viz.add_image_plane(
    name="panel_0",
    viewport="image_0",
    image=image0,
    width=1.7,
)

img1 = viz.add_image_plane(
    name="panel_1",
    viewport="image_1",
    image=image1,
    width=1.7,
)
```

---

## Render All Viewports

```python
while not viz.should_quit():
    update_data()
    viz.render()
```

`viz.render()` activates each viewport and draws its corresponding scene.

---

# Scene

The `Scene` class is an ordered object container.

Usually, you do not need to instantiate it manually because every viewport owns one.

If a default viewport exists, you can access:

```python
viz.scene
```

which is equivalent to:

```python
viz.require_viewport("main").scene
```

For custom viewports:

```python
trajectory_scene = viz.require_viewport("trajectory").scene
image_scene = viz.require_viewport("image_0").scene
```

---

## Constructor

```python
Scene()
```

---

## Properties

### `objects`

Dictionary:

```python
Dict[str, Drawable]
```

Maps object names to drawable objects.

### `draw_order`

List of object names defining rendering order.

---

## Methods

### `add(obj, name=None, replace=True)`

Add a drawable.

```python
scene.add(grid, name="grid")
```

If `replace=False` and the name already exists, raises `KeyError`.

---

### `remove(name)`

Remove object.

```python
scene.remove("grid")
```

---

### `get(name)`

Return object or `None`.

```python
obj = scene.get("grid")
```

---

### `require(name)`

Return object or raise `KeyError`.

```python
obj = scene.require("grid")
```

---

### `clear()`

Remove all objects.

```python
scene.clear()
```

---

### `names()`

Return object names in draw order.

```python
print(scene.names())
```

---

### `set_visible(name, visible)`

Show/hide an object.

```python
scene.set_visible("grid", False)
```

---

### `draw()`

Draw all objects in order.

Normally called internally by:

```python
viz.render()
```

---

# Drawable

Base abstract class for all scene objects.

You normally subclass this when adding new object types.

---

## Constructor

```python
Drawable(
    name=None,
    visible=True,
    color=(1.0, 1.0, 1.0, 1.0),
    line_width=1.0,
    point_size=3.0,
    properties=None,
)
```

---

## Common Properties

### `name`

Object name inside a `Scene`.

```python
obj.name
```

### `visible`

Whether object should be drawn.

```python
obj.visible = False
```

### `color`

RGB or RGBA tuple.

```python
obj.color = (1.0, 0.0, 0.0, 1.0)
```

### `line_width`

OpenGL line width.

```python
obj.line_width = 2.0
```

### `point_size`

OpenGL point size.

```python
obj.point_size = 5.0
```

### `properties`

Generic dictionary for custom user data.

```python
obj.properties["scale"] = 2.0
```

---

## Methods

### `draw()`

Abstract method. Subclasses implement this.

```python
def draw(self):
    ...
```

### `set_visible(visible)`

```python
obj.set_visible(False)
```

Returns self.

### `show()`

```python
obj.show()
```

### `hide()`

```python
obj.hide()
```

### `set_color(color)`

```python
obj.set_color((0.0, 1.0, 0.0, 1.0))
```

### `set_line_width(width)`

```python
obj.set_line_width(3.0)
```

### `set_point_size(size)`

```python
obj.set_point_size(6.0)
```

### `set_property(key, value)`

```python
obj.set_property("scale", 0.5)
```

### `get_property(key, default=None)`

```python
scale = obj.get_property("scale", 1.0)
```

---

# Grid

Draws a grid on selected coordinate planes.

```python
from visualization import Grid
```

---

## Constructor

```python
Grid(
    size=2.0,
    step=0.1,
    origin=(0.0, 0.0, 0.0),
    centered=False,
    draw_xy=True,
    draw_xz=False,
    draw_yz=False,
    color=(0.5, 0.5, 0.5, 1.0),
    line_width=1.0,
    visible=True,
    name="grid",
)
```

---

## Parameters

### `size`

Total grid size.

If `centered=False`, grid spans:

```text
0 to size
```

from `origin`.

If `centered=True`, grid spans:

```text
-size/2 to +size/2
```

around `origin`.

### `step`

Spacing between grid lines.

### `origin`

Grid origin.

```python
origin=(0.0, 0.0, 0.0)
```

### `centered`

Whether grid is centered around origin.

### `draw_xy`

Draw grid on XY plane.

### `draw_xz`

Draw grid on XZ plane.

### `draw_yz`

Draw grid on YZ plane.

### `color`

Grid color.

### `line_width`

Line width.

### `visible`

Visibility flag.

---

## Examples

### XY Ground Plane

```python
viz.add_grid(
    name="ground",
    viewport="trajectory",
    size=10.0,
    step=0.5,
    centered=True,
    draw_xy=True,
    draw_xz=False,
    draw_yz=False,
)
```

### Full 3D Grid

```python
viz.add_grid(
    name="grid_3d",
    viewport="trajectory",
    size=2.0,
    step=0.1,
    centered=False,
    draw_xy=True,
    draw_xz=True,
    draw_yz=True,
)
```

---

# Axis

Draws coordinate axes for a pose.

```python
from visualization import Axis
```

---

## Constructor

```python
Axis(
    pose=None,
    scale=1.0,
    line_width=2.0,
    visible=True,
    name="axis",
)
```

---

## Parameters

### `pose`

4x4 homogeneous matrix.

If `None`, identity pose is used.

### `scale`

Axis length.

### `line_width`

Axis line width.

### `visible`

Visibility flag.

---

## Methods

### `set_pose(pose)`

Update axis pose.

```python
axis.set_pose(T)
```

### `set_scale(scale)`

Update axis length.

```python
axis.set_scale(0.25)
```

---

## Example

```python
axis = viz.add_axis(
    name="robot_axis",
    viewport="trajectory",
    scale=0.2,
)

axis.set_pose(T_robot)
```

---

# Trajectory

Draws connected line segments from a sequence of poses or positions.

```python
from visualization import Trajectory
```

---

## Constructor

```python
Trajectory(
    poses=None,
    positions=None,
    color=(1.0, 0.0, 0.0, 1.0),
    line_width=2.0,
    draw_latest_axis=True,
    axis_scale=0.1,
    visible=True,
    name="trajectory",
)
```

---

## Parameters

### `poses`

Iterable of 4x4 homogeneous transforms.

```python
trajectory = Trajectory(poses=poses)
```

### `positions`

Iterable of 3D positions.

```python
trajectory = Trajectory(positions=positions)
```

If both `poses` and `positions` are provided, `poses` are used.

### `color`

Trajectory line color.

### `line_width`

Trajectory line width.

### `draw_latest_axis`

If `True` and trajectory was built from poses, draw coordinate axis at latest pose.

### `axis_scale`

Scale of latest pose axis.

### `visible`

Visibility flag.

---

## Methods

### `set_poses(poses)`

Replace trajectory with poses.

```python
trajectory.set_poses(poses)
```

Each pose must be shape `(4, 4)`.

### `set_positions(positions)`

Replace trajectory with positions.

```python
trajectory.set_positions(positions)
```

Each position must have 3 elements.

### `append_pose(pose)`

Append one pose.

```python
trajectory.append_pose(T)
```

### `append_position(position)`

Append one position.

```python
trajectory.append_position([x, y, z])
```

### `clear()`

Clear trajectory.

```python
trajectory.clear()
```

### `latest_pose()`

Return latest pose or `None`.

```python
T = trajectory.latest_pose()
```

### `latest_position()`

Return latest position or `None`.

```python
p = trajectory.latest_position()
```

---

## Examples

### Add and Update Incrementally

```python
traj = viz.add_trajectory(
    name="estimated",
    viewport="trajectory",
    color=(1.0, 0.0, 0.0, 1.0),
    draw_latest_axis=True,
)

for T in poses:
    traj.append_pose(T)
    viz.render()
```

### Compare Estimated and Ground Truth

```python
est = viz.add_trajectory(
    name="estimated",
    viewport="trajectory",
    color=(1.0, 0.0, 0.0, 1.0),
)

gt = viz.add_trajectory(
    name="ground_truth",
    viewport="trajectory",
    color=(0.0, 1.0, 0.0, 1.0),
)

est.set_poses(estimated_poses)
gt.set_poses(gt_poses)

viz.spin()
```

---

# PointCloud

Draws Nx3 points.

```python
from visualization import PointCloud
```

---

## Constructor

```python
PointCloud(
    points=None,
    colors=None,
    color=(0.0, 1.0, 0.0, 1.0),
    point_size=5.0,
    visible=True,
    name="point_cloud",
)
```

---

## Parameters

### `points`

Array of shape:

```python
(N, 3)
```

### `colors`

Optional per-point colors of shape:

```python
(N, 3)
```

or:

```python
(N, 4)
```

### `color`

Global color if `colors=None`.

### `point_size`

OpenGL point size.

### `visible`

Visibility flag.

---

## Methods

### `set_points(points, colors=None)`

Replace points.

```python
cloud.set_points(points)
```

With per-point colors:

```python
cloud.set_points(points, colors=colors)
```

### `append_points(points, colors=None)`

Append points.

```python
cloud.append_points(new_points)
```

### `clear()`

Clear points.

```python
cloud.clear()
```

---

## Examples

### Single Color Cloud

```python
points = np.random.randn(1000, 3)

cloud = viz.add_point_cloud(
    name="landmarks",
    viewport="trajectory",
    color=(0.0, 1.0, 0.0, 1.0),
    point_size=3.0,
)

cloud.set_points(points)
```

### Per-Point Colors

```python
points = np.random.randn(1000, 3)
colors = np.random.rand(1000, 3)

cloud.set_points(points, colors=colors)
```

---

# Sphere

Draws a solid sphere using GLUT.

```python
from visualization import Sphere
```

---

## Constructor

```python
Sphere(
    position=(0.0, 0.0, 0.0),
    radius=0.05,
    color=(0.0, 0.0, 1.0, 1.0),
    slices=20,
    stacks=20,
    visible=True,
    name="sphere",
)
```

---

## Parameters

### `position`

Sphere center.

### `radius`

Sphere radius.

### `color`

Sphere color.

### `slices`

Sphere longitudinal subdivisions.

Higher value gives smoother sphere but costs more.

### `stacks`

Sphere latitudinal subdivisions.

### `visible`

Visibility flag.

---

## Methods

### `set_position(position)`

Update sphere position.

```python
sphere.set_position([x, y, z])
```

### `set_radius(radius)`

Update sphere radius.

```python
sphere.set_radius(0.1)
```

---

## Example

```python
sphere = viz.add_sphere(
    name="robot",
    viewport="trajectory",
    radius=0.05,
    color=(1.0, 0.0, 0.0, 1.0),
)

while not viz.should_quit():
    sphere.set_position(current_position)
    viz.render()
```

---

# CameraFrustum

Draws a simple camera frustum from a 4x4 pose.

```python
from visualization import CameraFrustum
```

---

## Constructor

```python
CameraFrustum(
    pose=None,
    scale=0.2,
    color=(0.0, 0.0, 1.0, 1.0),
    line_width=1.5,
    visible=True,
    name="camera_frustum",
)
```

---

## Parameters

### `pose`

4x4 camera pose.

If `None`, identity is used.

### `scale`

Frustum size.

### `color`

Frustum line color.

### `line_width`

Line width.

### `visible`

Visibility flag.

---

## Methods

### `set_pose(pose)`

Update camera frustum pose.

```python
camera.set_pose(T_camera_world)
```

### `set_scale(scale)`

Update frustum size.

```python
camera.set_scale(0.25)
```

---

## Example

```python
camera = viz.add_camera_frustum(
    name="current_camera",
    viewport="trajectory",
    scale=0.15,
    color=(0.0, 0.0, 1.0, 1.0),
)

for T in poses:
    camera.set_pose(T)
    viz.render()
```

---

# ImagePlane

Draws an image as a textured plane inside the 3D scene.

`ImagePlane` is useful for visualizing:

- camera frames
- debug images
- semantic segmentation masks
- optical flow previews
- keyframes
- map textures
- occupancy images
- local map patches
- image overlays inside the 3D world
- dashboard image panels in dedicated viewports

The image is uploaded as an OpenGL texture and rendered on a rectangular plane.

---

## Import

```python
from visualization import ImagePlane
```

Or use the visualizer convenience method:

```python
image_plane = viz.add_image_plane(...)
```

---

## Constructor

```python
ImagePlane(
    image=None,
    pose=None,
    width=1.0,
    height=None,
    alpha=1.0,
    flip_y=True,
    visible=True,
    name="image_plane",
)
```

---

## Parameters

### `image`

Optional image as a NumPy array.

Supported shapes:

```python
(H, W)
(H, W, 1)
(H, W, 3)
(H, W, 4)
```

Supported dtypes:

```python
np.uint8
np.float32
np.float64
```

If the image dtype is floating point, values are expected in range:

```text
[0, 1]
```

and are internally converted to `uint8`.

Examples:

```python
gray = np.zeros((480, 640), dtype=np.uint8)
rgb = np.zeros((480, 640, 3), dtype=np.uint8)
rgba = np.zeros((480, 640, 4), dtype=np.uint8)
```

---

### `pose`

4x4 homogeneous transform of the image plane in world coordinates.

If `None`, identity pose is used.

```python
T_image = np.eye(4)
T_image[:3, 3] = [0.0, 0.0, 1.0]
```

The image plane lies in its local XY plane.

Its local normal direction is local positive Z.

---

### `width`

Width of the image plane in world units.

```python
width=1.0
```

---

### `height`

Height of the image plane in world units.

If `height=None`, the height is automatically computed from the image aspect ratio:

```python
height = width * image_height / image_width
```

Example:

```python
image_plane = viz.add_image_plane(
    image=image,
    width=1.0,
    height=None,
)
```

---

### `alpha`

Global opacity multiplier.

```python
alpha=1.0
```

Use lower values for transparency:

```python
alpha=0.5
```

---

### `flip_y`

Controls vertical texture coordinate flipping.

Usually, OpenCV/numpy images have origin at the top-left.

OpenGL texture coordinates usually have origin at the bottom-left.

Therefore, this is often useful:

```python
flip_y=True
```

If the image appears upside down, toggle this value.

---

### `visible`

Visibility flag.

```python
visible=True
```

---

### `name`

Scene object name.

```python
name="camera_image"
```

---

## Methods

### `set_image(image)`

Set or update the image texture.

```python
image_plane.set_image(image)
```

The new image is uploaded to the GPU on the next `draw()` call.

---

### `clear_image()`

Remove the current image.

```python
image_plane.clear_image()
```

---

### `set_pose(pose)`

Update image plane pose.

```python
image_plane.set_pose(T_image)
```

---

### `set_size(width, height=None)`

Update plane size.

If `height=None`, aspect ratio is preserved.

```python
image_plane.set_size(width=1.5, height=None)
```

---

### `set_alpha(alpha)`

Update global transparency.

```python
image_plane.set_alpha(0.6)
```

---

### `delete_texture()`

Delete the OpenGL texture manually.

Usually not needed, but useful if you want to explicitly release GPU texture memory.

```python
image_plane.delete_texture()
```

---

## Coordinate Convention

The image is drawn on a plane centered at the local origin:

```text
(-w/2,  h/2, 0) -------- ( w/2,  h/2, 0)
        |                         |
        |          image          |
        |                         |
(-w/2, -h/2, 0) -------- ( w/2, -h/2, 0)
```

The local normal is:

```text
+Z
```

The final world position is controlled by:

```python
T_world_image
```

or simply:

```python
pose
```

Example:

```python
T_image = np.eye(4)
T_image[:3, 3] = [0.0, 0.0, 0.5]

image_plane.set_pose(T_image)
```

---

## Basic Example

```python
import cv2
import numpy as np
import pypangolin as pango

from visualization import PangolinVisualizer

viz = PangolinVisualizer(
    title="ImagePlane Example",
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

viz.add_grid(
    name="grid",
    size=4.0,
    step=0.2,
    centered=True,
    draw_xy=True,
)

viz.add_axis(
    name="world_axis",
    scale=0.5,
)

image_bgr = cv2.imread("image.png")

if image_bgr is None:
    raise FileNotFoundError("Could not load image.png")

image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

T_image = np.eye(4)
T_image[:3, 3] = [0.0, 0.0, 0.6]

image_plane = viz.add_image_plane(
    name="image",
    image=image_rgb,
    pose=T_image,
    width=1.0,
    height=None,
    alpha=1.0,
    flip_y=True,
)

viz.spin(target_fps=60)
```

---

## Dynamic Image Update Example

This is useful for displaying live camera frames.

```python
import cv2
import pypangolin as pango

from visualization import PangolinVisualizer

viz = PangolinVisualizer(
    title="Live ImagePlane",
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

image_plane = viz.add_image_plane(
    name="camera_frame",
    width=1.5,
    alpha=1.0,
)

cap = cv2.VideoCapture(0)

while not viz.should_quit():
    ok, frame_bgr = cap.read()

    if not ok:
        break

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    image_plane.set_image(frame_rgb)

    viz.render()

cap.release()
```

---

## ImagePlane in a Dedicated Viewport

A common dashboard pattern is to create one viewport per image.

```python
viz = PangolinVisualizer(
    title="Image Dashboard",
    create_default_viewport=False,
)

viz.add_viewport(
    name="image_0",
    left=0.0,
    right=0.5,
    bottom=0.5,
    top=1.0,
    camera_eye=(0.0, 0.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisY,
)

image_plane = viz.add_image_plane(
    name="panel_0",
    viewport="image_0",
    image=image_rgb,
    pose=np.eye(4),
    width=1.7,
    height=None,
)
```

---

## ImagePlane Attached to Camera Pose

If your camera pose is `T_wc`, you can place the image plane near the camera.

```python
T_wc = np.eye(4)

T_camera_to_image = np.eye(4)
T_camera_to_image[:3, 3] = [0.0, 0.0, 0.5]

T_image = T_wc @ T_camera_to_image

image_plane.set_pose(T_image)
```

Depending on your camera convention, you may need to rotate the image plane so that it faces the viewer.

For example, rotate the image plane 180 degrees around X:

```python
R_flip = np.eye(4)
R_flip[:3, :3] = np.array(
    [
        [1.0,  0.0,  0.0],
        [0.0, -1.0,  0.0],
        [0.0,  0.0, -1.0],
    ]
)

T_image = T_wc @ T_camera_to_image @ R_flip
image_plane.set_pose(T_image)
```

---

## Creating a Synthetic Image

You can create an image directly with NumPy.

```python
import numpy as np

height = 180
width = 320

image = np.zeros((height, width, 3), dtype=np.uint8)

yy, xx = np.meshgrid(
    np.linspace(0.0, 1.0, height),
    np.linspace(0.0, 1.0, width),
    indexing="ij",
)

image[..., 0] = (255.0 * xx).astype(np.uint8)
image[..., 1] = (255.0 * yy).astype(np.uint8)
image[..., 2] = 128

image_plane.set_image(image)
```

---

## Transparency

`ImagePlane` supports global alpha:

```python
image_plane.set_alpha(0.5)
```

If your image has an alpha channel, use shape:

```python
(H, W, 4)
```

Example:

```python
rgba = np.zeros((480, 640, 4), dtype=np.uint8)
rgba[..., 0] = 255
rgba[..., 3] = 128

image_plane.set_image(rgba)
```

---

## ImagePlane Common Issues

### Image appears upside down

Toggle:

```python
image_plane.flip_y = not image_plane.flip_y
```

or construct with:

```python
flip_y=False
```

---

### Image colors look wrong

If loading with OpenCV, remember OpenCV loads images as BGR.

Convert to RGB:

```python
image_bgr = cv2.imread("image.png")
image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
```

---

### Image is not visible

Check:

1. The image is not `None`.
2. The image plane pose is in front of the Pangolin camera.
3. The plane is not too small.
4. The camera is not looking at the back side only.
5. Try increasing width:

```python
image_plane.set_size(width=2.0)
```

6. Try placing it at world origin:

```python
T = np.eye(4)
T[:3, 3] = [0.0, 0.0, 0.5]
image_plane.set_pose(T)
```

For image-only viewports, use:

```python
camera_eye=(0.0, 0.0, 2.0)
camera_target=(0.0, 0.0, 0.0)
```

and place the image at:

```python
pose=np.eye(4)
```

---

### Image is black or transparent

Check:

1. Image dtype.
2. Floating point images are in `[0, 1]`, not `[0, 255]`.
3. Alpha is not zero.

```python
image_plane.set_alpha(1.0)
```

---

### Texture warnings about `GL_CLAMP`

Some OpenGL implementations prefer:

```python
GL_CLAMP_TO_EDGE
```

instead of:

```python
GL_CLAMP
```

If you see warnings, update the code:

```python
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
```

---

# CustomDrawable

Allows user-defined OpenGL rendering logic.

```python
from visualization import CustomDrawable
```

---

## Constructor

```python
CustomDrawable(
    draw_callback,
    name="custom",
    visible=True,
    color=(1.0, 1.0, 1.0, 1.0),
    line_width=1.0,
    point_size=3.0,
    properties=None,
)
```

---

## Callback Signature

```python
def draw_callback(obj: CustomDrawable) -> None:
    ...
```

The callback receives the drawable object itself, so it can access:

```python
obj.color
obj.line_width
obj.point_size
obj.properties
```

---

## Example: Triangle

```python
from OpenGL.GL import *
from visualization import set_gl_color

def draw_triangle(obj):
    set_gl_color(obj.color)

    scale = obj.properties.get("scale", 1.0)

    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(scale, 0.0, 0.0)
    glVertex3f(0.5 * scale, scale, 0.0)
    glEnd()

triangle = viz.add_custom(
    draw_callback=draw_triangle,
    name="triangle",
    color=(1.0, 0.5, 0.0, 1.0),
    properties={
        "scale": 0.5,
    },
)
```

---

## Example: Dynamic Custom Object

```python
def draw_moving_line(obj):
    set_gl_color(obj.color)
    p1 = obj.properties["p1"]
    p2 = obj.properties["p2"]

    glBegin(GL_LINES)
    glVertex3f(*p1)
    glVertex3f(*p2)
    glEnd()

line = viz.add_custom(
    draw_callback=draw_moving_line,
    name="moving_line",
    color=(1.0, 0.0, 1.0, 1.0),
    properties={
        "p1": [0, 0, 0],
        "p2": [1, 0, 0],
    },
)

line.properties["p2"] = [0, 1, 0]
```

---

# Utility Functions

The package exposes several utility functions.

---

## `as_color(color)`

Convert RGB/RGBA to RGBA.

```python
rgba = as_color((1.0, 0.0, 0.0))
# returns (1.0, 0.0, 0.0, 1.0)
```

---

## `ensure_vec3(value, name="vector")`

Validate and convert value to shape `(3,)`.

```python
p = ensure_vec3([1, 2, 3])
```

Raises `ValueError` if invalid.

---

## `ensure_points(points, name="points")`

Validate and convert input to shape `(N, 3)`.

```python
points = ensure_points(np.random.randn(100, 3))
```

---

## `ensure_pose(pose, name="pose")`

Validate pose is shape `(4, 4)`.

```python
T = ensure_pose(np.eye(4))
```

---

## `pose_from_position_orientation(position, orientation=None)`

Create a 4x4 homogeneous transform.

```python
T = pose_from_position_orientation(
    position=[1, 2, 3],
    orientation=np.eye(3),
)
```

If orientation is `None`, identity rotation is used.

---

## `set_gl_color(color)`

Set OpenGL color.

```python
set_gl_color((1.0, 0.0, 0.0, 1.0))
```

---

## `draw_line(p1, p2, color, line_width=1.0)`

Draw a single OpenGL line.

```python
draw_line(
    p1=[0, 0, 0],
    p2=[1, 0, 0],
    color=(1, 0, 0, 1),
    line_width=2.0,
)
```

Usually used inside custom draw callbacks.

---

# Trajectory File Loading

The helper:

```python
load_tum_trajectory(path)
```

loads a TUM-style trajectory file.

---

## Expected Format

```text
timestamp tx ty tz qx qy qz qw
```

Example:

```text
0.000000 0.0 0.0 0.0 0.0 0.0 0.0 1.0
0.033333 0.1 0.0 0.0 0.0 0.0 0.01 0.99995
```

---

## Usage

```python
from visualization import load_tum_trajectory

poses = load_tum_trajectory("trajectory.txt")
```

Then:

```python
trajectory = viz.add_trajectory(name="loaded")
trajectory.set_poses(poses)
viz.spin()
```

---

# Common Usage Patterns

---

## Static Scene

Use this when the scene does not change.

```python
viz = PangolinVisualizer()

viz.add_grid(size=10, centered=True)
viz.add_axis(scale=1.0)

viz.spin()
```

---

## Dynamic Scene

Use this when objects update every frame.

```python
viz = PangolinVisualizer()

traj = viz.add_trajectory(name="trajectory")
sphere = viz.add_sphere(name="current_position")

while not viz.should_quit():
    T = get_current_pose()

    traj.append_pose(T)
    sphere.set_position(T[:3, 3])

    viz.render()
```

---

## Dynamic Image Scene

Use this when an image changes every frame.

```python
viz = PangolinVisualizer()

image_plane = viz.add_image_plane(
    name="debug_image",
    width=1.0,
    height=None,
    alpha=1.0,
)

while not viz.should_quit():
    image = get_debug_image_rgb()  # HxWx3, uint8 or float in [0, 1]

    image_plane.set_image(image)

    viz.render()
```

---

## Multi-Viewport Dashboard

Use this when you want separate visual areas inside one window.

```python
viz = PangolinVisualizer(
    title="Dashboard",
    width=1600,
    height=900,
    create_default_viewport=False,
)

viz.add_viewport(
    name="trajectory",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

viz.add_viewport(
    name="image_0",
    left=0.65,
    right=0.825,
    bottom=0.5,
    top=1.0,
    camera_eye=(0.0, 0.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisY,
)

traj = viz.add_trajectory(
    name="estimated",
    viewport="trajectory",
)

image_panel = viz.add_image_plane(
    name="panel_0",
    viewport="image_0",
    width=1.7,
)

while not viz.should_quit():
    traj.append_pose(get_pose())
    image_panel.set_image(get_image())

    viz.render()
```

---

## SLAM / VO Debugging

```python
viz = PangolinVisualizer(title="SLAM Debugger")

est = viz.add_trajectory(
    name="estimated",
    color=(1, 0, 0, 1),
)

gt = viz.add_trajectory(
    name="ground_truth",
    color=(0, 1, 0, 1),
)

landmarks = viz.add_point_cloud(
    name="landmarks",
    color=(0, 0, 1, 1),
    point_size=3,
)

camera = viz.add_camera_frustum(
    name="camera",
    scale=0.1,
)

debug_image = viz.add_image_plane(
    name="debug_image",
    width=1.0,
    alpha=1.0,
)

while not viz.should_quit():
    T_est = slam.get_pose()
    pts = slam.get_landmarks()
    image = slam.get_debug_image_rgb()

    est.append_pose(T_est)
    landmarks.set_points(pts)
    camera.set_pose(T_est)

    debug_image.set_image(image)

    # Optional: attach image near current camera pose.
    T_cam_to_img = np.eye(4)
    T_cam_to_img[:3, 3] = [0.0, 0.0, 0.5]
    debug_image.set_pose(T_est @ T_cam_to_img)

    viz.render()
```

---

## Multi-Viewport SLAM / VO Dashboard

```python
viz = PangolinVisualizer(
    title="SLAM Dashboard",
    width=1600,
    height=900,
    create_default_viewport=False,
)

viz.add_viewport(
    name="map",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

for name, bounds in {
    "rgb": dict(left=0.65, right=0.825, bottom=0.5, top=1.0),
    "depth": dict(left=0.825, right=1.0, bottom=0.5, top=1.0),
    "features": dict(left=0.65, right=0.825, bottom=0.0, top=0.5),
    "semantic": dict(left=0.825, right=1.0, bottom=0.0, top=0.5),
}.items():
    viz.add_viewport(
        name=name,
        camera_eye=(0.0, 0.0, 2.0),
        camera_target=(0.0, 0.0, 0.0),
        camera_up=pango.AxisY,
        **bounds,
    )

trajectory = viz.add_trajectory(viewport="map", name="trajectory")
landmarks = viz.add_point_cloud(viewport="map", name="landmarks")
camera = viz.add_camera_frustum(viewport="map", name="camera")

rgb_panel = viz.add_image_plane(viewport="rgb", name="rgb", width=1.7)
depth_panel = viz.add_image_plane(viewport="depth", name="depth", width=1.7)
feature_panel = viz.add_image_plane(viewport="features", name="features", width=1.7)
semantic_panel = viz.add_image_plane(viewport="semantic", name="semantic", width=1.7)

while not viz.should_quit():
    T = slam.get_pose()

    trajectory.append_pose(T)
    landmarks.set_points(slam.get_map_points())
    camera.set_pose(T)

    rgb_panel.set_image(slam.get_rgb_debug())
    depth_panel.set_image(slam.get_depth_debug())
    feature_panel.set_image(slam.get_feature_debug())
    semantic_panel.set_image(slam.get_semantic_debug())

    viz.render()
```

---

## Hide / Show Objects

```python
grid = viz.add_grid(name="grid")

grid.hide()
viz.render()

grid.show()
viz.render()
```

or:

```python
viz.scene.set_visible("grid", False)
```

For a specific viewport:

```python
viz.require_viewport("trajectory").scene.set_visible("grid", False)
```

---

## Modify Runtime Properties

```python
traj = viz.add_trajectory(name="trajectory")

traj.set_color((0.0, 0.0, 1.0, 1.0))
traj.set_line_width(4.0)

cloud = viz.add_point_cloud(name="points")
cloud.set_point_size(8.0)

image = viz.add_image_plane(name="image")
image.set_alpha(0.7)
image.set_size(width=2.0)
```

---

## Replace an Object

```python
viz.add_grid(name="grid", size=2.0)

# Replaces existing object with same name
viz.add_grid(name="grid", size=5.0)
```

To prevent replacement:

```python
viz.add(Grid(name="grid"), replace=False)
```

For a specific viewport:

```python
viz.add_grid(name="grid", viewport="trajectory", size=2.0)
viz.add_grid(name="grid", viewport="trajectory", size=5.0)
```

---

# Full Example

```python
import time
import numpy as np
import pypangolin as pango
from OpenGL.GL import *

from visualization import (
    PangolinVisualizer,
    CustomDrawable,
    set_gl_color,
)


def draw_triangle(obj: CustomDrawable):
    set_gl_color(obj.color)

    scale = obj.properties.get("scale", 1.0)

    glBegin(GL_TRIANGLES)
    glVertex3f(0, 0, 0)
    glVertex3f(scale, 0, 0)
    glVertex3f(0.5 * scale, scale, 0)
    glEnd()


def make_pose(i):
    t = i * 0.03
    x = np.cos(t)
    y = np.sin(t)
    z = 0.2 * np.sin(2.0 * t)

    T = np.eye(4)
    T[:3, 3] = [x, y, z]

    yaw = t + np.pi / 2
    c, s = np.cos(yaw), np.sin(yaw)

    T[:3, :3] = np.array([
        [c, -s, 0],
        [s, c, 0],
        [0, 0, 1],
    ])

    return T


def create_demo_image(width=320, height=180, frame_index=0):
    image = np.zeros((height, width, 3), dtype=np.uint8)

    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, height),
        np.linspace(0.0, 1.0, width),
        indexing="ij",
    )

    image[..., 0] = (255.0 * xx).astype(np.uint8)
    image[..., 1] = (255.0 * yy).astype(np.uint8)
    image[..., 2] = np.clip(
        127.0 + 127.0 * np.sin(8.0 * xx + frame_index * 0.03),
        0,
        255,
    ).astype(np.uint8)

    return image


viz = PangolinVisualizer(
    title="Full Example",
    width=1280,
    height=720,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

viz.add_grid(
    name="grid",
    size=4.0,
    step=0.2,
    centered=True,
    draw_xy=True,
)

viz.add_axis(
    name="world_axis",
    scale=0.5,
)

trajectory = viz.add_trajectory(
    name="trajectory",
    color=(1, 0, 0, 1),
    draw_latest_axis=True,
)

sphere = viz.add_sphere(
    name="current_position",
    radius=0.05,
    color=(1, 0.5, 0, 1),
)

camera = viz.add_camera_frustum(
    name="camera",
    scale=0.12,
)

image_plane = viz.add_image_plane(
    name="debug_image",
    image=create_demo_image(),
    width=0.8,
    height=None,
    alpha=0.95,
    flip_y=True,
)

points = np.random.uniform(-1, 1, size=(500, 3))
points[:, 2] *= 0.2

cloud = viz.add_point_cloud(
    name="points",
    color=(0, 0.5, 1, 1),
    point_size=3,
)

cloud.set_points(points)

viz.add_custom(
    draw_callback=draw_triangle,
    name="triangle",
    color=(1, 0.7, 0, 1),
    properties={"scale": 0.25},
)

for i in range(300):
    if viz.should_quit():
        break

    T = make_pose(i)

    trajectory.append_pose(T)
    sphere.set_position(T[:3, 3])
    camera.set_pose(T)

    T_img = T.copy()
    T_img[:3, 3] = T[:3, 3] + np.array([0.0, 0.0, 0.35])
    image_plane.set_pose(T_img)
    image_plane.set_image(create_demo_image(frame_index=i))

    viz.render()
    time.sleep(0.005)

viz.spin(target_fps=60)
```

---

# Multi-Viewport Full Example

This example creates one window with:

- trajectory viewport on the left
- four image viewports on the right

```python
import numpy as np
import pypangolin as pango

from visualization import PangolinVisualizer

viz = PangolinVisualizer(
    title="Trajectory + 2x2 Image Grid Viewports",
    width=1600,
    height=900,
    background_color=(0.05, 0.05, 0.05, 1.0),
    create_default_viewport=False,
)

viz.add_viewport(
    name="trajectory",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

image_layouts = {
    "image_0": dict(left=0.65, right=0.825, bottom=0.5, top=1.0),
    "image_1": dict(left=0.825, right=1.0, bottom=0.5, top=1.0),
    "image_2": dict(left=0.65, right=0.825, bottom=0.0, top=0.5),
    "image_3": dict(left=0.825, right=1.0, bottom=0.0, top=0.5),
}

for name, bounds in image_layouts.items():
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

trajectory = viz.add_trajectory(
    name="trajectory",
    viewport="trajectory",
    color=(1.0, 0.0, 0.0, 1.0),
)

image_panels = []
for i, viewport in enumerate(["image_0", "image_1", "image_2", "image_3"]):
    panel = viz.add_image_plane(
        name=f"panel_{i}",
        viewport=viewport,
        image=np.zeros((180, 320, 3), dtype=np.uint8),
        pose=np.eye(4),
        width=1.7,
        height=None,
    )
    image_panels.append(panel)

while not viz.should_quit():
    # Update trajectory and images here.
    viz.render()
```

For a complete runnable file, see:

```text
examples/multi_viewport_alternative_layout.py
```

---

# Multiple Windows

The recommended approach is to use one Pangolin window with multiple viewports.

Pangolin/OpenGL context management can be platform-dependent, and multiple OS-level windows in one Python process may not behave consistently across all systems.

Instead of:

```python
viz1 = PangolinVisualizer(title="Window 1")
viz2 = PangolinVisualizer(title="Window 2")
```

prefer:

```python
viz = PangolinVisualizer(
    title="Dashboard",
    create_default_viewport=False,
)

viz.add_viewport(name="view_1", left=0.0, right=0.5, bottom=0.0, top=1.0)
viz.add_viewport(name="view_2", left=0.5, right=1.0, bottom=0.0, top=1.0)
```

This is more reliable and gives better control over layout.

If you truly need multiple OS-level windows:

- use one visualizer per process for critical applications
- or create separate processes for independent viewers
- test multi-window behavior on your target platform

---

# Screenshots

Save current full framebuffer:

```python
viz.render()
viz.save_image("frame.png")
```

For animation export:

```python
for i, T in enumerate(poses):
    trajectory.append_pose(T)
    viz.render()
    viz.save_image(f"frames/{i:06d}.png")
```

Then convert frames to video with ffmpeg:

```bash
ffmpeg -framerate 30 -i frames/%06d.png -pix_fmt yuv420p output.mp4
```

For multi-viewport dashboards, the screenshot captures the entire dashboard window.

---

# Performance Notes

The current implementation uses simple immediate-mode OpenGL calls:

```python
glBegin(...)
glEnd()
```

This is easy to understand and convenient for debugging, but not optimal for very large datasets.

## Recommended Limits

For debugging and moderate scenes:

- trajectories: thousands to tens of thousands of poses
- point clouds: thousands to low hundreds of thousands of points depending on GPU/driver
- image planes: a few dynamic images at moderate resolution
- viewports: a handful of sub-displays is usually fine

For very large point clouds or high-resolution dynamic images, consider implementing:

- VBO-based point cloud rendering
- texture updates with `glTexSubImage2D`
- downsampling
- frustum culling
- level-of-detail rendering

---

## Multi-Viewport Performance

Each viewport activates its own display and draws its own scene.

Total rendering cost roughly scales with:

```text
number_of_viewports × scene_complexity_per_viewport
```

Recommendations:

- keep image-only viewport scenes simple
- use one `ImagePlane` per image viewport
- avoid drawing large point clouds in multiple viewports
- avoid unnecessary updates to image textures
- prefer moderate image resolution for debug panels

---

## Point Cloud Performance

With a single global color, `PointCloud` uses:

```python
pango.glDrawPoints(points)
```

This is generally faster than manually drawing each point.

With per-point colors, it uses:

```python
glBegin(GL_POINTS)
...
glEnd()
```

which is slower.

If performance matters, prefer one global color or implement a VBO-based colored point cloud.

---

## Trajectory Performance

Trajectory rendering currently redraws all line segments each frame.

For very long trajectories:

- downsample old poses
- keep only recent segments
- implement display lists/VBOs
- split trajectory into fixed chunks

---

## Sphere Performance

`Sphere` uses GLUT solid sphere rendering.

Many spheres can be expensive.

For many landmarks, use `PointCloud` instead.

---

## ImagePlane Performance

Updating an `ImagePlane` every frame uploads texture data to the GPU on the next draw call.

This is usually fine for small or medium debug images.

Recommended debug image sizes:

```text
320x180
640x360
640x480
```

For high-resolution images or multiple image planes, consider:

- reducing image resolution
- updating only when the image changes
- using `glTexSubImage2D`
- using persistent textures
- limiting frame rate
- avoiding unnecessary image copies

---

# Troubleshooting

## `ModuleNotFoundError: No module named 'pypangolin'`

Build Pangolin's Python bindings from the verified-working fork — see
[Pangolin / pypangolin](#pangolin--pypangolin) above. `pip install pypangolin` is not reliable
enough to depend on.

---

## `OpenGL.error.NullFunctionError`

This usually means OpenGL context is not properly created or a required OpenGL function is unavailable.

Check:

- Pangolin installed correctly
- graphics drivers installed
- running with display access
- not running in a headless terminal without OpenGL context

---

## Running on a Headless Server

Pangolin usually requires an OpenGL-capable display.

Possible solutions:

- run with X11 forwarding
- use VirtualGL
- use EGL-enabled Pangolin build
- run inside a desktop session
- use xvfb only if your OpenGL setup supports it

Example:

```bash
xvfb-run python examples/usage.py
```

This may or may not work depending on OpenGL driver support.

---

## GLUT Sphere Does Not Render

`Sphere` uses:

```python
glut.glutSolidSphere(...)
```

Make sure GLUT initializes correctly.

If you do not need spheres, set:

```python
initialize_glut=False
```

or avoid using `Sphere`.

---

## Window Opens Then Immediately Closes

Make sure your script keeps rendering:

```python
viz.spin()
```

or:

```python
while not viz.should_quit():
    viz.render()
```

---

## `KeyError: Viewport 'main' does not exist`

This happens when you created the visualizer with:

```python
create_default_viewport=False
```

and then tried to add an object without specifying a viewport:

```python
viz.add_grid()
```

Fix by specifying the target viewport:

```python
viz.add_grid(viewport="trajectory")
```

or create a default viewport:

```python
viz = PangolinVisualizer(create_default_viewport=True)
```

---

## Object Appears in the Wrong Viewport

Make sure you pass the correct viewport name:

```python
viz.add_image_plane(viewport="image_0")
```

not:

```python
viz.add_image_plane()
```

When omitted, `viewport="main"` is used.

---

## Viewport Bounds Error

Viewport bounds must satisfy:

```text
0 <= left < right <= 1
0 <= bottom < top <= 1
```

Correct:

```python
left=0.0
right=0.5
bottom=0.0
top=1.0
```

Incorrect:

```python
left=0.7
right=0.4
```

---

## Image Viewport is Empty

For image-only viewports, recommended camera setup is:

```python
camera_eye=(0.0, 0.0, 2.0)
camera_target=(0.0, 0.0, 0.0)
camera_up=pango.AxisY
```

and image pose:

```python
pose=np.eye(4)
```

Also check that the image panel width is visible:

```python
width=1.7
```

---

## `ValueError: pose must have shape 4x4`

All pose-based objects expect 4x4 homogeneous matrices.

Correct:

```python
T = np.eye(4)
T[:3, :3] = R
T[:3, 3] = t
```

Incorrect:

```python
T = np.eye(3)
```

---

## `ValueError: points must have shape Nx3`

Point clouds must be shaped:

```python
(N, 3)
```

Correct:

```python
points = np.random.randn(100, 3)
```

Incorrect:

```python
points = np.random.randn(3, 100)
```

Fix:

```python
points = points.T
```

---

## `ValueError: image must have shape HxW, HxWx3, or HxWx4`

`ImagePlane` expects images with shape:

```python
(H, W)
(H, W, 1)
(H, W, 3)
(H, W, 4)
```

Correct:

```python
image = np.zeros((480, 640, 3), dtype=np.uint8)
```

Incorrect:

```python
image = np.zeros((3, 480, 640), dtype=np.uint8)
```

Fix channel-first images by transposing:

```python
image = np.transpose(image, (1, 2, 0))
```

---

## Colors Look Wrong

Colors should be floats in range `[0, 1]`.

Correct:

```python
color=(1.0, 0.0, 0.0, 1.0)
```

Incorrect if interpreted as OpenGL float color:

```python
color=(255, 0, 0)
```

Convert:

```python
color=(255 / 255, 0 / 255, 0 / 255, 1.0)
```

For images loaded with OpenCV, convert BGR to RGB:

```python
image_bgr = cv2.imread("image.png")
image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
```

---

# Extending the Framework

There are several ways to add custom visualization.

---

## Option 1: Use `CustomDrawable`

Best for small/simple custom visualizations.

```python
def draw_object(obj):
    set_gl_color(obj.color)
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(1, 1, 1)
    glEnd()

custom = viz.add_custom(
    draw_callback=draw_object,
    name="my_object",
    viewport="trajectory",
)
```

---

## Option 2: Subclass `Drawable`

Best for reusable or complex objects.

```python
from OpenGL.GL import *
from visualization import Drawable, set_gl_color

class Box(Drawable):
    def __init__(self, center, size, **kwargs):
        super().__init__(**kwargs)
        self.center = center
        self.size = size

    def draw(self):
        if not self.visible:
            return

        set_gl_color(self.color)

        # Your OpenGL drawing code here.
        glBegin(GL_LINES)
        # ...
        glEnd()
```

Add it:

```python
box = Box(
    center=(0, 0, 0),
    size=(1, 1, 1),
    name="box",
    color=(1, 0, 0, 1),
)

viz.add(box, viewport="trajectory")
```

---

## Option 3: Build a Reusable Image-Based Object

For image-like objects, subclass `ImagePlane` or compose it.

Example:

```python
class KeyframeImage(ImagePlane):
    def __init__(self, keyframe_id, image, pose, **kwargs):
        super().__init__(image=image, pose=pose, **kwargs)
        self.keyframe_id = keyframe_id
```

Then:

```python
kf = KeyframeImage(
    keyframe_id=0,
    image=image_rgb,
    pose=T_keyframe,
    name="keyframe_0",
    width=0.5,
)

viz.add(kf, viewport="trajectory")
```

---

# Recommended Development Workflow

For robotics/SLAM debugging:

1. Create visualizer once.
2. Create viewports once.
3. Add persistent objects once to their target viewports.
4. Update object data every frame.
5. Call `viz.render()` once per iteration.

Example:

```python
viz = PangolinVisualizer(create_default_viewport=False)

viz.add_viewport(
    name="map",
    left=0.0,
    right=0.65,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, -3.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisZ,
)

viz.add_viewport(
    name="debug_image",
    left=0.65,
    right=1.0,
    bottom=0.0,
    top=1.0,
    camera_eye=(0.0, 0.0, 2.0),
    camera_target=(0.0, 0.0, 0.0),
    camera_up=pango.AxisY,
)

traj = viz.add_trajectory(name="trajectory", viewport="map")
cloud = viz.add_point_cloud(name="map_points", viewport="map")
camera = viz.add_camera_frustum(name="camera", viewport="map")
debug_image = viz.add_image_plane(name="debug_image", viewport="debug_image", width=1.7)

while not viz.should_quit():
    T = pipeline.current_pose()
    points = pipeline.current_map_points()
    image = pipeline.current_debug_image()

    traj.append_pose(T)
    cloud.set_points(points)
    camera.set_pose(T)
    debug_image.set_image(image)

    viz.render()
```

Avoid repeatedly creating/removing objects or viewports every frame unless necessary.

---

# API Summary

## Visualizer

```python
PangolinVisualizer(...)
viz.add_viewport(...)
viz.remove_viewport(name)
viz.get_viewport(name="main")
viz.require_viewport(name="main")
viz.viewport_names()
viz.add(obj, name=None, replace=True, viewport="main")
viz.remove(name, viewport="main")
viz.get(name, viewport="main")
viz.require(name, viewport="main")
viz.clear_scene(viewport="main")
viz.clear_all_scenes()
viz.add_grid(..., viewport="main")
viz.add_axis(..., viewport="main")
viz.add_trajectory(..., viewport="main")
viz.add_point_cloud(..., viewport="main")
viz.add_sphere(..., viewport="main")
viz.add_camera_frustum(..., viewport="main")
viz.add_image_plane(..., viewport="main")
viz.add_custom(..., viewport="main")
viz.render()
viz.render_viewport(viewport, clear=False, finish_frame=False)
viz.spin(target_fps=None)
viz.should_quit()
viz.save_image(filename)
```

## Viewport

```python
Viewport
Viewport.name
Viewport.display
Viewport.render_state
Viewport.handler
Viewport.scene
```

## Drawable Objects

```python
Drawable
Grid
Axis
Trajectory
PointCloud
Sphere
CameraFrustum
ImagePlane
CustomDrawable
Scene
```

## Utilities

```python
as_color(color)
ensure_vec3(value)
ensure_points(points)
ensure_pose(pose)
pose_from_position_orientation(position, orientation=None)
set_gl_color(color)
draw_line(p1, p2, color, line_width=1.0)
load_tum_trajectory(path)
```

---

# License

MIT — see [`LICENSE`](LICENSE). Use and modify freely for your own projects.