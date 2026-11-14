"""Exercise the actual checked-in alert expressions, including absent metrics."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


@unittest.skipUnless(shutil.which('promtool'), 'promtool is required for alert evaluation')
class AlertTests(unittest.TestCase):
    def test_backup_alerts_fire_only_after_their_thresholds(self):
        root = Path(__file__).resolve().parents[2]
        config = yaml.safe_load((root/'infrastructure/base/monitoring/victoria-metrics/values.yaml').read_text())
        groups = config['additionalVictoriaMetricsMap']['cluster-backup']['groups']
        rules = {r['alert']: r for g in groups for r in g['rules']}
        cases = [
            ('healthy', '1h', '31h', '0+3600x32', '1+0x32', '100+0x32', None),
            ('short failure', '1m', '19m', '0+60x40', '0+0x40', '100+0x40', None),
            ('failed', '1m', '21m', '0+60x40', '0+0x40', '100+0x40', 'ClusterBackupFailed'),
            ('stale', '1h', '31h', '0+0x32', '1+0x32', '100+0x32', 'ClusterBackupMissing'),
            ('missing', '1m', '16m', None, None, None, 'ClusterBackupMissing'),
            ('storage', '1m', '16m', '0+60x40', '1+0x40', '6000000001+0x40', 'ClusterBackupStorageBudget'),
        ]
        tests = []
        for name, interval, at, success_at, success, stored, expected in cases:
            series = [('last_success_timestamp_seconds', success_at), ('success', success), ('stored_bytes', stored)]
            tests.append({'name': name, 'interval': interval,
                          'input_series': [{'series': 'ops_cluster_backup_'+k, 'values': v} for k,v in series if v is not None],
                          'alert_rule_test': [
                              {'eval_time': at, 'alertname': alert, 'exp_alerts': [
                                  {'exp_labels': rule['labels'], 'exp_annotations': rule['annotations']}
                              ] if expected == alert else []}
                              for alert,rule in rules.items()]})
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory/'rules.yaml').write_text(yaml.safe_dump({'groups': groups}))
            (directory/'tests.yaml').write_text(yaml.safe_dump({'rule_files': ['rules.yaml'], 'evaluation_interval': '1m', 'tests': tests}))
            result = subprocess.run(['promtool','test','rules',str(directory/'tests.yaml')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
