"""Validated chart palette.

Values come from the dataviz reference palette and were validated with
scripts/validate_palette.js: categorical 8-slot ALL PASS in both modes
(worst adjacent CVD dE 9.1 light / 8.4 dark); blue<->red diverging poles
ALL PASS all-pairs (CVD dE 21.6 light / 19.2 dark).

Gains/losses are blue<->red, never green/red: green#008300<->red#e34948
measures protan dE 7.2, inside the failure band. Do not "fix" this to
match finance convention.
"""

CATEGORICAL = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark":  ["#3987e5", "#d95926", "#199e70", "#c98500",
              "#d55181", "#008300", "#9085e9", "#e66767"],
}

# Categorical slots below 3:1 contrast on the light surface. Charts using
# these MUST ship visible direct labels or an accompanying table.
LOW_CONTRAST_LIGHT_SLOTS = (2, 3, 4)  # aqua, yellow, magenta

POSITIVE = {"light": "#2a78d6", "dark": "#3987e5"}
NEGATIVE = {"light": "#e34948", "dark": "#e66767"}
NEUTRAL = {"light": "#f0efec", "dark": "#383835"}

SURFACE = {"light": "#fcfcfb", "dark": "#1a1a19"}

INK = {
    "light": {"primary": "#0b0b0b", "secondary": "#52514e",
              "muted": "#898781", "grid": "#e1e0d9", "baseline": "#c3c2b7"},
    "dark":  {"primary": "#ffffff", "secondary": "#c3c2b7",
              "muted": "#898781", "grid": "#2c2c2a", "baseline": "#383835"},
}

SEQUENTIAL_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
                   "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
                   "#184f95", "#104281", "#0d366b"]

DE_EMPHASIS = {"light": "#c3c2b7", "dark": "#52514e"}


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _cbrt(x: float) -> float:
    """Real cube root -- the LMS terms can go slightly negative."""
    return x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3))


def hex_to_oklab(h: str):
    h = h.lstrip("#")
    r, g, b = (_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_hex(lab) -> str:
    L, a, bb = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * bb) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * bb) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * bb) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    out = ""
    for c in (r, g, b):
        v = round(max(0.0, min(1.0, _linear_to_srgb(c))) * 255)
        out += f"{v:02x}"
    return "#" + out


def oklab_ramp(start_hex: str, end_hex: str, n: int):
    """n colors interpolated in OKLab; endpoints are exact."""
    if n < 2:
        raise ValueError("n must be >= 2")
    a, b = hex_to_oklab(start_hex), hex_to_oklab(end_hex)
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(oklab_to_hex(tuple(a[j] + (b[j] - a[j]) * t for j in range(3))))
    out[0], out[-1] = start_hex.lower(), end_hex.lower()
    return out


def diverging_ramp(mode: str, n_per_arm: int):
    """Negative pole -> neutral -> positive pole. Equal steps per arm."""
    neg = oklab_ramp(NEGATIVE[mode], NEUTRAL[mode], n_per_arm + 1)
    pos = oklab_ramp(NEUTRAL[mode], POSITIVE[mode], n_per_arm + 1)
    return neg[:-1] + [NEUTRAL[mode].lower()] + pos[1:]
