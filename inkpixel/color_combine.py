#!/usr/bin/env python3
import inkex
from inkex import Layer, PathElement, Color
import gettext as gettext_module
_ = gettext_module.gettext


class ColorCombine(inkex.EffectExtension):
    def effect(self):
        current_layer = self.svg.get_current_layer()
        rects = current_layer.findall('svg:rect')
        
        if not rects:
            inkex.errormsg(_("Not find rects in current layer"))
            return

        grouped_paths = {}
        styles_map = {}

        for rect in rects:
            style = rect.style
            fill = style.get('fill')
            if fill is None or fill == 'none' or ( ('url(#radialGradient_white_alpha' in fill) or ('url(#linearGradient' in fill) or ('url(#mesh' in fill)):
                continue
            try:
                color_key = Color(fill).to_rgba()
                color_key = tuple(color_key)
            except:
                color_key = str(fill)

            if color_key not in grouped_paths:
                grouped_paths[color_key] = []
                styles_map[color_key] = style

            grouped_paths[color_key].append(rect.get_path())
        new_layer = self.svg.add(Layer.new('Merged_Rects'))
        current_layer.addnext(new_layer) # カレントレイヤーの直上に配置

        count = 0
        for color_key, paths in grouped_paths.items():
            if not paths:
                continue

            combined_path_data = sum(paths, inkex.paths.Path())
            new_path_elem = PathElement()
            new_path_elem.style = styles_map[color_key]
            new_path_elem.path = combined_path_data
            
            label_name = f"Merged_{str(color_key)}"
            if isinstance(color_key, (list, tuple)) and len(color_key) >= 3:
                try:
                    r, g, b = int(color_key[0]), int(color_key[1]), int(color_key[2])
                    hex_str = f"#{r:02x}{g:02x}{b:02x}"
                    label_name = f"Merged_{hex_str}"
                except Exception:
                    pass
            new_path_elem.label = label_name
            new_path_elem.set_id(label_name)
            new_layer.append(new_path_elem)
            count += 1

        if count == 0:

            inkex.errormsg(_("No rectangles to process were found."))
        else:
            current_layer.style['display'] = 'none'
            namedview = self.svg.namedview
            namedview.set('inkscape:current-layer', label_name)

if __name__ == '__main__':
    ColorCombine().run()