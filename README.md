# Interactive 2D Vector Drawing Tool

**Course:** Computer Graphics Sessional — Final Project ("Bridge to the Real World")
**Career Track:** A — Software Job (UI Renderer / Vector Graphics Tool)
**Tech Stack:** Python, PyOpenGL, GLUT

## Overview

A small interactive 2D vector drawing application (similar in spirit to a mini
Paint/Illustrator engine) built from scratch in Python OpenGL — without relying
on any high-level shape or fill library calls. Every core algorithm is
implemented by hand to demonstrate understanding of the underlying Computer
Graphics techniques.

## Computer Graphics Techniques Implemented

| # | Technique | Real-world connection |
|---|---|---|
| 1 | Line & Shape Drawing | Google Maps, vector graphics editors (Figma, Illustrator) |
| 2 | 2D Transformations (translate / scale / rotate) | Game engines, animation systems |
| 3 | Color Fill (Scanline Polygon Fill Algorithm, implemented manually) | Photoshop's paint bucket, GPU rasterization |
| 4 | Bezier Curves (De Casteljau's Algorithm) | Font design (TTF/OTF glyphs), automotive/CAD body modelling |

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python vector_draw_tool.py
```

## Controls

| Key | Action |
|---|---|
| `l` | Line drawing mode (2 clicks) |
| `r` | Rectangle drawing mode (2 clicks) |
| `c` | Circle drawing mode (2 clicks: center, then radius point) |
| `b` | Bezier curve mode (4 clicks: control points) |
| `v` | Select mode — click a shape to select it |
| `t` | Translate mode — move selected shape with arrow keys |
| `s` | Scale mode — `+` / `=` to grow, `-` to shrink selected shape |
| `o` | Rotate mode — `[` to rotate left, `]` to rotate right |
| `1`–`6` | Change color of new shapes / the selected shape |
| `f` | Toggle fill (scanline algorithm) on the selected shape — works on rectangle & circle only, since line & bezier are open paths |
| `d` | Delete the selected shape |
| `Esc` | Quit |

A newly drawn shape is automatically selected, so you can immediately press
`f`, `1`–`6`, `t`, `s`, or `o` on it without switching to select mode first.

## Design Notes

- **Color fill** is implemented as a manual scanline polygon-fill algorithm
  (finding edge intersections per horizontal row and filling between pairs)
  rather than calling `glBegin(GL_POLYGON)`, to demonstrate the actual
  rasterization technique.
- **Transformations** (translate/scale/rotate) are computed manually around
  each shape's centroid using standard 2D transformation formulas, rather
  than relying on `glTranslatef` / `glScalef` / `glRotatef`.
- **Bezier curves** use De Casteljau's algorithm for numerically stable curve
  evaluation.

## Author

Built individually as part of the Computer Graphics Sessional final project.
