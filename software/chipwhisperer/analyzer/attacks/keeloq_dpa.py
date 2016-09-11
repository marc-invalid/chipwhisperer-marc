#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, MARC
# All rights reserved.
#
#=================================================

import sys
from chipwhisperer.common.utils import pluginmanager
from chipwhisperer.common.ui.ProgressBar import ProgressBar
from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI

from ._base import AttackBaseClass
from ._keeloq_parameters import AttackKeeloqParameters
import chipwhisperer.analyzer.attacks.models.keeloq as models_keeloq


class Keeloq_DPA(AttackBaseClass, AttackKeeloqParameters):
    """Differential Power Analysis Attack"""
    _name = "Keeloq DPA"
    _description = "Differential power analysis for Keeloq"

    def __init__(self):
        AttackBaseClass.__init__(self)
        self.attack = None

        algos = pluginmanager.getPluginsInDictFromPackage("chipwhisperer.analyzer.attacks.keeloq_dpa_algorithms", False, False)
        self.getParams().addChildren([

            {'name':'Crypto Algorithm',       'key':'hw_algo', 'type':'list', 'values':{'Keeloq':models_keeloq}, 'value':models_keeloq, 'action':self.updateScript},
            {'name':'Attack Algorithm',       'key':'attack_algo', 'type':'list', 'values':algos, 'value':algos[algos.keys()[0]], 'action':self.updateAlgorithm},
            {'name':'Leakage Model',          'key':'hw_leak', 'type':'list', 'values':models_keeloq.leakagemodels, 'value':"LEAK_HW_CIPHERTEXT_BIT", 'action':self.updateScript},

            {'name':'Trace Setup', 'key':'tracesetup', 'type':'group'},   # FIXME: "attack runs" makes no sense for our use
            {'name':'Point Setup', 'key':'pointsetup', 'type':'group'},   # TODO: redundant when round timing is known

            {'name':'Timing Setup (optional for some uses)', 'key':'keeloq_timing', 'type':'group', 'children':[
                # {'name': '', 'type': 'label', 'value':"Position of rounds within traces", 'readonly': True},
                {'name':'Round 528 (pos)',     'key':'round528',   'type':'int', 'value':301, 'default':301, 'action':self.updateScript},
                {'name':'Round width (samples)',    'key':'roundwidth',     'type':'int', 'value':3,   'default':3,   'action':self.updateScript},
            ]},
            {'name':'Analysis Options (for Partition modes)', 'key':'keeloq_analysis', 'type':'group', 'children':[
                {'name':'Depth (rounds)',  'key':'depth',     'type':'int',
                         'help': "Analysis depth (rounds):\n"\
                                 "------------------------\n\n"
                                 "Specifies how many rounds deep to analyze. "\
                                 "Used by certain partition modes in Trace Explorer.\n"\
                                 "\n"\
                                 "Analysis starts with the ciphertext and removes any known keystream. "\
                                 "It will then go N rounds backwards, opening a window of N unknown keybits.\n"\
                                 "\n"\
                                 "**Usage in partition mode: FIXME**\n"\
                                 "\n"\
                                 "Show correlation for each of the 2^N possible keystreams. "\
                                 "Trace number corresponds to the keystream used (ex. trace=5 keystream=0101).\n"\
                                 "\n"\
                                 "NOTE: The cipher applies the keystream over time, not instantly.\n"\
                                 "\n",
                                     'value':4, 'default':4, 'limits':(0, 8), 'action':self.updateScript},
                {'name':'Known keystream',          'key':'keystream', 'type':'text', 'value':'', 'default':'', 'action':self.updateScript},
            ]},


        ])
        self.findParam('hw_leak').hide()

        AttackKeeloqParameters.__init__(self, hasHardwareModel=False, hasMultipleRuns=False)
        self.setAnalysisAlgorithm(self.findParam('attack_algo').getValue(), None, None)
#        self.updateBytesVisible()
        self.updateScript()

    def updateAlgorithm(self, parameter):
        self.setAnalysisAlgorithm(parameter.getValue(), None, None)
#        self.updateBytesVisible()
        self.updateScript()

    def setHardwareModel(self, model):
        self.numsubkeys = model.numSubKeys
#!        self.updateBytesVisible()
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
        hardwareStr = self.findParam('hw_algo').getValue().__name__
        leakModelStr = hardwareStr + "." + self.findParam('hw_leak').getValue()

        self.importsAppend("from %s import %s" % (sys.modules[self.attack.__class__.__module__].__name__, analysAlgoStr))
        self.importsAppend("import %s" % hardwareStr)

        if hasattr(self.attack, '_smartstatements'):
            self.mergeGroups('init', self.attack, prefix='attack')

        self.addFunction("init", "setAnalysisAlgorithm", "%s,%s,%s" % (analysAlgoStr, hardwareStr, leakModelStr), loc=0)
        self.addFunction("init", "setTraceSource", "UserScript.traces, blockSignal=True", loc=0)

        #--- attack specific config

        keystream_raw = self.findParam(['keeloq_analysis', 'keystream']).getValue()
        keystream     = ''.join(c for c in keystream_raw if c.isalnum())
        # TODO: unify this config reading and sanitizing with the one below in partition init - eg. readToDict() then use

        self.addFunction("init", "setKeeloqAnalysis", "depth=%d, keystream='%s'" %\
                                         (self.findParam(['keeloq_analysis', 'depth']).getValue(),
                                          keystream))

        self.addFunction("init", "setKeeloqTiming", "round528=%d, roundwidth=%d" %\
                                         (self.findParam(['keeloq_timing', 'round528']).getValue(),
                                          self.findParam(['keeloq_timing', 'roundwidth']).getValue()))


    #--- receive config from script (used by ourselves during attack processing)

    def setKeeloqAnalysis(self, depth=0, keystream=''):
        self.keeloq_depth     = depth
        self.keeloq_keystream = keystream

    def setKeeloqTiming(self, round528=0, roundwidth=0):
        self.keeloq_round528   = round528
        self.keeloq_roundwidth = roundwidth


    #--- read config from GUI (used by "friend" partition modes)

    def initPartitionFromAttack(self, userscript=None, partObject=None):

        if (userscript is None) or (partObject is None):
            # invalid args, nothing to do
            return

        if not hasattr(partObject.partMethod, 'setConfig'):
            # config not possible with this method
            return

        #--- forward parameters into partition method

        params = userscript.cwagui.attackScriptGen.attackParams.getChild(self._name)

        keystream_raw = params.getChild(['keeloq_analysis', 'keystream']).getValue()
        keystream     = ''.join(c for c in keystream_raw if c.isalnum())

        config = {}
        config['keystream']  = keystream
        config['depth']      = params.getChild(['keeloq_analysis', 'depth']).getValue()
        config['round528']   = params.getChild(['keeloq_timing',   'round528']).getValue()
        config['roundwidth'] = params.getChild(['keeloq_timing',   'roundwidth']).getValue()

        print "Configuring partition method with attack parameters: %s" % str(config)
        partObject.partMethod.setConfig(config)

        return config


    #---

    def processKnownKey(self, inpkey):
        if inpkey is None:
            return None

        if hasattr(self.attack, 'processKnownKey'):
            return self.attack.processKnownKey(inpkey)
        else:
            return inpkey

    #--- Run the attack

    def processTraces(self):
        # print "Running attack: %s" % self._name

        self.sigAnalysisStarted.emit()

        progressBar = ProgressBar("Analysis in Progress", "Attacking with %s:" % self._name)
        with progressBar:
            self.attack.setTargetBytes(self.targetBytes())
            self.attack.setReportingInterval(self.getReportingInterval())
            self.attack.getStatistics().clear()
            self.attack.setStatsReadyCallback(self.sigAnalysisUpdated.emit)

            self.sigAnalysisStarted.emit()

            #--- call the algorithm module

            startingTrace = self.getTraceStart()
            endingTrace   = startingTrace + self.getTracesPerAttack() - 1

            self.attack.addTraces(self.getTraceSource(), (startingTrace, endingTrace), progressBar, pointRange=self.getPointRange(), attack=self)

        self.sigAnalysisDone.emit()

    def getStatistics(self):
        return self.attack.getStatistics()

