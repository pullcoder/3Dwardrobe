# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender 전용 오프라인 품질 실험. 앱의 자동 생성 엔진으로 사용하지 않는다.

blender --background --python scripts/cloth_quality_experiment.py -- input.glb output-dir
"""

import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def render(scene, objects, output, view):
    points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    center = (low + high) / 2
    distance = max(high - low) * 2
    camera = scene.camera
    camera.location = center + Vector(
        (distance if view == "side" else 0, distance if view == "back" else -distance, 0.08)
    )
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def inspect(objects):
    total = 0
    for obj in objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        faces = [tuple(t.vertices) for t in mesh.loop_triangles]
        # UV/부위 경계의 중복 정점도 좌표가 같으면 인접한 면으로 본다.
        keys = [tuple(round(c, 6) for c in v.co) for v in mesh.vertices]
        neighbors = [{keys[i] for i in face} for face in faces]
        tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], faces, all_triangles=True)
        total += sum(a < b and not neighbors[a] & neighbors[b] for a, b in tree.overlap(tree))
        evaluated.to_mesh_clear()
    return {"nonadjacent_triangle_overlap_pairs": total}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :]
    source, target = Path(args[0]).resolve(), Path(args[1]).resolve()
    target.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.world.color = (0.55, 0.55, 0.55)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 1.3
    for location, power in [((2, -3, 4), 350), ((-3, -1, 2), 180), ((0, 3, 3), 240)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        bpy.context.object.data.energy = power
        bpy.context.object.data.shape = "DISK"
        bpy.context.object.data.size = 3
        bpy.context.object.rotation_euler = (
            (-bpy.context.object.location).to_track_quat("-Z", "Y").to_euler()
        )
    before = inspect(objects)
    for view in ("front", "side", "back"):
        render(scene, objects, target / f"before-{view}.png", view)
    if len(objects) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        objects = [bpy.context.object]
    initial = {}
    for obj in objects:
        mesh = obj.data
        # 가져오기 시 분리된 UV 정점을 붙여 봉제 경계가 찢어지는 실험을 방지한다.
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=0.00001)
        bpy.ops.object.mode_set(mode="OBJECT")
        high = max((obj.matrix_world @ v.co).z for v in mesh.vertices)
        group = obj.vertex_groups.new(name="support")
        pinned = [v.index for v in mesh.vertices if (obj.matrix_world @ v.co).z > high - 0.045]
        group.add(pinned, 1.0, "REPLACE")
        initial[obj.name] = [v.co.copy() for v in mesh.vertices]
        cloth = obj.modifiers.new("offline_cloth_experiment", "CLOTH")
        cloth.settings.quality = 5
        cloth.settings.mass = 0.2
        cloth.settings.tension_stiffness = 25
        cloth.settings.compression_stiffness = 25
        cloth.settings.shear_stiffness = 15
        cloth.settings.bending_stiffness = 0.5
        cloth.settings.vertex_group_mass = group.name
        cloth.collision_settings.use_self_collision = True
        cloth.collision_settings.self_distance_min = 0.003
        cloth.point_cache.frame_start = 1
        cloth.point_cache.frame_end = 12
    start = time.perf_counter()
    for frame in range(1, 13):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in objects:
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            evaluated.to_mesh()
            evaluated.to_mesh_clear()
    elapsed = time.perf_counter() - start
    displacement = []
    for obj in objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        displacement.extend((v.co - initial[obj.name][v.index]).length for v in mesh.vertices)
        evaluated.to_mesh_clear()
    after = inspect(objects)
    for view in ("front", "side", "back"):
        render(scene, objects, target / f"after-{view}.png", view)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(target / "cloth-experiment.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    report = {
        "blender": bpy.app.version_string,
        "frames": 12,
        "simulation_seconds": elapsed,
        "mean_displacement_m": sum(displacement) / len(displacement),
        "max_displacement_m": max(displacement),
        "before": before,
        "after": after,
        "setup": "pinned_hanging_cloth_no_mannequin_collider",
        "production_enabled": False,
    }
    (target / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
