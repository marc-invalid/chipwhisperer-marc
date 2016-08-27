#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, MARC
# All rights reserved.
#
# Authors: MARC
#
#=================================================

import numpy as np
import math
from .._stats import DataTypeDiffs
from chipwhisperer.common.api.autoscript import AutoScript
from chipwhisperer.common.utils.pluginmanager import Plugin
from chipwhisperer.common.utils.parameter import Parameterized, Parameter

from chipwhisperer.analyzer.partition.keeloq import keeloqPartition_CiphertextMSB
from chipwhisperer.analyzer.models.keeloq import keeloqDecrypt

# TODO: The following two imports are made to avoid duplicating code.  However, those classes are
#       designed to work in the GUI environment.  Consider separating function from presentation.
from chipwhisperer.analyzer.utils.Partition import Partition
from chipwhisperer.analyzer.utils.TraceExplorerScripts.PartitionDisplay import PartitionDisplay

from chipwhisperer.analyzer.utils.TraceExplorerScripts.PartitionDisplay import DifferenceModeTTest
from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI




class KeeloqDPAEncoder(Parameterized, AutoScript, Plugin):
    """
    CPA Attack done as a loop, but using an algorithm which can progressively add traces & give output stats
    """
    _name = "Hardware Encoder (HCS301)"

    def __init__(self, targetModel, leakageFunction):
        AutoScript.__init__(self)

        self.getParams().addChildren([
            # {'name': '', 'type': 'label', 'value':"Attack-speficic options", 'readonly': True},
            {'name':'Utilize round timing', 'key':'roundtiming', 'type':'bool', 'value':False, 'action':self.updateScript,
                         'help': "Utilize round timing:\n"\
                                 "---------------------\n\n"\
                                 "Utilize round 528 position and width to predict where each round is.\n"\
                                 "\n"\
                                 "**Enabled:** The algorithm accepts correlation peaks only where they are expected, "\
                                 "according to the timing information that you have supplied.\n"\
                                 "\n"\
                                 "**Disabled:** The whole point-range (or trace) is examined for correlation peaks.\n"\
                                 "\n"\
                                 "This option should always be enabled, unless the timing is unknown. "\
                                 "The timing information can be extracted from traces using the Data Bits partition mode.\n"
                         },
        ])

        self.model = targetModel
        self.leakage = leakageFunction
        self.sr = None
        self.stats = DataTypeDiffs()
        self.updateScript()

    def updateScript(self, ignored=None):
        self.addFunction('init', 'setEnforceRoundTiming', '%s' % self.findParam('roundtiming').getValue())

        #self.addFunction('init', 'setReportingInterval', '%d' % self.findParam('reportinterval').getValue())
        #self.addFunction('init', 'setReportingInterval', '%d' % self.findParam('reportinterval').getValue())
        pass

    def setTargetBytes(self, brange):
        self.brange = brange

    def setReportingInterval(self, ri):
        self._reportingInterval = ri

    def setEnforceRoundTiming(self, roundtiming=False):
        self.roundtiming = roundtiming


    #--- this is the main processing loop

    def addTraces(self, tracedata, tracerange, progressBar=None, pointRange=None, attack=None):

        # NOTE: this is for calling substuff, not for legacy code here!
        if pointRange is None: pointRange = (0,-1)

        #---

        roundwidth = 0

        if attack is not None:
            round528 = attack.keeloq_round528
            roundwidth = attack.keeloq_roundwidth
            # print "Using KEELOQ timing values from attack: %d %d" % (round528, roundwidth)

        if self.roundtiming != True:
            roundwidth = 0

        #--- prepare environment

        partClass  = keeloqPartition_CiphertextMSB

        partObject = Partition()
        partObject.setPartMethod(partClass)
        partObject.setTraceSource(tracedata)

        partDisplay = PartitionDisplay(None)
        partDisplay._traces = tracedata

        if progressBar:
            progressBar.setMaximum(64 + 1)

        #--- loop for all unknown keybits

        keystream = ""

        for bit in range(0, 64):

            #--- Analize all possible values (0 and 1)

            guessNum   = 2
            guessDiffs = [] * guessNum

            #--- Partition and find differences using T-Test

            if bit==48:
                print "\nTODO: Sorry for becoming slower, the cipher implementation has not been optimized yet.\n"

            for guessBit in range (0, guessNum):

                # Probe known keystream + guessbit + dummybit
                #
                # The dummybit is necessary because of a property of Keeloq.  The last bit of the stream is
                # mixed into the attacked data bit with XOR.  This results in exactly complementary partitioning
                # for values 0 vs 1, making it impossible to pick a "winner".  Therefore we append the dummybit
                # at this position, so that guessbit is the last input that actually makes a measureable difference.

                partData  = partObject.generatePartitions(partitionClass=None,
                                         saveFile=False, loadFile=False, tRange=tracerange,
                                         partitionConfig={"keystream":"%s %d 0" % (keystream, guessBit)})

                partStats = partDisplay.generatePartitionStats(partitionData={"partclass":partClass, "partdata":partData},
                                         saveFile=False, loadFile=False,  tRange=tracerange, pointRange=pointRange)

                partDiffs = partDisplay.generatePartitionDiffs(DifferenceModeTTest,
                                         statsInfo={"partclass":partClass, "stats":partStats},
                                         saveFile=False, loadFile=False, tRange=tracerange)

                guessDiffs.append(partDiffs[0])

            #--- Determine range in which high correlation is expected

            if roundwidth <= 0: # look in whole pointRange
                lookStart = 0
                lookStop  = len(guessDiffs[0])

            else: # look only at expected position (enforce round timing)
                round      = 528 - 32 - (bit+1)
                roundStart = round528 - ((528-round) * roundwidth)
                roundStop  = roundStart + roundwidth

                lookStart  = roundStart - pointRange[0]
                lookStop   = roundStop  - pointRange[0]

                # print "Round=%d Pos=%d-%d look=%d-%d" % (round, roundStart, roundStop, lookStart, lookStop)

                if (lookStart < 0) or (lookStop > len(guessDiffs[0])):
                    print "Enforced round timing range (%d,%d) is outside of analyzed pointRange(%d,%d). "\
                          "Can't detect key bit %d. Result so far: %s" %\
                                   (roundStart, roundStop, pointRange[0], pointRange[1], bit, keystream)
                    return

            #--- Detect highest correlation
 
            # print "Looking at range %d-%d of %d" % (lookStart, lookStop, len(guessDiffs[0]))
            # if bit == 0:
            #     print guessDiffs[0][lookStart:lookStop]
            #     print guessDiffs[1][lookStart:lookStop]

            winBit = 0 if (np.nanmax(guessDiffs[0][lookStart:lookStop]) > np.nanmax(guessDiffs[1][lookStart:lookStop])) else 1
            badBit = winBit ^ 1

            winOffset     = np.argmax(guessDiffs[winBit][lookStart:lookStop]) + lookStart
            badOffset     = np.argmax(guessDiffs[badBit][lookStart:lookStop]) + lookStart

            winDiff       =           guessDiffs[winBit][winOffset]
            badDiff       =           guessDiffs[badBit][badOffset]
            winRatioSpot  = winDiff / guessDiffs[badBit][winOffset]
            winRatioTrace = winDiff / badDiff

            keystream = "%s%d" % (keystream, winBit)

            #--- report

            print "Analysis of keybit #%02d (of 64): %d (diff=%f spot=%f trace=%f pos=%d) vs %d (diff=%f pos=%d)" %\
                                              (bit,
                                               winBit, winDiff, winRatioSpot, winRatioTrace, winOffset + pointRange[0],
                                               badBit, badDiff,                              badOffset + pointRange[0])

            if progressBar:
                progressBar.setText("Attacking key bits (%d of 64)" % bit)
                progressBar.setStatusMask("Keystream: %s" % keystream)
                progressBar.updateStatus(bit)
                if progressBar.wasAborted():
                    print "Aborting. Result so far: %s" % keystream
                    return

        #---

        keyStr = "%s%s" % (keystream[16:64], keystream[0:16])
        keyInt = int(keyStr, 2)

        print "Keystream = %s" % keystream
        print "Key: %016x" % keyInt

        if progressBar:
            progressBar.setText("Attack finished")
            progressBar.setStatusMask("Key: %016x" % keyInt)
            progressBar.updateStatus(64)

        #--- Decrypt the data associated with all traces

        progress = 64

        if True:
            start = tracerange[0]
            end   = tracerange[1]
            if end == -1:
                end = tracedata.numTraces()
            tnum = start
            while tnum < end:
                t = tracedata.getSegment(tnum)
                # Discover where this trace starts & ends
                tmapstart = t.mappedRange[0]
                tmapend = t.mappedRange[1]

                if progressBar:
                    increment = tmapend + 1 - tmapstart
                    progressBar.setMaximum(progress + increment + 1)
                    progressBar.setText("Decrypting traces")

                for tnum in range(tmapstart, tmapend + 1):
                    if progressBar:
                        progressBar.updateStatus(progress)
                        progress += 1
                        if progressBar.wasAborted():
                            return
                    textout = t.getTextout(tnum - tmapstart)
                    if (textout is not None) and (len(textout) >= 4):
                        data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
                        decrypt = keeloqDecrypt(data, keyInt)
                        print "Trace %0d: %08x -> %08x" % (tnum - tmapstart, data, decrypt)

                tnum = tmapend + 1

        print "Key: %016x" % keyInt

        #--- cleanup

        if progressBar:
            progressBar.setMaximum(100)
            progressBar.updateStatus(100)



    def getStatistics(self):
        return self.stats

    def setStatsReadyCallback(self, sr):
        self.sr = sr

    def processKnownKey(self, inpkey):
        if hasattr(self.model, 'processKnownKey'):
            return self.model.processKnownKey(self.leakage, inpkey)
        else:
            return inpkey
