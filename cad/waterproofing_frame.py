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
    base_od: float = 210.0
    base_screw_sep_x: float = 45.0  # Flexible (slots on main).
    base_screw_sep_y: float = 60.0

    base_plate_thickness: float = 5.0

    base_plate_vertical_wall_t: float = 8.0

    base_relief_screw_sep_x: float = 60.0
    base_relief_screw_sep_y: float = 23.5
    base_relief_screw_depth: float = 2.8
    base_relief_screw_od: float = 8.0

    # Layer 1 to 2 Config
    base_clamp_overlap_axial: float = 10.0
    base_to_clamp_radial_gap: float = 3.0

    # Layer 2: Clamp
    clamp_plate_thickness: float = 5.0
    clamp_plate_vertical_wall_t: float = 8.0

    clamp_rib_width: float = 5.0
    clamp_rib_height: float = 7.0

    # Layer 3: Topper
    topper_general_thickness: float = 15.0
    topper_size_x: float = 45.0 + 16.0
    topper_size_y: float = 60.0 + 16.0

    topper_channel_width: float = 15.0 + 0.5  # Measured 15mm.
    topper_channel_thickness: float = 5.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert True

    @property
    def clamp_plate_od(self) -> float:
        """Outer diameter of clamp plate."""
        return (
            self.base_od
            - 2 * self.base_plate_vertical_wall_t
            - 2 * self.base_to_clamp_radial_gap
        )


def base_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of base_plate."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.base_od / 2,
        height=spec.base_plate_thickness + spec.base_clamp_overlap_axial,
        align=bde.align.ANCHOR_BOTTOM,
    )

    p -= bd.Pos(Z=spec.base_plate_thickness) * bd.Cylinder(
        radius=spec.base_od / 2 - spec.base_plate_vertical_wall_t,
        height=spec.base_clamp_overlap_axial,
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

    return p


def clamp_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of clamp_plate."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.clamp_plate_od / 2,
        height=spec.clamp_plate_thickness + spec.base_clamp_overlap_axial,
        align=bde.align.ANCHOR_BOTTOM,
    )

    p -= bd.Pos(Z=spec.clamp_plate_thickness) * bd.Cylinder(
        radius=spec.clamp_plate_od / 2 - spec.clamp_plate_vertical_wall_t,
        height=spec.base_clamp_overlap_axial,
        align=bde.align.ANCHOR_BOTTOM,
    )

    # Add structural ribs to the clamp plate. X-shape.
    for rot_z in (30, -30, 90):
        p += (
            bd.Rot(Z=rot_z)
            * bd.Pos(Z=spec.clamp_plate_thickness)
            * bd.Box(
                spec.clamp_plate_od - spec.clamp_plate_vertical_wall_t,
                spec.clamp_rib_width,
                spec.clamp_rib_height,
                align=bde.align.ANCHOR_BOTTOM,
            )
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
    """Create a CAD model of the waterproofing frame assembly."""
    p = bd.Part(None)

    p += bd.Pos(Z=0) * base_plate(spec)

    p += bd.Pos(Z=35) * clamp_plate(spec)

    p += bd.Pos(Z=70) * topper_plate(spec)

    return p


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
