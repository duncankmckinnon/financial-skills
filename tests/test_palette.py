import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "plugins/financial-skills/assets"))
import palette as p

HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_categorical_has_eight_slots_both_modes():
    for mode in ("light", "dark"):
        assert len(p.CATEGORICAL[mode]) == 8
        assert all(HEX.match(c) for c in p.CATEGORICAL[mode])
        assert len(set(p.CATEGORICAL[mode])) == 8


def test_slot_one_is_blue_slot_eight_is_red():
    assert p.CATEGORICAL["light"][0] == "#2a78d6"
    assert p.CATEGORICAL["light"][7] == "#e34948"


def test_gain_loss_poles_are_blue_and_red_not_green():
    assert p.POSITIVE["light"] == "#2a78d6"
    assert p.NEGATIVE["light"] == "#e34948"
    assert p.POSITIVE["dark"] == "#3987e5"
    assert p.NEGATIVE["dark"] == "#e66767"
    assert "#008300" not in (p.POSITIVE["light"], p.POSITIVE["dark"])


def test_surfaces_and_ink():
    assert p.SURFACE["light"] == "#fcfcfb"
    assert p.SURFACE["dark"] == "#1a1a19"
    for mode in ("light", "dark"):
        for role in ("primary", "secondary", "muted", "grid", "baseline"):
            assert HEX.match(p.INK[mode][role])


def test_sequential_blue_is_monotonically_darker():
    ls = [p.hex_to_oklab(c)[0] for c in p.SEQUENTIAL_BLUE]
    assert ls == sorted(ls, reverse=True)


def test_oklab_roundtrip_is_stable():
    for c in p.CATEGORICAL["light"]:
        assert p.oklab_to_hex(p.hex_to_oklab(c)) == c


def test_oklab_ramp_endpoints_and_length():
    r = p.oklab_ramp("#f0efec", "#2a78d6", 5)
    assert len(r) == 5
    assert r[0] == "#f0efec"
    assert r[-1] == "#2a78d6"
    assert all(HEX.match(c) for c in r)


def test_diverging_ramp_is_symmetric_with_neutral_centre():
    r = p.diverging_ramp("light", 4)
    assert len(r) == 9
    assert r[0] == p.NEGATIVE["light"]
    assert r[4] == p.NEUTRAL["light"]
    assert r[-1] == p.POSITIVE["light"]
