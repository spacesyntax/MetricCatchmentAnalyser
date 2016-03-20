from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.networkanalysis import *
from qgis.utils import *


class customProperter(QgsArcProperter):
    def __init__(self, attributeId, defaultValue):
        QgsArcProperter.__init__(self)
        self.AttributeId = attributeId
        self.DefaultValue = defaultValue

    def property(self, distance, Feature):
        cost = float(Feature.attributes()[self.AttributeId])
        if cost <= 0.0:
            return QVariant(self.DefaultValue)
        return cost

    def requiredAttributes(self):
        l = []
        l.append(self.AttributeId);
        return l