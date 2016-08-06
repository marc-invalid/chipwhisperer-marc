#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 MARC
# All rights reserved.
#
# Author: MARC

import numpy as np

from chipwhisperer.common.results.base import ResultsBase
from ._base import PreprocessingBase


class ResyncSliceToSlot(PreprocessingBase):
    _name = "Resync: Slice to Slot"
    _description = "For inputs with slight clock drift (RC OSC)."\
                   " Chops the input to slices and places them into equidistant slots."\
                   " NOTE: Align inputs at left edge of ref window!"

    def __init__(self, traceSource=None):
        PreprocessingBase.__init__(self, traceSource)

        #--- description of reference (user config)

        self.ref_trace            = 0

        self.ref_divs             = 1

        self.ref_window_start     = 0
        self.ref_window_stop      = 1

        self.ref_limit_start      = 0
        self.ref_limit_stop       = 1

        self.jitter_slice_percent = 0
        self.jitter_total_percent = 0

        #--- reference examination results

        self.ref_valid          = False						# True = examine has completed successfully

        self.sliceshapes        = None						# list of up to self.ref_div slices
        self.slicewidth_int     = 0						# (int)   sample points per sliceshape
        self.slicewidth_exact   = 0						# (float) exact width, useful to calc pos

        self.match_anchor_pos   = 0						# starting point for match, all inputs are aligned here
        self.match_anchor_cycle = 0						# anchor is not necessarily at the first cycle
        self.match_cycles       = 0						# total number of cycles to find

        self.jitter_slice       = 0						# (int sample pts) max deviation left/right between neighbor slices
        self.jitter_total       = 0						# (int sample pts) max deviation from ideal

        #--- output (placer)

        self.slot_width     = 0							# 0=auto -> use self.slicewidth_int

        #--- other config

        self.debug_print    = False

        #---

        self.params.addChildren([

            #--- define reference slice(s)

            {'name':'Reference Trace',          'key':'ref_trace',  'type':'int', 'value':0, 'action':self.updateScript},

            {'name':'  Ref slice window',       'key':'ref_window', 'type':'rangegraph',
                                                'graphwidget':ResultsBase.registeredObjects["Trace Output Plot"],
                                                'action':self.updateScript, 'value':(0, 0), 'default':(0, 0)},

            {'name':'  # of ref slices',        'key':'ref_divs', 'type':'int', 'value':1,
                         'help': "Number of ref slices:\n"\
                                 "---------------------\n\n"
                                 "Specifies how many cycles (or shapes or rounds) have been highlighted in the reference window.\n"\
                                 "\n"\
                                 "The window will be chopped into this many slices, "\
                                 "and each of them becomes a valid reference.\n"\
                                 "\n"\
                                 " * 1 is best for most cases.\n"\
                                 "\n"\
                                 " * >1 is useful when multiple different shapes are involved. "\
                                 "Present all of them in the reference window, and the best match will be used.\n"\
                                 "\n"\
                                 "Avoid including several seemingly identical shapes. "\
                                 "Tiny registration differences will translate into output jitter. "\
                                 "If necessary, fabricate a reference from cherry-picked snippets.\n",
                          'helpwnd': None,
                          'action':self.updateScript},

            {'name':'  Slice width (Pts)',        'key':'ref_slicewidth', 'type':'float', 'readonly':True, 'value':0.0, 'action':self.updateScript},

            {'name':'  Detection limit (0=all)', 'key':'ref_limit', 'type':'rangegraph', 'graphwidget':ResultsBase.registeredObjects["Trace Output Plot"],
                         'help': "Detection limit:\n"\
                                 "----------------\n\n"
                                 "Specifies where similar slices can be found (in the ref trace). "\
                                 "0,0 means 'whole trace'.\n"\
                                 "\n"\
                                 "Highlight the relevant area plus a slight bit of padding.\n"\
                                 "\n"\
                                 "The limit only applies to the ref trace. "\
                                 "For all other inputs, the number of detected slices is used instead "\
                                 "(to extract just as many slices).\n",
                                                'action':self.updateScript, 'value':(0, 0), 'default':(0, 0)},

            #--- define and restrict sync algorithm

            {'name':'Match method',             'key':'correlator', 'type':'list',
                                                'values':{"Sum-of-Difference":"sad"}, 'default':"sad", 'value':"sad",
                                                'action':self.updateScript},

            {'name':'  Jitter/slice (max %)',   'key':'jitter_slice', 'type':'float', 'value':10, 'default':10, 'limits':(0, 100), 'action':self.updateScript},
            {'name':'  Jitter/total (max %)',   'key':'jitter_total', 'type':'float', 'value':10, 'default':10, 'limits':(0, 100), 'action':self.updateScript,
                         'help': "Jitter/total:\n"\
                                 "-------------\n\n"
                                 "Specifies how far away slices may drift from their ideal positions.\n"\
                                 "\n"\
                                 "Think: max size difference of smallest/largest trace vs reference trace.\n"

#                                 "\n"\
#                                 "Technical note:\n"\
#                                 "When the actual drift approaches the allowance limit, the detection window is tightned up. "\
#                                 "Once completely exhausted, detection fails (no more neighbor slices).\n"\
#                                 "\n"\
#                                 "This behavior is subject to change. "\
#                                 "It degrades match quality when operating near the limit. "\
#                                 "Future versions will probably allow/fail without tightening.\n"
# TODO: implement this proposal
                                                 },

            #--- output algorithm

            {'name':'Place method',             'key':'placer', 'type':'list', 'action':self.updateScript,
                         'help': "Place method:\n"\
                                 "-------------\n\n"
                                 "Specifies how to place input slices into output slots.\n"\
                                 "\n"\
                                 " * Copy generously: Copy from input until the slot is filled, possibly duplicating data.\n"\
                                 " * Copy truncated: Copy just the input slice (slice-width), remainders filled with 0.\n"\
                                 "\n"\
                                 "FIXME: Some placer options (including this one) are disabled because they are not yet implemented.\n",
                                                'values':{"Copy generously":"copy_fill", "Copy truncated":"copy_trunc"},
                                                'default':"copy_trunc", 'value':"copy_trunc",
                                               'readonly':True   # FIXME: disabled because not yet implemented
                                               },

            {'name':'  Slot width (0=auto)',   'key':'slot_width', 'type':'int', 'value':0, 'action':self.updateScript},
            {'name':'  Alignment',             'key':'slot_align', 'type':'list', 'action':self.updateScript,
                                               'values':{"Left":"left", "Center":"center", "Right":"right"},
                                               'default':"left", 'value':"left",
                                               'readonly':True   # FIXME: disabled because not yet implemented
                                               },

            {'name':'  Copy remainder',        'key':'copyremainder', 'type':'bool', 'default':False, 'value':False, 'action':self.updateScript,
                                               'readonly':True   # FIXME: disabled because not yet implemented
                                               }

            #--- debug options

#            {'name':'Inject pilots',           'key':'pilot_enable', 'type':'bool', 'default':True, 'value':True,
#                         'help': "Inject pilots:\n"\
#                                 "--------------\n\n"
#                                 "If enabled, some output samples will be overwritten to show "\
#                                 "how the algorithm was applied to the data.\n"\
#                                 "\n"\
#                                 " * -1.0 = start of slot\n"
#                                 ,
#                          'helpwnd': None,
#                          'action':self.updateScript}
        ])
        self.updateScript()
        self.updateLimits()
        self.sigTracesChanged.connect(self.updateLimits)

    def updateLimits(self):
        if self._traceSource:
            self.findParam('ref_window').setLimits((0, self._traceSource.numPoints()))
            self.findParam('ref_limit').setLimits((0, self._traceSource.numPoints()))

    def updateScript(self, _=None):
        self.addFunction("init", "setEnabled", "%s" % self.findParam('enabled').getValue())

        ref_window = self.findParam('ref_window').getValue()
        ref_limit  = self.findParam('ref_limit' ).getValue()
        if (ref_limit != (0,0)) and (ref_window != (0,0)):
            ref_limit = (min(ref_limit[0], ref_window[0]), max(ref_limit[1],ref_window[1]))
            self.findParam('ref_limit').setValue(ref_limit, blockAction=True)

        ref_divs = self.findParam('ref_divs').getValue()
        ref_divs = max(1, ref_divs)

        #--- Calc and show reference slice width

        # force float where necessary
        if (ref_divs > 1):
            ref_divs = float(ref_divs)

        if ref_window[1] >= ref_window[0]:
            ref_slicewidth = (ref_window[1] - ref_window[0]) / ref_divs
        else:
            ref_slicewidth = 0

        self.findParam('ref_slicewidth').setValue(ref_slicewidth, blockAction=True, ignoreReadonly=True)

        #---

        self.addFunction("init", "setReference",
                         "ref_trace=%d, ref_window=(%d,%d), ref_divs=%d, ref_limit=(%d,%d), jitter_slice=%f, jitter_total=%f" %
                         (self.findParam('ref_trace').getValue(),
                          ref_window[0], ref_window[1],
                          self.findParam('ref_divs').getValue(),
                          ref_limit[0], ref_limit[1],
                          self.findParam('jitter_slice').getValue(),
                          self.findParam('jitter_total').getValue()
                         ))

        self.addFunction("init", "setPlacer",
                         "method='%s', slot_width=%d, slot_align='%s', copyremainder=%s" %
                         (self.findParam('placer').getValue(),
                          self.findParam('slot_width').getValue(),
                          self.findParam('slot_align').getValue(),
                          self.findParam('copyremainder').getValue()
                         ))



        self.updateLimits()



    def setReference(self, ref_trace=0, ref_window=(0, 0), ref_divs=1, ref_limit=(0, 0), jitter_slice=0, jitter_total=0):

        self.ref_trace        = ref_trace
        self.ref_window_start = ref_window[0]
        self.ref_window_stop  = ref_window[1]
        self.ref_divs         = ref_divs

        self.ref_limit_start  = ref_limit[0]
        self.ref_limit_stop   = ref_limit[1]

        self.jitter_slice_percent = jitter_slice
        self.jitter_total_percent = jitter_total

        self.init()


    def setPlacer(self, method='copy_fill', slot_width=0, slot_align='center', copyremainder=True):
        self.placer_method = method
        self.slot_width    = slot_width
        self.slot_align    = slot_align
        self.copyremainder = copyremainder


    #---
    #---
    #---

    def getTrace(self, n):
        if self.enabled:

            #--- prepare trace

            trace = self._traceSource.getTrace(n)
            if trace is None:
                return None

            outlen   = len(trace)
            outtrace = np.zeros(outlen)

            if self.ref_valid != True:
                return outtrace

            #--- semi-real thing

            slot_width = self.slot_width  if (self.slot_width > 0) else  self.slicewidth_int

            matches = self.findSlices(trace, 0, len(trace))


            for i in range(0, len(matches)):

                slice_start = matches[i][1]
                slice_stop  = matches[i][1] + self.slicewidth_int
    
                slice_len   = self.slicewidth_int

                slot_len    = slot_width
                slot_start  = matches[i][0]
                slot_stop   = matches[i][0] + slot_width

                cycle       = matches[i][2]

                if self.debug_print: print "Slot=%d Src=%d Cycle=%d width=%d" % (matches[i][0], matches[i][1], cycle, slot_width)

                # FIXME: right now we just left-align and copy_trunc.  implement the rest!

                if True:
                    # left-align
                    if slice_len >= slot_len:
                        slot = trace[slice_start:(slice_start + slot_len)]
                    else:
                        pad = slot_len - slice_len
                        # print "PAD = %d" % pad
                        slot = np.append(trace[slice_start:slice_stop], np.zeros(pad))

                if (slot_start >= 0) and (slot_stop <= outlen) and (len(slot)==slot_len):
                    outtrace = np.concatenate((outtrace[0:slot_start], slot, outtrace[slot_stop:outlen]))
                    # FIXME: this creates lots of copies and is slow.  need to overwrite the portion instead!

                # else:
                    if self.debug_print: print "WARN over the limits: start=%d len=%d stop=%d outlen=%d slotlen=%d" % (slot_start, len(slot), slot_stop, outlen, slot_len)



                    # TODO: We'd like to EXTEND the trace size here, instead of skipping slices that don't fit.
                    #       Remember that slots tend to be larger than slices, so the trace will grow.
                    #       This is a limitation of the current CW design.  We should rework CW to support it.

            return outtrace


        else:
            return self._traceSource.getTrace(n)


   
    def init(self):
        try:
            self.calcRefTrace(self.ref_trace)
        #Probably shouldn't do this, but deals with user enabling preprocessing
        #before trace management setup
        except ValueError:
            pass



    #---
    #---
    #---
    #    Returns a list of tuples with destination slots and source slices.
    #    For this to work, the slot_width must be valid.  Slot_width may be 0
    #    when the result is ignored, which is usually done during examinination
    #    of the reference trace.  It doesn't hurt to have slot_width correct
    #    at this point, but it isn't necessary.

    def findSlices(self, trace, limit_start, limit_stop, examine=False):

        match_results = []
        refslices = len(self.sliceshapes)

        cycle_counter = 0
        if examine == True:
            self.match_anchor_cycle = 0					# must be 0 for EXAMINE to work

        slot_width = self.slot_width  if (self.slot_width > 0) else  self.slicewidth_int

        #---

        for direction in range(0, 2):

            #--- start at anchor (0=left 1=right)

            if direction == 0:
                pos_actual    = float(self.match_anchor_pos) - self.slicewidth_exact
                pos_ideal     = float(self.match_anchor_pos) - self.slicewidth_exact
                pos_slot      =       self.match_anchor_pos  - slot_width
                cycle_current = self.match_anchor_cycle - 1
            else:
                pos_actual    = float(self.match_anchor_pos)
                pos_ideal     = float(self.match_anchor_pos)
                pos_slot      =       self.match_anchor_pos
                cycle_current = self.match_anchor_cycle

            #--- look (to find all slices in this direction)

            while True:

                #--- stop processing when cycle limit is exhausted

                if examine != True:
                    if (direction == 0) and (cycle_current < 0):
                        break
                    if (direction == 1) and (cycle_current >= self.match_cycles):
                        break

                    if ((pos_slot+slot_width) < 0) or (pos_slot >= len(trace)):
                        # Depending on size ratio slice/slot, the output trace can grow considerably larger
                        # than the input.  CW currently does not support this, so we will skip all slices
                        # that fall completely outside of the supported range.
                        # TODO: Enhance CW to support len(outtrace) > len(intrace)
                        break

                #--- determine acceptable window for this candidate

                range_start = max(pos_actual-self.jitter_slice, pos_ideal-self.jitter_total)
                range_stop  = min(pos_actual+self.jitter_slice, pos_ideal+self.jitter_total)

                range_start = max(int(range_start+0.5), limit_start)
                range_stop  = min(int(range_stop +0.5), limit_stop - self.slicewidth_int)

                range_size  = range_stop - range_start

                #--- exit when limit is exceeded

                if range_size < 0:
                    break

                if range_size == 0:
                    # normally this is result of jitter/total exhausted
                    if self.debug_print: print "Slice-to-Slot WARNING: range_size is 0, there is no wiggle room left!"
                    if self.debug_print: print "### for now interpreted as NO-GO -> aborting ###"
                    break

                #--- calc SAD over the window (for all ref slices)

                bestmatch_value = None
                bestmatch_pos   = None
                bestmatch_slice = None

                # print "SAD: range=%d-%d (wiggle room %d)  pos_actual=%d pos_ideal=%d" % (range_start, range_stop, range_size, pos_actual, pos_ideal)

                for slice in range(0, refslices):

                    #--- calculate SAD over the acceptable window

                    sad_array = np.empty(range_size)
                    for offset in range(0, range_size):
                        sad_start = range_start + offset
                        sad_stop  = range_start + offset + self.slicewidth_int
                        sad_array[offset] = np.sum(np.abs(trace[sad_start:sad_stop] - self.sliceshapes[slice]))
                        # print "SAD for slice %d pos=%d: %f" % (slice, sad_start, sad_array[offset])

                    match_value   = sad_array.min()
                    match_offsets = np.where(sad_array == match_value)

                    #--- among equally good matches, pick nearest to expected slice position (minimizes slice jitter)

                    offset_expected   = pos_actual - range_start
                    match_nearest_idx = np.abs(match_offsets - np.full_like(match_offsets, offset_expected)).argmin()
                    match_offset      = match_offsets[0][match_nearest_idx]
                    match_pos         = match_offset + range_start

                    #--- record only the best result among all slices

                    # print "===> SAD slice %d: pos=%d val=%f" % (slice, match_pos, match_value)

                    if (bestmatch_value is None) or (match_value < bestmatch_value):
                        bestmatch_value = match_value
                        bestmatch_pos   = match_pos
                        bestmatch_slice = slice

                # print "===> BEST SAD for round %d is slice %d: pos=%d val=%f" % (cycle_counter, bestmatch_slice, bestmatch_pos, bestmatch_value)

                # TODO: Track jitter and match quality, and report after processing
                # TODO: Track how many times each ref slice is used, and report after processing

                pos_best   = bestmatch_pos

                #--- record result

                result     = (pos_slot, int(pos_best+0.5), cycle_current)
                match_results.append(result)

                #--- advance to next round

                if direction == 0:
                    pos_actual     = pos_best  - self.slicewidth_exact
                    pos_ideal      = pos_ideal - self.slicewidth_exact
                    pos_slot       = pos_slot  - slot_width
                    cycle_current -= 1
                else:
                    pos_actual     = pos_best  + self.slicewidth_exact
                    pos_ideal      = pos_ideal + self.slicewidth_exact
                    pos_slot       = pos_slot  + slot_width
                    cycle_current += 1

                cycle_counter  += 1

        #--- report

        if examine:
            self.match_cycles       = cycle_counter
            self.match_anchor_cycle = cycle_counter - cycle_current

        return match_results










    def calcRefTrace(self, tnum):
        if self.enabled == False:
            return

        self.ref_valid = False

        if self.ref_window_stop <= self.ref_window_start:
            # invalid inputs
            return

        trace = self._traceSource.getTrace(tnum);

        #--- augment config: how to slice?

        self.ref_divs = max(1, self.ref_divs)

        self.slicewidth_exact = (self.ref_window_stop - self.ref_window_start) / float(self.ref_divs)
        self.slicewidth_int   = int(self.slicewidth_exact + 0.5) if (self.slicewidth_exact >=1) else 1

        #--- augment config: what range to work on?

        limit_start = self.ref_limit_start
        limit_stop  = self.ref_limit_stop
        # special case 0,0 = whole trace
        if (limit_start,limit_stop) == (0,0):
            limit_stop = len(trace)

        if limit_start >= limit_stop:
            # invalid inputs
            return

        #--- augment config: how much jitter allowed?

        self.jitter_slice = int((( self.slicewidth_exact    * self.jitter_slice_percent) / 100.0) + 0.5)
        self.jitter_total = int((( (limit_stop-limit_start) * self.jitter_total_percent) / 100.0) + 0.5)
        # TODO: maybe jitter is better expressed as float?

        #--- extract ref slices

        self.sliceshapes = []	 						# FIXME: this is a python list.  should we use a numpy array?

        for slice in range(0, self.ref_divs):
            start = self.ref_window_start + int((slice * self.slicewidth_exact) + 0.5)	# TODO: rounding tracks the left edge, consider tracking the center?
            stop  = start + self.slicewidth_int
            if stop > len(trace):
                # diabolic selection of inputs could cause the last slice to be off-trace (after rounding)
                self.ref_divs = slice
                print "SLICE prepare: Ignored slice #%d because trace length reached (%d>%d)" % (slice, stop, len(trace))
                break
            self.sliceshapes.append(trace[start:stop])
            # print "SLICE prepare: Added ref slice #%d (%d-%d)" % (slice, start, stop)

        #--- ### MATCHING


        # Matching begins at the left edge of ref window.  All inputs come aligned at this "anchor" position.
        self.match_anchor_pos = self.ref_window_start



        # for later: work on whole trace rather than user limit
        # limit_start = 0
        # limit_stop  = len(trace)


        # Match from ANCHOR to RIGHT

        match_results = self.findSlices(trace, limit_start, limit_stop, examine=True)

        #--- finish

        self.ref_valid = True

        #--- report

        if self.debug_print: print "Found a total of %d rounds (anchor at=%d)" % (self.match_cycles, self.match_anchor_cycle)


