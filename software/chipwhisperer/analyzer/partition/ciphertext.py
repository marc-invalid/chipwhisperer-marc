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



#------ Ciphertext: 32 single bits big-endian
#
#       This partitions using each of the first 32 data bits individually.
#       Identifies when exactly they are produced, thus revealing location
#       and timing of the cipher.

class ciphertextPartition_Bits_32BE(PartitionBase):

    _name = "Ciphertext: 32 single bits big-endian"
    _description = ""

    def getNumPartitions(self):
        return 2

    def getPartitionNum(self, trace, tnum):
        textout = trace.getTextout(tnum)

        if (textout is not None) and (len(textout) >= 4):
            # assume big-endian byte order
            data = (textout[0] << 24) | (textout[1] << 16) | (textout[2] << 8) | (textout[3] << 0)
        else:
            data = 0

        # assume big-endian bit order
        guess = [0] * 32
        for i in range(0, 32):
            guess[i] = (data >> i) % 2

        return guess

