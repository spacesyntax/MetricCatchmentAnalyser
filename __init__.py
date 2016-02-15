# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MetricCatchmentAnalyser
                                 A QGIS plugin
 Network based metric catchment analysis
                             -------------------
        begin                : 2016-02-13
        copyright            : (C) 2016 by Laurens Versluis
        email                : l.versluis@spacesyntax.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MetricCatchmentAnalyser class from file MetricCatchmentAnalyser.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .metric_catchment_analyser import MetricCatchmentAnalyser
    return MetricCatchmentAnalyser(iface)
