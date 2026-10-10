from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for waterproofing frame."""

    main_od: float = 210.0

    base_screw_sep_x: float = 45.0  # Flexible (slots on main).
    base_screw_sep_y: float = 60.0

    screw_od: float = 5.2

    base_plate_thickness: float = 5.0
    clamp_plate_thickness: float = 5.0

    base_plate_vertical_wall_t: float = 8.0
    clamp_plate_vertical_wall_t: float = 8.0

    base_clamp_overlap_axial: float = 10.0

    base_to_clamp_radial_gap: float = 3.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert True

    @property
    def clamp_plate_od(self) -> float:
        """Outer diameter of clamp plate."""
        return (
            self.main_od
            - 2 * self.base_plate_vertical_wall_t
            - 2 * self.base_to_clamp_radial_gap
        )


def base_plate(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of base_plate."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=spec.main_od / 2,
        height=spec.base_plate_thickness + spec.base_clamp_overlap_axial,
        align=bde.align.ANCHOR_BOTTOM,
    )

    p -= bd.Pos(Z=spec.base_plate_thickness) * bd.Cylinder(
        radius=spec.main_od / 2 - spec.base_plate_vertical_wall_t,
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


def assembly(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of the waterproofing frame assembly."""
    p = bd.Part(None)

    p += base_plate(spec)

    p += bd.Pos(Z=35) * clamp_plate(spec)

    return p


if __name__ == "__main__":
    parts = {
        "base_plate": show(base_plate(Spec())),
        "clamp_plate": show(clamp_plate(Spec())),
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
