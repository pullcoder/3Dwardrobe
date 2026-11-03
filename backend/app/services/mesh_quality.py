"""실제 삼각형/좌표를 검사한다. 전역 자체 교차 검사는 별도 Blender 실험으로 수행한다."""

from collections import Counter, defaultdict

import numpy as np


def inspect_meshes(meshes):
    points, faces, welded = [], [], {}
    for mesh in meshes:
        mapping = []
        for p in np.asarray(mesh["positions"]).reshape(-1, 3):
            key = tuple(round(float(v), 6) for v in p)
            if key not in welded:
                welded[key] = len(points)
                points.append(p)
            mapping.append(welded[key])
        faces.extend([[mapping[i] for i in f] for f in np.asarray(mesh["indices"]).reshape(-1, 3)])
    points, faces = np.asarray(points), np.asarray(faces)
    areas = np.linalg.norm(
        np.cross(
            points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]]
        ),
        axis=1,
    )
    edges, graph = defaultdict(list), defaultdict(set)
    for a, b, c in faces:
        for x, y in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((int(x), int(y))))].append(x < y)
            graph[int(x)].add(int(y))
            graph[int(y)].add(int(x))

    def components(adjacency):
        remaining = set(adjacency)
        count = 0
        while remaining:
            pending = [remaining.pop()]
            count += 1
            while pending:
                for other in adjacency[pending.pop()]:
                    if other in remaining:
                        remaining.remove(other)
                        pending.append(other)
        return count

    boundary = defaultdict(set)
    for (a, b), directions in edges.items():
        if len(directions) == 1:
            boundary[a].add(b)
            boundary[b].add(a)
    counts = Counter(len(v) for v in edges.values())
    return {
        "connected_components": components(graph),
        "boundary_loops": components(boundary),
        "boundary_branches": sum(len(v) != 2 for v in boundary.values()),
        "degenerate_triangles": int(np.sum(areas < 1e-11)),
        "nonmanifold_edges": sum(v for k, v in counts.items() if k > 2),
        "inconsistent_winding_edges": int(
            sum(len(v) == 2 and v[0] == v[1] for v in edges.values())
        ),
        "self_intersections": "not_evaluated_in_runtime",
    }
