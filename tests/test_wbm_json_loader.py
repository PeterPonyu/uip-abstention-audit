"""Regression test for the init-structs-json fallback in load_wbm_structures
(added 2026-07-09: both figshare routes for the extxyz DataFile 403 from the
AutoDL box, so the arms must be able to run from the json.bz2 DataFile that
DID download — same WBM content, different container).

The fixture mirrors the REAL on-box file's verified shape (probe 2026-07-09):
pandas column-orient dict with columns material_id / formula_from_cse /
initial_structure, rows keyed by stringified integers, and each
initial_structure a pymatgen-Structure-style dict (lattice.matrix +
sites[].species[0].element + sites[].xyz).
"""
import bz2
import importlib.util
import json
import sys
from pathlib import Path

_MT29 = Path(__file__).resolve().parents[1] / "research" / "results" / "MT29"
spec = importlib.util.spec_from_file_location("mt29_uip_inference", _MT29 / "mt29_uip_inference.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["mt29_uip_inference"] = mod
spec.loader.exec_module(mod)


def _fixture_payload():
    def struct(elems, n):
        return {
            "@module": "pymatgen.core.structure",
            "@class": "Structure",
            "lattice": {"matrix": [[float(n), 0.0, 0.0], [0.0, float(n), 0.0], [0.0, 0.0, float(n)]]},
            "sites": [
                {"species": [{"element": el, "occu": 1}], "abc": [0.0, 0.0, 0.0],
                 "xyz": [0.1 * i, 0.2 * i, 0.3 * i], "label": el}
                for i, el in enumerate(elems)
            ],
        }
    return {
        "material_id": {"0": "wbm-1-1", "1": "wbm-1-2", "2": "wbm-1-3"},
        "formula_from_cse": {"0": "NaCl", "1": "Fe2O3", "2": "Si"},
        "initial_structure": {
            "0": struct(["Na", "Cl"], 4),
            "1": struct(["Fe", "Fe", "O", "O", "O"], 5),
            "2": struct(["Si"], 3),
        },
    }


def _write_fixture(tmp_path):
    """Writes the bz2 fixture, padded past the loader's 1KB stale-download
    floor with INCOMPRESSIBLE content (a sha256 hash chain — whitespace
    padding compresses to almost nothing under bz2 and stays sub-1KB)."""
    import hashlib
    payload = _fixture_payload()
    chain, h = [], b"seed"
    for _ in range(200):
        h = hashlib.sha256(h).digest()
        chain.append(h.hex())
    payload["_pad_ignore"] = {"0": "".join(chain)}
    p = tmp_path / "2022-10-19-wbm-init-structs.json.bz2"
    p.write_bytes(bz2.compress(json.dumps(payload).encode()))
    assert p.stat().st_size > 1024, "fixture must clear the loader's size floor"
    return p


def test_json_bz2_fallback_yields_all_structures(tmp_path):
    _write_fixture(tmp_path)
    got = list(mod.load_wbm_structures(str(tmp_path)))
    assert [s.material_id for s in got] == ["wbm-1-1", "wbm-1-2", "wbm-1-3"]
    assert got[0].symbols == ["Na", "Cl"]
    assert got[1].symbols == ["Fe", "Fe", "O", "O", "O"]
    assert got[0].cell == [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]]
    assert got[2].positions == [[0.0, 0.0, 0.0]]
    assert got[0].pbc == (True, True, True)


def test_json_fallback_respects_limit(tmp_path):
    _write_fixture(tmp_path)
    got = list(mod.load_wbm_structures(str(tmp_path), limit=2))
    assert len(got) == 2


def test_zero_byte_extxyz_is_ignored_not_trusted(tmp_path):
    (tmp_path / "2024-08-04-wbm-initial-atoms.extxyz.zip").write_bytes(b"")
    _write_fixture(tmp_path)
    got = list(mod.load_wbm_structures(str(tmp_path)))
    assert len(got) == 3  # fell through to the json, did not crash on the stub


def test_missing_everything_raises(tmp_path):
    try:
        list(mod.load_wbm_structures(str(tmp_path)))
    except FileNotFoundError as e:
        assert "init-structs" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")
