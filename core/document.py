import io
import os
import traceback
from zipfile import PyZipFile

import cssselect2
from defusedxml import ElementTree

from .constants import UNITS
from .resources import res_add_font, res_add_multimedia, res_add_drawparams, MultiMedias, Images
from .surface import *


class OFDFile(object):
    """
    OFD Ref:GBT_33190-2016_电子文件存储与交换格式版式文档.pdf
    """
    #: contains OFD file header data
    header = None
    #: references to document's resources
    resources = None
    zf:PyZipFile

    def __init__(self, fobj):
        self.zf = fobj if isinstance(fobj, PyZipFile) else PyZipFile(fobj)
        if getattr(fobj, 'filename', None):
            self.zf.filename = getattr(fobj, 'filename')
        # for info in self._zf.infolist():
        #     print(info)
        self.node_tree = self.read_node('OFD.xml')

        # parse node
        self.document_node = self.read_node(self.node_tree['DocBody']['DocRoot'].text)
        self.document = OFDDocument(self.zf, self.document_node)
        # print_node_recursive(self.document_node)

    def read_node(self, location):
        document = self.zf.read(location)
        tree = ElementTree.fromstring(document)
        root = cssselect2.ElementWrapper.from_xml_root(tree)
        return Node(root)

    def draw_document(self, doc_num=0):
        document = self.document
        paths = []
        for page in document.pages:
            surface = Surface(page, os.path.split(self.zf.filename)[-1].strip('.ofd'))
            paths.append(surface.draw(page))
        return paths


class OFDDocument(object):
    def __init__(self, _zf, node, n=0):
        self.pages = []
        self._zf = _zf
        self.name = f'Doc_{n}'
        self.node = node
        try:
            self.physical_box = [float(i) for i in node['CommonData']['PageArea']['PhysicalBox'].text.split(' ')]
        except:
            self.physical_box = [0.0, 0.0, 210.0, 140.0]
        self._parse_res()
        # print('Resources:', Fonts, Images)
        # assert len(node['CommonData']['TemplatePage']) == len(node['Pages']['Page'])
        if isinstance(node['Pages']['Page'], list):
            sorted_pages = sorted(node['Pages']['Page'], key=lambda x: int(x.attr['ID']))
        else:
            sorted_pages = [node['Pages']['Page']]
        sorted_tpls = []
        if 'TemplatePage' in node['CommonData']:
            if isinstance(node['CommonData']['TemplatePage'], list):
                sorted_tpls = sorted(node['CommonData']['TemplatePage'], key=lambda x: int(x.attr['ID']))
            else:
                sorted_tpls = [node['CommonData']['TemplatePage']]

        seal_node = None
        if f'{self.name}/Signs/Sign_0/SignedValue.dat' in _zf.namelist():
            seal_file = OFDFile(io.BytesIO(_zf.read(f'{self.name}/Signs/Sign_0/SignedValue.dat')))
            seal_node = seal_file.document.pages[0].page_node

        annots = None
        if 'Annotations' in self.node:
            annots = self.get_node_tree(self.name + '/' + self.node['Annotations'].text)

        for i, p in enumerate(sorted_pages):
            page_id = p.attr['ID']
            page_node = self.get_node_tree(self.name + '/' + sorted_pages[i].attr['BaseLoc'])
            annot_node = None
            if annots:
                if isinstance(annots['Page'], list):
                    annot_page = next(iter([page for page in annots['Page'] if page.attr['PageID'] == page_id]), None)
                    if annot_page:
                        annot_node = self.get_node_tree(self.name + '/Annots/' + annot_page['FileLoc'].text)
                elif isinstance(annots['Page'], Node) and annots['Page'].attr['PageID'] == page_id:
                    annot_node = self.get_node_tree(self.name + '/Annots/' + annots['Page']['FileLoc'].text)
            tpl_node = None
            try:
                # get tpl_node from ID
                tpl = [tpl for tpl in sorted_tpls if page_node['Template'].attr['TemplateID'] == tpl.attr['ID']][0]
                tpl_node = self.get_node_tree(self.name + '/' + tpl.attr['BaseLoc'])
            except:
                pass
            # fallback using sorted one.
            if tpl_node is None and i < len(sorted_tpls):
                tpl_node = self.get_node_tree(self.name + '/' + sorted_tpls[i].attr['BaseLoc'])

            self.pages.append(OFDPage(self, f'Page_{i}', page_id, page_node, tpl_node, seal_node if i == 0 else None,
                                      annot_node=annot_node))

    def get_node_tree(self, location):
        if location not in self._zf.namelist():
            return None
        document = self._zf.read(location)
        tree = ElementTree.fromstring(document)
        root = cssselect2.ElementWrapper.from_xml_root(tree)
        return Node(root)

    def _parse_res(self):
        if 'DocumentRes' in self.node['CommonData']:
            node = Node.from_zp_location(self._zf, f"{self.name}/{self.node['CommonData']['DocumentRes'].text}")
            self._parse_res_node(node)

        if 'PublicRes' in self.node['CommonData']:
            node = Node.from_zp_location(self._zf, f"{self.name}/{self.node['CommonData']['PublicRes'].text}")
            self._parse_res_node(node)

    def _parse_res_node(self, node):
        if node.tag in RESOURCE_TAGS:
            try:
                RESOURCE_TAGS[node.tag](node, self._zf)
            except Exception as e:
                # Error in point parsing, do nothing
                print_node_recursive(node)
                print(traceback.format_exc())
                pass
            return  # no need to go deeper

        for child in node.children:
            self._parse_res_node(child)


class OFDPage(object):

    def __init__(self, parent: OFDDocument, name, page_id, page_node, tpl_node, seal_node=None, annot_node=None):
        self.parent = parent
        self.page_id = page_id
        self.name = f'{parent.name}_{name}'
        self.physical_box = self.parent.physical_box
        if 'Area' in page_node and 'PhysicalBox' in page_node['Area']:
            self.physical_box = [float(i) for i in page_node['Area']['PhysicalBox'].text.split(' ')]
        self.tpl_node = tpl_node
        self.page_node = page_node
        self.seal_node = seal_node
        self.annot_node = annot_node


class Surface(object):

    def __init__(self, page, name, dpi=192):
        self.page = page
        self.dpi = dpi
        self.filename = name

    @property
    def pixels_per_mm(self):
        return self.dpi * UNITS['mm']

    def cairo_draw(self, cr, node):
        # Only draw known tags
        if node.tag in CAIRO_TAGS:
            try:
                CAIRO_TAGS[node.tag](cr, node)
            except Exception as e:
                # Error in point parsing, do nothing
                print_node_recursive(node)
                print(traceback.format_exc())
                pass
            return  # no need to go deeper
        if node.tag == 'Appearance':
            boundary = [float(i) for i in node.attr['Boundary'].split(' ')]
            cr.save()
            cr.translate(boundary[0], boundary[1])
            for child in node.children:
                # Only draw known tags
                self.cairo_draw(cr, child)
            cr.restore()
            return
        elif node.tag == 'Layer':
            try:
                cairo_layer(node)
            except Exception as e:
                # Error in point parsing, do nothing
                print_node_recursive(node)
                print(traceback.format_exc())

        for child in node.children:
            # Only draw known tags
            self.cairo_draw(cr, child)

    def draw(self, page):
        # 计算A4 210mm 192dpi 下得到的宽高
        physical_width = self.page.physical_box[2]
        physical_height = self.page.physical_box[3]
        width = int(physical_width * self.pixels_per_mm)
        height = int(physical_height * self.pixels_per_mm)
        # print(f'create cairo surface, width: {width}, height: {height}')
        cairo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        self.cr = cairo.Context(cairo_surface)
        # scale mm to pixels
        self.cr.scale(self.pixels_per_mm, self.pixels_per_mm)
        self.cr.set_source_rgb(1, 1, 1)
        self.cr.paint()
        self.cr.move_to(0, 0)

        self.cairo_draw(self.cr, self.page.tpl_node)
        self.cairo_draw(self.cr, self.page.page_node)

        if self.page.annot_node:
            self.cairo_draw(self.cr, self.page.annot_node)

        # self.cr.scale(self.pixels_per_mm, self.pixels_per_mm)
        # draw StampAnnot
        if self.page.seal_node:
            # fixme: hardcode seal position
            self.cr.translate(90, 8)
            self.cairo_draw(self.cr, self.page.seal_node)

        path = f'{self.filename}_{page.name}.png'
        cairo_surface.write_to_png(path)
        cairo_surface.finish()
        return path


CAIRO_TAGS = {
    'PathObject': cairo_path,
    'TextObject': cairo_text,
    'ImageObject': cairo_image,
}

RESOURCE_TAGS = {
    'Font': res_add_font,
    'MultiMedia': res_add_multimedia,
    'DrawParams': res_add_drawparams,
}


class Node(dict):
    def __init__(self, element):
        super().__init__()
        self.element = element
        node = element.etree_element

        self.children = []
        self.text = node.text
        self.tag = (element.local_name
                    if element.namespace_url in ('', 'http://www.ofdspec.org/2016') else
                    '{%s}%s' % (element.namespace_url, element.local_name))
        self.attr = node.attrib
        for child in element.iter_children():
            child_node = Node(child)
            self.children.append(child_node)
            if child_node.tag:
                if child_node.tag in self:
                    if isinstance(self[child_node.tag], list):
                        self[child_node.tag].append(child_node)
                    else:
                        self[child_node.tag] = [self[child_node.tag], child_node]
                else:
                    self[child_node.tag] = child_node

    @staticmethod
    def from_zp_location(zf, location):
        # print('from_zp_location', location)
        document = zf.read(location)
        tree = ElementTree.fromstring(document)
        root = cssselect2.ElementWrapper.from_xml_root(tree)
        return Node(root)

    def __repr__(self):
        return f'Tag: {self.tag}, Attr: {self.attr}, Text: {self.text}'


def print_node_recursive(node, depth=0):
    print('  ' * depth, node)
    for child in node.children:
        print_node_recursive(child, depth=depth + 1)
