#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, MARC
# All rights reserved.
#
# Author: MARC
#
#=================================================

from ._base import PartitionBase

from chipwhisperer.analyzer.models.keeloq import keeloqEncryptKeybit
from chipwhisperer.analyzer.models.keeloq import keeloqEncryptKeybitHD
from chipwhisperer.analyzer.models.keeloq import keeloqDecryptKeybit
from chipwhisperer.analyzer.models.keeloq import keeloqDecryptKeybitHD
from chipwhisperer.analyzer.models.keeloq import keeloqGetHW
from chipwhisperer.analyzer.models.keeloq import keeloqGetHD

from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI



#------ KEELOQ: Ciphertext
#
#       This partitions using each of the 32 ciphertext bits individually.
#       Identifies when exactly they are produced, thus revealing location
#       and timing of the cipher.

class keeloqPartition_Ciphertext(PartitionBase):

    _name = "Keeloq: Data bits"
    _description = ""

    # def __init__(self):
    #     PartitionBase.__init__(self)
    #     self.updateScript()

    def getNumPartitions(self):
        # each bit is either 0 or 1
        return 2

    def getPartitionNum(self, trace, tnum):
        textout = trace.getTextout(tnum)

        if (textout is not None) and (len(textout) >= 4):
            # assume big-endian byte order
            data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
        else:
            data = 0

        #--- skip already known/guessed keybits

        # Example:
        # data = keeloqDecryptKeybit(data, 0)		# remove round 528
        # data = keeloqDecryptKeybit(data, 1)		# remove round 527
        # data = keeloqDecryptKeybit(data, 0)		# remove round 526

        currentround = 528

        if hasattr(CWCoreAPI.getInstance(), 'kludge_keeloq_keystream'):
            keystream = CWCoreAPI.getInstance().kludge_keeloq_keystream
            for i in range(0, len(keystream)):
                if keystream[i]=='0':
                    keybit = 0
                elif keystream[i]=='1':
                    keybit = 1
                else:
                    # silently skip whitespace and other unknown chars
                    continue
                data = keeloqDecryptKeybit(data, keybit)
                currentround -= 1

        #---

        # assume little-endian bit order, trace #0 is what is calculated last and sent first over RF
        guess = [0] * 32
        for i in range(0, 32):
            guess[i] = (data >> (31-i)) % 2
        return guess



#------ KEELOQ: 1+2+3 rounds back
#
#       This reverses (decrypts) the last 3 rounds of a given ciphertext, enumerating
#       all possible key inputs for each of the rounds.  Partitions are based on HD of
#       the status register.
#
#       Trace 0,1:                   keybit_528 = 0,1
#       Trace 2+4,3+5:               keybit_527 = 0,1
#       Trace 6+7,8+9,10+11,12+13:   keybit_526 = 0,1

class keeloqPartition_123back(PartitionBase):

    _name = "Keeloq: HD(data) 1+2+3 rounds back"
    _description = ""

    def getNumPartitions(self):
        # We work the 32 bit status register, so there are 33 possible hamming weights
        return 33

    def getPartitionNum(self, trace, tnum):
        textout = trace.getTextout(tnum)

        if (textout is not None) and (len(textout) >= 4):
            # assume big-endian byte order
            data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
        else:
            data = 0

        #--- skip already known/guessed keybits

        # Example:
        # data = keeloqDecryptKeybit(data, 0)		# remove round 528
        # data = keeloqDecryptKeybit(data, 1)		# remove round 527
        # data = keeloqDecryptKeybit(data, 0)		# remove round 526

        currentround = 528

        if hasattr(CWCoreAPI.getInstance(), 'kludge_keeloq_keystream'):
            keystream = CWCoreAPI.getInstance().kludge_keeloq_keystream
            for i in range(0, len(keystream)):
                if keystream[i]=='0':
                    keybit = 0
                elif keystream[i]=='1':
                    keybit = 1
                else:
                    # silently skip whitespace and other unknown chars
                    continue
                data = keeloqDecryptKeybit(data, keybit)
                currentround -= 1

        #--- guess decryption 3 rounds deep with all possible key bit values
        #
        # To be used like this:
        #
        #   Step 1)  - Enable only traces 0 + 1
	#	     - Look at round 528 (minus skipped rounds)
	#	     - Highest peak is candidate
        #
        #   Step 2)  - Disable all traces
        #            - If candidate was 0, enable traces 2 + 3
        #            - If candidate was 1, enable traces 4 + 5 instead
        #            - Look at round 527 (minus skipped rounds)
        #            - Compare this "hot" pair of traces to the other one (2+3 vs 4+5) to confirm guess from Step 1
        #
        #   Step 3)  - Now look for the highest peak in the hot pair, this is the next candidate
        #
        #   Step 4)  - Disable all traces
        #            - Enable next hot pair, eg for 528->0 527->1 it would be pair 8 + 9
        #            - Look at round 526 (minus skipped rounds)
        #            - Confirm guess 527 by with the complementary pair, eg 528->0 527->0 which is 6 + 7
        #
        # If a confirm fails, track back.

        guess = [0] * 14
        data0,   guess[ 0] = keeloqDecryptKeybitHD(data,0)                      # trace  0
        data1,   guess[ 1] = keeloqDecryptKeybitHD(data,1)                      # trace  1

        data00,  guess[ 2] = keeloqDecryptKeybitHD(data0,0)                     # trace  2
        data01,  guess[ 3] = keeloqDecryptKeybitHD(data0,1)                     # trace  3
        data10,  guess[ 4] = keeloqDecryptKeybitHD(data1,0)                     # trace  4
        data11,  guess[ 5] = keeloqDecryptKeybitHD(data1,1)                     # trace  5

        data000, guess[ 6] = keeloqDecryptKeybitHD(data00,0)                    # trace  6
        data001, guess[ 7] = keeloqDecryptKeybitHD(data00,1)                    # trace  7
        data010, guess[ 8] = keeloqDecryptKeybitHD(data01,0)                    # trace  8
        data011, guess[ 9] = keeloqDecryptKeybitHD(data01,1)                    # trace  9
        data100, guess[10] = keeloqDecryptKeybitHD(data10,0)                    # trace 10
        data101, guess[11] = keeloqDecryptKeybitHD(data10,1)                    # trace 11
        data110, guess[12] = keeloqDecryptKeybitHD(data11,0)                    # trace 12
        data111, guess[13] = keeloqDecryptKeybitHD(data11,1)                    # trace 13

        return guess



#------ KEELOQ: N rounds back
#
#       This reverses (decrypts) the last N rounds of a given ciphertext, enumerating
#       all possible key inputs (just) that round.  Partitions are based on HD of the
#       status register.
#
#       The desired number of rounds can be set in the KEELOQ_DPA attack dock.

class keeloqPartition_Nback(PartitionBase):

    _name = "Keeloq: HD(data) N rounds back"
    _description = ""

    def getNumPartitions(self):
        # We work the 32 bit status register, so there are 33 possible hamming weights
        return 33

    def getPartitionNum(self, trace, tnum):
        textout = trace.getTextout(tnum)

        if (textout is not None) and (len(textout) >= 4):
            # assume big-endian byte order
            data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
        else:
            data = 0

        #--- skip already known/guessed keybits

        # Example:
        # data = keeloqDecryptKeybit(data, 0)		# remove round 528
        # data = keeloqDecryptKeybit(data, 1)		# remove round 527
        # data = keeloqDecryptKeybit(data, 0)		# remove round 526

        currentround = 528

        if hasattr(CWCoreAPI.getInstance(), 'kludge_keeloq_keystream'):
            keystream = CWCoreAPI.getInstance().kludge_keeloq_keystream
            for i in range(0, len(keystream)):
                if keystream[i]=='0':
                    keybit = 0
                elif keystream[i]=='1':
                    keybit = 1
                else:
                    # silently skip whitespace and other unknown chars
                    continue
                data = keeloqDecryptKeybit(data, keybit)
                currentround -= 1

        #--- guess decryption N rounds deep with all possible key bit values

        rounds = 4
        if hasattr(CWCoreAPI.getInstance(), 'kludge_keeloq_rounds'):
            rounds = CWCoreAPI.getInstance().kludge_keeloq_rounds

        rounds  = max(rounds, 1)
        guesses = 2**rounds

        guess = [0] * guesses
        for key in range(0, guesses):
            guess_data = data
            guess_key  = key
            for bit in range(0, rounds):
                guess_bit  = (guess_key >> bit) % 2
                guess_prev = guess_data
                guess_data = keeloqDecryptKeybit(guess_data, guess_bit)

            guess[key]  = keeloqGetHD(guess_data, guess_prev)

#            state1 = guess_data
#            state2 = guess_prev
#            hd     = state1 ^ state2
#            hd1    = hd & state2
#            guess[key] = keeloqGetHW(hd1)

        currentround -= rounds

        if tnum==0:
            poi1 = 102  - ((528 - currentround) *  1)
            poi2 = 3070 - ((528 - currentround) * 30)
            poi3 = 205  - ((528 - currentround) *  2)
            print "Look at %d / %d / %d" % (poi1, poi2, poi3)

        return guess


