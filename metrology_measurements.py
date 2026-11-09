"""Load optical-metrology files and associate measured points with ladder modules.

This module is intentionally optional. The core :mod:`sts_db_api.db_api` module stays
limited to PostgreSQL access and does not import NumPy or scikit-learn. Consumers that
need measurement-file grouping import this module explicitly.
"""

from pathlib import Path
from typing import Any

import numpy as np


def _get_ladder_modules(ladder_id: str, conn: Any | None) -> list[str]:
    """Query module IDs without importing PostgreSQL support at module import time."""
    from .db_api import get_ladder_modules

    return get_ladder_modules(ladder_id, conn=conn, sorted=True)


def _load_array(path: Path, expected_columns: int, measurement_type: str) -> np.ndarray:
    """Load one whitespace-delimited measurement file after its header row."""
    if not path.is_file():
        raise FileNotFoundError(f"{measurement_type} file does not exist: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"{measurement_type} file is empty: {path}")

    data = np.loadtxt(path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != expected_columns:
        raise ValueError(
            f"{measurement_type} file {path} has {data.shape[1]} columns; "
            f"expected {expected_columns}"
        )
    return data


def _constrained_agglomerative(
    points: np.ndarray,
    n_clusters: int,
    *,
    y_max: float = 20.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Cluster points along Z while constraining links by table-frame Y distance.

    scikit-learn is imported lazily so importing ``sts_db_api`` and
    ``sts_db_api.db_api`` does not pull in optional numerical dependencies.
    """
    from sklearn.cluster import AgglomerativeClustering

    if n_clusters < 1:
        raise ValueError("At least one ladder module is required")
    if len(points) < n_clusters:
        raise ValueError(
            f"Cannot form {n_clusters} module clusters from {len(points)} points"
        )

    connectivity = np.zeros((len(points), len(points)), dtype=np.int8)
    for first in range(len(points)):
        for second in range(first + 1, len(points)):
            if abs(points[first, 1] - points[second, 1]) <= y_max:
                connectivity[first, second] = 1
                connectivity[second, first] = 1

    model = AgglomerativeClustering(
        n_clusters=n_clusters,
        linkage="ward",
        connectivity=connectivity,
    )
    labels = model.fit_predict(points[:, 2].reshape(-1, 1))
    centers = np.array(
        [points[labels == index].mean(axis=0) for index in range(n_clusters)]
    )
    return labels, centers


def fetch_measurements(
    ladder_id: str,
    folder: str | Path,
    *,
    use_markers: bool = True,
    use_surface: bool = False,
    conn: Any | None = None,
) -> dict[str, np.ndarray]:
    """Group optical-metrology points by the modules installed on a ladder.

    Marker rows contain nominal ``X Y Z`` followed by measured ``dX dY dZ``;
    surface rows contain ``X Y Z dZ``. The function reconstructs measured points,
    converts the optical-table frame to the CBM frame by swapping X and Y, clusters
    the points, and maps clusters to the top-to-bottom module order returned by the
    STS database.

    Parameters
    ----------
    ladder_id:
        STS ladder name used to query its installed modules.
    folder:
        Directory containing ``<ladder_id>_marker.txt`` and/or
        ``<ladder_id>_surface.txt``.
    use_markers, use_surface:
        Select the measurement sources to include. At least one must be enabled.
    conn:
        Optional existing PostgreSQL connection forwarded to
        :func:`sts_db_api.db_api.get_ladder_modules`.
    """
    if not use_markers and not use_surface:
        raise ValueError("At least one measurement source must be enabled")

    module_ids = _get_ladder_modules(ladder_id, conn)
    if not module_ids:
        raise ValueError(f"No modules found for ladder {ladder_id}")

    folder = Path(folder)
    point_sets: list[np.ndarray] = []

    if use_markers:
        marker_path = folder / f"{ladder_id}_marker.txt"
        markers = _load_array(marker_path, 6, "Marker")
        point_sets.append(markers[:, :3] + markers[:, 3:])

    if use_surface:
        surface_path = folder / f"{ladder_id}_surface.txt"
        surface = _load_array(surface_path, 4, "Surface")
        point_sets.append(
            np.column_stack((surface[:, :2], surface[:, 2] + surface[:, 3]))
        )

    points = np.vstack(point_sets)

    # Optical-table files use the opposite X/Y convention from the CBM frame.
    points[:, [0, 1]] = points[:, [1, 0]]

    labels, centers = _constrained_agglomerative(
        points,
        len(module_ids),
        y_max=20.0,
    )

    # Database module order is top-to-bottom; measured clusters follow descending Y.
    cluster_ids = sorted(np.unique(labels), key=lambda index: -centers[index, 1])
    if len(cluster_ids) != len(module_ids):
        raise RuntimeError(
            f"Found {len(cluster_ids)} clusters for {len(module_ids)} modules"
        )

    return {
        module_id: points[labels == cluster_id]
        for module_id, cluster_id in zip(module_ids, cluster_ids, strict=True)
    }
