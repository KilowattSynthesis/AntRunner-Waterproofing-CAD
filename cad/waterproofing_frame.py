from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for waterproofing frame."""

    screw_od: float = 5.2

    # Layer 1: Base
    base_od: float = 180.0
    base_screw_sep_x: float = 45.0  # Flexible (slots on main).
    base_screw_sep_y: float = 60.0

    base_plate_thickness: float = 5.0

    base_relief_screw_sep_x: float = 60.0
    base_relief_screw_sep_y: float = 23.5
    base_relief_screw_depth: float = 2.8
    base_relief_screw_od: float = 8.0

    zip_tie_width: float = 12.0
    zip_tie_height: float = 3.8
    zip_tie_channel_length: float = 100.0
    zip_tie_sep_x: float = 45.0  # Matches base screw spacing.

    # Layer 1 to 2 Config
    # Wavy (labyrinth) fabric clamp between base and clamp.
    # Ridges alternate clamp/base/clamp/... going inward from the outside.
    # Outermost clamp ridge is a skirt around the outside of the base OD.
    # Next ridge in is the base's outer rim.
    fabric_gap: float = 4.0  # Fabric is 4-5mm thick. Slightly compressed.
    wave_depth: float = 5.0
    wave_ridge_width: float = 5.0
    wave_ridge_count: int = 5

    # Layer 2: Clamp
    clamp_plate_thickness: float = 5.0

    # Nominally could be: self.base_plate_thickness + self.fabric_gap
    clamp_skirt_extra_depth: float = 7.0

    # Layer 3: Topper
    topper_general_thickness: float = 15.0
    topper_size_x: float = 45.0 + 16.0
    topper_size_y: float = 60.0 + 16.0
    topper_corner_fillet_radius: float = 5.0

    topper_channel_width: float = 15.0 + 0.5  # Measured 15mm.
    topper_channel_thickness: float = 5.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert self.wave_ridge_count % 2 == 1, "Must start/end on clamp."
        innermost_ridge_r = self.wave_ridges[-1][1]
        assert innermost_ridge_r > 0

        logger.info(f"Base Plate OD: {self.base_od:.1f} mm")
        logger.info(f"Clamp Plate OD: {self.clamp_plate_od:.1f} mm")

        screw_length = (
            self.base_plate_thickness
            + self.wave_depth
            + self.clamp_plate_thickness
            + self.topper_general_thickness
        )
        logger.info(
            f"Minimum screw length: {screw_length:.1f} mm + 15mm for safety"
        )

        fabric_ring_circumference = 3.14159 * self.base_od
        logger.info(
            f"Fabric ring: D={self.base_od:.1f} mm, "
            f"circumference={fabric_ring_circumference / 10:.1f} cm"
        )

    @property
    def clamp_plate_od(self) -> float:
        """Outer diameter of clamp plate."""
        return 2 * self.wave_ridges[0][0]

    @property
    def wave_ridges(self) -> list[tuple[float, float, str]]:
        """List of (r_outer, r_inner, owner) for each wave ridge.

        Owner is "clamp" (ridge points down) or "base" (ridge points up).
        Ordered from outside to inside.
        """
        ridges: list[tuple[float, float, str]] = []
        r_outer = self.base_od / 2 + self.fabric_gap + self.wave_ridge_width
        for i in range(self.wave_ridge_count):
            owner = "clamp" if i % 2 == 0 else "base"
            r_inner = r_outer - self.wave_ridge_width
            ridges.append((r_outer, r_inner, owner))
            r_outer = r_inner - self.fabric_gap
        return ridges


def _ring(
    r_outer: float, r_inner: float, height: float
) -> bd.Part | bd.Compound:
    """Create an annular ring, anchored at the bottom."""
    return (
        bd.Part(None)
        + bd.Cylinder(
            radius=r_outer, height=height, align=bde.align.ANCHOR_BOTTOM
        )
        - bd.Cylinder(
            radius=r_inner, height=height, align=bde.align.ANCHOR_BOTTOM
        )
    )


def base_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of base_plate."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.base_od / 2,
        height=spec.base_plate_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Add the upward-pointing wave ridges (outermost is the outer rim).
    for r_outer, r_inner, owner in spec.wave_ridges:
        if owner == "base":
            p += bd.Pos(Z=spec.base_plate_thickness) * _ring(
                r_outer, r_inner, spec.wave_depth
            )

    # Remove the screw holes.
    for x in (-1, 1):
        for y in (-1, 1):
            p -= bd.Pos(
                X=x * spec.base_screw_sep_x / 2,
                Y=y * spec.base_screw_sep_y / 2,
            ) * bd.Cylinder(
                radius=spec.screw_od / 2,
                height=spec.base_plate_thickness,
                align=bde.align.ANCHOR_BOTTOM,
            )

    # Remove the base relief screw holes.
    for x in (-1, 1):
        for y in (-1, 1):
            p -= bd.Pos(
                X=x * spec.base_relief_screw_sep_x / 2,
                Y=y * spec.base_relief_screw_sep_y / 2,
            ) * bd.Cylinder(
                radius=spec.base_relief_screw_od / 2,
                height=spec.base_relief_screw_depth,
                align=bde.align.ANCHOR_BOTTOM,
            )

    # Remove zip tie channels in Y axis.
    for x in (-1, 1):
        p -= bd.Pos(X=x * spec.zip_tie_sep_x / 2) * bd.Box(
            spec.zip_tie_width,
            spec.zip_tie_channel_length,
            spec.zip_tie_height,
            align=bde.align.ANCHOR_BOTTOM,
        )

    return p


def clamp_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of clamp_plate."""
    p = bd.Part(None)

    # Z where the (non-skirt) ridges start, and where the body starts.
    ridge_z = spec.clamp_skirt_extra_depth
    body_z = ridge_z + spec.wave_depth

    # Body sits above the downward-pointing wave ridges. Smooth top.
    p += bd.Pos(Z=body_z) * bd.Cylinder(
        radius=spec.clamp_plate_od / 2,
        height=spec.clamp_plate_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Add the downward-pointing wave ridges. First one is the outer skirt.
    for i, (r_outer, r_inner, owner) in enumerate(spec.wave_ridges):
        if owner == "clamp":
            extra = spec.clamp_skirt_extra_depth if i == 0 else 0
            p += bd.Pos(Z=ridge_z - extra) * _ring(
                r_outer, r_inner, spec.wave_depth + extra
            )

    # Remove the screw holes.
    for x in (-1, 1):
        for y in (-1, 1):
            p -= bd.Pos(
                X=x * spec.base_screw_sep_x / 2,
                Y=y * spec.base_screw_sep_y / 2,
            ) * bd.Cylinder(
                radius=spec.screw_od / 2,
                height=body_z + spec.clamp_plate_thickness,
                align=bde.align.ANCHOR_BOTTOM,
            )

    return p


def topper_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of topper_plate."""
    p = bd.Part(None)

    p += bd.Box(
        spec.topper_size_x,
        spec.topper_size_y,
        spec.topper_general_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Fillet the vertical (Z-axis) corners.
    p = bd.fillet(
        p.edges().filter_by(bd.Axis.Z),
        radius=spec.topper_corner_fillet_radius,
    )

    # Remove the channel (along Y-axis) for antenna.
    p -= bd.Box(
        spec.topper_channel_width,
        spec.topper_size_y,
        spec.topper_general_thickness - spec.topper_channel_thickness,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Remove the screw holes.
    for x in (-1, 1):
        for y in (-1, 1):
            p -= bd.Pos(
                X=x * spec.base_screw_sep_x / 2,
                Y=y * spec.base_screw_sep_y / 2,
            ) * bd.Cylinder(
                radius=spec.screw_od / 2,
                height=spec.topper_general_thickness,
                align=bde.align.ANCHOR_BOTTOM,
            )

    return p


def assembly(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of the waterproofing frame assembly.

    Each layer is a separate labeled child (shows up by name in viewers/STEP).
    """
    base = bd.Pos(Z=0) * base_plate(spec)
    base.label = "base_plate"

    clamp = bd.Pos(Z=35) * clamp_plate(spec)
    clamp.label = "clamp_plate"

    topper = bd.Pos(Z=70) * topper_plate(spec)
    topper.label = "topper_plate"

    return bd.Compound(label="assembly", children=[base, clamp, topper])


if __name__ == "__main__":
    parts = {
        "base_plate": show(base_plate(Spec())),
        "clamp_plate": show(clamp_plate(Spec())),
        "topper_plate": show(topper_plate(Spec())),
        "assembly": show(assembly(Spec())),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
