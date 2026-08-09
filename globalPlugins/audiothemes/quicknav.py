import textInfos
from browseMode import BrowseModeTreeInterceptor
from typing import Optional, Callable, Any
from inputCore import InputGesture
import controlTypes
from . import common
from . import frenzy
from . import utils
from .handler import role_name_to_int

# Container/document roles that are never a form control we want a themed
# sound for. When the object at the caret is one of these, walk up to the
# nearest real control (e.g. an editable combo box that a quick-nav "edit"
# actually landed on).
_QUICKNAV_SKIP_ROLES = None


def _get_quicknav_skip_roles():
    global _QUICKNAV_SKIP_ROLES
    if _QUICKNAV_SKIP_ROLES is None:
        skip = set()
        for name in ("UNKNOWN", "DOCUMENT", "LANDMARK", "REGION", "GROUPING",
                     "PARAGRAPH", "PANE", "WINDOW", "FRAME", "APPLICATION",
                     "DIALOG", "ROOT_PANE", "TEXT_FRAME"):
            role = getattr(controlTypes.Role, name, None)
            if role is not None:
                skip.add(int(role))
        _QUICKNAV_SKIP_ROLES = skip
    return _QUICKNAV_SKIP_ROLES


def _actual_landed_role(new_selection):
    """Best-effort real role of the element the browse-mode caret landed on.

    A quick-nav "edit" (E) can land on an editable combo box, a search field,
    a multi-line edit, etc. This inspects the object at the new caret and walks
    up from generic containers until a concrete control role is found, so the
    correct themed sound plays. Returns None when no concrete control is found.
    """
    if new_selection is None:
        return None
    try:
        obj = new_selection.NVDAObjectAtStart
    except Exception:
        obj = None
    skip = _get_quicknav_skip_roles()
    doc_role = int(controlTypes.Role.DOCUMENT)
    depth = 0
    while obj is not None and depth < 8:
        try:
            role = getattr(obj, "role", None)
            role_int = int(role) if role is not None else None
        except Exception:
            return None
        if role_int is None or role_int in skip:
            if role_int == doc_role:
                return None
            try:
                obj = getattr(obj, "parent", None)
            except Exception:
                return None
            depth += 1
            continue
        try:
            return controlTypes.Role(role_int)
        except Exception:
            return None
    return None


# Roles that make up the "button" family for quick-nav. B is supposed to land on
# every kind of button (plain, toggle, menu, split, dropdown). A concrete
# role outside this family is NOT the button the user pressed B for, so fall
# back to the plain button sound instead of playing a container sound.
_QUICKNAV_BUTTON_ROLES = None


def _get_quicknav_button_roles():
    global _QUICKNAV_BUTTON_ROLES
    if _QUICKNAV_BUTTON_ROLES is None:
        roles = set()
        for name in ("BUTTON", "TOGGLEBUTTON", "MENUBUTTON", "SPLITBUTTON",
                     "DROPDOWNBUTTON", "DROPDOWNBUTTONGRID"):
            role = getattr(controlTypes.Role, name, None)
            if role is not None:
                roles.add(int(role))
        _QUICKNAV_BUTTON_ROLES = roles
    return _QUICKNAV_BUTTON_ROLES


def _default_quicknav_role(itemType):
    """Fallback role for quick-nav types whose sound resolves via the real
    landed element: editable types default to EDITABLETEXT, button to BUTTON."""
    if itemType in ("formField", "edit", "editMultiline"):
        return controlTypes.Role.EDITABLETEXT
    if itemType == "button":
        return controlTypes.Role.BUTTON
    return None


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
                except Exception as e:
                    import logging
                    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
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
                except Exception as e:
                    import logging
                    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
            if new_selection:
                if not old_info or old_info.compareEndPoints(new_selection, "startToStart") != 0:
                    self._check_and_play_nav(itemType, new_selection)

        self._patched_script_ref = patched_quick_nav_script
        setattr(BrowseModeTreeInterceptor, "_quickNavScript", patched_quick_nav_script)

    def terminate(self) -> None:
        if self.orig_quick_nav_script and self._patched_script_ref:
            current_script = getattr(BrowseModeTreeInterceptor, "_quickNavScript", None)
            if current_script == self._patched_script_ref:
                setattr(BrowseModeTreeInterceptor, "_quickNavScript", self.orig_quick_nav_script)

    def _check_and_play_nav(self, itemType: str, new_selection=None) -> bool:
        played = False
        
        # 1. First check Audio Themes
        import time
        cfg = getattr(self.handler, '_cached_config', None) or {}
        if cfg.get("enable_audio_themes", True) and self.handler.active_theme:
            self.handler.last_quicknav_time = time.monotonic()
            theme = self.handler.active_theme
            role = None
            sound_key = None

            if itemType in ("formField", "edit", "editMultiline", "button"):
                # The element quick-nav actually landed on may be an editable
                # combo box, a search field, a checkbox, an editable combo box,
                # a toggle/menu/split button, etc. Prefer the REAL role of that
                # element so the matching themed sound plays. For "button" only
                # the button family is accepted; anything else falls back to the
                # plain button role.
                role = _actual_landed_role(new_selection)
                if itemType == "button" and role is not None and int(role) not in _get_quicknav_button_roles():
                    role = None
                if role is None:
                    role = _default_quicknav_role(itemType)
                sound_key = int(role)
            else:
                if itemType.startswith("heading"):
                    role = controlTypes.Role.HEADING
                elif itemType in ("link", "visitedLink"):
                    role = controlTypes.Role.LINK
                elif itemType in ("table", "list"):
                    role = getattr(controlTypes.Role, itemType.upper())
                else:
                    try:
                        role = getattr(controlTypes.Role, itemType.upper())
                    except AttributeError:
                        role = None
                # Resolve the sound key: exact lowercase name first (covers the
                # pseudo quick-nav keys like unvisitedlink/nonheading/quote/annotation
                # and role names), then fall back to the resolved role int.
                sound_key = role_name_to_int.get(itemType.lower())
                if sound_key is None and role is not None:
                    sound_key = role

            if sound_key is None:
                return played

            with theme._lock:
                sound_obj = theme.sounds.get(sound_key)

            if sound_obj is None and itemType.startswith("heading"):
                sound_key = role
                with theme._lock:
                    sound_obj = theme.sounds.get(sound_key)

            if sound_obj is None and itemType in ("formField", "edit", "editMultiline", "button"):
                # The landed element's own sound is missing from this theme:
                # use the default sound for this quick-nav family as a stable
                # fallback (plain edit for editable types, plain button for B).
                fallback_role = _default_quicknav_role(itemType)
                try:
                    fallback_key = int(fallback_role)
                except Exception:
                    fallback_key = role_name_to_int.get(fallback_role.name.lower()) if getattr(fallback_role, "name", None) else None
                if fallback_key is not None and fallback_key != sound_key:
                    with theme._lock:
                        sound_obj = theme.sounds.get(fallback_key)
                    if sound_obj is not None:
                        sound_key = fallback_key

            if sound_obj is None:
                return played
            obj_info = {"role": role, "name": itemType, "is_quicknav": True}
            utils.threadPool.add_task(self.handler.play, obj_info, sound_key)
            played = True

        return played
