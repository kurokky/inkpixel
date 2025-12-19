#!/usr/bin/env python3
import inkex

class About(inkex.EffectExtension):
    def effect(self):
        #if self.svg.selection:
        #    for node in self.svg.selection:
        #        inkex.errormsg(f"選択されたオブジェクトID: {node.get('id')}")
        #else:
        #    inkex.errormsg("オブジェクトが選択されていません。")

if __name__ == '__main__':
    About().run()