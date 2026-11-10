"""Optional independent CGAL oracle. Test-only; no runtime dependency/adoption."""
from CGAL.CGAL_Kernel import Point_3, Triangle_3, do_intersect
from CGAL.CGAL_Polyhedron_3 import Polyhedron_3
from CGAL.CGAL_Polygon_mesh_processing import polygon_soup_to_polygon_mesh, self_intersections


def triangle_hit(a,b):
    return bool(do_intersect(Triangle_3(*(Point_3(*p) for p in a)),
                             Triangle_3(*(Point_3(*p) for p in b))))


def mesh_hits(mesh):
    # Caller supplies an oriented manifold polygon mesh; soup conversion does
    # not repair it. Reject changed face counts rather than treating as clean.
    p=Polyhedron_3()
    polygon_soup_to_polygon_mesh([Point_3(*v) for v in mesh.vertices],mesh.faces.tolist(),p)
    if not p.is_valid() or p.size_of_facets()!=len(mesh.faces):
        raise ValueError('CGAL topology precondition failed')
    for i,f in enumerate(p.facets()):
        f.set_id(i)
    out=[]
    self_intersections(p,out)
    return sorted(tuple(sorted((int(pair.first.id()),int(pair.second.id())))) for pair in out)
