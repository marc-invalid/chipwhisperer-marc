#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 MARC
# All rights reserved.
#
# Authors: MARC

from chipwhisperer.common.utils import util

LEAK_HW_CIPHERTEXT_BIT = 1
LEAK_HD_DATA_REG_SHIFT = 2

leakagemodels = util.dictSort({"Bit Model: msb(data)":"LEAK_HW_CIPHERTEXT_BIT",
                               "Hamming Distance: shiftr(data32)":"LEAK_HD_DATA_REG_SHIFT"})

leakagehelp = "foo"

def processKnownKey(setting, inpkey):
    return inpkey


def leakage(pt, ct, guess, bnum, setting, state):
    return 0

