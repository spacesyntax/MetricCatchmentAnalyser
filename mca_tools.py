# Build-in dependencies
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.networkanalysis import *
from qgis.utils import *
import math
import sys
import inspect

# Custom cost builder
from arc_properter import customProperter

# Loading shapely and SciPy
try:
    from shapely.ops import cascaded_union, polygonize
    from shapely.geometry import MultiPoint
    from scipy.spatial import Delaunay
    ex_dep_loaded = True
except ImportError,e:
    	ex_dep_loaded = False

def graph_builder(network_lines, origin_points, origin_column, tolerance,custom_cost, cost_column):
    # Settings
    crs = network_lines.crs()
    epsg = crs.authid()
    otf = False
    default_value = 0
    network_fields = network_lines.pendingFields()
    cost_index = network_fields.indexFromName(cost_column)
    # Setting up graph build director
    director = QgsLineVectorLayerDirector(network_lines, -1, '', '', '', 3)
    # Determining cost calculation
    if custom_cost == True:
        properter = customProperter(cost_index,default_value)
    else:
        properter = QgsDistanceArcProperter()
    # Building graph
    director.addProperter(properter)
    builder = QgsGraphBuilder(crs, otf, tolerance, epsg)
    # Reading origins and making list of coordinates
    origins = []
    origins_name ={}
    for i,f in enumerate(origin_points.getFeatures()):
        geom = f.geometry().asPoint()
        origins.append(geom)
        if origins_name:
            print origins_name
            #f[origin_column]
            origins_name[i] = name
    # Connect origin points to the director and build graph
    tied_origins = director.makeGraph(builder, origins)
    graph = builder.graph()

    return graph, tied_origins, origins_name


def alpha_shape(points, alpha):
    # Empty triangle list
    pl_lines = []
    # Transform points into Shapely's MultiPoint format
    multi_points = MultiPoint(points)
    # Create delaunay triangulation
    triangles = Delaunay(multi_points)
    # Assess triangles
    for a, b, c in triangles.vertices:
        coord_a = points[a]
        coord_b = points[b]
        coord_c = points[c]

        # Calculating length of triangle sides
        a = math.sqrt((coord_a[0] - coord_b[0]) ** 2 + (coord_a[1] - coord_b[1]) ** 2)
        b = math.sqrt((coord_a[0] - coord_c[0]) ** 2 + (coord_a[1] - coord_c[1]) ** 2)
        c = math.sqrt((coord_c[0] - coord_b[0]) ** 2 + (coord_c[1] - coord_b[1]) ** 2)

        # Calculating circumcircle radius
        circum_rad = (a * b * c) / math.sqrt((a + b + c) * (b + c - a) * (c + a - b) * (a + b - c))

        # Circumcircle radius filter
        if circum_rad < alpha:
            pl_lines.append((coord_a, coord_b))
            pl_lines.append((coord_a, coord_c))
            pl_lines.append((coord_c, coord_b))

    # Circumcircle radius filter
    pl_triangles = list(polygonize(pl_lines))
    pl_polygon = cascaded_union(pl_triangles)

    return pl_polygon


def mca_network_writer(output_network, mca_network):
    output_network.dataProvider().addAttributes([QgsField("min_dist", QVariant.Int)])
    output_network.updateFields()

    arc_geom_length = []
    i = 0
    for arc in mca_network:
        arc_geom = QgsGeometry.fromPolyline(arc['arcGeom'])
        if arc_geom.length() in arc_geom_length:  # removes duplicates
            pass
        elif not arc['arcCost']:  # removes unconnected lines or lines out of reach
            pass
        else:
            f = QgsFeature(output_network.pendingFields())
            f.setAttribute("id", i)
            geom = QgsGeometry.fromPolyline(arc['arcGeom'])
            f.setGeometry(geom)

            cost_list = []
            for cost_dict in arc['arcCost']:
                for origin_index,origin in enumerate(cost_dict):
                    cost_list.append(cost_dict[origin])
                    f.setAttribute(origin_index + 1, int(cost_dict[origin]))

                if len(cost_list) > 0:
                    f.setAttribute('min_dist', int(min(cost_list)))

            output_network.dataProvider().addFeatures([f])
            arc_geom_length.append(arc_geom.length())
        i += 1


def mca_catchment_writer(output_catchment, mca_catchments, origins_name, alpha):
    for i,j in enumerate(mca_catchments):
        origin = j.keys()[0]
        points = j[origin]
        p = QgsFeature(output_catchment.pendingFields())
        if origins_name:
            p.setAttribute("origin", "%s" % origins_name.get(i))
        else:
            p.setAttribute("origin", "origin_%s" % i)
        p_geom = QgsGeometry.fromWkt((alpha_shape(points, alpha)).wkt)
        p.setGeometry(p_geom)
        output_catchment.dataProvider().addFeatures([p])

def mca_vector_writer(layer, path, crs):
    shp_writer = QgsVectorFileWriter.writeAsVectorFormat(
        layer,
        r"%s" % path,
        "utf-8",
        crs,
        "ESRI Shapefile")
        
def mca(graph,
        tied_origins,
        origins_name,
        output_network,
        output_catchment,
        alpha,
        radius):

    output_network.dataProvider().addAttributes([QgsField("id", QVariant.Int)])
    output_network.updateFields()
    # dictionary with id's, list of lines and their respective costs
    mca_network = []
    # list with dictionaries of polygon points
    mca_catchments = []

    n = 0

    while n < graph.arcCount():
        arc_prop = {'arcId': 0, 'arcGeom': [], 'arcCost': [],}

        arc_prop['arcId'] = n;

        inVertexId = graph.arc(n).inVertex()
        outVertexId = graph.arc(n).outVertex()

        inVertexGeom = graph.vertex(inVertexId).point()
        outVertexGeom = graph.vertex(outVertexId).point()

        arc_prop['arcGeom'] = [inVertexGeom, outVertexGeom];
        mca_network.append(arc_prop)

        n += 1

    # iteration through all tied origin points
    i = 0

    for o in tied_origins:

        mca_catchment_points = {i: []}

        origin_vertex_id = graph.findVertex(tied_origins[i])
        if origins_name:
            origin_field_name = str(origins_name.get(i))
        else: # No name in record
            origin_field_name = "origin_%s" % (i + 1)
        output_network.dataProvider().addAttributes([QgsField("%s" % (origin_field_name), QVariant.Int)])
        output_network.updateFields()

        (tree, cost) = QgsGraphAnalyzer.dijkstra(graph, origin_vertex_id, 0)

        # Analysing the costs of the tree
        x = 0

        while x < graph.arcCount():
            inVertexId = graph.arc(x).inVertex()

            # origin lines
            if inVertexId == origin_vertex_id:
                arcCost = {i: 0}
                mca_network[x]['arcCost'].append(arcCost)

                # lines within the radius
            if cost[inVertexId] < radius and tree[inVertexId] != -1:  # lines within the radius
                outVertexId = graph.arc(x).outVertex()
                if cost[outVertexId] < radius:
                    arc_cost = cost[outVertexId]
                    arcCost = {i: arc_cost}
                    mca_network[x]['arcCost'].append(arcCost)

                    mca_catchment_points[i].append(graph.vertex(inVertexId).point())

            # lines at the edge of the radius
            elif cost[inVertexId] > radius and tree[inVertexId] != -1:
                outVertexId = graph.arc(x).outVertex()

                if cost[outVertexId] < radius:
                    # constructing cut down edge lines
                    edge_line_length = radius - cost[outVertexId]
                    edge_line_azimuth = graph.vertex(outVertexId).point().azimuth(
                        graph.vertex(inVertexId).point())  # degrees from north

                    new_point_adjacent = math.sin(math.radians(edge_line_azimuth)) * edge_line_length
                    new_point_opposite = math.cos(math.radians(edge_line_azimuth)) * edge_line_length

                    new_point_x = graph.vertex(outVertexId).point()[0] + new_point_adjacent
                    new_point_y = graph.vertex(outVertexId).point()[1] + new_point_opposite

                    # add edge lines
                    l = QgsFeature(output_network.pendingFields())

                    l.setAttribute(i + 1, int(cost[outVertexId]))
                    l.setGeometry(QgsGeometry.fromPolyline(
                        [graph.vertex(outVertexId).point(), QgsPoint(new_point_x, new_point_y)]))
                    output_network.dataProvider().addFeatures([l])

                    # add edge points
                    mca_catchment_points[i].append((new_point_x, new_point_y))

            x += 1

        mca_catchments.append(mca_catchment_points)

        i += 1

    # running writers
    mca_network_writer(output_network, mca_network)

    mca_catchment_writer(output_catchment, mca_catchments, origins_name, alpha)


def mca_network_renderer(output_network, radius):
    # settings for 10 color ranges depending on the radius
    color_ranges = (
        (0, (0.1 * radius), '#ff0000'),
        ((0.1 * radius), (0.2 * radius), '#ff5100'),
        ((0.2 * radius), (0.3 * radius), '#ff9900'),
        ((0.3 * radius), (0.4 * radius), '#ffc800'),
        ((0.4 * radius), (0.5 * radius), '#ffee00'),
        ((0.5 * radius), (0.6 * radius), '#a2ff00'),
        ((0.6 * radius), (0.7 * radius), '#00ff91'),
        ((0.7 * radius), (0.8 * radius), '#00f3ff'),
        ((0.8 * radius), (0.9 * radius), '#0099ff'),
        ((0.9 * radius), (1 * radius), '#0033ff'))

    # list with all color ranges
    ranges = []
    # for each range create a symbol with its respective color
    for lower, upper, color in color_ranges:
        symbol = QgsSymbolV2.defaultSymbol(output_network.geometryType())
        symbol.setColor(QColor(color))
        symbol.setWidth(0.5)
        range = QgsRendererRangeV2(lower, upper, symbol, '')
        ranges.append(range)

    # create renderer based on ranges and apply to network
    renderer = QgsGraduatedSymbolRendererV2('min_dist', ranges)
    output_network.setRendererV2(renderer)
    # add network to the canvas
    QgsMapLayerRegistry.instance().addMapLayer(output_network)


def mca_catchment_renderer(output_catchment):
    # create a black dotted outline symbol layer
    symbol_layer = QgsMarkerLineSymbolLayerV2()
    symbol_layer.setColor(QColor('black'))
    symbol_layer.setWidth(1)
    # create renderer and change the symbol layer in its symbol
    renderer = output_catchment.rendererV2()
    renderer.symbols()[0].changeSymbolLayer(0, symbol_layer)
    output_catchment.setRendererV2(renderer)
    # add catchment to the canvas
    QgsMapLayerRegistry.instance().addMapLayer(output_catchment)
