from math import pi, sin, cos, hypot, atan2, radians
import re
import gi

from .resources import Fonts, Images, DrawParams, DrawParam

gi.require_version("Gtk", "3.0")
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo
import cairo

SCALE_192 = 7.559
SCALE_128 = 5.039
COMMANDS = set('SMLQBAC')
COMMAND_RE = re.compile(r"([SMLQBAC])")
FLOAT_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")

font_map = PangoCairo.font_map_get_default()
print([f.get_name() for f in font_map.list_families() if
       'song' in f.get_name().lower() or 'cour' in f.get_name().lower() or 'kai' in f.get_name().lower()])


# https://github.com/Kozea/CairoSVG/blob/main/cairosvg/helpers.py#L95
def rotate(x, y, angle):
    """Rotate a point of an angle around the origin point."""
    return x * cos(angle) - y * sin(angle), y * cos(angle) + x * sin(angle)


def point_angle(cx, cy, px, py):
    """Return angle between x axis and point knowing given center."""
    return atan2(py - cy, px - cx)


def _tokenize_path(pathdef):
    for x in COMMAND_RE.split(pathdef):
        if x in COMMANDS:
            yield x
        for token in FLOAT_RE.findall(x):
            yield token


def _draw_AbbreviatedData(draw, boundary, path, fillColor=(128, 128, 128), lineWidth=2, scale=SCALE_192):
    x_start = boundary[0]
    y_start = boundary[1]
    current_pos = (x_start, y_start)

    elements = list(_tokenize_path(path))
    elements.reverse()

    while elements:
        if elements[-1] in COMMANDS:
            command = elements.pop()
        else:
            raise Exception('操作符违法')

        if command == 'M':
            x = scale * float(elements.pop())
            y = scale * float(elements.pop())
            pos = (x_start + x, y_start + y)
            current_pos = pos

        elif command == 'L':
            x = scale * float(elements.pop())
            y = scale * float(elements.pop())
            pos = (x_start + x, y_start + y)
            draw.line(current_pos + pos, fill=fillColor, width=lineWidth)

        elif command == 'B':
            pass


def _cairo_draw_path(cr, boundary, path):
    x_start = boundary[0]
    y_start = boundary[1]
    current_pos = (x_start, y_start)
    # cr.translate(x_start, y_start)
    elements = list(_tokenize_path(path))
    elements.reverse()

    command = None
    while elements:
        if elements[-1] in COMMANDS:
            command = elements.pop()
        else:
            raise Exception(f'操作符 {elements[-1]} 违法')

        if command == 'M':
            x = float(elements.pop())
            y = float(elements.pop())
            cr.move_to(x, y)
            current_pos = (x, y)
        elif command == 'L':
            x = float(elements.pop())
            y = float(elements.pop())
            # pos = (x_start + x, y_start + y)
            cr.line_to(x, y)
            current_pos = (x, y)
            # draw.line(current_pos + pos, fill=fillColor, width=lineWidth)

        elif command == 'B':
            x1 = float(elements.pop())
            y1 = float(elements.pop())
            x2 = float(elements.pop())
            y2 = float(elements.pop())
            x3 = float(elements.pop())
            y3 = float(elements.pop())
            cr.curve_to(x1, y1, x2, y2, x3, y3)
            current_pos = (x3, y3)
        elif command == 'A':
            # rx ry x-axis-rotation large-arc-flag sweep-flag x y
            # A 1.875 1.875 90 0 1 0.125 2
            # GBT_33190-2016_电子文件存储与交换格式版式文档.pdf #9.3.5
            # https://github.com/Kozea/CairoSVG/blob/main/cairosvg/path.py#L209
            ellipse_x, ellipse_y, rotation_angle, large, sweep, x3, y3 = [elements.pop() for _ in range(7)]
            rx, ry = float(ellipse_x), float(ellipse_y)
            rotation = radians(float(rotation_angle))
            large, sweep = int(large), int(sweep)
            x1, y1 = current_pos
            radius = rx
            radii_ratio = ry / rx
            x3, y3 = float(x3) - x1, float(y3) - y1

            xe, ye = rotate(x3, y3, -rotation)
            ye /= radii_ratio
            # Find the angle between the second point and the x axis
            angle = point_angle(0, 0, xe, ye)

            # Put the second point onto the x axis
            xe = hypot(xe, ye)
            ye = 0

            # Update the x radius if it is too small
            rx = max(rx, xe / 2)

            # Find one circle centre
            xc = xe / 2
            yc = (rx ** 2 - xc ** 2) ** .5

            # Choose between the two circles according to flags
            if not (large ^ sweep):
                yc = -yc

            # Define the arc sweep
            arc = cr.arc if sweep else cr.arc_negative

            # Put the second point and the center back to their positions
            xe, ye = rotate(xe, 0, angle)
            xc, yc = rotate(xc, yc, angle)

            # Find the drawing angles
            angle1 = point_angle(xc, yc, 0, 0)
            angle2 = point_angle(xc, yc, xe, ye)

            cr.save()
            cr.translate(x1, y1)
            cr.rotate(rotation)
            cr.scale(1, radii_ratio)
            arc(xc, yc, rx, angle1, angle2)
            cr.restore()
            current_pos = (current_pos[0] + x3, current_pos[1] + y3)
        elif command == 'Q':
            x1 = float(elements.pop())
            y1 = float(elements.pop())
            x2 = float(elements.pop())
            y2 = float(elements.pop())
            cr.curve_to(x1, y1, x1, y1, x2, y2)
            current_pos = (x2, y2)
        elif command == 'C':
            pass


def _trans_Delta(elements, scale=SCALE_192):
    parsed = []
    elements.reverse()
    while elements:
        e = elements.pop()
        if e == 'g':
            c = int(elements.pop())
            v = float(elements.pop())
            parsed += c * [v * scale]
        else:
            parsed.append(float(e) * scale)
    # print('_trans_Delta', elements, parsed)
    return parsed


layer_draw: DrawParam = DrawParam()


def cairo_layer(node):
    global layer_draw
    layer_drawparam = node.attr.get('DrawParam', None)
    if layer_drawparam in DrawParams:
        layer_draw = DrawParams.get(layer_drawparam)
        print(layer_draw)
    else:
        layer_draw = DrawParam()


def cairo_path(cr: cairo.Context, node):
    lineWidth = layer_draw.line_width if layer_draw.line_width else 0.5
    lineWidth = float(node.attr['LineWidth']) if 'LineWidth' in node.attr else lineWidth
    boundary = [float(i) for i in node.attr['Boundary'].split(' ')]
    ctm = None
    if 'CTM' in node.attr:
        ctm = [float(i) for i in node.attr['CTM'].split(' ')]
    fillColor = layer_draw.fill_color
    if 'FillColor' in node and 'Value' in node.attr:
        fillColor = [float(i) / 256. for i in node['FillColor'].attr['Value'].split(' ')]
    using_fill_color = sum(fillColor) > 0.0
    strokeColor = layer_draw.stroke_color
    if 'StrokeColor' in node and 'Value' in node.attr:
        strokeColor = [float(i) / 256. for i in node['StrokeColor'].attr['Value'].split(' ')]
    # print('draw path', boundary, fillColor, strokeColor)
    cr.save()
    if ctm:
        # 如果有ctm，对cr进行的矩阵变换
        # print('cairo path ctm:', ctm)
        ctm_matrix = cairo.Matrix(*ctm)
        matrix = cr.get_matrix().multiply(ctm_matrix)
        cr.set_matrix(matrix)
        ctm_matrix.invert()
        cr.translate(*ctm_matrix.transform_point(boundary[0], boundary[1]))
    else:
        cr.translate(boundary[0], boundary[1])

    AbbreviatedData = node['AbbreviatedData'].text
    if using_fill_color:
        cr.set_source_rgba(*fillColor)
    else:
        cr.set_source_rgba(*strokeColor)
    cr.set_line_width(lineWidth)
    _cairo_draw_path(cr, boundary, AbbreviatedData)
    cr.stroke()
    cr.restore()


def cairo_text(cr: cairo.Context, node):
    boundary = [float(i) for i in node.attr['Boundary'].split(' ')]
    ctm = None
    if 'CTM' in node.attr:
        ctm = [float(i) for i in node.attr['CTM'].split(' ')]
    font_id = node.attr['Font']
    font_family = get_font_from_id(font_id).get_font_family()
    font_size = float(node.attr['Size']) / 1.3
    fillColor = layer_draw.fill_color
    if 'FillColor' in node and 'Value' in node['FillColor'].attr:
        fillColor = [float(i) / 255. for i in node['FillColor'].attr['Value'].split(' ')]

    strokeColor = layer_draw.stroke_color
    if 'StrokeColor' in node and 'Value' in node['StrokeColor'].attr:
        strokeColor = [float(i) / 255. for i in node['StrokeColor'].attr['Value'].split(' ')]

    TextCode = node['TextCode']
    text = TextCode.text
    # print(f'cario text {text}, {font_id}')

    deltaX = None
    deltaY = None
    if 'DeltaX' in TextCode.attr:
        deltaX = _trans_Delta(TextCode.attr['DeltaX'].split(' '), scale=1)
    if deltaX and len(deltaX) + 1 != len(text):
        # raise Exception(f'{text} TextCode DeltaX 与字符个数不符')
        deltaX = deltaX[:len(text)-1]
    if deltaX and len(deltaX) < len(text) - 1:
        deltaX.extend([deltaX[-1]] * (len(text) - 1 - len(deltaX)))

    if 'DeltaY' in TextCode.attr:
        deltaY = _trans_Delta(TextCode.attr['DeltaY'].split(' '), scale=1)
    if deltaY and len(deltaY) + 1 != len(text):
        # raise Exception(f'{text} TextCode DeltaY 与字符个数不符')
        deltaY = deltaY[:len(text)-1]
    if deltaY and len(deltaY) < len(text) - 1:
        deltaY.extend([deltaY[-1]] * (len(text) - 1 - len(deltaY)))

    X = float(TextCode.attr['X'])
    Y = float(TextCode.attr['Y'])
    for idx, rune in enumerate(text):
        cr.save()
        # cr.identity_matrix()
        # cr.scale(SCALE_128, SCALE_128)
        layout = PangoCairo.create_layout(cr)
        layout.set_text(rune, -1)
        # print(font_family, rune)
        desc = Pango.FontDescription.from_string(f"{font_family} {font_size}")
        layout.set_font_description(desc)

        ink_rect, logical_rect = layout.get_pixel_extents()
        r_w, r_h = layout.get_size()
        baseline = layout.get_baseline() / Pango.SCALE
        # print(f'{rune}, baseline: {baseline}, X:{X}, Y:{Y} Boundary:{boundary}')

        offset_x = sum(deltaX[:idx]) if deltaX else 0
        offset_y = sum(deltaY[:idx]) if deltaY else 0
        # cr.move_to(boundary[0] + offset_x, boundary[1] + offset_y)
        cr.move_to(boundary[0], boundary[1])
        if ctm:
            matrix = cr.get_matrix().multiply(cairo.Matrix(*ctm))
            cr.set_matrix(matrix)
        cr.rel_move_to(X + offset_x, Y + offset_y)

        cr.set_source_rgb(*fillColor)
        # PangoCairo.show_layout(cr, layout)
        PangoCairo.show_layout_line(cr, layout.get_line(0))
        cr.restore()
    pass


def cairo_image(cr: cairo.Context, node):
    resource_id = node.attr['ResourceID']
    boundary = [float(i) for i in node.attr['Boundary'].split(' ')]
    ctm = None
    if 'CTM' in node.attr:
        ctm = [float(i) for i in node.attr['CTM'].split(' ')]
    img_surface = get_res_image(resource_id).get_cairo_surface()

    cr.save()
    x, y = boundary[0], boundary[1]
    width = cr.get_matrix().xx * boundary[2]
    height = cr.get_matrix().yy * boundary[3]
    # print('cairo image ctm:', ctm)  # ctm用不到
    x, y = cr.get_matrix().transform_point(x, y)

    # 画图片是fillparent，自己重新计算缩放matrix， 同时缩放基础点x，y
    matrix = cairo.Matrix(width / img_surface.get_width(), 0, 0, height / img_surface.get_height(), 0, 0)
    cr.identity_matrix()
    cr.set_matrix(matrix)
    matrix.invert()
    x, y = matrix.transform_point(x, y)
    # x, y = cr.get_matrix().invert().transform_point(x, y)
    # print(x, y)
    cr.set_source_surface(img_surface, x, y)
    cr.paint()
    cr.restore()
    pass


def get_font_from_id(font_id):
    return Fonts.get(font_id)


def get_res_image(res_id):
    return Images.get(res_id)
