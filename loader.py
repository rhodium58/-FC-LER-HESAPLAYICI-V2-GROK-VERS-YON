# -*- coding: utf-8 -*-
"""v5.3 giris: CadScreen'i oto tarama ile degistirir."""
import main as appmod
from cadscan import CadScreen, request_storage_perm
from kivy.clock import Clock

appmod.CadScreen = CadScreen


class HesaplaApp(appmod.HesaplaApp):
    def on_start(self):
        try:
            super(HesaplaApp, self).on_start()
        except Exception:
            pass
        try:
            Clock.schedule_once(lambda *_: request_storage_perm(), 0.3)
        except Exception:
            pass


if __name__ == "__main__":
    HesaplaApp().run()
