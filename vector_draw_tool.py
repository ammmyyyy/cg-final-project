"""
=================================================================
প্রজেক্ট: Interactive 2D Vector Drawing Tool
Track: A (Software Job) -> UI Renderer / Vector Graphics Tool
Tools: Python + PyOpenGL + GLUT

ব্যবহৃত Computer Graphics টেকনিক (৪টা - requirement অনুযায়ী):
  1. Line & Shape Drawing   -> Google Maps / vector graphics এর মতো
  2. 2D Transformations     -> game engine এবং animation এর মতো
  3. Color Fill (Scanline)  -> Photoshop এর paint bucket এর মতো
  4. Bezier Curves          -> font design / automotive modelling এর মতো
=================================================================
"""

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# ---------------------------------------------------------------
# গ্লোবাল স্টেট
# ---------------------------------------------------------------
WIDTH, HEIGHT = 800, 600

# প্রতিটা shape একটা dict হিসেবে সেভ থাকবে
# {type: 'line'/'rect'/'circle'/'bezier', points: [(x,y), ...], color: (r,g,b), filled: bool}
shapes = []

current_mode = 'line'            # কোন টুল এখন active
temp_points = []                 # ইউজার ক্লিক করে যেসব পয়েন্ট এখনো জমা হচ্ছে
current_color = (1.0, 1.0, 1.0)  # নতুন shape এর জন্য default রং (সাদা)
selected_index = -1              # কোন shape select করা আছে (translate/scale/rotate এর জন্য)

COLOR_LIST = [
    (1.0, 1.0, 1.0),  # 1 -> সাদা
    (1.0, 0.2, 0.2),  # 2 -> লাল
    (0.2, 1.0, 0.2),  # 3 -> সবুজ
    (0.3, 0.5, 1.0),  # 4 -> নীল
    (1.0, 1.0, 0.2),  # 5 -> হলুদ
    (1.0, 0.4, 1.0),  # 6 -> ম্যাজেন্টা
]

STATUS_TEXT = ""


# =================================================================
# TECHNIQUE 1: LINE & SHAPE DRAWING
# =================================================================
def draw_shape_outline(shape):
    # কী করছে: shape এর outline (রেখা/আউটলাইন) GL_LINE primitive দিয়ে আঁকছে
    # কেন লাগছে: প্রতিটা vector shape এর basic building block হলো লাইন
    # real world-এ এটা কোথায় দেখা যায়: Google Maps এর road/border drawing,
    #                                   Figma/Illustrator এর vector paths
    glColor3f(*shape['color'])
    pts = shape['points']

    if shape['type'] == 'line':
        glBegin(GL_LINES)
        for p in pts:
            glVertex2f(*p)
        glEnd()

    elif shape['type'] == 'rect':
        (x1, y1), (x2, y2) = pts
        glBegin(GL_LINE_LOOP)
        glVertex2f(x1, y1)
        glVertex2f(x2, y1)
        glVertex2f(x2, y2)
        glVertex2f(x1, y2)
        glEnd()

    elif shape['type'] == 'circle':
        cx, cy = pts[0]
        rx, ry = pts[1]
        r = math.hypot(rx - cx, ry - cy)
        glBegin(GL_LINE_LOOP)
        for i in range(60):
            theta = 2 * math.pi * i / 60
            glVertex2f(cx + r * math.cos(theta), cy + r * math.sin(theta))
        glEnd()

    elif shape['type'] == 'bezier':
        curve_pts = compute_bezier(pts, 50)
        glBegin(GL_LINE_STRIP)
        for p in curve_pts:
            glVertex2f(*p)
        glEnd()
        # control points গুলো ছোট বিন্দু দিয়ে দেখানো হচ্ছে (বোঝার সুবিধার জন্য)
        glPointSize(5)
        glColor3f(0.6, 0.6, 0.6)
        glBegin(GL_POINTS)
        for p in pts:
            glVertex2f(*p)
        glEnd()


def shape_to_polygon(shape):
    """rect / circle কে polygon (points এর list) এ রূপান্তর করে, fill করার জন্য দরকার"""
    if shape['type'] == 'rect':
        (x1, y1), (x2, y2) = shape['points']
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    elif shape['type'] == 'circle':
        cx, cy = shape['points'][0]
        rx, ry = shape['points'][1]
        r = math.hypot(rx - cx, ry - cy)
        return [(cx + r * math.cos(2 * math.pi * i / 30),
                  cy + r * math.sin(2 * math.pi * i / 30)) for i in range(30)]
    return None  # line / bezier এর জন্য fill প্রযোজ্য না


# =================================================================
# TECHNIQUE 2: 2D TRANSFORMATIONS (ম্যানুয়াল ফর্মুলা দিয়ে)
# =================================================================
def get_centroid(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def translate_shape(shape, dx, dy):
    # কী করছে: shape এর প্রতিটা পয়েন্টে (dx, dy) যোগ করছে
    # কেন লাগছে: object কে screen-এ move করানোর basic transformation
    # real world-এ এটা কোথায় দেখা যায়: game এ character move করা, UI drag করা
    shape['points'] = [(x + dx, y + dy) for (x, y) in shape['points']]


def scale_shape(shape, factor):
    # কী করছে: centroid কে কেন্দ্র ধরে shape কে বড়/ছোট করছে
    # কেন লাগছে: object এর size পরিবর্তন করতে হলে centroid-relative scaling দরকার,
    #             নাহলে shape জায়গা থেকে সরে যায়
    # real world-এ এটা কোথায় দেখা যায়: zoom in/out, UI resize animation
    cx, cy = get_centroid(shape['points'])
    new_pts = []
    for (x, y) in shape['points']:
        nx = cx + (x - cx) * factor
        ny = cy + (y - cy) * factor
        new_pts.append((nx, ny))
    shape['points'] = new_pts


def rotate_shape(shape, angle_deg):
    # কী করছে: centroid কে কেন্দ্র ধরে shape কে rotation matrix দিয়ে ঘুরাচ্ছে
    # কেন লাগছে: rotation matrix [[cos -sin],[sin cos]] হলো CG এর core concept
    # real world-এ এটা কোথায় দেখা যায়: game এ character turn করা, steering wheel animation
    cx, cy = get_centroid(shape['points'])
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    new_pts = []
    for (x, y) in shape['points']:
        tx, ty = x - cx, y - cy
        rx = tx * cos_t - ty * sin_t
        ry = tx * sin_t + ty * cos_t
        new_pts.append((rx + cx, ry + cy))
    shape['points'] = new_pts


# =================================================================
# TECHNIQUE 3: COLOR FILL (Scanline Polygon Fill Algorithm)
# =================================================================
def scanline_fill(polygon_pts, color):
    # কী করছে: প্রতিটা scanline (অনুভূমিক রেখা) polygon এর edge গুলোকে
    #           কোথায় ছেদ করছে তা বের করে, দুই intersection এর মাঝে রং ভরাট করছে
    # কেন লাগছে: glBegin(GL_POLYGON) সরাসরি ব্যবহার না করে, আসল fill algorithm
    #             (যেটা Photoshop/Paint এর bucket-fill এর ভিত্তি) হাতে implement করা শেখার জন্য
    # real world-এ এটা কোথায় দেখা যায়: Photoshop paint bucket, GPU rasterization stage
    n = len(polygon_pts)
    ys = [p[1] for p in polygon_pts]
    y_min, y_max = int(min(ys)), int(max(ys))

    glColor3f(*color)
    glBegin(GL_LINES)
    for y in range(y_min, y_max + 1):
        intersections = []
        for i in range(n):
            x1, y1 = polygon_pts[i]
            x2, y2 = polygon_pts[(i + 1) % n]
            if y1 == y2:
                continue  # অনুভূমিক edge স্কিপ (special case)
            if min(y1, y2) <= y < max(y1, y2):
                # edge এর সাথে y = const রেখার x ছেদবিন্দু বের করা (linear interpolation)
                x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                intersections.append(x)

        intersections.sort()
        # প্রতি জোড়া intersection এর মাঝে একটা horizontal রেখা টানা = fill
        for i in range(0, len(intersections) - 1, 2):
            glVertex2f(intersections[i], y)
            glVertex2f(intersections[i + 1], y)
    glEnd()


# =================================================================
# TECHNIQUE 4: BEZIER CURVE (De Casteljau's Algorithm)
# =================================================================
def de_casteljau(points, t):
    # কী করছে: control points গুলোকে বার বার linear interpolate করে t সময়ে
    #           curve এর উপর একটা বিন্দু বের করছে
    # কেন লাগছে: এটাই Bezier curve আঁকার mathematically stable পদ্ধতি
    # real world-এ এটা কোথায় দেখা যায়: font glyph design (TTF/OTF), car body/automotive CAD modelling
    pts = points[:]
    while len(pts) > 1:
        new_pts = []
        for i in range(len(pts) - 1):
            x = (1 - t) * pts[i][0] + t * pts[i + 1][0]
            y = (1 - t) * pts[i][1] + t * pts[i + 1][1]
            new_pts.append((x, y))
        pts = new_pts
    return pts[0]


def compute_bezier(control_points, resolution=50):
    return [de_casteljau(control_points, i / resolution) for i in range(resolution + 1)]


# =================================================================
# GLUT CALLBACKS (UI event handling)
# =================================================================
def display():
    glClear(GL_COLOR_BUFFER_BIT)

    for idx, shape in enumerate(shapes):
        poly = shape_to_polygon(shape)
        if shape.get('filled') and poly:
            scanline_fill(poly, shape['color'])
        draw_shape_outline(shape)

        # select করা shape এর centroid-এ হলুদ বিন্দু দেখানো
        if idx == selected_index:
            cx, cy = get_centroid(shape['points'])
            glColor3f(1.0, 1.0, 0.0)
            glPointSize(8)
            glBegin(GL_POINTS)
            glVertex2f(cx, cy)
            glEnd()

    # বর্তমানে আঁকতে থাকা (এখনো complete হয়নি এমন) shape দেখানো
    if temp_points:
        glColor3f(0.5, 0.5, 0.5)
        glPointSize(6)
        glBegin(GL_POINTS)
        for p in temp_points:
            glVertex2f(*p)
        glEnd()

    draw_status_text()
    glutSwapBuffers()


def draw_status_text():
    glColor3f(1, 1, 1)
    glRasterPos2f(10, HEIGHT - 20)
    text = f"Mode: {current_mode} | Shapes: {len(shapes)} | Selected: {selected_index} | {STATUS_TEXT}"
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))


def reshape(w, h):
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, w, 0, h)
    glMatrixMode(GL_MODELVIEW)


def mouse(button, state, x, y):
    global temp_points, selected_index, STATUS_TEXT
    if button != GLUT_LEFT_BUTTON or state != GLUT_DOWN:
        return
    y = HEIGHT - y  # OpenGL এর y-axis উল্টা, তাই flip করা

    if current_mode == 'select':
        selected_index = find_shape_at(x, y)
        glutPostRedisplay()
        return

    draw_modes = {'line': 2, 'rect': 2, 'circle': 2, 'bezier': 4}
    if current_mode not in draw_modes:
        # translate/scale/rotate মোডে ক্যানভাসে ক্লিক করলে কিছু হবে না
        # (এতে leftover click থেকে ভুলবশত shape তৈরি হওয়াও বন্ধ হয়)
        return

    temp_points.append((x, y))
    needed = draw_modes[current_mode]
    STATUS_TEXT = f"{current_mode}: {len(temp_points)}/{needed} points placed"

    if len(temp_points) == needed:
        shapes.append({
            'type': current_mode,
            'points': temp_points[:],
            'color': current_color,
            'filled': False
        })
        temp_points = []
        selected_index = len(shapes) - 1  # আঁকা শেষ হলে shape-টা auto-select হয়ে যাবে
        STATUS_TEXT = f"{current_mode} shape created & selected"
    glutPostRedisplay()


def find_shape_at(x, y):
    # ক্লিক করা পয়েন্টের সবচেয়ে কাছের centroid যেই shape এর, সেটা select হবে
    best_i, best_d = -1, 40  # 40 pixel radius এর মধ্যে হতে হবে
    for i, shape in enumerate(shapes):
        cx, cy = get_centroid(shape['points'])
        d = math.hypot(cx - x, cy - y)
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def keyboard(key, x, y):
    global current_mode, current_color, temp_points, selected_index, STATUS_TEXT
    key = key.decode('utf-8') if isinstance(key, bytes) else key

    mode_map = {'l': 'line', 'r': 'rect', 'c': 'circle', 'b': 'bezier', 'v': 'select'}
    if key in mode_map:
        current_mode = mode_map[key]
        temp_points = []
        STATUS_TEXT = f"{current_mode} mode chalu"

    elif key in '123456':
        current_color = COLOR_LIST[int(key) - 1]
        if selected_index != -1:
            shapes[selected_index]['color'] = current_color
        STATUS_TEXT = "color changed"

    elif key == 'f':
        if selected_index != -1:
            shapes[selected_index]['filled'] = not shapes[selected_index]['filled']
            STATUS_TEXT = "fill toggled"

    elif key == 't':
        current_mode = 'translate'
        temp_points = []  # আধা-আঁকা shape থাকলে discard করা হচ্ছে, এই মোডে দরকার নেই
        STATUS_TEXT = "translate mode: arrow keys use koro"

    elif key == 's':
        current_mode = 'scale'
        temp_points = []
        STATUS_TEXT = "scale mode: +/- (or =/-) chapo"

    elif key == 'o':
        current_mode = 'rotate'
        temp_points = []
        STATUS_TEXT = "rotate mode: [ ] chapo"

    elif key in ('+', '=') and current_mode == 'scale' and selected_index != -1:
        # '=' ও রাখা হয়েছে কারণ কিছু keyboard layout-এ Shift+'=' এর '+'
        # GLUT সবসময় ঠিকমতো ধরতে পারে না
        scale_shape(shapes[selected_index], 1.1)

    elif key == '-' and current_mode == 'scale' and selected_index != -1:
        scale_shape(shapes[selected_index], 0.9)

    elif key == '[' and selected_index != -1:
        rotate_shape(shapes[selected_index], -10)

    elif key == ']' and selected_index != -1:
        rotate_shape(shapes[selected_index], 10)

    elif key == 'd' and selected_index != -1:
        shapes.pop(selected_index)
        selected_index = -1
        STATUS_TEXT = "shape deleted"

    elif key == '\x1b':  # ESC
        glutLeaveMainLoop()

    glutPostRedisplay()


def special_keys(key, x, y):
    """Arrow keys -> translate মোডে selected shape সরানোর জন্য"""
    if current_mode == 'translate' and selected_index != -1:
        step = 5
        if key == GLUT_KEY_LEFT:
            translate_shape(shapes[selected_index], -step, 0)
        elif key == GLUT_KEY_RIGHT:
            translate_shape(shapes[selected_index], step, 0)
        elif key == GLUT_KEY_UP:
            translate_shape(shapes[selected_index], 0, step)
        elif key == GLUT_KEY_DOWN:
            translate_shape(shapes[selected_index], 0, -step)
    glutPostRedisplay()


def init():
    glClearColor(0.08, 0.08, 0.1, 1.0)


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutCreateWindow(b"2D Vector Drawing Tool - CG Project")
    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutMouseFunc(mouse)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMainLoop()


if __name__ == "__main__":
    main()
