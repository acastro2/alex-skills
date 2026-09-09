"""Read-only ctypes boundary to public macOS Accessibility APIs."""

import ctypes as C
import sys
import time

from browser_ae import BrowserError

P = C.c_void_p
INDEX = C.c_long


def check_error(code, *, optional=False, operation=None, attribute=None):
    if code == 0:
        return True
    if optional and code in (-25205, -25212):
        return False
    name = {-25211: "AX_PERMISSION_DENIED", -25202: "AX_TARGET_MISSING",
            -25204: "AX_CANNOT_COMPLETE", -25206: "AX_ACTION_UNSUPPORTED",
            -25205: "AX_ATTRIBUTE_UNSUPPORTED", -25212: "AX_ATTRIBUTE_MISSING",
            -25208: "AX_UNSUPPORTED"}.get(code, "AX_ERROR")
    raise BrowserError(name, "Accessibility request failed; no automatic retry.", number=code,
                       operation=operation, attribute=attribute)


class Element:
    def __init__(self, pointer):
        self.pointer = pointer


class NativeAX:
    def __init__(self):
        if sys.platform != "darwin":
            raise BrowserError("AX_UNAVAILABLE", "Accessibility requires macOS.")
        self.cf = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.ax = C.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        self.owned = []
        declarations = [
            (self.cf, "CFRelease", None, [P]),
            (self.cf, "CFEqual", C.c_ubyte, [P, P]),
            (self.cf, "CFGetTypeID", C.c_ulong, [P]),
            (self.cf, "CFStringCreateWithCString", P, [P, C.c_char_p, C.c_uint32]),
            (self.cf, "CFStringGetLength", INDEX, [P]),
            (self.cf, "CFStringGetMaximumSizeForEncoding", INDEX, [INDEX, C.c_uint32]),
            (self.cf, "CFStringGetCString", C.c_ubyte, [P, P, INDEX, C.c_uint32]),
            (self.cf, "CFArrayGetCount", INDEX, [P]),
            (self.cf, "CFArrayGetValueAtIndex", P, [P, INDEX]),
            (self.cf, "CFBooleanGetValue", C.c_ubyte, [P]),
            (self.cf, "CFNumberGetValue", C.c_ubyte, [P, C.c_int, P]),
            (self.cf, "CFURLGetString", P, [P]),
            (self.ax, "AXIsProcessTrusted", C.c_ubyte, []),
            (self.ax, "AXUIElementCreateSystemWide", P, []),
            (self.ax, "AXUIElementCreateApplication", P, [C.c_int]),
            (self.ax, "AXUIElementGetPid", C.c_int, [P, C.POINTER(C.c_int)]),
            (self.ax, "AXUIElementSetMessagingTimeout", C.c_int, [P, C.c_float]),
            (self.ax, "AXUIElementCopyAttributeValue", C.c_int, [P, P, C.POINTER(P)]),
            (self.ax, "AXUIElementGetAttributeValueCount", C.c_int, [P, P, C.POINTER(INDEX)]),
            (self.ax, "AXUIElementCopyAttributeValues", C.c_int, [P, P, INDEX, INDEX, C.POINTER(P)]),
            (self.ax, "AXUIElementCopyActionNames", C.c_int, [P, C.POINTER(P)]),
            (self.ax, "AXUIElementIsAttributeSettable", C.c_int, [P, P, C.POINTER(C.c_ubyte)]),
        ]
        for library, name, result, arguments in declarations:
            function = getattr(library, name)
            function.restype, function.argtypes = result, arguments
        self.types = {}
        for name in ("String", "Array", "Boolean", "Number", "URL"):
            function = getattr(self.cf, f"CF{name}GetTypeID")
            function.restype, function.argtypes = C.c_ulong, []
            self.types[name] = function()
        self.ax.AXUIElementGetTypeID.restype = C.c_ulong
        self.ax.AXUIElementGetTypeID.argtypes = []
        self.types["Element"] = self.ax.AXUIElementGetTypeID()
        self.system = None
        self.deadline = None

    def check_time(self):
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise BrowserError("AX_TIMEOUT", "Accessibility inspection deadline reached; no retry.")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        for pointer in reversed(self.owned):
            self.cf.CFRelease(pointer)
        self.owned.clear()

    def own(self, pointer):
        if not pointer:
            raise BrowserError("AX_ERROR", "Native API returned a null object.")
        self.owned.append(pointer)
        return pointer

    def string(self, value):
        if "\x00" in value:
            raise BrowserError("AX_VALUE_UNSUPPORTED", "Embedded NUL is unsupported; no truncated native string.")
        return self.own(self.cf.CFStringCreateWithCString(None, value.encode("utf-8"), 0x08000100))

    def decode(self, pointer):
        if not pointer:
            return None
        kind = self.cf.CFGetTypeID(pointer)
        if kind == self.types["Element"]:
            return Element(pointer)
        if kind == self.types["String"]:
            length = self.cf.CFStringGetLength(pointer)
            size = self.cf.CFStringGetMaximumSizeForEncoding(length, 0x08000100) + 1
            if size > 65536:
                raise BrowserError("AX_OUTPUT_LIMIT", "An AX attribute exceeds the private-read limit.")
            buffer = C.create_string_buffer(size)
            if not self.cf.CFStringGetCString(pointer, buffer, size, 0x08000100):
                raise BrowserError("AX_ERROR", "Cannot decode Accessibility text.")
            text = buffer.value.decode("utf-8")
            if len(text.encode("utf-16-le")) // 2 != length:
                raise BrowserError("AX_VALUE_UNSUPPORTED", "Native text contains unsupported embedded NUL.")
            return text
        if kind == self.types["URL"]:
            return self.decode(self.cf.CFURLGetString(pointer))
        if kind == self.types["Boolean"]:
            return bool(self.cf.CFBooleanGetValue(pointer))
        if kind == self.types["Number"]:
            value = C.c_double()
            if not self.cf.CFNumberGetValue(pointer, 13, C.byref(value)):
                raise BrowserError("AX_ERROR", "Cannot decode Accessibility number.")
            return value.value
        if kind == self.types["Array"]:
            count = self.cf.CFArrayGetCount(pointer)
            if count > 600:
                raise BrowserError("AX_TREE_LIMIT", "AX array exceeds the bounded inspection size.")
            return [self.decode(self.cf.CFArrayGetValueAtIndex(pointer, i)) for i in range(count)]
        raise BrowserError("AX_VALUE_UNSUPPORTED", "Unsupported native Accessibility value type.")

    def start(self, pid):
        self.deadline = time.monotonic() + 45
        if not self.ax.AXIsProcessTrusted():
            raise BrowserError("AX_PERMISSION_DENIED", "This launcher lacks Accessibility permission. User grants it manually; no prompt automation.")
        self.system = Element(self.own(self.ax.AXUIElementCreateSystemWide()))
        self.application = Element(self.own(self.ax.AXUIElementCreateApplication(pid)))
        check_error(self.ax.AXUIElementSetMessagingTimeout(self.system.pointer, 1.0), operation="set-messaging-timeout")

    def get(self, element, attribute, optional=True):
        self.check_time()
        output = P()
        code = self.ax.AXUIElementCopyAttributeValue(element.pointer, self.string(attribute), C.byref(output))
        if not check_error(code, optional=optional, operation="read-attribute", attribute=attribute):
            return None
        return self.decode(self.own(output.value))

    def children(self, element, limit):
        self.check_time()
        count, attribute = INDEX(), self.string("AXChildren")
        code = self.ax.AXUIElementGetAttributeValueCount(element.pointer, attribute, C.byref(count))
        if not check_error(code, optional=True, operation="count-children", attribute="AXChildren"):
            leaf_roles = {"AXButton", "AXCheckBox", "AXTextField", "AXTextArea", "AXStaticText", "AXImage", "AXLink", "AXRadioButton"}
            if self.get(element, "AXRole", optional=False) not in leaf_roles:
                raise BrowserError("AX_TREE_INCOMPLETE", "Container children are unavailable; cannot prove uniqueness.")
            return []
        if count.value > limit:
            raise BrowserError("AX_TREE_LIMIT", "Children exceed remaining traversal budget; selection is incomplete.")
        if count.value == 0:
            return []
        output = P()
        check_error(self.ax.AXUIElementCopyAttributeValues(element.pointer, attribute, 0, count.value, C.byref(output)), operation="read-children", attribute="AXChildren")
        children = self.decode(self.own(output.value))
        if len(children) != count.value or not all(isinstance(child, Element) for child in children):
            raise BrowserError("AX_TREE_CHANGED", "Children changed or are not Accessibility elements.")
        return children

    def actions(self, element):
        self.check_time()
        output = P()
        check_error(self.ax.AXUIElementCopyActionNames(element.pointer, C.byref(output)), operation="list-actions")
        return self.decode(self.own(output.value))

    def settable(self, element, attribute):
        self.check_time()
        value = C.c_ubyte()
        code = self.ax.AXUIElementIsAttributeSettable(element.pointer, self.string(attribute), C.byref(value))
        return bool(value.value) if check_error(code, optional=True, operation="is-settable", attribute=attribute) else False

    def pid(self, element):
        value = C.c_int()
        check_error(self.ax.AXUIElementGetPid(element.pointer, C.byref(value)), operation="get-pid")
        return value.value

    def equal(self, left, right):
        return bool(left and right and self.cf.CFEqual(left.pointer, right.pointer))

    def focus(self):
        app = self.application
        if self.get(app, "AXFrontmost", optional=False) is not True:
            raise BrowserError("AX_FOCUS_CHANGED", "Bound browser is no longer the foreground AX application.")
        window = self.get(app, "AXFocusedWindow", optional=False)
        element = self.get(app, "AXFocusedUIElement", optional=False)
        return app, window, element

    def perform(self, element, action):
        raise BrowserError("AX_WRITES_DISABLED", "Native AX actions are disabled; use a manual click.", outcome="not_started")

    def set_value(self, element, value):
        raise BrowserError("AX_WRITES_DISABLED", "Native AX value writes are disabled; use manual input.", outcome="not_started")
