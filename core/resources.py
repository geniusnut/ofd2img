import platform
import gi
import os

gi.require_version("Gtk", "3.0")
gi.require_version('PangoCairo', '1.0')
from gi.repository import PangoCairo
import cairo
from subprocess import Popen, PIPE


Fonts = {}
MultiMedias = {}
Images = {}
DrawParams = {}
font_map = PangoCairo.font_map_get_default()
Cairo_Font_Family_Names = [f.get_name() for f in font_map.list_families()]
# print(Cairo_Font_Family_Names)
print([f.get_name() for f in font_map.list_families() if
       'sun' in f.get_name().lower() or 'cour' in f.get_name().lower() or 'kai' in f.get_name().lower()])

OFD_FONT_MAP = {
    '楷体': ['KaiTi', 'Kai'],
    'KaiTi': ['KaiTi', 'Kai'],
    '宋体': ['SimSun', 'FangSong', 'STSong'],
    'Courier New': ['Courier New', 'Courier'],
}


class ResNotFoundException(Exception):
    """
    资源文件找不到
    """
    pass


class Font(object):
    ID = ''
    FontName = ''
    FamilyName = ''

    def __init__(self, attr):
        self.ID = attr['ID'] if 'ID' in attr else ''
        self.FontName = attr['FontName'] if 'FontName' in attr else ''
        self.FamilyName = attr['FamilyName'] if 'FamilyName' in attr else ''

    def get_font_family(self):
        # fixme: 印章的Font只有FontName， 沒有FamilyName
        if self.FontName in OFD_FONT_MAP:
            candidates = OFD_FONT_MAP[self.FontName]
            for c in candidates:
                if c in Cairo_Font_Family_Names:
                    return c
            raise ResNotFoundException(f'OFD字体文件[{self.FontName}] 找不到')
        return self.FontName

    def __repr__(self):
        return f'ID:{self.ID}, FontName:{self.FontName} FamilyName:{self.FamilyName}, System:{self.get_font_family()}'


class MultiMedia(object):
    def __init__(self, node):
        self.ID = node.attr['ID']
        self.Type = node.attr['Type']
        self.location = node['MediaFile'].text

    @staticmethod
    def parse_from_node(node):
        pass


class Image(MultiMedia):
    def __init__(self, node, _zf):
        super().__init__(node)
        self.png_location = None
        self.Format = node.attr['Format'] if 'Format' in node.attr else ''
        suffix = self.location.split('.')[-1]
        if suffix == 'jb2':
            # print('tempdir', tempfile.gettempdir())
            jb2_path = [loc for loc in _zf.namelist() if self.location in loc][0]

            tmp_folder = os.path.basename(_zf.filename).replace('.ofd', '')
            x_path = _zf.extract(jb2_path, tmp_folder)
            png_path = x_path.replace('.jb2', '.png')
            if platform.system() == 'Windows':
                Popen(['./bin/jbig2dec', '-o', png_path, x_path], stdout=PIPE)
            else:
                Popen(['jbig2dec', '-o', png_path, x_path], stdout=PIPE)

            # print(f'jbig2dec {png_path}', output.stdout.read())
            self.png_location = png_path
        elif suffix == 'png':
            png_path = [loc for loc in _zf.namelist() if self.location in loc][0]
            tmp_folder = os.path.basename(_zf.filename).replace('.ofd', '')
            x_path = _zf.extract(png_path, tmp_folder)
            self.png_location = x_path

    def get_cairo_surface(self):
        if self.png_location:
            return cairo.ImageSurface.create_from_png(self.png_location)
        return None

    def __repr__(self):
        return f'Image ID:{self.ID}, Format:{self.Format}'


class DrawParam(object):
    def __init__(self, node=None):
        self.ID = node.attr.get('ID', None) if node else None
        self.line_width = node.attr.get('LineWidth', 0.25) if node else 0.25

        self.stroke_color = next(iter(
            [[float(i) / 256. for i in child.attr['Value'].split(' ')]
             for child in node.children if child.tag == 'StrokeColor' and 'Value' in child.attr]
        ), [0, 0, 0]) if node else [0, 0, 0]
        self.fill_color = next(iter(
            [[float(i) / 256. for i in child.attr['Value'].split(' ')]
             for child in node.children if child.tag == 'FillColor' and 'Value' in child.attr]
        ), [0, 0, 0]) if node else [0, 0, 0]
        # print(self)

    def __repr__(self):
        return f'ID[{self.ID}], line_width: {self.line_width}, stroke{self.stroke_color}, fill{self.fill_color}'

def res_add_font(node, _zf):
    Fonts[node.attr['ID']] = Font(node.attr)


def res_add_multimedia(node, _zf):
    if node.attr['Type'] == 'Image':
        image = Image(node, _zf)
        Images[node.attr['ID']] = image


def res_add_drawparams(node, _zf):
    for draw_param in node.children:
        DrawParams[draw_param.attr['ID']] = DrawParam(draw_param)