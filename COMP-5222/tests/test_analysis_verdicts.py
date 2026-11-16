"""Keep simulation and experimental conclusions distinct."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/edge_ablation'))
from summarize import interpret


def comparison(low, high, n=3):
    return {'n_seeds': n, 'reference_n_seeds': 3, 'difference_nm': (low + high) / 2,
            'ci_low': low, 'ci_high': high}


def test_mixed_datasets_remain_inconclusive():
    text = interpret({'local_only:test:full': comparison(.01, .02),
                      'local_only:exp151:full': comparison(-.02, -.01)}, 'local_only', 'Non-local edges help')
    assert text.startswith('**Inconclusive.**')
    assert 'Test: supported' in text
    assert 'Exp151: not supported' in text


def test_both_positive_control_minus_full_support_original_rule():
    text = interpret({'distance_only:test:full': comparison(.01, .02),
                      'distance_only:exp151:full': comparison(.02, .03)}, 'distance_only', 'The AA ranking term helps')
    assert text.startswith('**Supported.**')


def test_partial_seeds_do_not_support_a_conclusion():
    text = interpret({'local_only:test:full': comparison(.01, .02, n=1)}, 'local_only', 'Non-local edges help')
    assert text.startswith('**Inconclusive.**')
    assert 'partial seed coverage' in text
