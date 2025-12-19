#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inkex
from inkex import Rectangle, Group, ShapeElement
from utils import set_gradient_def, get_layer_or_fallback

class ManageRectGrid(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--direction", type=str, default="right", help="Direction to add/delete")
        pars.add_argument("--amount", type=int, default=1, help="Number of cols/rows")
        pars.add_argument("--mode", type=str, default="add", help="Action: add or delete")
        pars.add_argument("--resize_doc", type=inkex.Boolean, default=False, help="Resize document to content")

    def set_gradient_def(self):
        return set_gradient_def(self.svg)

    def effect(self):
        layer = get_layer_or_fallback(self.svg)
        
        # 2. レイヤー内のRectオブジェクトを取得
        rects = [node for node in layer if isinstance(node, Rectangle)]

        if not rects:
            inkex.errormsg("レイヤー内にRectが見つかりません。")
            return


        is_horizontal = self.options.direction in ['left', 'right']
        tolerance = 1.0 

        def get_groups(rect_list, verify_axis_x):
            items = []
            for r in rect_list:
                bbox = r.bounding_box()
                pos = bbox.center_x if verify_axis_x else bbox.center_y
                items.append({'node': r, 'pos': pos, 'bbox': bbox})
            
            # 座標順(小さい順)にソート
            # X: 左→右, Y: 上→下
            items.sort(key=lambda x: x['pos'])
            
            groups = []
            if not items:
                return groups

            current_group = [items[0]]
            for i in range(1, len(items)):
                if abs(items[i]['pos'] - items[i-1]['pos']) < tolerance:
                    current_group.append(items[i])
                else:
                    groups.append(current_group)
                    current_group = [items[i]]
            groups.append(current_group)
            return groups

        groups = get_groups(rects, is_horizontal)
        
        direction = self.options.direction
        mode = self.options.mode
        amount = self.options.amount

        # 3. 処理の実行
        if mode == 'delete':
            # 削除対象の特定
            if direction in ['right', 'bottom']:
                # 右/下なら「末尾」から削除
                target_groups = groups[-amount:] if amount < len(groups) else groups
            else: # left, top
                # 左/上なら「先頭」から削除
                target_groups = groups[:amount]

            for group in target_groups:
                for item in group:
                    layer.remove(item['node'])
        elif mode == 'add':
            # 追加元の特定
            if direction in ['right', 'bottom']:
                src_group = groups[-1] 
            else: 
                src_group = groups[0] 

            # 移動距離（ピッチ）の計算
            step_size = 0
            if len(groups) >= 2:
                if direction in ['right', 'bottom']:
                    p1 = groups[-1][0]['pos']
                    p2 = groups[-2][0]['pos']
                else:
                    p1 = groups[1][0]['pos']
                    p2 = groups[0][0]['pos']
                step_size = abs(p1 - p2)
            else:
                ref_bbox = src_group[0]['bbox']
                step_size = ref_bbox.width if is_horizontal else ref_bbox.height

            # 方向ごとの移動ベクトル
            vec_x, vec_y = 0, 0
            if direction == 'right':
                vec_x = step_size
            elif direction == 'left':
                vec_x = -step_size
            elif direction == 'bottom':
                vec_y = step_size
            elif direction == 'top':
                vec_y = -step_size

            gradient_id = self.set_gradient_def()
            # 追加ループ (新規作成モード)
            for i in range(1, amount + 1):
                dx = vec_x * i
                dy = vec_y * i
                
                for item in src_group:
                    original_node = item['node']
                    
                    # --- ここから変更: 新規Rect作成ロジック ---
                    
                    # 1. 元のノードの属性を辞書としてコピー
                    new_attribs = dict(original_node.attrib)
                    
                    # 2. IDは削除（新規作成時に自動生成させるため）
                    if 'id' in new_attribs:
                        del new_attribs['id']
                    
                    # 3. 新しいRectangleオブジェクトをインスタンス化
                    new_node = Rectangle(**new_attribs)
                    new_node.style['fill'] = f'url(#{gradient_id})'
                    
                    layer.add(new_node)
                    
                    new_node.transform.add_translate(dx, dy)
            
            delta = step_size * amount
            direction_config = {
                "top":  (3, 'height', (0, delta)),
                "left": (2, 'width',  (delta, 0))
            }
            if direction in direction_config:
                delta = step_size * amount
                vbox_idx, attr_name, translate_vector = direction_config[direction]

                # --- 1. すべての要素を移動 ---
                # カンバスを広げた分、既存の要素をずらす処理
                for element in self.svg:
                    if isinstance(element, (inkex.Defs, inkex.NamedView, inkex.Metadata)):
                        continue
                    element.transform.add_translate(*translate_vector)

                vbox_list = self.svg.get_viewbox()
                if len(vbox_list) == 4:
                    # 対象の次元（widthまたはheight）を拡張
                    vbox_list[vbox_idx] += delta
                    
                    # 文字列に戻してセット
                    new_vbox_str = ' '.join(str(x) for x in vbox_list)
                    self.svg.set('viewBox', new_vbox_str)

                # --- 3. 物理サイズ属性（width/height）の更新 ---
                current_unit_value = self.svg.get(attr_name)

                if current_unit_value:
                    # 単位付き数値をパースして計算 (例: "100mm" -> px変換)
                    parsed_val = self.svg.unit_to_viewport(current_unit_value)
                    new_val_px = parsed_val + delta
                    self.svg.set(attr_name, str(new_val_px))
                else:
                    # 属性がない場合はViewBoxの計算結果を利用してセット
                    if len(vbox_list) == 4:
                        self.svg.set(attr_name, str(vbox_list[vbox_idx]))



        # 4. ドキュメントサイズのリサイズ
        if self.options.resize_doc:
            bbox = None
            for node in self.svg:
                if isinstance(node, (ShapeElement, Group)):
                    try:
                        child_bbox = node.bounding_box()
                        if child_bbox: 
                            if bbox is None:
                                bbox = child_bbox
                            else:
                                bbox += child_bbox
                    except Exception:
                        pass
            
            if bbox:
                self.svg.set('viewBox', f"{bbox.x} {bbox.y} {bbox.width} {bbox.height}")
                self.svg.set('width', f"{bbox.width}px")
                self.svg.set('height', f"{bbox.height}px")

if __name__ == '__main__':
    ManageRectGrid().run()