#!/usr/bin/env python3
import sys
import os
import inkex
from inkex import Rectangle, Group, units, TextElement
from lxml import etree
import math
from utils import set_gradient_def, normalize_color, update_grid
import gettext as gettext_module
_ = gettext_module.gettext


class DotManageMain(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--mode", type=str, default="")
        pars.add_argument("--confirm_delete", type=inkex.Boolean, default=False)
        pars.add_argument("--command", type=str, default="")
        pars.add_argument("--only_grid", type=inkex.Boolean, default=False)
        pars.add_argument("--dot_size", type=str, default="32", help="Dot Grid Size in px")

    def set_gradient_def(self):
        return set_gradient_def(self.svg)

    def effect(self):
        command = self.options.command
        mode = self.options.mode
        #print(command, file=sys.stderr) # デバッグ用出力
        if command == "remove":
            self.colored_layer()
        elif command == "sep":
            self.separate_colors()
        elif command == "analyze":
            self.count_colors()
        elif command == "toggle":
            self.toggle_number_layer()
        elif mode == "list_page":
            self.list_colors()
        else:
            if not self.options.confirm_delete:
                inkex.errormsg(_("Please enable the checkbox in the settings to run."))
                return
            self.create_grid()

    def get_rects(self):
        """カレントレイヤーのRectを取得するヘルパー"""
        layer = self.svg.get_current_layer()
        return [node for node in layer if isinstance(node, Rectangle)]

    def list_colors(self):
        """カレントレイヤーにあるRectのFillカラー一覧をポップアップ表示"""
        rects = self.get_rects()
        if not rects:
            inkex.errormsg(_("Not find rects in current layer"))
            return

        found_colors = set()
        
        for r in rects:
            # style['fill'] を取得
            fill_val = r.style.get('fill')
            hex_color = self.normalize_color(fill_val)
            
            if hex_color:
                found_colors.add(hex_color)
            else:
                found_colors.add("None (塗りなし)")

        # ソートして表示用テキストを作成
        sorted_colors = sorted(list(found_colors))
        msg = "検出された色一覧:\n" + "\n".join(sorted_colors)
        msg += "\n\n※このHexコードをコピーして、置換モードで使用できます。"
        
        inkex.errormsg(msg)

    def count_colors(self):
        current_layer = self.svg.get_current_layer()
        rects = [node for node in current_layer if isinstance(node, Rectangle)]
        color_count = {}

        for node in rects:
            style = node.style
            fill = style.get('fill')
            
            is_alpha_gradient = (fill is not None) and ( ('url(#radialGradient_white_alpha' in fill) or ('url(#linearGradient' in fill) or ('url(#mesh' in fill))
            has_no_fill = (fill is None) or (fill == 'none') or is_alpha_gradient

            if not has_no_fill:
                color_code = str(fill).upper()
                if color_code in color_count:
                    color_count[color_code] += 1
                else:
                    color_count[color_code] = 1

        result_lines = ["Color Analysis Results:"]
        for color, count in color_count.items():
            result_lines.append(f"{color}: {count}")
        
        result_message = "\n".join(result_lines)
        inkex.errormsg(result_message)

    def toggle_number_layer(self):
        svg = self.svg
        analyze_layer = None
        existing_layers = svg.xpath('//svg:g[@inkscape:groupmode="layer" and @inkscape:label="analyze"]')
        if existing_layers:
            for layer in existing_layers:
                # 見つかったら削除 (親要素からremoveする)
                layer.getparent().remove(layer)
            return
        # 新しいanalyzeレイヤーを作成
        analyze_layer = Group()
        analyze_layer.set('inkscape:groupmode', 'layer')
        analyze_layer.set('inkscape:label', 'analyze')
        analyze_layer.style = {'display': 'inline'}
        
        svg.append(analyze_layer)

        # 現在選択されているレイヤーを取得
        current_layer = svg.get_current_layer()

        all_rects = [node for node in current_layer if isinstance(node, Rectangle)]

        if not all_rects:
            inkex.errormsg("Plase select a layer with rectangles.")
            return

        valid_rects = []
        for r in all_rects:
            try:
                r.x_val = float(r.get('x', 0))
                r.y_val = float(r.get('y', 0))
                valid_rects.append(r)
            except ValueError:
                continue
        
        if not valid_rects:
            return

        min_x = min(r.x_val for r in valid_rects)
        min_y = min(r.y_val for r in valid_rects)

        TOLERANCE = 1.0  # 誤差許容範囲
        
        target_rects = []
        for r in valid_rects:
            is_left_col = abs(r.x_val - min_x) < TOLERANCE
            is_top_row  = abs(r.y_val - min_y) < TOLERANCE
            
            if is_left_col or is_top_row:
                target_rects.append(r)

        if not target_rects:
            return
        all_target_x = sorted([r.x_val for r in target_rects])
        all_target_y = sorted([r.y_val for r in target_rects])

        # 座標を「ビン」にまとめてユニーク化する関数 (100.0 と 100.001 を同一視するため)
        def get_unique_coords(coords, tol=1.0):
            if not coords: return []
            unique = [coords[0]]
            for c in coords[1:]:
                # 直前の値との差が許容範囲を超えていれば新しい列/行とみなす
                if c - unique[-1] > tol:
                    unique.append(c)
            return unique

        unique_x_list = get_unique_coords(all_target_x, TOLERANCE)
        unique_y_list = get_unique_coords(all_target_y, TOLERANCE)

        analyze_layer = Group()
        analyze_layer.set('inkscape:groupmode', 'layer')
        analyze_layer.set('inkscape:label', 'analyze')
        analyze_layer.style = {'display': 'inline'}
        svg.append(analyze_layer)

        for r in target_rects:
            x = r.x_val
            y = r.y_val
            w = float(r.get('width', 0))
            h = float(r.get('height', 0))

            col_idx = -1
            for i, ux in enumerate(unique_x_list, start=1):
                if abs(x - ux) < TOLERANCE:
                    col_idx = i
                    break
            
            row_idx = -1
            for j, uy in enumerate(unique_y_list, start=1):
                if abs(y - uy) < TOLERANCE:
                    row_idx = j
                    break

            font_size = min(w, h) * 0.5
            new_rect = Rectangle()
            new_rect.set('x', x)
            new_rect.set('y', y)
            new_rect.set('width', w)
            new_rect.set('height', h)
            new_rect.style = {
                'fill': 'none',
                'stroke': 'none',
            }
            analyze_layer.append(new_rect)
            text = TextElement()
            if col_idx == 1:
                text.text = f"{row_idx}"
            else:
                text.text = f"{col_idx}"

            center_x = x + (w / 2)
            center_y = y + (h / 2)
            
            text.set('x', center_x)
            text.set('y', center_y)
            text.style = {
                'font-size': font_size,
                'font-family': 'sans-serif',
                'text-anchor': 'middle',
                'fill': '#000000',
                'dominant-baseline': 'central' 
            }
            analyze_layer.append(text)

    def update_grid(self, spacing_x, spacing_y):
        root = self.document.getroot()
        update_grid(root, spacing_x, spacing_y)

    def create_grid(self):
        grid_size = float(self.options.dot_size)
        namedview = self.svg.namedview

        if grid_size == 0.0:
            grid = namedview.findall('inkscape:grid')
            if grid is None:
                grid_size = self.options.dot_size
            else:
                first_grid = grid[0]
                spacing_x = first_grid.get('spacingx')
                spacing_y = first_grid.get('spacingy')
                #inkex.errormsg(f"Grid Size: {spacing_y}")
                grid_size = spacing_x

        size = grid_size
        svg = self.svg
        width  = svg.viewbox_width
        height = svg.viewbox_height

        self.update_grid(grid_size, grid_size)
        only_grid = self.options.only_grid
        if only_grid:
            return

        layer = svg.get_current_layer()
        if layer == self.svg:
            layers = [child for child in self.svg if isinstance(child, inkex.Layer)]
            if layers:
                layer = layers[-1]
        #remove all rect
        for child in list(layer):
            # 要素が「Rectangle (矩形)」かどうか判定
            if isinstance(child, inkex.Rectangle):
                child.delete()


        cols = int(width // size) + 1
        rows = int(height // size) + 1

        #inkex.errormsg(f"Cols: {cols}, Rows: {rows}")
        # gradientの定義を追加
        gradient_id = self.set_gradient_def()

        for r in range(rows):
            for c in range(cols):
                x = c * size
                y = r * size
                
                if x >= width or y >= height:
                    continue
                rect = Rectangle()
                rect.set('x', str(x))
                rect.set('y', str(y))
                rect.set('width', str(size))
                rect.set('height', str(size))
                # 塗りなし
                rect.style['fill'] = f'url(#{gradient_id})'
                rect.set('id', f'grid_{size}_{r}_{c}')
                layer.add(rect)

    def colored_layer(self):
        current_layer = self.svg.get_current_layer()
        # 現在のレイヤーからRectangleノードを取得（リストとして確保しておく）
        rects = [node for node in current_layer if isinstance(node, Rectangle)]

        target_layer_name = "colored_layer"

        # --- 手順1: 既存の colored_layer があれば削除 ---
        # ドキュメント内の全レイヤーを検索
        for existing_layer in self.svg.findall('svg:g[@inkscape:groupmode="layer"]'):
            if existing_layer.get('inkscape:label') == target_layer_name:
                existing_layer.getparent().remove(existing_layer)

        # --- 手順2: 新しいレイヤーを必ず作成 ---
        target_layer = self.svg.add(Group())
        target_layer.set('inkscape:groupmode', 'layer')
        target_layer.set('inkscape:label', target_layer_name)

        # --- 手順3: 条件に合うRectを抽出してコピー ---
        for node in rects:
            style = node.style
            fill = style.get('fill')
            
            # 特定のグラデーションURLが含まれているか判定
            is_alpha_gradient = (fill is not None) and ( ('url(#radialGradient_white_alpha' in fill) or ('url(#linearGradient' in fill) or ('url(#mesh' in fill))
            
            # 除外対象のFill判定 (None, 'none', または透明グラデーション)
            has_no_fill = (fill is None) or (fill == 'none') or is_alpha_gradient

            # Fillが有効な場合のみ処理
            if not has_no_fill:
                # ノードを複製
                new_node = node.copy()
                
                # 新しく作ったレイヤーに追加
                target_layer.add(new_node)
        current_layer.style['display'] = 'none'
        self.svg.namedview.set('inkscape:current-layer', target_layer.get_id())

    def separate_colors(self):
        current_layer = self.svg.get_current_layer()
        # 現在のレイヤーからRectangleノードを取得
        rects = [node for node in current_layer if isinstance(node, Rectangle)]
        color_layers = {}

        for node in rects:
            style = node.style
            fill = style.get('fill')
            
            # 特定のグラデーションURLが含まれているか判定
            is_alpha_gradient = (fill is not None) and ( ('url(#radialGradient_white_alpha' in fill) or ('url(#linearGradient' in fill) or ('url(#mesh' in fill))
            
            # Fillの状態を判定 (None, 'none', または透明グラデーション)
            has_no_fill = (fill is None) or (fill == 'none') or is_alpha_gradient

            # --- 変更点: Fillが有効な場合のみ処理（削除処理は行わない） ---
            if not has_no_fill:
                # 色コードを取得 (例: #ff0000)
                color_code = str(fill).upper()
                
                # レイヤー名を定義
                layer_name = f"Color {color_code}"
                
                # 該当するレイヤーがキャッシュにない場合、ドキュメントから検索または作成
                if layer_name not in color_layers:
                    found_layer = None
                    # 既存のレイヤーを探す
                    for existing_layer in self.svg.findall('svg:g[@inkscape:groupmode="layer"]'):
                        if existing_layer.get('inkscape:label') == layer_name:
                            found_layer = existing_layer
                            break
                    
                    if found_layer is not None:
                        color_layers[layer_name] = found_layer
                    else:
                        # 新規レイヤー作成
                        new_layer = self.svg.add(Group())
                        new_layer.set('inkscape:groupmode', 'layer')
                        new_layer.set('inkscape:label', layer_name)
                        color_layers[layer_name] = new_layer

                # --- 重要な変更点: 移動ではなく「コピー」を追加 ---
                target_layer = color_layers[layer_name]
                
                # ノードを複製 (copyメソッドを使用)
                new_node = node.copy()
                
                # 複製したノードをターゲットレイヤーに追加
                target_layer.add(new_node)
                current_layer.style['display'] = 'none'

                self.svg.namedview.set('inkscape:current-layer', target_layer.get_id())

if __name__ == '__main__':
    DotManageMain().run()