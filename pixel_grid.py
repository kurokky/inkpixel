#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex
from inkex import Rectangle
from utils import set_gradient_def, normalize_color, update_grid

class PixelGrid(inkex.EffectExtension):
    def set_gradient_def(self):
        return set_gradient_def(self.svg)

    def update_grid(self, spacing_x, spacing_y):
        root = self.document.getroot()
        update_grid(root, spacing_x, spacing_y)

    def add_arguments(self, pars):
        # .inxファイルで定義したパラメータを受け取る設定
        pars.add_argument("--num_rows", type=int, default=10, help="Number of rows")
        pars.add_argument("--num_cols", type=int, default=10, help="Number of columns")
        pars.add_argument("--pixel_size", type=float, default=5.0, help="Size of one pixel in mm")
        pars.add_argument("--resize_doc", type=inkex.Boolean, default=False, help="Resize document to fit")
    def effect(self):
        # ユーザー入力の取得
        rows = self.options.num_rows
        cols = self.options.num_cols
        size_mm = self.options.pixel_size

        total_width = cols * size_mm
        total_height = rows * size_mm

        size_px = self.svg.unittouu(f"{size_mm}mm")

        if self.options.resize_doc:
            self.svg.set('width', f'{total_width}')
            self.svg.set('height', f'{total_height}')
            self.svg.set('viewBox', f'0 0 {total_width} {total_height}')

        layer = self.svg.get_current_layer()

        self.update_grid(size_mm, size_mm)

        gradient_id = self.set_gradient_def()
        # rect要素の作成ループ
        for r in range(rows):
            for c in range(cols):
                # 座標計算
                x = c * size_px
                y = r * size_px

                # Rect要素の作成
                rect = layer.add(Rectangle())
                rect.set('x', x)
                rect.set('y', y)
                rect.set('width', size_px)
                rect.set('height', size_px)
                rect.style['fill'] = f'url(#{gradient_id})'
                rect.set('id', f'grid_{size_mm}_{r}_{c}')

if __name__ == '__main__':
    PixelGrid().run()