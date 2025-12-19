#!/usr/bin/env python3
import inkex
from inkex import Color, Rectangle

class ReplaceRectRGB(inkex.EffectExtension):
    def add_arguments(self, pars):
        # .inxファイルで定義したパラメータを受け取る設定
        pars.add_argument("--find_color", type=str, default="ff0000", help="Color to find")
        pars.add_argument("--replace_color", type=str, default="0000ff", help="Color to replace with")

    def get_color(self, color_str):
        s = str(color_str).strip()
        if not s:
            return None
        # '#' で始まっていない場合、HEXコードとみなして '#' を付与
        if not s.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in s):
             s = '#' + s
        return Color(s)

    def effect(self):
        try:
            target_color = self.get_color(self.options.find_color)
            replacement_color = self.get_color(self.options.replace_color)
        except Exception as e:
            inkex.errormsg(f"カラー変換エラー: 入力された色を確認してください。\n詳細: {str(e)}")
            return

        if target_color is None or replacement_color is None:
            inkex.errormsg("エラー: 色が入力されていません。")
            return

        # 選択範囲がある場合は選択範囲内を、なければドキュメント全体を対象にする
        selection = self.svg.selection
        if not selection:
            # ドキュメント内のすべての長方形(rect)を取得
            nodes = self.svg.xpath('//svg:rect')
        else:
            # 選択範囲内の長方形のみをフィルタリング
            nodes = [node for node in selection.values() if isinstance(node, Rectangle)]

        count = 0
        for node in nodes:
            # fill（塗りつぶし）プロパティを取得
            fill_value = node.style.get('fill')

            # 塗りつぶしが設定されていない、またはグラデーション等の場合はスキップ
            if not fill_value or fill_value == 'none' or fill_value.startswith('url'):
                continue

            try:
                # 現在の色を取得して比較
                current_color = Color(fill_value)
                
                # 色が一致する場合（Colorオブジェクト同士で比較すると正確です）
                # 赤、緑、青の値が一致するか確認
                if (current_color.red == target_color.red and 
                    current_color.green == target_color.green and 
                    current_color.blue == target_color.blue):
                    
                    # 色を置換
                    node.style['fill'] = replacement_color
                    count += 1
            except:
                pass # 色の解析に失敗した場合は無視

        if count == 0:
            inkex.errormsg("該当する色の長方形は見つかりませんでした。")

if __name__ == '__main__':
    ReplaceRectRGB().run()