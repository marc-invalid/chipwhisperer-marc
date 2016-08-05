#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 MARC
# All rights reserved.
#
# Author: MARC


from chipwhisperer.common.results.base import ResultsBase
from ._base import PreprocessingBase

from datetime import datetime


class CacheRam(PreprocessingBase):
    _name = "Cache: RAM"
    _description = "getTrace() results kept in RAM until change signal"


    def __init__(self, traceSource=None):
        PreprocessingBase.__init__(self, traceSource)

#        self.params.addChildren([
#            {'name':'(rfu) Use HDD',           'key':'use_hdd', 'type':'bool', 'default':False, 'value':False, 'action':self.updateScript}
#        ])

        self.constructed = str(datetime.now())
        self.traces = None

        self.stats_load    = 0
        self.stats_changed = 0
        self.stats_hit     = 0

        self.debug_print   = False

        self.updateScript()
        self.updateLimits()
        self.sigTracesChanged.connect(self.updateLimits)


    def updateLimits(self):
        self.traces = None
        self.stats_changed += 1
        if self.debug_print: print "Cache L=%05d H=%05d CH=%03d %s: connect" % (self.stats_load, self.stats_hit, self.stats_changed, self.constructed)
        return


    def updateScript(self, _=None):
        self.addFunction("init", "setEnabled", "%s" % self.findParam('enabled').getValue())
        self.updateLimits()


    def getTrace(self, n):
        if self.enabled:

            if self.traces is None:
                self.traces = [None] * self._traceSource.numTraces()

            if self.traces[n] is None:
                self.stats_load += 1
                self.traces[n] = self._traceSource.getTrace(n)
                if self.debug_print: print "Cache L=%05d H=%05d CH=%03d %s: fetch" % (self.stats_load, self.stats_hit, self.stats_changed, self.constructed)
            else:
                self.stats_hit  += 1
                if self.debug_print: print "Cache L=%05d H=%05d CH=%03d %s: hit" % (self.stats_load, self.stats_hit, self.stats_changed, self.constructed)

            return self.traces[n]

        else:
            return self._traceSource.getTrace(n)


    def init(self):
        self.traces = None
        self.stats_changed += 1
        if self.debug_print: print "Cache L=%05d H=%05d CH=%03d %s: init" % (self.stats_load, self.stats_hit, self.stats_changed, self.constructed)
        return


