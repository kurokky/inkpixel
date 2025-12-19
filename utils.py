from lxml import etree
import inkex
from inkex import RadialGradient, Stop

"""
現在のレイヤーを取得し、失敗した場合は最背面（一番下）のレイヤーを返す。
レイヤーが一つもない場合はルート(svg)を返す。
Args:
    svg_root (inkex.SvgDocumentElement): self.svg オブジェクト
Returns:
    inkex.BaseElement: 対象となるレイヤーまたはSVGルート
"""
def get_layer_or_fallback(svg_root):
    layer = svg_root.get_current_layer()
    if layer is not None:
        return layer
    for child in svg_root:
        if isinstance(child, inkex.Group) and child.get('inkscape:groupmode') == 'layer':
            return child
    return svg_root

def set_gradient_def(svg):
    target_color = '#ffffff'
    gradient_id = None
    
    # self.svg.defs ではなく svg.defs に変更
    for elem in svg.defs:
        if isinstance(elem, RadialGradient):
            stops = list(elem)
            if len(stops) == 2:
                c1 = stops[0].get('stop-color') or stops[0].style.get('stop-color')
                o1 = stops[0].get('stop-opacity') or stops[0].style.get('stop-opacity') or '1'
                
                c2 = stops[1].get('stop-color') or stops[1].style.get('stop-color')
                o2 = stops[1].get('stop-opacity') or stops[1].style.get('stop-opacity') or '1'

                is_white_c1 = c1 and c1.lower() in [target_color, '#fff', 'white']
                is_white_c2 = c2 and c2.lower() in [target_color, '#fff', 'white']
                
                is_opaque_start = str(o1).strip() == '1'
                is_transparent_end = str(o2).strip() == '0'

                if is_white_c1 and is_white_c2 and is_transparent_end:
                    gradient_id = elem.get('id')
                    break
    
    if gradient_id is None:
        # self.svg.get_unique_id ではなく svg.get_unique_id に変更
        gradient_id = svg.get_unique_id('radialGradient_white_alpha')
        
        gradient = RadialGradient()
        gradient.set('id', gradient_id)
        gradient.set('gradientUnits', 'objectBoundingBox')
        gradient.set('cx', '50%')
        gradient.set('cy', '50%')
        gradient.set('r', '50%')

        stop_start = Stop()
        stop_start.set('offset', '0%')
        stop_start.set('stop-color', target_color)
        stop_start.set('stop-opacity', '1')

        stop_end = Stop()
        stop_end.set('offset', '100%')
        stop_end.set('stop-color', target_color)
        stop_end.set('stop-opacity', '0')

        gradient.append(stop_start)
        gradient.append(stop_end)
        
        # self.svg.defs ではなく svg.defs に変更
        svg.defs.append(gradient)
        
    return gradient_id

def normalize_color(color_input):
    if not color_input or str(color_input).lower() == 'none':
        return None
    
    try:
        # inkex.Color は '#ff0000' や int型入力をよしなに扱ってくれる
        c = Color(color_input)
        # アルファチャンネルを除外してRGBのHexのみ返す (#rrggbb)
        return str(c.to_rgb())
    except:
        return None

def update_grid(svg_root, spacing_x, spacing_y):
    """
    SVGのルート要素を受け取り、グリッド(xygrid)を更新または作成する
    """
    namedview = None
    
    # self.document.getroot() の代わりに引数 svg_root を使用
    for elem in svg_root:
        if elem.tag == inkex.addNS('namedview', 'sodipodi'):
            namedview = elem
            break
    
    if namedview is None:
        namedview = etree.Element(inkex.addNS('namedview', 'sodipodi'))
        svg_root.insert(0, namedview)

    for grid in namedview.findall(inkex.addNS('grid', 'inkscape')):
        namedview.remove(grid)
    
    grid = etree.SubElement(namedview, inkex.addNS('grid', 'inkscape'))
    grid.set('type', 'xygrid')
    grid.set('units', 'mm')
    grid.set('spacingx', str(spacing_x)) # 数値が来てもいいように念のためstr化
    grid.set('spacingy', str(spacing_y))
    grid.set('originx', '0')
    grid.set('originy', '0')
    namedview.set('showgrid', 'true')

