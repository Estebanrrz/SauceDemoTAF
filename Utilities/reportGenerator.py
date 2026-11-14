# Own run report: collects one record per scenario and writes report.json + report.html
import json
import os
from datetime import datetime
from html import escape


class RunReport:
    def __init__(self, outputDir, baseUrl):
        self.outputDir = outputDir
        self.baseUrl = baseUrl
        self.startedAt = datetime.now()
        self.results = {}   # key -> record (the last attempt wins)
        self.attempts = {}  # key -> number of attempts so far

    def startAttempt(self, key):
        self.attempts[key] = self.attempts.get(key, 0) + 1

    def record(self, key, feature, name, tags, status, duration, error=None, screenshot=None):
        attempts = self.attempts.get(key, 1)
        self.results[key] = {
            'id': key, 'feature': feature, 'name': name, 'tags': sorted(tags), 'status': status,
            'duration': round(duration, 2), 'attempts': attempts,
            # Passed only after a retry: the test is unreliable and must not be hidden
            'flaky': status == 'passed' and attempts > 1,
            'error': error,
            'screenshot': os.path.relpath(screenshot, self.outputDir) if screenshot else None,
        }

    def summary(self):
        rows = list(self.results.values())
        count = lambda s: sum(1 for r in rows if r['status'] == s)
        total = len(rows)
        return {
            'baseUrl': self.baseUrl,
            'startedAt': self.startedAt.isoformat(timespec='seconds'),
            'durationSeconds': round((datetime.now() - self.startedAt).total_seconds(), 1),
            'total': total, 'passed': count('passed'), 'failed': count('failed'), 'skipped': count('skipped'),
            'flaky': sum(1 for r in rows if r['flaky']),
            'passRate': round(100 * count('passed') / total, 1) if total else 0.0,
        }

    def write(self):
        os.makedirs(self.outputDir, exist_ok=True)
        data = {'summary': self.summary(), 'scenarios': list(self.results.values())}
        with open(os.path.join(self.outputDir, 'report.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.outputDir, 'report.html'), 'w', encoding='utf-8') as f:
            f.write(self._html(data))
        return os.path.join(self.outputDir, 'report.html')

    @staticmethod
    def _html(data):
        s = data['summary']
        cards = ''.join(f'<div class="card {k}"><b>{s[k]}</b><span>{label}</span></div>' for k, label in
                        [('total', 'Total'), ('passed', 'Passed'), ('failed', 'Failed'),
                         ('skipped', 'Skipped'), ('flaky', 'Flaky')])
        rows = ''
        for r in sorted(data['scenarios'], key=lambda r: (r['status'] == 'passed', r['feature'], r['id'])):
            badge = 'flaky' if r['flaky'] else r['status']
            detail = ''
            if r['error']:
                detail += f'<pre>{escape(r["error"])}</pre>'
            if r['screenshot']:
                detail += f'<a href="{escape(r["screenshot"])}">screenshot</a>'
            rows += (f'<tr class="{badge}"><td><span class="badge {badge}">{badge}</span></td>'
                     f'<td>{escape(r["feature"])}</td><td>{escape(r["name"])}{detail}</td>'
                     f'<td>{escape(" ".join("@" + t for t in r["tags"]))}</td>'
                     f'<td>{r["attempts"]}</td><td>{r["duration"]}s</td></tr>')
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>SauceDemoTAF report</title>
<style>
body{{font:14px system-ui,sans-serif;margin:24px;color:#222}} h1{{margin:0 0 4px}} .meta{{color:#666;margin-bottom:16px}}
.cards{{display:flex;gap:12px;margin-bottom:20px}} .card{{border:1px solid #ddd;border-radius:8px;padding:10px 18px;text-align:center}}
.card b{{display:block;font-size:24px}} .card.passed b{{color:#1a7f37}} .card.failed b{{color:#cf222e}} .card.flaky b{{color:#9a6700}}
table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}}
.badge{{padding:2px 8px;border-radius:10px;color:#fff;font-size:12px}} .badge.passed{{background:#1a7f37}}
.badge.failed{{background:#cf222e}} .badge.skipped{{background:#6e7781}} .badge.flaky{{background:#9a6700}}
pre{{background:#f6f8fa;padding:8px;white-space:pre-wrap;margin:6px 0}}
</style></head><body>
<h1>SauceDemoTAF report</h1>
<div class="meta">{escape(s["baseUrl"])} &middot; {escape(s["startedAt"])} &middot; {s["durationSeconds"]}s &middot; pass rate {s["passRate"]}%</div>
<div class="cards">{cards}</div>
<table><tr><th>Status</th><th>Feature</th><th>Scenario</th><th>Tags</th><th>Attempts</th><th>Time</th></tr>{rows}</table>
</body></html>'''
