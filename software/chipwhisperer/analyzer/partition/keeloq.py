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
from chipwhisperer.analyzer.models.keeloq import keeloqDecryptKeystream
from chipwhisperer.analyzer.models.keeloq import keeloqGetHW
from chipwhisperer.analyzer.models.keeloq import keeloqGetHD

from chipwhisperer.common.api.CWCoreAPI import CWCoreAPI


#------ Helper for parsing partConfig into partMethod object

def parseConfig(obj, config=None):
        obj.config     = config
        obj.depth      = config.get('depth'     ) if config is not None else None
        obj.keystream  = config.get('keystream' ) if config is not None else None
        obj.round528   = config.get('round528'  ) if config is not None else None
        obj.roundwidth = config.get('roundwidth') if config is not None else None


#------ Helper for fetching ciphertext data and partial decrypt according to partConfig

def prepareData(trace, tnum, keystream=None, configObj=None):

        if (keystream is None) and (configObj is not None) and hasattr(configObj, "keystream"):
            keystream = configObj.keystream

        #--- get ciphertext

        textout = trace.getTextout(tnum)

        if (textout is not None) and (len(textout) >= 4):
            # assume big-endian byte order
            data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
        else:
            data = 0

        #--- skip already known/guessed keybits

        data, round = keeloqDecryptKeystream(data, keystream, round=528)
        return data, round


#------ Helper for printing advice to user on where to look for POIs

def printRoundPos(round, configObj=None):
        if(configObj is None) or not hasattr(configObj, "round528") or not hasattr(configObj, "roundwidth"):
            return

        round528   = configObj.round528
        roundwidth = configObj.roundwidth

        if roundwidth > 0:
            roundstart = round528 - ((528-round)*roundwidth)
            roundstop  = roundstart + roundwidth
            print "For round %d look at %d-%d" % (round, roundstart, roundstop-1)


#------ KEELOQ: Ciphertext
#
#       This partitions using each of the 32 ciphertext bits individually.
#       Identifies when exactly they are produced, thus revealing location
#       and timing of the cipher.

class keeloqPartition_Ciphertext(PartitionBase):

    _name = "Keeloq: Data (all bits)"
    _description = ""

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        return 2

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

        # assume little-endian bit order, output #0 is what is calculated last and sent first over RF
        guess = [0] * 32
        for i in range(0, 32):
            guess[i] = (data >> (31-i)) % 2
        return guess


#------ KEELOQ: Ciphertext (only MSB)

class keeloqPartition_CiphertextMSB(PartitionBase):

    _name = "Keeloq: Data (msb only)"
    _description = ""

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        return 2

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

        # assume little-endian bit order, trace #0 is what is calculated last and sent first over RF
        guess = [0] * 1
        guess[0] = (data >> 0) % 2
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

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        # We work the 32 bit status register, so there are 33 possible hamming weights
        return 33

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

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

#------ KEELOQ: 1+2+3+4 rounds back
#
#       Like above, with one more round (adding 16 traces)

class keeloqPartition_1234back(PartitionBase):

    _name = "Keeloq: HD(data) 1+2+3+4 rounds back"
    _description = ""

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        return 33

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

        guess = [0] * (2+4+8+16)
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

        data0000, guess[14] = keeloqDecryptKeybitHD(data000,0)                  # trace 14
        data0001, guess[15] = keeloqDecryptKeybitHD(data000,1)                  # trace 15
        data0010, guess[16] = keeloqDecryptKeybitHD(data001,0)                  # trace 16
        data0011, guess[17] = keeloqDecryptKeybitHD(data001,1)                  # trace 17
        data0100, guess[18] = keeloqDecryptKeybitHD(data010,0)                  # trace 18
        data0101, guess[19] = keeloqDecryptKeybitHD(data010,1)                  # trace 19
        data0110, guess[20] = keeloqDecryptKeybitHD(data011,0)                  # trace 20
        data0111, guess[21] = keeloqDecryptKeybitHD(data011,1)                  # trace 21
        data1000, guess[22] = keeloqDecryptKeybitHD(data100,0)                  # trace 22
        data1001, guess[23] = keeloqDecryptKeybitHD(data100,1)                  # trace 23
        data1010, guess[24] = keeloqDecryptKeybitHD(data101,0)                  # trace 24
        data1011, guess[25] = keeloqDecryptKeybitHD(data101,1)                  # trace 25
        data1100, guess[26] = keeloqDecryptKeybitHD(data110,0)                  # trace 26
        data1101, guess[27] = keeloqDecryptKeybitHD(data110,1)                  # trace 27
        data1110, guess[28] = keeloqDecryptKeybitHD(data111,0)                  # trace 28
        data1111, guess[29] = keeloqDecryptKeybitHD(data111,1)                  # trace 29

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

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        # We work the 32 bit status register, so there are 33 possible hamming weights
        return 33

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

        #--- guess decryption N rounds deep with all possible key bit values

        depth   = max(1, self.depth if hasattr(self, 'depth') and (self.depth is not None) else 4)
        guesses = 2**depth
        guess   = [0] * guesses

        for key in range(0, guesses):
            guess_data = data
            for bit in range(0, depth):
                guess_key  = (key >> bit) % 2
                guess_prev = guess_data
                guess_data = keeloqDecryptKeybit(guess_data, guess_key)

            guess[key] = keeloqGetHD(guess_data, guess_prev)

            # if tnum==0: print "Trace %d guess_key=0x%02x data=%08x prev=%08x hd=%d" % (tnum, key, guess_data, guess_prev, guess[key])

        #--- helpful output

        round -= depth
        if tnum==0: printRoundPos(round, self)

        return guess

#------ 

class keeloqPartition_BitNback(PartitionBase):

    _name = "Keeloq: bit(msb) N rounds back"
    _description = ""

    def setConfig(self, config=None):
        parseConfig(self, config)

    def getNumPartitions(self):
        return 2

    def getPartitionNum(self, trace, tnum, keystream=None):
        data, round = prepareData(trace, tnum, keystream, self)

        #--- guess decryption N rounds deep with all possible key bit values

        depth   = max(1, self.depth if hasattr(self, 'depth') and (self.depth is not None) else 4)
        guesses = 2**depth
        guess   = [0] * guesses

        for key in range(0, guesses):
            guess_data = data
            for bit in range(0, depth):
                guess_key  = (key >> bit) % 2
                guess_data = keeloqDecryptKeybit(guess_data, guess_key)

            # assume little-endian bit order, trace #0 is what is calculated last and sent first over RF
            guess[key] = (guess_data >> 0) % 2

            if tnum<4: print "Trace %d guess_key=0x%02x data=%08x initial=%08x guess=%d" % (tnum, key, guess_data, data, guess[key])

        #--- helpful output

        round -= depth
        if tnum==0: printRoundPos(round, self)

        return guess


