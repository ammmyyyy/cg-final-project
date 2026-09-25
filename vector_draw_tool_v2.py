"""
CG FINAL PROJECT - Interactive 2D Vector Graphics Studio v2.0
Python + PyOpenGL + GLUT

Upgraded features:
- Professional toolbar-style UI
- Line, Rectangle, Circle, Ellipse, Polygon, Star, Bezier
- Selection + mouse dragging
- Translation, scaling and rotation
- RGB color palette
- Scanline polygon filling
- De Casteljau Bezier curve
- Grid + snap-to-grid
- Zoom + pan
- Undo / Redo
- Duplicate / Delete
- Save / Load project as JSON
- Layer panel
- Keyboard shortcuts
"""

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import json
import copy

# ==================== WINDOW / UI SIZE ====================
# পুরো application window এবং UI অংশগুলোর dimension নির্ধারণ করা হচ্ছে।
WIDTH, HEIGHT = 1000, 700
TOOLBAR_H = 72
STATUS_H = 28
SIDEBAR_W = 190

# ==================== GLOBAL STATE ====================
# সব আঁকা object এখানে dictionary হিসেবে রাখা হয়।
shapes = []
selected_index = -1
current_mode = "select"
current_color = (0.3, 0.65, 1.0)
fill_enabled = False
temp_points = []
STATUS_TEXT = "Ready"

show_grid = True
snap_enabled = False
zoom = 1.0
pan_x = 0.0
pan_y = 0.0
dragging = False
drag_last = (0, 0)
pan_dragging = False

undo_stack = []
redo_stack = []

# বিভিন্ন predefined RGB color এখানে রাখা হয়েছে।
PALETTE = [
    (1.0, 1.0, 1.0), (1.0, 0.25, 0.25), (0.25, 1.0, 0.35),
    (0.25, 0.55, 1.0), (1.0, 0.85, 0.2), (1.0, 0.3, 0.85),
    (0.2, 0.9, 0.9), (1.0, 0.55, 0.2)
]

# Toolbar-এ দেখানোর drawing tools এবং তাদের internal mode।
TOOLS = [
    ("SEL", "select"), ("LINE", "line"), ("RECT", "rect"),
    ("CIRC", "circle"), ("ELL", "ellipse"), ("POLY", "polygon"),
    ("STAR", "star"), ("BEZ", "bezier")
]


# ==================== UNDO HISTORY ====================
# বর্তমান drawing-এর একটি কপি undo stack-এ সংরক্ষণ করে।
def push_undo():
    global undo_stack, redo_stack
    # বর্তমান shape list-এর deep copy রাখি, যাতে পরে আগের অবস্থায় ফেরা যায়।
    undo_stack.append(copy.deepcopy(shapes))
    if len(undo_stack) > 50:
        undo_stack.pop(0)
    redo_stack.clear()


# আগের drawing state-এ ফিরে যায়।
def undo():
    global shapes, selected_index, STATUS_TEXT
    if not undo_stack:
        STATUS_TEXT = "Nothing to undo"
        return
        # Undo করার আগের state redo stack-এ রাখি।
    redo_stack.append(copy.deepcopy(shapes))
    shapes = undo_stack.pop()
    selected_index = -1
    STATUS_TEXT = "Undo completed"


# Undo করার পর আবার পরের drawing state-এ ফিরে যায়।
def redo():
    global shapes, selected_index, STATUS_TEXT
    if not redo_stack:
        STATUS_TEXT = "Nothing to redo"
        return
    undo_stack.append(copy.deepcopy(shapes))
    shapes = redo_stack.pop()
    selected_index = -1
    STATUS_TEXT = "Redo completed"


# Snap চালু থাকলে coordinate-কে কাছের 20-pixel grid point-এ বসায়।
def snap(v):
    return round(v / 20.0) * 20.0 if snap_enabled else v


# একটি shape-এর সব point-এর গড় বের করে তার কেন্দ্র/centroid নির্ণয় করে।
def get_centroid(points):
    if not points:
        return 0, 0
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points)
    )


# Shape-টিকে x ও y direction-এ সরিয়ে দেয়।
def translate_shape(shape, dx, dy):
    shape["points"] = [(x + dx, y + dy) for x, y in shape["points"]]


# Shape-এর centroid-কে কেন্দ্র ধরে shape বড় বা ছোট করে।
def scale_shape(shape, factor):
    cx, cy = get_centroid(shape["points"])
    shape["points"] = [
        (cx + (x - cx) * factor, cy + (y - cy) * factor)
        for x, y in shape["points"]
    ]


# Shape-এর centroid-কে কেন্দ্র ধরে নির্দিষ্ট angle-এ rotate করে।
def rotate_shape(shape, angle):
    cx, cy = get_centroid(shape["points"])
    t = math.radians(angle)
    c, s = math.cos(t), math.sin(t)
    out = []
    for x, y in shape["points"]:
        tx, ty = x - cx, y - cy
        out.append((cx + tx*c - ty*s, cy + tx*s + ty*c))
    shape["points"] = out


# De Casteljau algorithm ব্যবহার করে Bezier curve-এর একটি point বের করে।
def de_casteljau(points, t):
    pts = points[:]
    while len(pts) > 1:
        pts = [
            (
                (1-t)*pts[i][0] + t*pts[i+1][0],
                (1-t)*pts[i][1] + t*pts[i+1][1]
            )
            for i in range(len(pts)-1)
        ]
    return pts[0]


# t=0 থেকে t=1 পর্যন্ত অনেকগুলো point বের করে সম্পূর্ণ Bezier curve তৈরি করে।
def compute_bezier(points, resolution=80):
    return [de_casteljau(points, i/resolution) for i in range(resolution+1)]


# বিভিন্ন shape-কে polygon point list-এ রূপান্তর করে, যাতে fill/bounds বের করা যায়।
def shape_polygon(shape):
    typ = shape["type"]
    p = shape["points"]

    if typ == "rect":
        (x1,y1),(x2,y2) = p
        return [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]

    if typ in ("circle", "ellipse"):
        cx, cy = p[0]
        rx, ry = p[1]
        ax = abs(rx-cx)
        ay = abs(ry-cy) if typ == "ellipse" else ax
        return [
            (cx + ax*math.cos(2*math.pi*i/60),
             cy + ay*math.sin(2*math.pi*i/60))
            for i in range(60)
        ]

    if typ in ("polygon", "star"):
        return p

    return None


# Scanline algorithm দিয়ে polygon-এর ভিতরের অংশ horizontal line দিয়ে fill করে।
def scanline_fill(poly, color):
    if not poly:
        return
    ymin = int(min(y for x,y in poly))
    ymax = int(max(y for x,y in poly))
    glColor3f(*color)
    glBegin(GL_LINES)
    n = len(poly)
    for y in range(ymin, ymax+1):
        xs = []
        for i in range(n):
            x1,y1 = poly[i]
            x2,y2 = poly[(i+1)%n]
            if y1 == y2:
                continue
            if min(y1,y2) <= y < max(y1,y2):
                xs.append(x1 + (y-y1)*(x2-x1)/(y2-y1))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            glVertex2f(xs[i], y)
            glVertex2f(xs[i+1], y)
    glEnd()


# Shape-এর type অনুযায়ী OpenGL দিয়ে shape-টি screen-এ আঁকে।
def draw_shape(shape):
    glLineWidth(2.2)
    glColor3f(*shape["color"])
    typ, p = shape["type"], shape["points"]

    poly = shape_polygon(shape)
    if shape.get("filled") and poly:
        scanline_fill(poly, shape["color"])

    if typ == "line":
        glBegin(GL_LINES)
        for q in p: glVertex2f(*q)
        glEnd()

    elif typ in ("rect", "circle", "ellipse", "polygon", "star"):
        if poly:
            glBegin(GL_LINE_LOOP)
            for q in poly: glVertex2f(*q)
            glEnd()

    elif typ == "bezier":
        curve = compute_bezier(p)
        glBegin(GL_LINE_STRIP)
        for q in curve: glVertex2f(*q)
        glEnd()

        glPointSize(6)
        glColor3f(0.65,0.65,0.65)
        glBegin(GL_POINTS)
        for q in p: glVertex2f(*q)
        glEnd()


# Shape-এর minimum ও maximum x,y বের করে bounding box তৈরি করে।
def bounds(shape):
    p = shape_polygon(shape)
    if p:
        xs = [x for x,y in p]; ys = [y for x,y in p]
    else:
        xs = [x for x,y in shape["points"]]
        ys = [y for x,y in shape["points"]]
    return min(xs), min(ys), max(xs), max(ys)


# Mouse position-এর নিচে কোন shape আছে তা খুঁজে বের করে; উপরের layer আগে পরীক্ষা করে।
def find_shape_at(x,y):
    # top-most object wins
    for i in range(len(shapes)-1, -1, -1):
        x1,y1,x2,y2 = bounds(shapes[i])
        margin = 12 / zoom
        if x1-margin <= x <= x2+margin and y1-margin <= y <= y2+margin:
            return i
    return -1


# Screen-এর mouse coordinate-কে drawing/world coordinate-এ রূপান্তর করে।
def world_from_mouse(x, y):
    # Canvas area excludes toolbar/status/sidebar.
    canvas_top = HEIGHT - TOOLBAR_H
    sx = x
    sy = HEIGHT - y
    wx = (sx - SIDEBAR_W)/zoom - pan_x
    wy = (sy - STATUS_H - 10)/zoom - pan_y
    return snap(wx), snap(wy)


# Canvas-এর জন্য OpenGL 2D world projection সেট করে; zoom ও pan এখানে কাজ করে।
def set_world_projection():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    left = -pan_x
    right = (WIDTH-SIDEBAR_W)/zoom - pan_x
    bottom = -pan_y
    top = (HEIGHT-TOOLBAR_H-STATUS_H-10)/zoom - pan_y
    gluOrtho2D(left, right, bottom, top)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# Canvas-এর background grid আঁকে।
def draw_grid():
    if not show_grid:
        return
    left = -pan_x
    right = (WIDTH-SIDEBAR_W)/zoom - pan_x
    bottom = -pan_y
    top = (HEIGHT-TOOLBAR_H-STATUS_H-10)/zoom - pan_y

    step = 20
    startx = math.floor(left/step)*step
    starty = math.floor(bottom/step)*step

    glLineWidth(1)
    glColor3f(0.16,0.18,0.22)
    glBegin(GL_LINES)
    x = startx
    while x <= right:
        glVertex2f(x,bottom); glVertex2f(x,top)
        x += step
    y = starty
    while y <= top:
        glVertex2f(left,y); glVertex2f(right,y)
        y += step
    glEnd()


# OpenGL GLUT ব্যবহার করে screen-এ text লেখে।
def draw_text(x,y,text,size=GLUT_BITMAP_HELVETICA_12):
    glRasterPos2f(x,y)
    for ch in text:
        glutBitmapCharacter(size, ord(ch))


# Toolbar, sidebar, color palette, layers এবং status bar আঁকে।
def draw_ui():
    # Screen-coordinate UI
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, 0, HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # toolbar
    glColor3f(0.07,0.08,0.11)
    glBegin(GL_QUADS)
    glVertex2f(0, HEIGHT); glVertex2f(WIDTH, HEIGHT)
    glVertex2f(WIDTH, HEIGHT-TOOLBAR_H); glVertex2f(0, HEIGHT-TOOLBAR_H)
    glEnd()

    # sidebar
    glColor3f(0.06,0.07,0.09)
    glBegin(GL_QUADS)
    glVertex2f(0, HEIGHT-TOOLBAR_H)
    glVertex2f(SIDEBAR_W, HEIGHT-TOOLBAR_H)
    glVertex2f(SIDEBAR_W, STATUS_H)
    glVertex2f(0, STATUS_H)
    glEnd()

    # toolbar buttons
    x = 8
    for label, mode in TOOLS:
        active = current_mode == mode
        glColor3f(0.18,0.45,0.75) if active else glColor3f(0.13,0.15,0.19)
        glBegin(GL_QUADS)
        glVertex2f(x,HEIGHT-58); glVertex2f(x+72,HEIGHT-58)
        glVertex2f(x+72,HEIGHT-14); glVertex2f(x,HEIGHT-14)
        glEnd()
        glColor3f(1,1,1)
        draw_text(x+10,HEIGHT-43,label)
        x += 78

    # action buttons
    actions = [("UNDO", "undo"),("REDO","redo"),("GRID","grid"),
               ("SNAP","snap"),("SAVE","save"),("LOAD","load")]
    for label, act in actions:
        active = (act=="grid" and show_grid) or (act=="snap" and snap_enabled)
        glColor3f(0.18,0.45,0.75) if active else glColor3f(0.13,0.15,0.19)
        glBegin(GL_QUADS)
        glVertex2f(x,HEIGHT-58); glVertex2f(x+72,HEIGHT-58)
        glVertex2f(x+72,HEIGHT-14); glVertex2f(x,HEIGHT-14)
        glEnd()
        glColor3f(1,1,1)
        draw_text(x+8,HEIGHT-43,label)
        x += 78

    # sidebar title
    glColor3f(0.85,0.9,1)
    draw_text(15, HEIGHT-98, "TOOLS & LAYERS", GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.65,0.7,0.75)
    draw_text(15, HEIGHT-122, "Color palette")

    # palette
    px, py = 15, HEIGHT-160
    for i,c in enumerate(PALETTE):
        if i and i % 4 == 0:
            px = 15; py -= 30
        glColor3f(*c)
        glBegin(GL_QUADS)
        glVertex2f(px,py); glVertex2f(px+25,py)
        glVertex2f(px+25,py+22); glVertex2f(px,py+22)
        glEnd()
        px += 32

    base = HEIGHT-250
    glColor3f(0.65,0.7,0.75)
    draw_text(15,base,"Layers")
    for i,shape in enumerate(reversed(shapes[-12:])):
        real_i = len(shapes)-1-i
        y = base-25-(i*24)
        if real_i == selected_index:
            glColor3f(0.18,0.45,0.75)
            glBegin(GL_QUADS)
            glVertex2f(10,y-5); glVertex2f(SIDEBAR_W-10,y-5)
            glVertex2f(SIDEBAR_W-10,y+15); glVertex2f(10,y+15)
            glEnd()
        glColor3f(1,1,1)
        draw_text(18,y+2,f"{real_i+1}. {shape['type'].upper()}")

    # status bar
    glColor3f(0.05,0.06,0.08)
    glBegin(GL_QUADS)
    glVertex2f(0,STATUS_H); glVertex2f(WIDTH,STATUS_H)
    glVertex2f(WIDTH,0); glVertex2f(0,0)
    glEnd()
    glColor3f(0.85,0.9,1)
    draw_text(12,9,f"{STATUS_TEXT}   |   Objects: {len(shapes)}   |   Zoom: {zoom*100:.0f}%   |   "
                    f"Grid: {'ON' if show_grid else 'OFF'}   |   Snap: {'ON' if snap_enabled else 'OFF'}")


# প্রতিবার screen refresh হলে grid, সব shape, selection box এবং UI আঁকে।
def display():
    glClear(GL_COLOR_BUFFER_BIT)

    set_world_projection()
    draw_grid()

    for i,shape in enumerate(shapes):
        draw_shape(shape)
        if i == selected_index:
            x1,y1,x2,y2 = bounds(shape)
            glColor3f(1.0,0.85,0.15)
            glLineWidth(1.5)
            glBegin(GL_LINE_LOOP)
            glVertex2f(x1-5,y1-5); glVertex2f(x2+5,y1-5)
            glVertex2f(x2+5,y2+5); glVertex2f(x1-5,y2+5)
            glEnd()

    if temp_points:
        glColor3f(0.8,0.8,0.8)
        glPointSize(6)
        glBegin(GL_POINTS)
        for p in temp_points: glVertex2f(*p)
        glEnd()

    draw_ui()
    glutSwapBuffers()


# Current tool অনুযায়ী পাওয়া point দিয়ে নতুন shape তৈরি করে।
def create_shape(points):
    global temp_points, selected_index, STATUS_TEXT
    typ = current_mode

    if typ == "line" and len(points) == 2:
        pass
    elif typ in ("rect","circle","ellipse") and len(points) == 2:
        pass
    elif typ == "polygon" and len(points) >= 3:
        pass
    elif typ == "star" and len(points) == 2:
        c = points[0]
        edge = points[1]
                # কেন্দ্র থেকে edge point-এর দূরত্বই star-এর outer radius।
        outer = math.hypot(edge[0]-c[0],edge[1]-c[1])
        angle0 = math.atan2(edge[1]-c[1],edge[0]-c[0])
        pts=[]
                # 10টি vertex: 5টি outer এবং 5টি inner point মিলে star তৈরি হয়।
        for i in range(10):
            r = outer if i%2==0 else outer*0.45
            a = angle0 + i*math.pi/5
            pts.append((c[0]+r*math.cos(a),c[1]+r*math.sin(a)))
        points = pts
    elif typ == "bezier" and len(points) == 4:
        pass
    else:
        return

    push_undo()
    # Shape-এর type, points, color এবং fill status একসাথে save করা হচ্ছে।
    shapes.append({
        "type": typ,
        "points": points[:],
        "color": current_color,
        "filled": fill_enabled
    })
    selected_index = len(shapes)-1
    temp_points = []
    STATUS_TEXT = f"{typ.title()} created"


# Mouse click, drag, middle-button pan এবং mouse wheel zoom নিয়ন্ত্রণ করে।
def mouse(button,state,x,y):
    global selected_index,temp_points,STATUS_TEXT,current_mode
    global dragging,drag_last,pan_dragging,zoom,pan_x,pan_y

    if state != GLUT_DOWN:
        if button == GLUT_LEFT_BUTTON:
            dragging = False
        if button == GLUT_MIDDLE_BUTTON:
            pan_dragging = False
        return

    # toolbar
    sy = HEIGHT-y
    if sy >= HEIGHT-TOOLBAR_H:
        toolbar_click(x,sy)
        return

    # sidebar
    if x < SIDEBAR_W and sy > STATUS_H:
        sidebar_click(x,sy)
        return

    if sy <= STATUS_H:
        return

    if button == GLUT_MIDDLE_BUTTON:
        pan_dragging=True
        drag_last=(x,y)
        return

    if button == GLUT_LEFT_BUTTON:
        wx,wy=world_from_mouse(x,y)

        if current_mode == "select":
            selected_index = find_shape_at(wx,wy)
            dragging = selected_index != -1
            drag_last=(x,y)
            STATUS_TEXT = "Object selected" if dragging else "No object selected"
            glutPostRedisplay()
            return

        if current_mode == "polygon":
            temp_points.append((wx,wy))
            STATUS_TEXT=f"Polygon: {len(temp_points)} points - press ENTER to finish"
            glutPostRedisplay()
            return

        temp_points.append((wx,wy))

        required = {
            "line":2, "rect":2, "circle":2, "ellipse":2,
            "star":2, "bezier":4
        }.get(current_mode)

        if required and len(temp_points)==required:
            create_shape(temp_points)
        glutPostRedisplay()

    elif button == 3: # wheel up
        zoom=min(3.0,zoom*1.1)
    elif button == 4: # wheel down
        zoom=max(0.35,zoom/1.1)
    glutPostRedisplay()


# Mouse button ধরে movement করলে object drag অথবা canvas pan করে।
def motion(x,y):
    global drag_last,pan_x,pan_y,STATUS_TEXT

    if pan_dragging:
        dx=x-drag_last[0]
        dy=drag_last[1]-y
        pan_x += dx/zoom
        pan_y += dy/zoom
        drag_last=(x,y)
        glutPostRedisplay()
        return

    if dragging and selected_index != -1 and current_mode=="select":
        dx=(x-drag_last[0])/zoom
        dy=(drag_last[1]-y)/zoom
        if abs(dx)+abs(dy)>0:
            push_undo()
            translate_shape(shapes[selected_index],dx,dy)
            # avoid creating an undo entry every mouse movement
            if undo_stack:
                undo_stack.pop()
        drag_last=(x,y)
        STATUS_TEXT="Dragging object"
        glutPostRedisplay()


# Toolbar-এর কোন button-এ click করা হয়েছে তা নির্ধারণ করে এবং action চালায়।
def toolbar_click(x,y):
    global current_mode,show_grid,snap_enabled,STATUS_TEXT,temp_points
    # same positions used in draw_ui
    bx=8
    for label,mode in TOOLS:
        if bx<=x<=bx+72:
            current_mode=mode
            temp_points=[]
            STATUS_TEXT=f"{label.title()} tool selected"
            glutPostRedisplay()
            return
        bx+=78

    actions=[("UNDO","undo"),("REDO","redo"),("GRID","grid"),
             ("SNAP","snap"),("SAVE","save"),("LOAD","load")]
    for label,act in actions:
        if bx<=x<=bx+72:
            if act=="undo": undo()
            elif act=="redo": redo()
            elif act=="grid":
                show_grid=not show_grid
                STATUS_TEXT="Grid toggled"
            elif act=="snap":
                snap_enabled=not snap_enabled
                STATUS_TEXT="Snap toggled"
            elif act=="save": save_project()
            elif act=="load": load_project()
            glutPostRedisplay()
            return
        bx+=78


# Sidebar-এর color palette বা layer list-এ click handle করে।
def sidebar_click(x,y):
    global current_color,fill_enabled,selected_index,STATUS_TEXT
    # palette region
    py0=HEIGHT-160
    if py0-70 <= y <= py0+25:
        col=max(0,min(3,int((x-15)/32)))
        row=max(0,min(1,int((py0+22-y)/30)))
        idx=row*4+col
        if 0<=idx<len(PALETTE):
            current_color=PALETTE[idx]
            if selected_index!=-1:
                push_undo()
                shapes[selected_index]["color"]=current_color
            STATUS_TEXT="Color changed"
            glutPostRedisplay()
            return

    # layer rows
    base=HEIGHT-250
    for i in range(min(12,len(shapes))):
        yy=base-25-(i*24)
        if yy-5<=y<=yy+15:
            selected_index=len(shapes)-1-i
            STATUS_TEXT=f"Layer {selected_index+1} selected"
            glutPostRedisplay()
            return


# Keyboard shortcut ব্যবহার করে tool, fill, grid, undo/redo, delete ইত্যাদি নিয়ন্ত্রণ করে।
def keyboard(key,x,y):
    global current_mode,temp_points,selected_index,current_color,fill_enabled
    global show_grid,snap_enabled,STATUS_TEXT

    if isinstance(key,bytes):
        key=key.decode("utf-8")

    if key in ("l","L"): current_mode="line"
    elif key in ("r","R"): current_mode="rect"
    elif key in ("c","C"): current_mode="circle"
    elif key in ("e","E"): current_mode="ellipse"
    elif key in ("p","P"): current_mode="polygon"
    elif key in ("a","A"): current_mode="star"
    elif key in ("b","B"): current_mode="bezier"
    elif key in ("v","V"): current_mode="select"
    elif key in ("f","F"):
        if selected_index!=-1:
            push_undo()
            shapes[selected_index]["filled"]=not shapes[selected_index].get("filled",False)
            STATUS_TEXT="Fill toggled"
    elif key in ("g","G"):
        show_grid=not show_grid
    elif key in ("n","N"):
        snap_enabled=not snap_enabled
    elif key in ("u","U"): undo()
    elif key in ("y","Y"): redo()
    elif key in ("d","D") and selected_index!=-1:
        push_undo()
        shapes.pop(selected_index)
        selected_index=-1
        STATUS_TEXT="Object deleted"
    elif key in ("q","Q") and selected_index!=-1:
        push_undo()
        shapes.append(copy.deepcopy(shapes[selected_index]))
        selected_index=len(shapes)-1
        translate_shape(shapes[selected_index],20,20)
        STATUS_TEXT="Object duplicated"
    elif key=="[" and selected_index!=-1:
        push_undo(); rotate_shape(shapes[selected_index],-10)
    elif key=="]" and selected_index!=-1:
        push_undo(); rotate_shape(shapes[selected_index],10)
    elif key in ("+","=") and selected_index!=-1:
        push_undo(); scale_shape(shapes[selected_index],1.1)
    elif key=="-" and selected_index!=-1:
        push_undo(); scale_shape(shapes[selected_index],0.9)
    elif key=="\r" and current_mode=="polygon" and len(temp_points)>=3:
        create_shape(temp_points)
    elif key=="\x1b":
        glutLeaveMainLoop()

    temp_points = temp_points if current_mode=="polygon" else []
    STATUS_TEXT = STATUS_TEXT or f"{current_mode.title()} tool selected"
    glutPostRedisplay()


# Arrow key দিয়ে selected object-কে ছোট step-এ move করে।
def special_keys(key,x,y):
    global STATUS_TEXT
    if selected_index==-1:
        return
    step=5
    if key==GLUT_KEY_LEFT:
        push_undo(); translate_shape(shapes[selected_index],-step,0)
    elif key==GLUT_KEY_RIGHT:
        push_undo(); translate_shape(shapes[selected_index],step,0)
    elif key==GLUT_KEY_UP:
        push_undo(); translate_shape(shapes[selected_index],0,step)
    elif key==GLUT_KEY_DOWN:
        push_undo(); translate_shape(shapes[selected_index],0,-step)
    STATUS_TEXT="Object moved"
    glutPostRedisplay()


# সব shape JSON file হিসেবে save করে।
def save_project():
    try:
        with open("my_drawing.json","w",encoding="utf-8") as f:
            json.dump(shapes,f,indent=2)
        global STATUS_TEXT
        STATUS_TEXT="Saved to my_drawing.json"
    except Exception as e:
        STATUS_TEXT=f"Save error: {e}"


# JSON file থেকে আগের drawing আবার load করে।
def load_project():
    global shapes,selected_index,STATUS_TEXT
    try:
        with open("my_drawing.json","r",encoding="utf-8") as f:
            push_undo()
            shapes=json.load(f)
        selected_index=-1
        STATUS_TEXT="Loaded my_drawing.json"
    except FileNotFoundError:
        STATUS_TEXT="No my_drawing.json found"
    except Exception as e:
        STATUS_TEXT=f"Load error: {e}"


# Window resize হলে নতুন width/height ও OpenGL viewport সেট করে।
def reshape(w,h):
    global WIDTH,HEIGHT
    WIDTH=max(700,w)
    HEIGHT=max(500,h)
    glViewport(0,0,w,h)


# OpenGL-এর প্রাথমিক configuration সেট করে।
def init():
    glClearColor(0.035,0.04,0.055,1)
    glEnable(GL_POINT_SMOOTH)


# Program-এর main entry point; GLUT window তৈরি ও callback function register করে।
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB)
    glutInitWindowSize(WIDTH,HEIGHT)
    glutCreateWindow(b"CG Vector Studio - Final Project v2.0")
    init()

    # GLUT event callback হিসেবে প্রয়োজনীয় functionগুলো register করা হচ্ছে।
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)

    glutMainLoop()


if __name__=="__main__":
    main()
