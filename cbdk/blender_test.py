"""Opt-in runtime smoke runner, never imports untrusted addon sources."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

PASS_MARKER = 'CBDK_BLENDER_SMOKE_PASS '


def run_smoke(blender: str, *, timeout: int = 90, suite: str = 'basic') -> dict:
    if timeout < 1 or timeout > 600:
        raise ValueError('timeout must be in 1..600 seconds')
    scripts = {'basic': 'blender_smoke.py', 'parts': 'blender_parts_smoke.py'}
    if suite not in scripts:
        raise ValueError('Unknown smoke suite; expected basic or parts')
    script = Path(__file__).resolve().parent.parent / 'scripts' / scripts[suite]
    if not script.is_file():
        raise FileNotFoundError('Trusted Blender smoke script missing')
    cmd = [blender, '--background', '--factory-startup', '--python-exit-code', '7', '--python', str(script)]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {'status': 'failed', 'reason': str(exc), 'verified': False, 'command': cmd}
    marker = next((line for line in completed.stdout.splitlines() if line.startswith(PASS_MARKER)), None)
    status = 'passed' if completed.returncode == 0 and marker else 'failed'
    return {'status': status, 'verified': status == 'passed', 'returncode': completed.returncode,
            'message': marker[len(PASS_MARKER):] if marker else 'Smoke marker missing',
            'stdout_tail': completed.stdout[-1500:], 'stderr_tail': completed.stderr[-1500:],
            'command': cmd}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Opt-in Blender smoke test (not addon verification)')
    parser.add_argument('blender', help='Path to blender executable, or blender if in PATH')
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--suite', choices=['basic', 'parts'], default='basic')
    parser.add_argument('--output', default='reports/latest/blender_smoke.json')
    args = parser.parse_args(argv)
    report = run_smoke(args.blender, timeout=args.timeout, suite=args.suite)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Blender smoke: {report['status']} ({output})")
    return 0 if report['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
