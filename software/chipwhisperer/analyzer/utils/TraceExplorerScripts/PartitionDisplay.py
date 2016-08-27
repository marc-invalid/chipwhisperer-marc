#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, NewAE Technology Inc
# All rights reserved.
#
# Author: Colin O'Flynn
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================

from functools import partial
import numpy as np
import copy
from PySide.QtCore import *
from PySide.QtGui import *
import chipwhisperer.common.utils.qt_tweaks as QtFixes
import pyqtgraph as pg
from chipwhisperer.analyzer.utils.Partition import Partition
from chipwhisperer.common.utils import util
from chipwhisperer.common.api.autoscript import AutoScript
from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI
from chipwhisperer.common.ui.GraphWidget import GraphWidget
from chipwhisperer.common.ui.GraphWidget import ColorPalette
from chipwhisperer.common.utils.parameter import Parameterized, Parameter, setupSetParam
from chipwhisperer.common.ui.CWMainGUI import CWMainGUI


class DifferenceModeTTest(object):
    sectionName = "Difference of Partitions using Welch's T-Test"
    moduleName = "PartitionDifferencesWelchTTest"
    differenceType = "Welch's T-Test"

    def difference(self, numkeys, numparts, trace, numpoints, stats, pbDialog=None):
        means = stats["mean"]
        var = stats["variance"]
        num = stats["number"]

        if pbDialog:
            pbDialog.setMinimum(0)
            pbDialog.setMaximum(numkeys * numparts)

        # scalingFactor compensates for number of inner loop executions, to arrive at mean(ttests) rather than sum(ttests)
        loopIterations = numparts * (numparts-1) / 2
        scalingFactor  = 1.0 / loopIterations

        SADSeg = np.zeros((numkeys, numpoints))
        for bnum in range(0, numkeys):
            for i in range(0, numparts):
                if pbDialog:
                    pbDialog.updateStatus(numparts * bnum + i)
                    util.updateUI()
                    if pbDialog.wasAborted():
                        return SADSeg
                for j in range(i+1, numparts):
                    #          ^^^ Starting at i+1 because all comparisons j<i have been done already in previous
                    #              iterations of the parent loop, and comparison j==i wastes time with add(0)

                    if means[bnum][i] is not None and means[bnum][j] is not None:

                        ttest = np.subtract(means[bnum][i], means[bnum][j])
                        ttest /= np.sqrt((var[bnum][i]/num[bnum][i]) + (var[bnum][j]/num[bnum][j]))

                        # Working with unexpected input can lead to NaN (not a number) or +-inf.  Example: 1.0/0 = inf
                        # Allowing inf leads to "number out of range" exceptions during graph display.
                        # Therefore we replace ALL unexpected results with 0 (not just NaNs, as the original code did).
                        ttest[~np.isfinite(ttest)] = 0

                        # calculate sum(ttests) here, apply scalingFactor after the loop (faster)
                        SADSeg[bnum] = np.add(SADSeg[bnum], np.abs(ttest))

            # calculate mean(ttests) = sum(ttests) / count
            SADSeg[bnum] = np.multiply(SADSeg[bnum], scalingFactor)

        if pbDialog:
            pbDialog.updateStatus(numkeys * numparts)

        return SADSeg


class DifferenceModeSAD(object):
    sectionName = "Difference of Partitions using SAD"
    moduleName = "PartitionDifferencesSAD"
    differenceType = "Sum of Absolute Difference"

    def difference(self, numkeys, numparts, trace, numpoints, stats, pbDialog=None):

        means = stats["mean"]

        if pbDialog:
            pbDialog.setMinimum(0)
            pbDialog.setMaximum(numkeys * numparts)

        SADSeg = np.zeros((numkeys, numpoints))
        for bnum in range(0, numkeys):
            for i in range(0, numparts):
                if pbDialog:
                    pbDialog.updateStatus(numparts * bnum + i)
                    util.updateUI()
                    if pbDialog.wasAborted():
                        return SADSeg
                for j in range(i+1, numparts):
                    if means[bnum][i] is not None and means[bnum][j] is not None:
                        SADSeg[bnum] = np.add(SADSeg[bnum], np.abs(np.subtract(means[bnum][i], means[bnum][j])))

            # MARC: calculate mean(sads) = sum(sads) / count
            SADSeg[bnum] = np.divide(SADSeg[bnum], numparts * (numparts-1) / 2)

        return SADSeg


class DifferenceMode(object):
    attrDictCombination = {
                "sectionName":"Difference Based on XXXX",
                "moduleName":"PartitionDifferences",
                "module":None,
                "values":{
                    "mode":{"value":"sad", "desc":"How Differences are Generated", "changed":False, "definesunique":True},
                    "partmode":{"value":"0", "desc":"Partition Mode in Use", "changed":False, "definesunique":True},
                    "combomode":{"value":"0", "desc":"Partition Mode in Use", "changed":False, "definesunique":True},
                    "filename":{"value":None, "desc":"Combination File", "changed":False, "headerLabel":"Difference Data"},
                    },
                }

    supportedMethods = [DifferenceModeTTest, DifferenceModeSAD]

    def __init__(self):
        super(DifferenceMode, self).__init__()
        self.setDiffMethod(self.supportedMethods[0])

    def setDiffMethod(self, mode):
        self.mode = mode()
        self.diffMethodClass = mode
        self.attrDictCombination["sectionName"] = self.mode.sectionName
        self.attrDictCombination["moduleName"] = self.mode.moduleName
        # self.attrDictCombination["values"]["mode"]["value"] = self.

    def difference(self, numkeys, numparts, trace, numpoints, stats, pbDialog=None):
        self.data = self.mode.difference(numkeys, numparts, trace, numpoints, stats, pbDialog)
        return self.data

    def save(self, trace):
        newCfgDict = copy.deepcopy(self.attrDictCombination)
        updatedDict = trace.addAuxDataConfig(newCfgDict)
        trace.saveAuxData(self.data, updatedDict)

    def load(self, trace):
        # Check if trace has stuff
        cfg = trace.getAuxDataConfig(self.attrDictCombination)
        if cfg is None:
            return None
        return trace.loadAuxData(cfg["filename"])


class POI(QWidget):
    def __init__(self, parent):
        super(POI, self).__init__()

        self.parent = parent

        layout = QVBoxLayout()

        self.setWindowTitle('Point of Interest Selection')

        self.mainTable = QTableWidget()

        layout.addWidget(self.mainTable)
        pbSave = QPushButton('Set as POI in Project')
        pbSave.clicked.connect(self.savePOI)
        pbCalc = QPushButton('Recalc POI Values')
        pbCalc.clicked.connect(self.parent.updatePOI)
        # pbSaveNPY = QPushButton('Save to NPY File')
        # pbLoadNPY = QPushButton('Load NPY File')

        pbLayout = QHBoxLayout()
        pbLayout.addWidget(pbSave)
        pbLayout.addWidget(pbCalc)
        # pbLayout.addWidget(pbSaveNPY)
        # pbLayout.addWidget(pbLoadNPY)

        layout.addLayout(pbLayout)
        self.setLayout(layout)
        self.diffs = []
        self.poiArray = []

    def setDifferences(self, diffs):
        self.diffs = diffs
        self.parent.findParam(["Points of Interest",'poi-pointrng']).setValue((0, len(self.parent.SADList[0])))

    def savePOI(self):
        poiDict = {"poi":self.poiArray, "partitiontype":self.parent.partObject.partMethod.__class__.__name__}
        CWCoreAPI.getInstance().project().addDataConfig(poiDict, "Template Data", "Points of Interest")

    def calcPOI(self, numMax, pointRange, minSpace, diffs=None):
        if diffs:
            self.setDifferences(diffs)

        # Setup Table for current stuff
        self.mainTable.setRowCount(len(self.diffs))
        self.mainTable.setColumnCount(2)
        self.mainTable.setHorizontalHeaderLabels(["Subkey", "Point List"])
        self.mainTable.horizontalHeader().setStretchLastSection(True)
        self.mainTable.verticalHeader().hide()

        self.poiArray = []

        startPoint = pointRange[0]
        endPoint = pointRange[1]

        if startPoint == endPoint:
            endPoint += 1

        extendDownhill = self.parent.findParam(["Points of Interest",'Hill detection']).getValue()

        for bnum in range(0, len(self.diffs)):

            maxarray = []

            # Copy since we will be overwriting it a bunch
            data = copy.deepcopy(self.diffs[bnum][startPoint:endPoint])

            while len(maxarray) < numMax:
                # Find maximum location
                mloc = np.argmax(data)

                # Store this maximum
                maxarray.append(mloc + startPoint)

                # set to -INF data within +/- the minspace
                mstart = max(0, mloc - minSpace)
                while extendDownhill and mstart>0 and data[mstart-1] <= data[mstart]:
                    mstart-=1
                mend = min(mloc + minSpace, len(data))
                while extendDownhill and mend<len(data)-1 and data[mend+1] <= data[mend]:
                    mend+=1
                data[mstart:mend] = -np.inf

            # print maxarray
            self.poiArray.append(maxarray)

            self.mainTable.setItem(bnum, 0, QTableWidgetItem("%d" % bnum))
            self.mainTable.setCellWidget(bnum, 1, QtFixes.QLineEdit(str(maxarray)))
        return {"poi":self.poiArray}


class PartitionDisplay(Parameterized, AutoScript):
    _name = "Partition Comparison"

    def __init__(self, parent):

        #--- mandatory init

        AutoScript.__init__(self)
        self._autoscript_init = False
        self.parent = parent
        self._traces = None

        self.api = CWCoreAPI.getInstance()

        self.partObject = Partition()
        self.diffObject = DifferenceMode()

        #--- Skip GUI init unless a parent has been given (avoids adding docks multiple times)

        if parent is None:
            return

        #--- GUI init

        self.poi = POI(self)
        self.poiDock = CWMainGUI.getInstance().addDock(self.poi, "Partition Comparison POI Table", area=Qt.TopDockWidgetArea)
        self.poiDock.hide()
        self.defineName()

        self.graph = GraphWidget()
        self.bselection = QToolBar()
        self.graph.addWidget(self.bselection)
        self.graphDock = CWMainGUI.getInstance().addDock(self.graph, "Partition Comparison Graph", area=Qt.TopDockWidgetArea)
        self.graphDock.hide()

        self.palette = ColorPalette()


    def defineName(self):

        #--- Collect supported partition modes
        #
        #    * (DEPRECATED) The ones listed in "supportedMethods", using their .sectionName / .partitionType
        #    * Those in the "partition/" folder (via CoreAPI.valid_partitionModules) using ._name / ._description

        partModeList = {}

        for a in self.partObject.supportedMethods:
            partModeList[a.partitionType] = a

        partModeList.update(CWCoreAPI.getInstance().valid_partitionModules)

        #---

        diffModeList = {}
        for a in self.diffObject.supportedMethods:
            diffModeList[a.differenceType] = a

        self.addGroup("generatePartitions")
        self.addGroup("generatePartitionStats")
        self.addGroup("generatePartitionDiffs")
        self.addGroup("displayPartitionDiffs")

        self.getParams().addChildren([
              {'name':'Comparison Mode', 'key':'diffmode', 'type':'list', 'values':diffModeList, 'value':self.diffObject.diffMethodClass, 'action':lambda _: self.updateScript()},
              {'name':'Partition Mode', 'key':'partmode', 'type':'list', 'values':util.dictSort(partModeList), 'value':self.partObject.partMethodClass, 'action':lambda _: self.updateScript()},
              {'name':'Color Palette', 'key':'colorpalette', 'type':'list', 'values':util.dictSort({"Automatic":"auto", "Rainbow":"rainbow", "Accessible":"accessible", "Two colors":"dual", "Monochrome":"mono"}), 'value':"auto"},
              {'name':'Trace Range (all: 0,-1)', 'key':'trace_range', 'type':'range', 'default':(0, -1), 'value':(0, -1), 'action':lambda _: self.updateScript()},
              {'name':'Display', 'type':'action', 'action':lambda _:self.runAction()},
              {'name':'Keeloq', 'type':'action', 'action':lambda _:self.runAction_Keeloq()},

              {'name':'Auto-Save Data to Project', 'key':'part-saveints', 'type':'bool', 'value':False, 'action':lambda _: self.updateScript()},
              {'name':'Auto-Load Data from Project', 'key':'part-loadints', 'type':'bool', 'value':False, 'action':lambda _: self.updateScript()},

              {'name':'Points of Interest', 'key':'poi', 'type':'group', 'children':[
                 {'name':'Selection Mode', 'type':'list', 'values':{'Max N Points/Subkey':'maxn'}, 'value':'maxn'},
                 {'name':'Point Range', 'key':'poi-pointrng', 'type':'range', 'limits':(0, 0), 'default':(0, 0), 'value':(0, 0), 'action':lambda _: self.updatePOI()},
                 {'name':'Num POI/Subkey', 'key':'poi-nummax', 'type':'int', 'limits':(1, 200), 'value':1, 'action':lambda _: self.updatePOI()},
                 {'name':'Min Spacing between POI', 'key':'poi-minspace', 'type':'int', 'limits':(1, 100E6), 'value':1, 'step':100, 'action':lambda _: self.updatePOI()},
                 {'name':'Hill detection', 'key':'poi-hilldet', 'type':'bool', 'value':True, 'tip':"Extend the bounds downhill for each peak", 'action':lambda _: self.updatePOI()},
                 # {'name':'Threshold', 'key':'threshold', 'type':'int', 'visible':False},
                 {'name':'Open POI Table', 'type':'action', 'action':lambda _: self.poiDock.show()},
              ]},
        ])

    def updatePOI(self, _=None):
        self.updateScript()

        if self._autoscript_init == False:
            return

        # Some sort of race condition - applying Therac-25 type engineering and just
        # randomly hope this is enough delay
        QTimer.singleShot(500, lambda:self.runScriptFunction.emit("TraceExplorerDialog_PartitionDisplay_findPOI"))

    def setBytePlot(self, num, sel):
        self.enabledbytes[num] = sel
        if self.doRedraw:
            self.redrawPlot()

    def setByteAll(self, status):
        self.doRedraw = False
        for i, t in enumerate(self.byteNumAct):
            t.defaultWidget().setChecked(status)
            self.setBytePlot(i, status)
        self.doRedraw = True
        self.redrawPlot()

    def setByteShowEvenOdd(self, show_even):
        self.doRedraw = False
        for i, t in enumerate(self.byteNumAct):
            status = show_even if (i%2 == 0) else not show_even
            t.defaultWidget().setChecked(status)
            self.setBytePlot(i, status)
        self.doRedraw = True
        self.redrawPlot()

    def setByteToggle(self):
        self.doRedraw = False
        for i, t in enumerate(self.byteNumAct):
            status = not t.defaultWidget().isChecked()
            t.defaultWidget().setChecked(status)
            self.setBytePlot(i, status)
        self.doRedraw = True
        self.redrawPlot()

    def redrawPlot(self):
        self.graph.clearPushed()

        palette_preference = self.findParam('colorpalette').getValue()

        for bnum in range(0, self.numKeys):
            if self.enabledbytes[bnum]:
                self.graph.setColorInt(bnum, self.numKeys, palette=palette_preference)
                self.graph.passTrace(self.SADList[bnum], pen=pg.mkPen(self.palette.intColor(bnum, self.numKeys, palette=palette_preference)), idString = str(bnum))

    def updateScript(self, ignored=None):
        ##Partitioning & Differences
        try:
            diffMethodStr = self.findParam('diffmode').getValue().__name__
            partMethod    = self.findParam('partmode').getValue()
            partMethodStr = partMethod.__name__
        except AttributeError as e:
            return

        traceRange = self.findParam("trace_range").getValue()
        traceStart = max(traceRange[0], 0)
        traceStop  = traceRange[1]
        if traceStop != -1:
            traceStop = max(traceStop, traceStart)
        traceRangeStr = "(%d,%d)" % (traceStart, traceStop)

        #--- Imports (general)

        self.importsAppend('from chipwhisperer.analyzer.ui.CWAnalyzerGUI import CWAnalyzerGUI')
        self.importsAppend('from chipwhisperer.analyzer.utils.TraceExplorerScripts.PartitionDisplay import DifferenceModeTTest, DifferenceModeSAD')

        #--- Imports (the one currently active partition module)
        #
        # FIXME: This maintains our import list always up-to-date (purging stale imports).
        #        However, someone appends a COPY of it into AttackScriptGen.utilList,
        #        effectively deafeating the intent.

        if hasattr(self, "partition_import") and self.partition_import is not None:
            self.importsRemove(self.partition_import)
        self.partition_import = "from %s import %s" % (partMethod.__module__, partMethod.__name__)
        self.importsAppend(self.partition_import)

        #---- ACTION: Display

        self.addGroup("displayPartitionStats")
        self.addVariable('displayPartitionStats', 'ted', 'self.')
        self.addFunction('displayPartitionStats', 'setTraceSource', 'UserScript.traces', obj='ted')
        self.addFunction('displayPartitionStats', 'parent.getProgressIndicator', '', 'progressBar', obj='ted')
        self.addFunction('displayPartitionStats', 'partObject.setPartMethod', partMethodStr, obj='ted')
        self.addFunction('displayPartitionStats', 'initPartitionFromAttack', 'userscript=self, partObject=ted.partObject', obj='ted')
        self.addFunction('displayPartitionStats', 'partObject.generatePartitions',
                            'saveFile=False, loadFile=False, tRange=%s' % traceRangeStr,
                            'partData', obj='ted')
        self.addFunction('displayPartitionStats', 'generatePartitionStats',
                            'partitionData={"partclass":%s, "partdata":partData}, saveFile=False, progressBar=progressBar, tRange=%s' %
                            (partMethodStr, traceRangeStr),
                            'partStats', obj='ted')
        self.addFunction('displayPartitionStats', 'generatePartitionDiffs',
                            '%s, statsInfo={"partclass":%s, "stats":partStats}, saveFile=False, loadFile=False, progressBar=progressBar'%
                            (diffMethodStr, partMethodStr),
                            'partDiffs', obj='ted')
        self.addFunction('displayPartitionStats', 'displayPartitions', 'differences={"partclass":%s, "diffs":partDiffs}' % partMethodStr, obj='ted')
        self.addFunction('displayPartitionStats', 'poi.setDifferences', 'partDiffs', obj='ted')
        self.addFunction('displayPartitionStats', 'hide', '', '', obj='progressBar')

        #---- ACTION: Keeloq

        self.addGroup("displayKeeloqStats")
        self.addVariable('displayKeeloqStats', 'ted', 'self.')
        self.addFunction('displayKeeloqStats', 'setTraceSource', 'UserScript.traces', obj='ted')
        self.addFunction('displayKeeloqStats', 'parent.getProgressIndicator', '', 'progressBar', obj='ted')
        self.addFunction('displayKeeloqStats', 'partObject.setPartMethod', partMethodStr, obj='ted')
        self.addFunction('displayKeeloqStats', 'initPartitionFromAttack', 'userscript=self, partObject=ted.partObject', obj='ted')
        self.addFunction('displayKeeloqStats', 'generatePartitionStats_KEELOQ',
                            'partitionData={"partclass":%s} ,saveFile=False, progressBar=progressBar, tRange=%s' % (partMethodStr, traceRangeStr),
                            'partStats', obj='ted')
        self.addFunction('displayKeeloqStats', 'generatePartitionDiffs',
                            '%s, statsInfo={"partclass":%s, "stats":partStats}, saveFile=False, loadFile=False, progressBar=progressBar'%
                            (diffMethodStr, partMethodStr),
                            'partDiffs', obj='ted')
        self.addFunction('displayKeeloqStats', 'displayPartitions', 'differences={"partclass":%s, "diffs":partDiffs}' % partMethodStr, obj='ted')
        self.addFunction('displayKeeloqStats', 'poi.setDifferences', 'partDiffs', obj='ted')
        self.addFunction('displayKeeloqStats', 'hide', '', '', obj='progressBar')

        #---- ACTION: Calc POI

        ##Points of Interest
        ptrng = self.findParam(["Points of Interest",'poi-pointrng']).getValue()
        self.addGroup("findPOI")
        self.addVariable('findPOI', 'ted', 'self.')
        self.addFunction('findPOI', 'poi.calcPOI', 'numMax=%d, pointRange=(%d, %d), minSpace=%d' % (
                            self.findParam(["Points of Interest",'poi-nummax']).getValue(),
                            ptrng[0], ptrng[1],
                            self.findParam(["Points of Interest",'poi-minspace']).getValue()),
                          obj='ted')

        #Check if this updateScript was called as a result of showing the TraceExplorer window
        if ignored == "traceexplorer_show":
            self._autoscript_init = True


    #--- Allow ATTACK module to pass GUI config down to PARTITION method
    #
    #    Useful to interact with a partition method and test ideas manually.
    #
    #    This is a trampoline function.  We mean to call the attack, but it's difficult to test
    #    for presence of the necessary API inside of auto-generated scripts, so we do it here.
    #
    #    TODO: The partition method API could be enhanced by letting it add parameters right
    #          into the TraceExplorer dock.

    def initPartitionFromAttack(self, userscript=None, partObject=None):
        # TODO: often partObject==self, redundant?
        attack = userscript.cwagui.attackScriptGen.getAttack()
        if (attack is not None) and hasattr(attack, "initPartitionFromAttack"):
            self.partConfig = attack.initPartitionFromAttack(userscript, partObject)
            # retain a copy of the latest config for our own use
        else:
            self.partConfig = None

    #---

    def generatePartitionStats_KEELOQ(self, partitionData={"partclass":None, "partconfig":None}, saveFile=False, loadFile=False,  tRange=(0, -1), progressBar=None):

        partClass = partitionData["partclass"]

        #--- read config

        config = None
        if hasattr(partitionData, 'partconfig') and (partitionData["partconfig"] is not None):
            config = partitionData["partconfig"]
        elif hasattr(self, 'partConfig'):
            config = self.partConfig

        if config is not None:
            maxdepth   = config['depth']
            round528   = config['round528']
            roundwidth = config['roundwidth']
        else:
            maxdepth   = 1
            round528   = 1
            roundwidth = 1

        print "generatePartitionStats_KEELOQ(): Using depth=%d round528=%d width=%d" % (maxdepth, round528, roundwidth)

        #---

        allStats = None

        # we'll be changing values, so we make a copy
        config = config.copy() if (config is not None) else {}

        for round in range(0, max(maxdepth,1)):

            #--- prepare

            depth      = round+1

            roundStart = round528 - (round * roundwidth)
            roundStop  = roundStart + roundwidth

            factor     = 2**(maxdepth-depth)

            print "round=%d depth=%d maxdepth=%d factor=%d" % (round, depth, maxdepth, factor)

            #--- probe at current depth

            config['depth'] = depth

            partData  = self.partObject.generatePartitions(saveFile=saveFile, loadFile=loadFile, tRange=tRange, partitionConfig=config)

            partStats = self.generatePartitionStats(partitionData={"partclass":partClass, "partdata":partData},
                        saveFile=saveFile, loadFile=loadFile, tRange=tRange, progressBar=progressBar, pointRange=(roundStart, roundStop))

            # print "generatePartitionStats gave numKeys=%d numPartitions=%d" % (len(partStats["mean"]), len(partStats["mean"][0]))

            #--- append to previous probe results

            if factor > 1:
                partStats = self.inflatePartitionStats(partStats, factor=factor, interleave=False)
                # print "inflated with factor=%d to numKeys=%d numPartitions=%d" % (factor, len(partStats["mean"]), len(partStats["mean"][0]))

            if allStats == None:
                # print "append mode: USE round=%d depth=%d pos=(%d,%d) factor=%d" % (round, depth, roundStart, roundStop, factor)
                allStats = partStats
            else:
                # print "append mode: APPEND round=%d depth=%d pos=(%d,%d) factor=%d" % (round, depth, roundStart, roundStop, factor)
                allStats = self.appendPartitionStats(partStats, allStats)
                # print "appended, resulting in numKeys=%d numPartitions=%d" % (len(allStats["mean"]), len(allStats["mean"][0]))

        return allStats


    #--- Append two STATS arrays
    #
    #    The two arrays must have identical layout, except for the number of samples covered within.
    #    Returns the new merged STATS array, although the current implementation may damage the stats1 input.
    #    Recommended use case: stats1 = append(stats1, stats2)

    def appendPartitionStats(self, stats1=None, stats2=None):

        if len(stats1["mean"]) != len(stats2["mean"]):
            print "ERROR: appendPartitionStats() incompatible numKeys %d vs %d" % (len(stats1["mean"]), len(stats2["mean"]))
            return stats1

        if len(stats1["mean"][0]) != len(stats2["mean"][0]):
            print "ERROR: appendPartitionStats() incompatible numPartitions %d vs %d" % (len(stats1["mean"][0]), len(stats2["mean"][0]))
            return stats1

        numKeys       = len(stats1["mean"])
        numPartitions = len(stats1["mean"][0])

        for bnum in range(0, numKeys):
            for i in range(0, numPartitions):

                #--- convert "number" from scalar to array
                #
                #    Normal partitioning works on whole traces, so "number" (sample count for t-test) may be a scalar.
                #    With "sliced" partitioning, the number of samples at one point may be different than at another
                #    point.  Therefore we need to make sure that "number" is converted to an array of corresponding
                #    length, and also that subsequent operations (such as t-test) don't choke on it.

                len1 = len(stats1["mean"][bnum][i])
                len2 = len(stats2["mean"][bnum][i])
                num1 = stats1["number"][bnum][i]
                num2 = stats2["number"][bnum][i]

                if not isinstance(num1, (list, tuple, np.ndarray)):
                    num1 = np.full_like(stats1["mean"][bnum][i], num1)
                if not isinstance(num2, (list, tuple, np.ndarray)):
                    num2 = np.full_like(stats2["mean"][bnum][i], num2)

                #--- append the arrays

                stats1["mean"    ][bnum][i] = np.append(stats1["mean"    ][bnum][i], stats2["mean"    ][bnum][i])
                stats1["variance"][bnum][i] = np.append(stats1["variance"][bnum][i], stats2["variance"][bnum][i])
                stats1["number"  ][bnum][i] = np.append(num1, num2)

        return stats1

    #--- Inflate a STATS array
    #
    #    Grow the "numKeys" (or "bnum") dimension of the array by an integer factor.
    #    Useful to match the layout to another given array with higher numKeys (eg.
    #    in a binary tree where numKeys doubles with each iteration).
    #
    #    The array content can be resized in two ways:
    #
    #    interleave=False: Content is repeated as block, several times.  The first
    #                      section of the output will look same as the input.
    #
    #    interleave=True:  Each element is repeated several times, then the next
    #                      element.
    #
    #    --------------->  NOTE: interleave==True is not yet implemented !!!

    def inflatePartitionStats(self, stats=None, factor=1, interleave=False):

        inKeys = len(stats["mean"])

        A_k  = []
        Q_k  = []
        ACnt = []

        if not interleave:

            # repeat blocks of all elements

            outKey = 0
            for clone in range(0, factor):
                for inKey in range(0, inKeys):
                    A_k.append([])
                    Q_k.append([])
                    ACnt.append([])
                    for i in range(0, len(stats["mean"][inKey])):
                        A_k[outKey].append(stats["mean"][inKey][i])
                        Q_k[outKey].append(stats["variance"][inKey][i])
                        ACnt[outKey].append(stats["number"][inKey][i])
                    outKey += 1

        else:

            # repeat each element individually

# FIXME: broken, the outkey index is missing!  See above for how it has to be done
            print "FIXME: Executing broken code path in inflatePartitionStats(): interleave==True"
            outKey = 0
            for inKey in range(0, inKeys):
                for clone in range(0, factor):
                    A_k.append(stats["mean"][inKey])
                    Q_k.append(stats["variance"][inKey])
                    ACnt.append(stats["number"][inKey])
                    outKey += 1

        return {"mean":A_k, "variance":Q_k, "number":ACnt}

    #---

    def generatePartitionStats(self, partitionData={"partclass":None, "partdata":None}, saveFile=False, loadFile=False,  tRange=(0, -1), progressBar=None, pointRange=(0,-1)):

        traces = self._traces

        if tRange[1] < 0:
            tRange = (tRange[0], traces.numTraces() + 1 + tRange[1])

        if partitionData["partdata"] is not None:
            self.numKeys  = len(partitionData["partdata"])
            numPartitions = len(partitionData["partdata"][0])
        else:
            print "WARNING: generatePartitionStats() deprecated code path should never execute"
            # MARC: Deprecated because it replaces the method instance and all associated config with it.
            #       Should never be necessary anyway, because we can extract the required from partdata.
            self.partObject.setPartMethod(partitionData["partclass"])
            self.numKeys  = len(self.partObject.partMethod.getPartitionNum(traces, 0))
            numPartitions = self.partObject.partMethod.getNumPartitions()
        # print "generatePartitionStats: using numKeys=%d numPartitions=%d" % (self.numKeys, numPartitions)

        pointStart = max(pointRange[0], 0)
        pointStop  = pointRange[1] if (pointRange[1] >= 0) else traces.numPoints() + 1 + pointRange[1]
        pointStart = min(pointStart, pointStop)
        numPoints  = pointStop - pointStart

        if loadFile:
            cfgsecs = self.api.project().getDataConfig(sectionName="Trace Statistics", subsectionName="Total Trace Statistics")
            foundsecs = []
            for cfg in cfgsecs:
                desiredsettings = {}
                desiredsettings["tracestart"] = tRange[0]
                desiredsettings["traceend"] = tRange[1]
                desiredsettings["partitiontype"] = self.partObject.partMethod.__class__.__name__
                if self.api.project().checkDataConfig(cfg, desiredsettings):
                    foundsecs.append(cfg)
        else:
            foundsecs = []

        if len(foundsecs) > 1:
            IOError("Too many sections!!!")
        elif len(foundsecs) == 1:
            fname = self.api.project().convertDataFilepathAbs(foundsecs[0]["filename"])
            stats = np.load(fname)
        else:
            # Array to hold average + stddev of all traces/partitions
            A_k = []
            A_j = []
            Q_k = []
            dataArrays = [A_k, A_j, Q_k]
            ACnt = []
            for bnum in range(0, self.numKeys):
                for d in dataArrays:
                    d.append([])
                ACnt.append([])
                for i in range(0, numPartitions):
                    for d in dataArrays:
                        d[bnum].append(np.zeros(numPoints))
                    ACnt[bnum].append(0)

            # Get segment list
            segList = traces.getSegmentList()

            if progressBar:
                progressBar.setWindowTitle("Phase 1: Trace Statistics")
                progressBar.setMaximum(bnum)  # len(segList['offsetList']) * self.numKeys)
                progressBar.show()

            # TODO: Double-check this fix
            # for tsegn, segtrace in enumerate(segList['offsetList']):
            tsegn = 0
            if progressBar: progressBar.setText("Segment %d" % tsegn)

            # Average data needs to be calculated
            # Require partition list
            partData = partitionData["partdata"]


            # print "Calculating Average + Std-Dev"
            # Std-Dev calculation:
            # A[0] = 0
            # A[k] = A[k-1] + (x[k] - A[k-1]) / k
            # Q[0] = 0
            # Q[k] = Q[k-1] + (x[k] - A[k-1])(x[k] - A[k])
            for bnum in range(0, self.numKeys):
                if progressBar:
                    progressBar.updateStatus(tsegn * self.numKeys + bnum)
                    if progressBar.wasAborted():
                        break
                for i in range(0, numPartitions):
                    util.updateUI()
                    tlist = partData[bnum][i]
                    if len(tlist) > 0:
                        for tnum in tlist:
                            # MARC bugfix: trace==0 was never used
                            if tnum >= tRange[0] and tnum < tRange[1]:
                                t = traces.getTrace(tnum)[pointStart:pointStop]
                                ACnt[bnum][i] += 1
                                A_k[bnum][i] = A_k[bnum][i] + ((t - A_j[bnum][i]) / ACnt[bnum][i])
                                Q_k[bnum][i] = Q_k[bnum][i] + ((t - A_j[bnum][i]) * (t - A_k[bnum][i]))
                                A_j[bnum][i] = A_k[bnum][i]

            if progressBar and progressBar.wasAborted():
                progressBar.hide()
                return

            # Finally get variance
            for bnum in range(0, self.numKeys):
                    for i in range(0, numPartitions):
                        # TODO: Should be using population variance or sample variance (e.g. /n or /n-1)?
                        #      Since this is taken over very large sample sizes I imagine it won't matter
                        #      ultimately.
                        # MARC: (from Wiki) The t-distribution with n − 1 degrees of freedom is the sampling
                        #       distribution of the t-value when the samples consist of independent
                        #       identically distributed observations from a normally distributed population.
                        #       Thus for inference purposes t is a useful "pivotal quantity" in the case
                        #       when the mean and variance are unknown population parameters, in the sense
                        #       that the t-value has then a probability distribution that depends on neither
                        #       mean nor variance.
                        Q_k[bnum][i] = Q_k[bnum][i] / max(ACnt[bnum][i] - 1, 1)

            # Average is in A_k
            stats = {"mean":A_k, "variance":Q_k, "number":ACnt}

            # Wasn't cancelled - save this to project file for future use if requested
            if saveFile:
                if progressBar: progressBar.setText("Saving Mean/Variance Partitions")
                cfgsec = self.api.project().addDataConfig(sectionName="Trace Statistics", subsectionName="Total Trace Statistics")
                cfgsec["tracestart"] = tRange[0]
                cfgsec["traceend"] = tRange[1]
                cfgsec["partitiontype"] = self.partObject.partMethod.__class__.__name__
                fname = self.api.project().getDataFilepath('tracestats-%s-%d-%s.npz' % (cfgsec["partitiontype"], tRange[0], tRange[1]), 'analysis')

                # Save mean/variance for trace
                np.savez(fname["abs"], mean=A_k, variance=Q_k, number=ACnt)
                cfgsec["filename"] = fname["rel"]

        # if progressBar: progressBar.hide()
        return stats

    #---

    def generatePartitionDiffs(self, diffModule, statsInfo={"partclass":None, "stats":None}, saveFile=False, loadFile=False, tRange=(0, -1), progressBar=None):

        traces = self._traces

        if tRange[1] < 0:
            tRange = (tRange[0], traces.numTraces() + 1 + tRange[1])

        # self.partObject.setPartMethod(statsInfo["partclass"])
        # MARC: Deprecated because it replaces the method instance and all associated config with it.

        self.diffObject.setDiffMethod(diffModule)

        # extract layout from input data
        self.numKeys  = len(statsInfo["stats"]["mean"])
        numPartitions = len(statsInfo["stats"]["mean"][0])
        numPoints     = len(statsInfo["stats"]["mean"][0][0])
        # print "generatePartitionDiffs: using numKeys=%d numPartitions=%d" % (self.numKeys, numPartitions)

        foundsecs = []
        if loadFile:
            cfgsecs = self.api.project().getDataConfig(sectionName="Trace Statistics", subsectionName="Partition Differences")
            for cfg in cfgsecs:
                desiredsettings = {}
                desiredsettings["tracestart"] = tRange[0]
                desiredsettings["traceend"] = tRange[1]
                desiredsettings["partitiontype"] = self.partObject.partMethod.__class__.__name__
                desiredsettings["comparetype"] = self.diffObject.mode.moduleName
                if self.api.project().checkDataConfig(cfg, desiredsettings):
                    foundsecs.append(cfg)
        else:
            cfgsecs = []

        if len(foundsecs) > 1:
            IOError("Too many sections!!!")
        elif len(foundsecs) == 1:
            fname = self.api.project().convertDataFilepathAbs(foundsecs[0]["filename"])
            SADList = np.load(fname)
        else:
            if progressBar:
                progressBar.setWindowTitle("Phase 2: Calculating Partition Differences")
                progressBar.setText("Calculating all Differences based on " + self.diffObject.mode.differenceType)
            SADList = self.diffObject.difference(self.numKeys, numPartitions, None, numPoints, statsInfo["stats"], progressBar)

            if saveFile:
                cfgsec = self.api.project().addDataConfig(sectionName="Trace Statistics", subsectionName="Partition Differences")
                cfgsec["tracestart"] = tRange[0]
                cfgsec["traceend"] = tRange[1]
                cfgsec["partitiontype"] = self.partObject.partMethod.__class__.__name__
                cfgsec["comparetype"] = self.diffObject.mode.moduleName
                fname = self.api.project().getDataFilepath('partdiffs-%s-%s-%d-%s.npy' % (cfgsec["partitiontype"], cfgsec["comparetype"], tRange[0], tRange[1]), 'analysis')
                np.save(fname["abs"], SADList)
                cfgsec["filename"] = fname["rel"]

        if progressBar:
            progressBar.updateStatus(progressBar.maximum)
            # progressBar.setWindowTitle('Debug Fail')
            if progressBar.wasAborted():
                return

        self.SADList = SADList
        return SADList

    #---

    def displayPartitions(self, differences={"partclass":None, "diffs":None}, tRange=(0, -1)):
        self.graphDock.show()
        traces = self._traces

        if tRange[1] < 0:
            tRange = (tRange[0], traces.numTraces() + 1 + tRange[1])

        # self.partObject.setPartMethod(differences["partclass"])
        # MARC: Deprecated because it replaces the method instance and all associated config with it.

        self.numKeys = len(differences["diffs"])
        self.SADList = differences["diffs"]

        # Place byte selection option on graph
        if hasattr(self, 'enabledbytes') and len(self.enabledbytes) == self.numKeys:
            pass
        else:
            self.enabledbytes = [True] * self.numKeys

        self.doRedraw = True

        palette_preference = self.findParam('colorpalette').getValue()

        self.byteNumAct = []
        for i in range(0, self.numKeys):
            ql = QToolButton()
            ql.setText('%d' % i)
            color = self.palette.intColor(i, self.numKeys, palette=palette_preference)
            ql.setStyleSheet("color: rgb(%d, %d, %d)" % (color.red(), color.green(), color.blue()))
            qa = QWidgetAction(self.graph)
            qa.setDefaultWidget(ql)
            qa.setStatusTip('%d' % i)
            ql.setCheckable(True)
            ql.setChecked(self.enabledbytes[i])
            ql.clicked[bool].connect(partial(self.setBytePlot, i))
            self.byteNumAct.append(qa)

        byteNumAllOn = QAction('All', self.graph)
        byteNumAllOff = QAction('None', self.graph)
        byteNumAllOn.triggered.connect(partial(self.setByteAll, True))
        byteNumAllOff.triggered.connect(partial(self.setByteAll, False))
        byteNumEven = QAction('Even', self.graph)
        byteNumOdd  = QAction('Odd', self.graph)
        byteNumEven.triggered.connect(partial(self.setByteShowEvenOdd, True))
        byteNumOdd.triggered.connect(partial(self.setByteShowEvenOdd, False))
        byteNumToggle = QAction('Inv', self.graph)
        byteNumToggle.triggered.connect(partial(self.setByteToggle))

        self.bselection.clear()
        self.bselection.addAction(byteNumAllOn)
        self.bselection.addAction(byteNumAllOff)
        self.bselection.addAction(byteNumEven)
        self.bselection.addAction(byteNumOdd)
        self.bselection.addAction(byteNumToggle)
        for i in range(0, self.numKeys):
            self.bselection.addAction(self.byteNumAct[i])
        self.graph.setPersistance(True)

        self.poi.setDifferences(self.SADList)

        self.findParam(["Points of Interest",'poi-pointrng']).setLimits((0, len(self.SADList[0])))
        self.findParam(["Points of Interest",'poi-pointrng']).setValue((0, len(self.SADList[0])))
        self.redrawPlot()

    def runAction(self):
        self.runScriptFunction.emit('TraceExplorerDialog_PartitionDisplay_displayPartitionStats')

    def runAction_Keeloq(self):
        self.runScriptFunction.emit('TraceExplorerDialog_PartitionDisplay_displayKeeloqStats')

    def setTraceSource(self, traces):
        self._traces = traces
        self.partObject.setTraceSource(self._traces)
