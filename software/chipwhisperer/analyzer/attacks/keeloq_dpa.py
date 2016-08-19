#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, MARC
# All rights reserved.
#
#=================================================

import sys
from chipwhisperer.common.utils import pluginmanager
from ._base import AttackBaseClass
from ._generic_parameters import AttackGenericParameters
from chipwhisperer.common.ui.ProgressBar import ProgressBar
from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI


class Keeloq_DPA(AttackBaseClass, AttackGenericParameters):
    """Correlation Power Analysis Attack"""
    _name = "Keeloq DPA (hardware encoders)"

    def __init__(self):
        AttackBaseClass.__init__(self)
        self.attack = None

        algos = pluginmanager.getPluginsInDictFromPackage("chipwhisperer.analyzer.attacks.cpa_algorithms", False, False)
        self.getParams().addChildren([
            {'name':'Keeloq depth (rounds)',  'key':'keeloq_round',     'type':'int', 'value':4, 'default':4, 'limits':(0, 528), 'action':self.updateScript},
            {'name':'Keeloq keystream',       'key':'keeloq_keystream', 'type':'text', 'value':'', 'default':'', 'action':self.updateScript},
            {'name':'Round 528 (pos)',        'key':'keeloq_pos_528',   'type':'int', 'value':204, 'default':204, 'action':self.updateScript},
            {'name':'Round width (pts)',      'key':'keeloq_width',     'type':'int', 'value':2,   'default':2,   'action':self.updateScript},
            {'name':'Algorithm', 'key':'CPA_algo', 'type':'list',  'values':algos, 'value':algos["Progressive"], 'action':self.updateAlgorithm}, #TODO: Should be called from the AES module to figure out # of bytes

        ])
        AttackGenericParameters.__init__(self)
        self.setAnalysisAlgorithm(self.findParam('CPA_algo').getValue(), None, None)
        self.updateBytesVisible()
        self.updateScript()

    def updateAlgorithm(self, parameter):
        self.setAnalysisAlgorithm(parameter.getValue(), None, None)
        self.updateBytesVisible()
        self.updateScript()

    def setHardwareModel(self, model):
        self.numsubkeys = model.numSubKeys
        self.updateBytesVisible()
        self.updateScript()

    def setAnalysisAlgorithm(self, analysisAlgorithm, hardwareModel, leakageModel):
        if self.attack is not None:
            self.attack.getParams().remove()
        self.attack = analysisAlgorithm(hardwareModel, leakageModel)

        try:
            self.attackParams = self.attack.paramList()[0]
        except:
            self.attackParams = None

        if hasattr(self.attack, 'scriptsUpdated'):
            self.attack.scriptsUpdated.connect(self.updateScript)

        self.getParams().append(self.attack.getParams())

    def updateScript(self, _=None):
        self.importsAppend("from %s import %s" % (self.__class__.__module__, self.__class__.__name__))

        analysAlgoStr = self.attack.__class__.__name__
        hardwareStr = self.findParam(['Hardware Model','hw_algo']).getValue().__name__
        leakModelStr = hardwareStr + "." + self.findParam(['Hardware Model','hw_leak']).getValue()
#MARC !!! ^^^ !!! how to read parameters from subgroups

        self.importsAppend("from %s import %s" % (sys.modules[self.attack.__class__.__module__].__name__, analysAlgoStr))
        self.importsAppend("import %s" % hardwareStr)

        if hasattr(self.attack, '_smartstatements'):
            self.mergeGroups('init', self.attack, prefix='attack')

        self.addFunction("init", "setKeeloqRound", "round=%d" % self.findParam('keeloq_round').getValue())
        self.addFunction("init", "setKeeloqKeystream", "keystream='%s'" % self.findParam('keeloq_keystream').getValue())
        self.addFunction("init", "setKeeloqTiming", "round528=%d, roundwidth=%d" % (self.findParam('keeloq_pos_528').getValue(), self.findParam('keeloq_width').getValue()))

        self.addFunction("init", "setAnalysisAlgorithm", "%s,%s,%s" % (analysAlgoStr, hardwareStr, leakModelStr), loc=0)
        self.addFunction("init", "setTraceSource", "UserScript.traces, blockSignal=True", loc=0)


    def setKeeloqRound(self, round=0):
        # print "KEELOQ_ROUND CALLED: %d" % round
        self.keeloq_round = round


    def setKeeloqKeystream(self, keystream=''):
        # print "KEELOQ_KEYSTREAM CALLED: %s" % keystream
        self.keeloq_keystream = keystream


    def setKeeloqTiming(self, round528=0, roundwidth=0):
        self.keeloq_round528   = round528
        self.keeloq_roundwidth = roundwidth


    def initPartitionFromAttack(self, userscript=None):
        # print "ARRIVED at ATTACK !!!!!!!!!"

        rounds = userscript.cwagui.attackScriptGen.attackParams.getChild(self._name).getChild('keeloq_round').getValue()
        # print "Keeloq rounds cfg: %d" % rounds
        CWCoreAPI.getInstance().kludge_keeloq_rounds = rounds

        keystream = userscript.cwagui.attackScriptGen.attackParams.getChild(self._name).getChild('keeloq_keystream').getValue()
        # print "Keeloq stream cfg: '%s'" % keystream
        CWCoreAPI.getInstance().kludge_keeloq_keystream = keystream

        round528 = userscript.cwagui.attackScriptGen.attackParams.getChild(self._name).getChild('keeloq_pos_528').getValue()
        CWCoreAPI.getInstance().kludge_keeloq_round528   = round528
        roundwidth = userscript.cwagui.attackScriptGen.attackParams.getChild(self._name).getChild('keeloq_width').getValue()
        CWCoreAPI.getInstance().kludge_keeloq_roundwidth = roundwidth


    def processKnownKey(self, inpkey):
        if inpkey is None:
            return None

        if hasattr(self.attack, 'processKnownKey'):
            return self.attack.processKnownKey(inpkey)
        else:
            return inpkey

    def processTraces(self):
        progressBar = ProgressBar("Analysis in Progress", "Attacking with %s:" % self._name)
        with progressBar:
            self.attack.setTargetBytes(self.targetBytes())
            self.attack.setReportingInterval(self.getReportingInterval())
            self.attack.getStatistics().clear()
            self.attack.setStatsReadyCallback(self.sigAnalysisUpdated.emit)

            self.sigAnalysisStarted.emit()
            for itNum in range(1, self.getIterations()+1):
                startingTrace = self.getTracesPerAttack() * (itNum - 1) + self.getTraceStart()
                endingTrace = startingTrace + self.getTracesPerAttack() - 1
                #TODO:  pointRange=self.TraceRangeList[1:17]
                self.attack.addTraces(self.getTraceSource(), (startingTrace, endingTrace), progressBar, pointRange=self.getPointRange())
                if progressBar and progressBar.wasAborted():
                    return

        self.sigAnalysisDone.emit()

    def getStatistics(self):
        return self.attack.getStatistics()

