#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import inkex
import json
import os
from inkex import Rectangle, Group
from utils import set_gradient_def, normalize_color, update_grid
import gettext as gettext_module
_ = gettext_module.gettext


class Ibe(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--json_file", type=str, help="Path to the JSON file")
        pars.add_argument("--pixel_size", type=float, default=5.0, help="Size of one pixel in mm")
        pars.add_argument("--resize_doc", type=inkex.Boolean, default=False, help="Resize document to content")
    def set_gradient_def(self):
        return set_gradient_def(self.svg)

    def get_first_grid_size(self):
        grids = self.svg.xpath('//inkscape:grid')
        if not grids:
            return None
        
        grid = grids[0]
        spacing_x = grid.get('spacingx')
        units = grid.get('units')

        if spacing_x is None:
            return None

        if units:
            return self.svg.unittouu(f"{spacing_x}{units}")
        else:
            return float(spacing_x)

    def setup_layer(self, layer_name):
        svg = self.svg
        xpath_query = f'//svg:g[@inkscape:groupmode="layer" and @inkscape:label="{layer_name}"]'
        existing_layers = svg.xpath(xpath_query)
        if existing_layers:
            for layer in existing_layers:
                layer.getparent().remove(layer)
            return None
        new_layer = Group()
        new_layer.set('inkscape:groupmode', 'layer')
        new_layer.set('inkscape:label', layer_name)
        new_layer.style = {'display': 'inline'}
        svg.append(new_layer)
        return new_layer

    def effect(self):
        # ファイルパスを取得
        file_path = self.options.json_file
        if not file_path:
            inkex.errormsg(_("Not find json file"))
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.draw_json_content(data)
        except json.JSONDecodeError:
            inkex.errormsg(_("Is this json file?"))
            return
        except Exception as e:
            inkex.errormsg(f"エラーが発生しました: {str(e)}")
            return

    def draw_json_content(self, data):
        size_px = self.get_first_grid_size()
        # グリッドがない場合はエラーメッセージを出して終了
        if size_px is None:
            inkex.errormsg(_("Grid not found in document properties."))
            return

        if not data["palette"]:
            inkex.errormsg(_("Palette not found"))
            return
        palette = data["palette"]
        #size_px = self.svg.unittouu(f"{size_mm}mm")

        layer_name = "from_ibe_json"
        temp_layer = self.setup_layer(layer_name)
        if temp_layer is None:
            return

        gradient_id = self.set_gradient_def()
        total_height = len(data["data"]) * size_px
        total_width  = len(data["data"][0]) * size_px

        for r ,row in enumerate(data["data"]):
            for c ,cell in enumerate(row):
                rgb = palette[cell]
                x = c * size_px
                y = r * size_px
                rect = temp_layer.add(Rectangle())
                rect.set('x', x)
                rect.set('y', y)
                rect.set('width', size_px)
                rect.set('height', size_px)
                if rgb == "transparent":
                    rect.style['fill'] = f'url(#{gradient_id})'
                else:
                    rect.style['fill'] = rgb
                rect.set('id', f'grid_{size_px}_{r}_{c}')

        if self.options.resize_doc:
            self.svg.set('width', f'{total_width}mm')
            self.svg.set('height', f'{total_height}mm')
            self.svg.set('viewBox', f'0 0 {total_width} {total_height}')



if __name__ == '__main__':
    Ibe().run()
