from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.networkanalysis import *
from qgis.utils import *


class SpeedProperter(QgsArcProperter):

    def __init__(self, attributeId, defaultValue, toMetricFactor = 1000 ):
        QgsArcProperter.__init__(self)
        self.AttributeId = attributeId
        self.DefaultValue = defaultValue
        self.ToMetricFactor = toMetricFactor

    def property(self, distance, Feature):
        map = Feature.attributeMap()
        it = map[self.AttributeId]
        val = distance / ( it.toDouble()[0] * self.ToMetricFactor )
        if (val <= 0.0):
            return QVariant( distance / ( self.DefaultValue * self.ToMetricFactor ) )
        return QVariant( val )

    def requiredAttributes(self):
        l = []
        l.append(self.AttributeId);
        return l