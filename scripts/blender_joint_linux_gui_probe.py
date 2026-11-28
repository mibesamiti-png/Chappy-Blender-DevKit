"""One bounded real-window X11 pilot; use only on a private Xvfb display.

Uses the same Blender observer as the Windows pilot. No explicit undo pushes,
no direct operator calls for tested actions, no production sidebar hit test.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
for name in ('blender', 'zip', 'gl', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
args = p.parse_args()
out = args.output.resolve()
out.parent.mkdir(parents=True, exist_ok=True)
state = out.with_name('linux-gui-live-state.json')
log = out.with_name('linux-gui-blender.log')
wm_log = out.with_name('linux-gui-window-manager.log')
if any(x.exists() for x in (out, state, log, wm_log)):
    raise ValueError('fresh evidence paths required')
report = dict(scope='Linux isolated Xvfb X11 real-window input, fixed rotary fixture',
              production_sidebar_click=False, explicit_undo_push=False,
              approved=False, result='not_passed', rows=[])
stage = 'display'
proc = wm = None


def xdo(*parts):
    return subprocess.check_output(['xdotool', *map(str, parts)], text=True,
                                   stderr=subprocess.STDOUT, timeout=10).strip()


def wait(predicate, seconds=90):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        if proc.poll() is not None:
            raise RuntimeError('Blender exited: ' + str(proc.returncode))
        try:
            v = json.loads(state.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            time.sleep(.15)
            continue
        if 'probe_error' in v:
            raise RuntimeError(v['probe_error'])
        if time.time() - v['observed'] < 20:
            last = v
            if predicate(v):
                return v
        time.sleep(.15)
    raise RuntimeError('observation timeout: ' + str(last))


def same_source(v, original):
    return all(v[k] == original[k] for k in
               ('geometry', 'scene', 'selected', 'active', 'mode'))


def record(name, v):
    report['rows'].append(dict(case=name, status='passed',
        observation={k:v[k] for k in
            ('status','diameter','geometry','scene','selected','active','mode')}))
    print('CBDK_A_LINUX_GUI_CASE', name, flush=True)


def focus(window, v):
    xdo('windowactivate', '--sync', window)
    active = xdo('getactivewindow')
    if active != str(window) or xdo('getwindowpid', active) != str(proc.pid):
        raise RuntimeError('foreground window not owned by launched Blender')
    geometry = dict(line.split('=',1) for line in
                    xdo('getwindowgeometry','--shell',window).splitlines()
                    if '=' in line)
    x,y,w,h,ww,wh = v['viewport']
    if not ww or not wh:
        raise RuntimeError('invalid viewport')
    px = int(int(geometry['WIDTH']) * (x+w*.45)/ww)
    py = int(int(geometry['HEIGHT']) * (1-(y+h*.55)/wh))
    xdo('mousemove','--window',window,px,py)


def key(window, observation, chord):
    focus(window, observation)
    # XTEST via the focused real X11 window, not bpy operator dispatch.
    xdo('key','--clearmodifiers',chord)


def stop(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)


with log.open('wb') as stream, wm_log.open('wb') as window_log:
    try:
        # CI wrapper owns this private display. Never send input to the user's desktop.
        if os.environ.get('CBDK_PRIVATE_XVFB') != '1' or not os.environ.get('DISPLAY'):
            raise RuntimeError('private Xvfb wrapper required')
        wm = subprocess.Popen(['openbox','--sm-disable'], stdout=window_log,
                              stderr=subprocess.STDOUT)
        time.sleep(1)
        if wm.poll() is not None:
            raise RuntimeError('window manager exited')
        stage = 'startup'
        observer = Path(__file__).with_name('blender_joint_gui_probe.py').resolve()
        proc = subprocess.Popen([str(args.blender.resolve()),'--factory-startup',
            '--disable-autoexec','--python-exit-code','7','--python',str(observer),
            '--','--gui-probe','--zip',str(args.zip.resolve()),'--gl',str(args.gl.resolve()),
            '--state',str(state)], stdout=stream, stderr=subprocess.STDOUT)
        baseline = wait(lambda v:v['status']=='IDLE' and v['diameter']==5)
        stage = 'focus'
        matches = xdo('search','--onlyvisible','--pid',proc.pid).splitlines()
        windows = []
        for handle in matches:
            geometry = dict(line.split('=',1) for line in
                xdo('getwindowgeometry','--shell',handle).splitlines() if '=' in line)
            if int(geometry.get('WIDTH',0))>500 and int(geometry.get('HEIGHT',0))>300:
                windows.append(handle)
        if len(windows)!=1:
            raise RuntimeError('expected one visible Blender window: '+str(windows))
        window = windows[0]
        focus(window,baseline)
        report['blender'] = baseline['blender']
        record('visible_foreground_window',baseline)
        key(window,baseline,'Escape')
        time.sleep(.5)
        stage = 'generate'
        key(window,baseline,'ctrl+alt+shift+F6')
        ready = wait(lambda v:v['status'] in ('READY','FAILED','BLOCKED'))
        assert ready['status']=='READY' and ready['diameter']==5 and same_source(ready,baseline), ready
        record(stage,ready)
        stage = 'adopt'
        key(window,ready,'ctrl+alt+shift+F7')
        adopted = wait(lambda v:v['status'] in ('ADOPTED_DIMENSION_ONLY','FAILED','BLOCKED'))
        assert adopted['status']=='ADOPTED_DIMENSION_ONLY' and adopted['diameter']==4 and same_source(adopted,baseline), adopted
        record(stage,adopted)
        stage = 'ordinary_undo'
        key(window,adopted,'ctrl+z')
        undone = wait(lambda v:v['diameter']!=4 or not same_source(v,baseline),15)
        assert undone['diameter']==5 and same_source(undone,baseline) and undone['status']!='READY', undone
        record(stage,undone)
        stage = 'ordinary_redo'
        key(window,undone,'ctrl+shift+z')
        redone = wait(lambda v:v['diameter']!=5 or not same_source(v,baseline),15)
        assert redone['diameter']==4 and same_source(redone,baseline), redone
        record(stage,redone)
        report['result']='passed'
    except Exception as exc:
        report.update(stop_stage=stage, reason=type(exc).__name__+': '+str(exc))
    finally:
        stop(proc)
        stop(wm)
        out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CBDK_A_LINUX_GUI_REPORT',json.dumps(report),flush=True)
# A non-passing experiment is retained as evidence, not a product approval.
