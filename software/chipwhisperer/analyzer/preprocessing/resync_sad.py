#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014, NewAE Technology Inc
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
#
#    Date         Author                Changes
#    -----------  --------------------  -----------------------------------
#    21-Jun-2016  marc                  Added "Transparent Filter" to affect registration without altering trace data

import numpy as np

from chipwhisperer.common.results.base import ResultsBase
from ._base import PreprocessingBase
from scipy import signal


class ResyncSAD(PreprocessingBase):
    _name = "Resync: Sum-of-Difference"
    _description = "Minimizes the 'Sum of Absolute Difference' (SAD), also known as 'Sum of Absolute Error'. Uses "\
                  "a portion of one of the traces as the 'reference'. This reference is then slid over the 'input "\
                  "window' for each trace, and the amount of shift resulting in the minimum SAD criteria is selected "\
                  "as the shift amount for that trace."

    def __init__(self, traceSource=None):
        PreprocessingBase.__init__(self, traceSource)

        self.importsAppend("import scipy as sp")
        self.filterGenerator = None

        self.rtrace = 0
        self.debugReturnSad = False
        self.ccStart = 0
        self.ccEnd = 1
        self.wdStart = 0
        self.wdEnd = 1

        self.params.addChildren([
            {'name':'Ref Trace', 'key':'reftrace', 'type':'int', 'value':0, 'action':self.updateScript},
            {'name':'Reference Points', 'key':'refpts', 'type':'rangegraph', 'graphwidget':ResultsBase.registeredObjects["Trace Output Plot"],
                                                                     'action':self.updateScript, 'value':(0, 0), 'default':(0, 0)},

            {'name':'Input Window', 'key':'windowpt', 'type':'rangegraph', 'graphwidget':ResultsBase.registeredObjects["Trace Output Plot"],
                                                                     'action':self.updateScript, 'value':(0, 0), 'default':(0, 0)},
            # {'name':'Valid Limit', 'type':'float', 'value':0, 'step':0.1, 'limits':(0, 10), 'set':self.setValidLimit},
            # {'name':'Output SAD (DEBUG)', 'type':'bool', 'value':False, 'set':self.setOutputSad},

            {'name':'Transparent Filter', 'key':'filtergenerator', 'type':'list', 'values':{"None":"None", "Butterworth":"sp.signal.butter"}, 'default':"None", 'value':"None", 'action':self.updateScript},
            {'name':'  Type', 'key':'filtertype', 'type':'list', 'values':["low", "high", "bandpass", "bandstop"], 'default':'low', 'value':'low', 'action':self.updateScript},
            {'name':'  Freq #1 (0-1)', 'key':'filterfreq1', 'type':'float', 'limits':(0, 1), 'step':0.05, 'default':0.1, 'value':0.1, 'action':self.updateScript},
            {'name':'  Freq #2 (0-1)', 'key':'filterfreq2', 'type':'float', 'limits':(0, 1), 'step':0.05, 'default':0.8, 'value':0.8, 'action':self.updateScript},
            {'name':'  Order', 'key':'filterorder', 'type':'int', 'limits':(1, 32), 'default':5, 'value':5, 'action':self.updateScript},
            {'name':'  Alter trace data', 'key':'filtervisible', 'type':'bool', 'default':True, 'value':True, 'action':self.updateScript}

        ])
        self.updateScript()
        self.updateLimits()
        self.sigTracesChanged.connect(self.updateLimits)

    def updateLimits(self):
        if self._traceSource:
            self.findParam('refpts').setLimits((0, self._traceSource.numPoints()-1))
            self.findParam('windowpt').setLimits((0, self._traceSource.numPoints()-1))

    def updateScript(self, _=None):
        self.addFunction("init", "setEnabled", "%s" % self.findParam('enabled').getValue())

        refpt = self.findParam('refpts').getValue()
        windowpt = self.findParam('windowpt').getValue()
        windowpt = (min(windowpt[0],refpt[0]), max(windowpt[1],refpt[1]))
        self.findParam('windowpt').setValue(windowpt, blockAction=True)

        self.addFunction("init", "setReference", "rtraceno=%d, refpoints=(%d,%d), inputwindow=(%d,%d)" %
                         (self.findParam('reftrace').getValue(), refpt[0], refpt[1], windowpt[0], windowpt[1]))

        self.updateLimits()

	filtergenerator = self.findParam('filtergenerator').getValue()
        self.addFunction("init", "setFilterGenerator", filtergenerator)

        # remove stale filter args (optional ones that are use only by some filter generators)
        self.delFunction("init", "setFilterParams")
        self.delFunction("init", "setFilterVisible")

	# describe BUTTERWORTH filter

	if filtergenerator == "sp.signal.butter":

	    filtertype  = self.findParam('filtertype').getValue()
            filterfreq1 = self.findParam('filterfreq1').getValue()
            filterfreq2 = self.findParam('filterfreq2').getValue()

	    self.findParam('filtertype').show()
	    self.findParam('filterfreq1').show()
	    self.findParam('filterorder').show()
	    self.findParam('filtervisible').show()

            if filtertype == "bandpass":
                self.findParam('filterfreq2').show()
                filterfreqs = "(%f, %f)" % (filterfreq1, filterfreq2)
            elif filtertype == "bandstop":
                self.findParam('filterfreq2').show()
                filterfreqs = "(%f, %f)" % (filterfreq1, filterfreq2)
            else:
                self.findParam('filterfreq2').hide()
                filterfreqs = "%f" % filterfreq1

            self.addFunction("init", "setFilterParams", "type='%s', freq=%s, order=%d" % (
                                filtertype,
                                filterfreqs,
                                self.findParam('filterorder').getValue()
                            ))

            self.addFunction("init", "setFilterVisible", self.findParam('filtervisible').getValue())

        else:
	    self.findParam('filtertype').hide()
	    self.findParam('filterfreq1').hide()
	    self.findParam('filterfreq2').hide()
	    self.findParam('filterorder').hide()
	    self.findParam('filtervisible').hide()

    def setFilterGenerator(self, filtergenerator=None):
        self.filterGenerator = filtergenerator

    def setFilterParams(self, type='low', freq=0.8, order=5):
        if self.filterGenerator != None:
            self.b, self.a = self.filterGenerator(order, freq, type)

    def setFilterVisible(self, visible=True):
        self.filterVisible = visible

    def setReference(self, rtraceno=0, refpoints=(0, 0), inputwindow=(0, 0)):
        self.rtrace = rtraceno
        self.wdStart = inputwindow[0]
        self.wdEnd = inputwindow[1]
        self.ccStart = refpoints[0]
        self.ccEnd = refpoints[1]
        self.init()

    def setOutputSad(self, enabled):
        self.debugReturnSad = enabled
   
    def getTrace(self, n):
        if self.enabled:
            trace = self._traceSource.getTrace(n)
            if trace is None:
                return None

            if self.filterGenerator != None:
                filttrace = signal.lfilter(self.b, self.a, trace)
                sad = self.findSAD(filttrace)
                if self.filterVisible == True:
                    trace = filttrace
            else:
                sad = self.findSAD(trace)
            
            if self.debugReturnSad:
                return sad
            
            if len(sad) == 0:
                return None            
            
            newmaxloc = np.argmin(sad)
            maxval = min(sad)
            #if (maxval > self.refmaxsize * 1.01) | (maxval < self.refmaxsize * 0.99):
            #    return None
            
            if maxval > self.maxthreshold:
                return None
            
            diff = newmaxloc-self.refmaxloc
            if diff < 0:
                trace = np.append(np.zeros(-diff), trace[:diff])
            elif diff > 0:
                trace = np.append(trace[diff:], np.zeros(diff))
            return trace
        else:
            return self._traceSource.getTrace(n)
   
    def init(self):
        try:
            self.calcRefTrace(self.rtrace)
        #Probably shouldn't do this, but deals with user enabling preprocessing
        #before trace management setup
        except ValueError:
            pass
        
    def findSAD(self, inputtrace):
        reflen = self.ccEnd-self.ccStart
        sadlen = self.wdEnd-self.wdStart
        sadarray = np.empty(sadlen-reflen)
        
        for ptstart in range(self.wdStart, self.wdEnd-reflen):
            #Find SAD        
            sadarray[ptstart-self.wdStart] = np.sum(np.abs(inputtrace[ptstart:(ptstart+reflen)] - self.reftrace))
            
        return sadarray
        
    def calcRefTrace(self, tnum):
        if self.enabled == False:
            return
        
        trace = self._traceSource.getTrace(tnum);
        if self.filterGenerator != None:
            trace = signal.lfilter(self.b, self.a, trace)

        self.reftrace = trace[self.ccStart:self.ccEnd]
        sad = self.findSAD(trace)
        self.refmaxloc = np.argmin(sad)
        self.refmaxsize = min(sad)
        self.maxthreshold = np.mean(sad)
