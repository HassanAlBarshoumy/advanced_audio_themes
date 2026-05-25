import textInfos
from browseMode import BrowseModeTreeInterceptor
from typing import Optional, Callable, Any
from inputCore import InputGesture
import controlTypes
from . import common
from . import frenzy

class BrowseModeQuickNavInterceptor:
    def __init__(self, handler):
        self.handler = handler
        self.orig_quick_nav_script: Optional[Callable] = None
        self._patched_script_ref: Optional[Callable] = None

    def patch(self) -> None:
        self.orig_quick_nav_script = getattr(BrowseModeTreeInterceptor, "_quickNavScript", None)

        def patched_quick_nav_script(
                instance: BrowseModeTreeInterceptor,
                gesture: Optional[InputGesture],
                *args: Any,
                **kwargs: Any
        ) -> None:
            if self.orig_quick_nav_script is None:
                return

            itemType = kwargs.get("itemType")
            if itemType is None and len(args) > 0:
                itemType = args[0]
            if itemType is None:
                itemType = ""


            try:
                selection = instance.selection
            except Exception:
                selection = None
                
            if not selection and hasattr(instance, "makeTextInfo"):
                try:
                    selection = instance.makeTextInfo(textInfos.POSITION_CARET)
                except Exception:
                    pass
                    
            old_info = selection.copy() if selection else None

            self.orig_quick_nav_script(
                instance, gesture, *args, **kwargs
            )

            try:
                new_selection = instance.selection
            except Exception:
                new_selection = None
                
            if not new_selection and hasattr(instance, "makeTextInfo"):
                try:
                    new_selection = instance.makeTextInfo(textInfos.POSITION_CARET)
                except Exception:
                    pass

            if new_selection:
                if not old_info or old_info.compareEndPoints(new_selection, "startToStart") != 0:
                    self._check_and_play_nav(itemType)

        self._patched_script_ref = patched_quick_nav_script
        setattr(BrowseModeTreeInterceptor, "_quickNavScript", patched_quick_nav_script)

    def terminate(self) -> None:
        if self.orig_quick_nav_script and self._patched_script_ref:
            current_script = getattr(BrowseModeTreeInterceptor, "_quickNavScript", None)
            if current_script == self._patched_script_ref:
                setattr(BrowseModeTreeInterceptor, "_quickNavScript", self.orig_quick_nav_script)

    def _check_and_play_nav(self, itemType: str) -> bool:
        played = False
        
        # 1. First check Audio Themes
        import config
        import time
        if config.conf["audiothemes"]["enable_audio_themes"] and self.handler.active_theme:
            self.handler.last_quicknav_time = time.monotonic()
            role = None
            if itemType.startswith("heading"):
                role = controlTypes.Role.HEADING
            elif itemType == "link":
                role = controlTypes.Role.LINK
            elif itemType == "visitedLink":
                role = controlTypes.Role.LINK
            elif itemType == "formField":
                role = controlTypes.Role.EDIT
            elif itemType == "table":
                role = controlTypes.Role.TABLE
            elif itemType == "list":
                role = controlTypes.Role.LIST
            else:
                try:
                    role = getattr(controlTypes.Role, itemType.upper())
                except AttributeError:
                    pass
                    
            if role is not None:
                theme = self.handler.active_theme
                from .handler import role_name_to_int
                sound_key = role_name_to_int.get(itemType.lower())
                if sound_key is None:
                    sound_key = role_name_to_int.get(itemType.upper(), role)
                
                with theme._lock:
                    sound_obj = theme.sounds.get(sound_key)
                
                if sound_obj is None and itemType.startswith("heading"):
                    sound_key = role
                    with theme._lock:
                        sound_obj = theme.sounds.get(sound_key)
                        
                if sound_obj is None:
                    return played
                obj_info = {"role": role, "name": itemType, "is_quicknav": True}
                from . import utils
                utils.threadPool.add_task(self.handler.play, obj_info, sound_key)
                played = True

        return played
