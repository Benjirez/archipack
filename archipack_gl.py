# -*- coding:utf-8 -*-

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------
# Author: Stephen Leger (s-leger)
#
# ----------------------------------------------------------

import bgl
import blf
from math import sin, cos, atan2, pi
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils, object_utils

# ------------------------------------------------------------------
# Define Gl Handle types
# ------------------------------------------------------------------

# Arrow sizes (world units)
arrow_size = 0.1
# Handle area size (pixels)
handle_size = 10

# Font sizes and basic colour scheme
# kept outside of addon prefs until now
# as for a generic toolkit it is not appropriate
# we could provide a template for addon prefs
# matching those one
feedback_size_main = 16
feedback_size_title = 14
feedback_size_shortcut = 11
feedback_colour_main = (0.95, 0.95, 0.95, 1.0)
feedback_colour_key = (0.67, 0.67, 0.67, 1.0)
feedback_colour_shortcut = (0.51, 0.51, 0.51, 1.0)


# @TODO:
# 1 Make a clear separation of 2d (pixel position) and 3d (world position)
#   modes way to set gl coords
# 2 Unify methods to set points - currently set_pts, set_pos ...
# 3 Put all Gl part in a sub module as it may be used by other devs
#   as gl toolkit abstraction for screen feedback
# 4 Implement cursor badges (np_station sample)
# 5 Define a clear color scheme so it is easy to customize
# 6 Allow different arguments for each classes like
#   eg: for line p0 p1, p0 and vector (p1-p0)
#       raising exceptions when incomplete
# 7 Use correct words, normal is not realy a normal
#   but a perpendicular
# May be hard code more shapes ?
# Fine tuned text styles with shadows and surronding boxes / backgrounds
# Extending tests to hdr screens, ultra wide ones and so on
# Circular handle, handle styling (only border, filling ...)

# Keep point 3 in mind while doing this, to keep it simple and easy to use
# Take inspiration from other's feed back systems, talk to other devs
# and find who actually work on bgl future for 2.8 release


class Gl():
    """
        handle 3d -> 2d gl drawing
        d : dimensions
            3 to convert pos from 3d
            2 to keep pos as 2d absolute screen position
    """
    def __init__(self, d=3):
        # flag output over render image
        self.render = False
        # default line width
        self.width = 1
        # default line style
        self.style = bgl.GL_LINE
        # allow closed lines
        self.closed = False
        # nth dimensions of input coords 3=word coords 2=pixel screen coords
        self.d = d
        self.pos_2d = Vector((0, 0))
        self.colour_active = (1.0, 0.0, 0.0, 1.0)
        self.colour_hover = (1.0, 1.0, 0.0, 1.0)
        self.colour_normal = (1.0, 1.0, 1.0, 1.0)
        self.colour_inactive = (0.0, 0.0, 0.0, 1.0)

    @property
    def colour(self):
        return self.colour_inactive

    def position_2d_from_coord(self, context, coord, render=False):
        """ coord given in local input coordsys
        """
        if self.d == 2:
            return coord
        if render:
            return self.get_render_location(context, coord)
        region = context.region
        rv3d = context.region_data
        loc = view3d_utils.location_3d_to_region_2d(region, rv3d, coord, self.pos_2d)
        return loc

    def get_render_location(self, context, coord):
        scene = context.scene
        co_2d = object_utils.world_to_camera_view(scene, scene.camera, coord)
        # Get pixel coords
        render_scale = scene.render.resolution_percentage / 100
        render_size = (int(scene.render.resolution_x * render_scale),
                       int(scene.render.resolution_y * render_scale))
        return [round(co_2d.x * render_size[0]), round(co_2d.y * render_size[1])]

    def _end(self):
        bgl.glEnd()
        bgl.glPopAttrib()
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

    def _start_poly(self):
        bgl.glPushAttrib(bgl.GL_ENABLE_BIT)
        bgl.glEnable(bgl.GL_BLEND)
        if self.render:
            # enable anti-alias on polygons
            bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
        bgl.glColor4f(*self.colour)
        bgl.glBegin(bgl.GL_POLYGON)

    def _start_line(self):
        bgl.glPushAttrib(bgl.GL_ENABLE_BIT)
        if self.style == bgl.GL_LINE_STIPPLE:
            bgl.glLineStipple(1, 0x9999)
        bgl.glEnable(self.style)
        bgl.glEnable(bgl.GL_BLEND)
        if self.render:
            # enable anti-alias on lines
            bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glColor4f(*self.colour)
        bgl.glLineWidth(self.width)
        if self.closed:
            bgl.glBegin(bgl.GL_LINE_LOOP)
        else:
            bgl.glBegin(bgl.GL_LINE_STRIP)

    def draw_text(self, x, y):
        # dirty fast assignment
        dpi, font_id = 72, 0
        bgl.glColor4f(*self.colour)
        if self.angle != 0:
            blf.enable(font_id, blf.ROTATION)
            blf.rotation(font_id, self.angle)
        blf.size(font_id, self.font_size, dpi)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, self.text)
        if self.angle != 0:
            blf.disable(font_id, blf.ROTATION)

    def draw(self, context, render=False):
        """
            render flag when rendering
        """
        self.render = render
        gl_type = type(self).__name__
        if 'Handle' in gl_type or gl_type in ['GlPolygon']:
            self._start_poly()
        elif gl_type in ['GlArc', 'GlLine', 'GlPolyline']:
            self._start_line()
        if 'Text' in gl_type:
            x, y = self.position_2d_from_coord(context, self.pts[0], render)
            self.draw_text(x, y)
        else:
            for pt in self.pts:
                x, y = self.position_2d_from_coord(context, pt, render)
                bgl.glVertex2f(x, y)
            self._end()


class GlText(Gl):

    def __init__(self, d=3, round=2, label='', font_size=16, colour=(1, 1, 1, 1), z_axis=Vector((0, 0, 1))):
        self.z_axis = z_axis
        self.value = None
        self.round = round
        self.label = label
        self.unit = ''
        self.font_size = font_size
        self.angle = 0
        Gl.__init__(self, d)
        self.colour_inactive = colour

    @property
    def text_size(self):
        dpi, font_id = 72, 0
        blf.enable(font_id, blf.ROTATION)
        blf.rotation(font_id, self.angle)
        blf.size(font_id, self.font_size, dpi)
        x, y = blf.dimensions(font_id, self.text)
        blf.disable(font_id, blf.ROTATION)
        return Vector((x, y))

    @property
    def pts(self):
        return [self.pos_3d]

    @property
    def text(self):
        if self.value is not None:
            return self.label + str(round(self.value, self.round)) + self.unit
        else:
            return self.label

    def set_pos(self, context, value, pos_3d, direction, angle=0, normal=Vector((0, 0, 1))):
        self.up_axis = direction.normalized()
        self.c_axis = self.up_axis.cross(normal)
        self.pos_3d = pos_3d
        self.value = value
        self.angle = angle


class GlLine(Gl):
    """
        3d Line
        mostly a gl enabled for future use in manipulators
        coords are in world space
    """
    def __init__(self, d=3, p=None, v=None, p0=None, p1=None, z_axis=None):
        """
            d=3 use 3d coords, d=2 use 2d pixels coords
            Init by either
            p: Vector or tuple origin
            v: Vector or tuple size and direction
            or
            p0: Vector or tuple 1 point location
            p1: Vector or tuple 2 point location
            Will convert any into Vector 3d
            both optionnals
        """
        if p is not None and v is not None:
            self.p = Vector(p)
            self.v = Vector(v)
        elif p0 is not None and p1 is not None:
            self.p = Vector(p0)
            self.v = Vector(p1) - self.p
        else:
            self.p = Vector((0, 0, 0))
            self.v = Vector((0, 0, 0))
        if z_axis is not None:
            self.z_axis = z_axis
        else:
            self.z_axis = Vector((0, 0, 1))
        Gl.__init__(self, d)

    @property
    def p0(self):
        return self.p

    @property
    def p1(self):
        return self.p + self.v

    @p0.setter
    def p0(self, p0):
        """
            Note: setting p0
            move p0 only
        """
        p1 = self.p1
        self.p = Vector(p0)
        self.v = p1 - p0

    @p1.setter
    def p1(self, p1):
        """
            Note: setting p1
            move p1 only
        """
        self.v = Vector(p1) - self.p

    @property
    def length(self):
        return self.v.length

    @property
    def angle(self):
        return atan2(self.v.y, self.v.x)

    @property
    def cross(self):
        """
            Vector perpendicular on plane defined by z_axis
            lie on the right side
            p1
            |--x
            p0
        """
        return self.v.cross(self.z_axis)

    def normal(self, t=0):
        """
            Line perpendicular on plane defined by z_axis
            lie on the right side
            p1
            |--x
            p0
        """
        n = GlLine()
        n.p = self.lerp(t)
        n.v = self.cross
        return n

    def sized_normal(self, t, size):
        """
            GlLine perpendicular on plane defined by z_axis and of given size
            positionned at t in current line
            lie on the right side
            p1
            |--x
            p0
        """
        n = GlLine()
        n.p = self.lerp(t)
        n.v = size * self.cross.normalized()
        return n

    def lerp(self, t):
        """
            Interpolate along segment
            t parameter [0, 1] where 0 is start of arc and 1 is end
        """
        return self.p + self.v * t

    def offset(self, offset):
        """
            offset > 0 on the right part
        """
        self.p += offset * self.cross.normalized()

    @property
    def pts(self):
        return [self.p0, self.p1]


class GlCircle(Gl):

    def __init__(self, d=3):
        self.r = 0
        self.c = Vector((0, 0, 0))
        Gl.__init__(self, d)


class GlArc(GlCircle):

    def __init__(self, d=3, z_axis=Vector((0, 0, 1))):
        """
            a0 and da arguments are in radians
            a0 = 0   on the right side
            a0 = pi on the left side
            da > 0 CCW contrary-clockwise
            da < 0 CW  clockwise
            stored internally as radians
        """
        GlCircle.__init__(self, d)
        if z_axis.z < 1:
            x_axis = z_axis.cross(Vector((0, 0, 1)))
            y_axis = x_axis.cross(z_axis)
        else:
            x_axis = Vector((1, 0, 0))
            y_axis = Vector((0, 1, 0))
        self.rM = Matrix([
            x_axis,
            y_axis,
            z_axis
        ])
        self.z_axis = z_axis
        self.a0 = 0
        self.da = 0

    @property
    def length(self):
        return self.r * abs(self.da)

    def normal(self, t=0):
        """
            always on the right side
        """
        n = GlLine(z_axis=self.z_axis)
        n.p = self.lerp(t)
        if self.da < 0:
            n.v = self.c - n.p
        else:
            n.v = n.p - self.c
        return n

    def sized_normal(self, t, size):
        n = GlLine(z_axis=self.z_axis)
        n.p = self.lerp(t)
        if self.da < 0:
            n.v = size * (self.c - n.p).normalized()
        else:
            n.v = size * (n.p - self.c).normalized()
        return n

    def lerp(self, t):
        a = self.a0 + t * self.da
        return self.c + self.rM * Vector((self.r * cos(a), self.r * sin(a), 0))

    def tangeant(self, t, length):
        a = self.a0 + t * self.da
        ca = cos(a)
        sa = sin(a)
        n = GlLine()
        n.p = self.c + self.rM * Vector((self.r * ca, self.r * sa, 0))
        n.v = self.rM * Vector((length * sa, -length * ca, 0))
        if self.da > 0:
            n.v = -n.v
        return n

    def offset(self, offset):
        """
            offset > 0 on the right part
        """
        if self.da > 0:
            radius = self.r + offset
        else:
            radius = self.r - offset
        return GlArc(self.c, radius, self.a0, self.da, z_axis=self.z_axis)

    @property
    def pts(self):
        n_pts = max(1, int(round(abs(self.da) / pi * 30, 0)))
        t_step = 1 / n_pts
        return [self.lerp(i * t_step) for i in range(n_pts + 1)]


class GlPolygon(Gl):
    def __init__(self, colour, d=3):
        self.pts_3d = []
        Gl.__init__(self, d)
        self.colour_inactive = colour

    def set_pos(self, pts_3d):
        self.pts_3d = pts_3d

    @property
    def pts(self):
        return self.pts_3d


class GlPolyline(Gl):
    def __init__(self, colour, d=3):
        self.pts_3d = []
        Gl.__init__(self, d=d)
        self.colour_inactive = colour

    def set_pos(self, pts_3d):
        self.pts_3d = pts_3d
        # self.pts_3d.append(pts_3d[0])

    @property
    def pts(self):
        return self.pts_3d


class GlHandle(Gl):

    def __init__(self, sensor_size, size, selectable=False):
        """
            sensor_size : 2d size in pixels of sensor area
            size : 3d size of handle
        """
        self.size = size
        self.sensor_width = sensor_size
        self.sensor_height = sensor_size
        self.pos_3d = Vector((0, 0, 0))
        self.up_axis = Vector((0, 0, 0))
        self.c_axis = Vector((0, 0, 0))
        self.hover = False
        self.active = False
        self.selectable = selectable
        Gl.__init__(self)

    def set_pos(self, context, pos_3d, direction, normal=Vector((0, 0, 1))):
        self.up_axis = direction.normalized()
        self.c_axis = self.up_axis.cross(normal)
        self.pos_3d = pos_3d
        self.pos_2d = self.position_2d_from_coord(context, self.sensor_center)

    def check_hover(self, pos_2d):
        if self.selectable:
            dp = pos_2d - self.pos_2d
            self.hover = abs(dp.x) < self.sensor_width and abs(dp.y) < self.sensor_height

    @property
    def sensor_center(self):
        pts = self.pts
        n = len(pts)
        x, y, z = 0, 0, 0
        for pt in pts:
            x += pt.x
            y += pt.y
            z += pt.z
        return Vector((x / n, y / n, z / n))

    @property
    def pts(self):
        raise NotImplementedError

    @property
    def colour(self):
        if self.selectable:
            if self.active:
                return self.colour_active
            elif self.hover:
                return self.colour_hover
            return self.colour_normal
        else:
            return self.colour_inactive


class SquareHandle(GlHandle):

    def __init__(self, sensor_size, size, selectable=False):
        GlHandle.__init__(self, sensor_size, size, selectable)

    @property
    def pts(self):
        n = self.up_axis
        c = self.c_axis
        x = n * self.size / 2
        y = c * self.size / 2
        return [self.pos_3d - x - y, self.pos_3d + x - y, self.pos_3d + x + y, self.pos_3d - x + y]


class TriHandle(GlHandle):

    def __init__(self, sensor_size, size, selectable=False):
        GlHandle.__init__(self, sensor_size, size, selectable)

    @property
    def pts(self):
        n = self.up_axis
        c = self.c_axis
        x = n * self.size
        y = c * self.size / 2
        return [self.pos_3d - x + y, self.pos_3d - x - y, self.pos_3d]


class EditableText(GlText, GlHandle):
    def __init__(self, sensor_size, size, selectable=False):
        GlHandle.__init__(self, sensor_size, size, selectable)
        GlText.__init__(self)

    def set_pos(self, context, value, pos_3d, direction, normal=Vector((0, 0, 1))):
        self.up_axis = direction.normalized()
        self.c_axis = self.up_axis.cross(normal)
        self.pos_3d = pos_3d
        self.value = value
        self.sensor_width, self.sensor_height = self.text_size
        self.pos_2d = self.position_2d_from_coord(context, pos_3d)

    @property
    def sensor_center(self):
        return self.pos_3d


class FeedbackPanel():
    """
        Feed-back panel
        inspired by np_station
    """
    def __init__(self, title='Archipack'):

        self.main_title = GlText(d=2, label=title, font_size=feedback_size_main, colour=feedback_colour_main)
        self.title = GlText(d=2, font_size=feedback_size_title, colour=feedback_colour_main)
        self.spacing = Vector((0.5 * feedback_size_shortcut, 0.5 * feedback_size_shortcut))
        self.margin = 50
        self.explanation = GlText(d=2, font_size=feedback_size_shortcut, colour=feedback_colour_main)
        self.shortcut_area = GlPolygon(colour=(0, 0.4, 0.6, 0.2), d=2)
        self.title_area = GlPolygon(colour=(0, 0.4, 0.6, 0.5), d=2)
        self.shortcuts = []
        self.on = False

    def disable(self):
        self.on = False

    def enable(self):
        self.on = True

    def instructions(self, context, title, explanation, shortcuts):
        """
            position from bottom to top
        """
        w = context.region.width
        # h = context.region.height
        # 0,0 = bottom left
        pos = Vector((self.margin + self.spacing.x, self.margin))
        self.shortcuts = []

        if len(shortcuts) > 0:
            pos.y += self.spacing.y

        add_y = 0

        for key, label in shortcuts:
            key = GlText(d=2, label=key + ' : ', font_size=feedback_size_shortcut, colour=feedback_colour_key)
            label = GlText(d=2, label=label, font_size=feedback_size_shortcut, colour=feedback_colour_shortcut)
            ks = key.text_size
            ls = label.text_size
            space = ks.x + ls.x + self.spacing.x
            add_y = ks.y + self.spacing.y
            if pos.x + space > w - 2 * self.margin:
                # add_y = 0
                pos.y += ks.y + 2 * self.spacing.y
                pos.x = self.margin + self.spacing.x
            key.pos_3d = pos.copy()
            pos.x += ks.x
            label.pos_3d = pos.copy()
            pos.x += ls.x + 2 * self.spacing.x
            self.shortcuts.extend([key, label])

        if len(shortcuts) > 0:
            pos.y += add_y + 0.5 * self.spacing.y

        self.shortcut_area.pts_3d = [
            (self.margin, self.margin),
            (w - self.margin, self.margin),
            (w - self.margin, pos.y),
            (self.margin, pos.y)
            ]

        if len(shortcuts) > 0:
            pos.y += 0.5 * self.spacing.y

        self.title.label = ' : ' + title
        main_title_size = self.main_title.text_size
        self.title_area.pts_3d = [
            (self.margin, pos.y),
            (w - self.margin, pos.y),
            (w - self.margin, pos.y + main_title_size.y + 2 * self.spacing.y),
            (self.margin, pos.y + main_title_size.y + 2 * self.spacing.y)
            ]
        pos.y += self.spacing.y
        self.explanation.label = explanation
        self.explanation.pos_3d = (w - self.margin - self.spacing.x - self.explanation.text_size.x, pos.y)
        self.main_title.pos_3d = (self.margin + self.spacing.x, pos.y)
        self.title.pos_3d = (self.margin + self.spacing.x + main_title_size.x, pos.y)

    def draw(self, context, render=False):
        if self.on:
            """
                draw from bottom to top
                so we are able to always fit needs
            """
            self.shortcut_area.draw(context)
            self.title_area.draw(context)
            self.main_title.draw(context)
            self.title.draw(context)
            self.explanation.draw(context)
            for s in self.shortcuts:
                s.draw(context)


class GlCursorFence():
    """
        Cursor crossing Fence
    """
    def __init__(self, width=1, colour=(1.0, 1.0, 1.0, 0.5), style=bgl.GL_LINE_STIPPLE):
        self.line_x = GlLine(d=2)
        self.line_x.style = style
        self.line_x.width = width
        self.line_x.colour_inactive = colour
        self.line_y = GlLine(d=2)
        self.line_y.style = style
        self.line_y.width = width
        self.line_y.colour_inactive = colour
        self.on = True

    def set_location(self, context, location):
        w = context.region.width
        h = context.region.height
        x, y = location
        self.line_x.p = Vector((0, y))
        self.line_x.v = Vector((w, 0))
        self.line_y.p = Vector((x, 0))
        self.line_y.v = Vector((0, h))

    def enable(self):
        self.on = True

    def disable(self):
        self.on = False

    def draw(self, context, render=False):
        if self.on:
            self.line_x.draw(context)
            self.line_y.draw(context)


class GlCursorArea():
    def __init__(self,
                width=1,
                bordercolour=(1.0, 1.0, 1.0, 0.5),
                areacolour=(1.0, 1.0, 1.0, 0.1),
                style=bgl.GL_LINE_STIPPLE):

        self.border = GlPolyline(bordercolour, d=2)
        self.border.style = style
        self.border.width = width
        self.area = GlPolygon(areacolour, d=2)
        self.on = False

    def set_location(self, context, p0, p1):
        x0, y0 = p0
        x1, y1 = p1
        pos = [Vector((x0, y0)), Vector((x0, y1)), Vector((x1, y1)), Vector((x1, y0))]
        self.area.set_pos(pos)
        self.border.set_pos(pos)

    def enable(self):
        self.on = True

    def disable(self):
        self.on = False

    def draw(self, context, render=False):
        if self.on:
            self.area.draw(context)
            self.border.draw(context)
