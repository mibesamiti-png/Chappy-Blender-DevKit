"""Windows GUI pilot for the fixed Team A joint preview.

No simulated bpy operators or explicit undo pushes for the tested actions.
OS mouse/key events are routed through test-only shortcuts to the actual
operators. This does NOT test clicking the production sidebar buttons.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path, value):
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(value), encoding="utf-8")
        tmp.replace(path)
    except PermissionError:
        # A Windows reader can briefly hold the destination open.
        pass


def gui_probe(args):
    import bpy
    sys.path.insert(0, str(ROOT))
    from parts.blender import joint_preview as ui

    def snapshot():
        # Semantic comparison across Undo: RNA pointers may be invalidated.
        objects = []
        for obj in sorted(bpy.data.objects, key=lambda o: o.name):
            mesh = None
            if obj.type == "MESH":
                mesh = [[list(v.co) for v in obj.data.vertices],
                        [list(e.vertices) for e in obj.data.edges],
                        [list(f.vertices) for f in obj.data.polygons]]
            objects.append([obj.name, obj.type, [list(row) for row in obj.matrix_world], mesh])
        return hashlib.sha256(json.dumps(objects, sort_keys=True).encode()).hexdigest()

    ui.register()
    bpy.context.preferences.view.show_splash = False
    bpy.context.preferences.edit.use_global_undo = True
    ready = False
    keymaps = []

    def observe():
        nonlocal ready
        try:
            wm = bpy.context.window_manager
            window = next((win for win in wm.windows
                           if any(a.type == "VIEW_3D" for a in win.screen.areas)), None)
            if window is None:
                return .15
            area = max((a for a in window.screen.areas if a.type == "VIEW_3D"),
                       key=lambda a: a.width * a.height)
            s = window.scene.cbdk_a_joint
            if not ready:
                if wm.keyconfigs.addon is None:
                    return .15
                s.provider_zip = str(args.zip.resolve())
                s.geometry_root = str(args.gl.resolve())
                s.candidate = 2
                km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
                keymaps.append(km)
                # Mouse and key events use production operators, but not panel hit-testing.
                for key, action in (("LEFTMOUSE", None), ("F6", None),
                                    ("F7", "ADOPT"), ("F8", "RESTORE")):
                    item = km.keymap_items.new(
                        "cbdk_a.joint_start" if action is None else "cbdk_a.joint_action",
                        key, "PRESS", ctrl=True, alt=True, shift=True)
                    if action is not None:
                        item.properties.action = action
                ready = True
            atomic_json(args.state, dict(status=s.status, reason=s.reason,
                         diameter=float(s.diameter), candidate=int(s.candidate),
                         geometry=snapshot(), scene=window.scene.name,
                         selected=sorted(o.name for o in window.view_layer.objects if o.select_get(view_layer=window.view_layer)),
                         active=window.view_layer.objects.active.name if window.view_layer.objects.active else None,
                         mode=bpy.context.mode,
                         viewport=[area.x, area.y, area.width, area.height, window.width, window.height],
                         blender=bpy.app.version_string, observed=time.time()))
            return .15
        except Exception as exc:
            atomic_json(args.state, dict(probe_error=type(exc).__name__ + ": " + str(exc)))
            return None

    bpy.app.timers.register(observe, first_interval=.5, persistent=True)


def driver(args):
    import ctypes as C
    from ctypes import wintypes as W
    u = C.WinDLL("user32", use_last_error=True)
    u.SetProcessDPIAware()
    u.GetForegroundWindow.restype = W.HWND
    u.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    u.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    u.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
    u.SetForegroundWindow.argtypes = [W.HWND]
    u.ShowWindow.argtypes = [W.HWND, C.c_int]
    u.IsWindowVisible.argtypes = [W.HWND]
    u.SetCursorPos.argtypes = [C.c_int, C.c_int]
    u.keybd_event.argtypes = [C.c_ubyte, C.c_ubyte, W.DWORD, C.c_size_t]
    u.mouse_event.argtypes = [W.DWORD, W.DWORD, W.DWORD, W.DWORD, C.c_size_t]
    rows = []
    report = dict(scope="Windows OS input, test-only shortcuts, fixed rotary fixture",
                  production_sidebar_click=False, explicit_undo_push=False, rows=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.state = args.output.with_name("gui-live-state.json")
    if args.state.exists() or args.output.exists():
        raise ValueError("fresh evidence paths required")
    log = args.output.with_name("gui-blender.log")
    proc = None
    stage = "startup"

    def pid_of(hwnd):
        pid = W.DWORD()
        u.GetWindowThreadProcessId(hwnd, C.byref(pid))
        return pid.value

    def read():
        if proc.poll() is not None:
            raise RuntimeError("Blender exited before probe finished")
        try:
            v = json.loads(args.state.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if "probe_error" in v:
            raise RuntimeError(v["probe_error"])
        if time.time() - v["observed"] > 20:
            return None
        return v

    def wait(predicate, seconds=90):
        end = time.monotonic() + seconds
        last = None
        while time.monotonic() < end:
            v = read()
            if v is not None:
                last = v
                if predicate(v):
                    return v
            time.sleep(.1)
        raise RuntimeError("observation timeout: " + str(last))

    def window_handle():
        handles = []
        callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        @callback_type
        def each(hwnd, unused):
            if pid_of(hwnd) == proc.pid and u.IsWindowVisible(hwnd):
                rect = W.RECT()
                if u.GetClientRect(hwnd, C.byref(rect)) and rect.right > 500 and rect.bottom > 300:
                    handles.append(hwnd)
            return True
        u.EnumWindows(each, 0)
        if len(handles) != 1:
            raise RuntimeError("expected one visible Blender window, got " + str(len(handles)))
        return handles[0]

    def focus(hwnd, observation):
        u.ShowWindow(hwnd, 9)
        u.SetForegroundWindow(hwnd)
        time.sleep(.25)
        if pid_of(u.GetForegroundWindow()) != proc.pid:
            raise RuntimeError("interactive foreground desktop unavailable")
        rect = W.RECT()
        if not u.GetClientRect(hwnd, C.byref(rect)):
            raise RuntimeError("client rectangle unavailable")
        x,y,w,h,ww,wh = observation["viewport"]
        point = W.POINT(int(rect.right*(x+w*.45)/ww),
                        int(rect.bottom*(1-(y+h*.55)/wh)))
        if not u.ClientToScreen(hwnd, C.byref(point)) or not u.SetCursorPos(point.x, point.y):
            raise RuntimeError("viewport cursor positioning failed")

    def input_event(hwnd, observation, key=None, mods=(), mouse=False):
        focus(hwnd, observation)
        try:
            for m in mods:
                u.keybd_event(m, 0, 0, 0)
            if mouse:
                u.mouse_event(2, 0, 0, 0, 0)
                u.mouse_event(4, 0, 0, 0, 0)
            else:
                u.keybd_event(key, 0, 0, 0)
                u.keybd_event(key, 0, 2, 0)
        finally:
            for m in reversed(mods):
                u.keybd_event(m, 0, 2, 0)

    def same_source(v, baseline):
        return all(v[k] == baseline[k] for k in ("geometry", "scene", "selected", "active", "mode"))

    def record(name, observation):
        rows.append(dict(case=name, status="passed",
                         observation={k: observation[k] for k in
                           ("status", "diameter", "geometry", "selected", "active", "mode")}))
        print("CBDK_A_GUI_CASE", name, flush=True)

    with log.open("wb") as stream:
        try:
            proc = subprocess.Popen([str(args.blender), "--factory-startup", "--disable-autoexec",
                "--python-exit-code", "7", "--python", str(Path(__file__).resolve()),
                "--", "--gui-probe", "--zip", str(args.zip), "--gl", str(args.gl),
                "--state", str(args.state)], stdout=stream, stderr=subprocess.STDOUT)
            baseline = wait(lambda v: v["status"] == "IDLE" and v["diameter"] == 5, 90)
            hwnd = window_handle()
            focus(hwnd, baseline)
            record("visible_foreground_window", baseline)
            report["blender"] = baseline["blender"]
            # Real OS keyboard dismisses any startup splash; no operator invocation.
            input_event(hwnd, baseline, 0x1B)
            time.sleep(.5)
            stage = "mouse_start_cancel"
            mods = (0x11, 0x12, 0x10)
            input_event(hwnd, baseline, mods=mods, mouse=True)
            running = wait(lambda v: v["status"] == "RUNNING", 20)
            input_event(hwnd, running, 0x1B)
            cancelled = wait(lambda v: v["status"] in ("CANCELLED", "READY", "FAILED", "BLOCKED"))
            assert cancelled["status"] == "CANCELLED" and same_source(cancelled, baseline), cancelled
            record(stage, cancelled)

            def generate(from_state):
                input_event(hwnd, from_state, 0x75, mods)
                v = wait(lambda v: v["status"] in ("READY", "FAILED", "BLOCKED"))
                assert v["status"] == "READY" and same_source(v, baseline), v
                return v

            def adopt(v):
                input_event(hwnd, v, 0x76, mods)
                a = wait(lambda v: v["status"] in ("ADOPTED_DIMENSION_ONLY", "FAILED", "BLOCKED"))
                assert a["status"] == "ADOPTED_DIMENSION_ONLY" and a["diameter"] == 4 and same_source(a, baseline), a
                return a

            stage = "retry_adopt"
            adopted = adopt(generate(cancelled))
            record(stage, adopted)
            stage = "explicit_restore"
            input_event(hwnd, adopted, 0x77, mods)
            restored = wait(lambda v: v["status"] in ("RESTORED", "FAILED", "BLOCKED"))
            assert restored["status"] == "RESTORED" and restored["diameter"] == 5 and same_source(restored, baseline), restored
            record(stage, restored)
            stage = "ordinary_undo"
            adopted = adopt(generate(restored))
            input_event(hwnd, adopted, 0x5A, (0x11,))
            undone = wait(lambda v: v["diameter"] != 4 or not same_source(v, baseline), 12)
            assert undone["diameter"] == 5 and same_source(undone, baseline), undone
            record(stage, undone)
            stage = "ordinary_redo"
            input_event(hwnd, undone, 0x5A, (0x11, 0x10))
            redone = wait(lambda v: v["diameter"] != 5 or not same_source(v, baseline), 12)
            assert redone["diameter"] == 4 and same_source(redone, baseline), redone
            record(stage, redone)
            report["result"] = "passed"
        except Exception as exc:
            report["result"] = "not_passed"
            report["stop_stage"] = stage
            report["reason"] = str(exc)
            print("CBDK_A_GUI_NOT_PASSED", stage, str(exc), flush=True)
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("CBDK_A_GUI_REPORT", json.dumps(report), flush=True)
    if report["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gui-probe", action="store_true")
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--gl", type=Path, required=True)
    p.add_argument("--state", type=Path)
    p.add_argument("--blender", type=Path)
    p.add_argument("--output", type=Path)
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:]
    args = p.parse_args(argv)
    if args.gui_probe:
        gui_probe(args)
    else:
        driver(args)
