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
import logging

from chipwhisperer.common.api.autoscript import AutoScript
from chipwhisperer.common.utils.pluginmanager import Plugin
from chipwhisperer.common.utils.parameter import Parameterized
from chipwhisperer.common.utils.parameter import setupSetParam


class PartitionBase(AutoScript, Plugin, Parameterized):
    """
    Base Class for all partition modules
    See ciphertext.py for an example of how to use it.
    """
    _name = "None"

    def __init__(self):
        self.enabled = False
        AutoScript.__init__(self)
#        self.getParams().addChildren([
#                 {'name':'Enabled', 'key':'enabled', 'type':'bool', 'default':self.getEnabled(), 'get':self.getEnabled, 'set':self.setEnabled}
#        ])
#        self.findParam('input').hide()

        if __debug__: logging.debug('Created: ' + str(self))

    def updateScript(self, ignored=None):
        pass

    def getEnabled(self):
        """Return if it is enabled or not"""
        return self.enabled

    @setupSetParam("Enabled")
    def setEnabled(self, enabled):
        """Turn on/off this module"""
        self.enabled = enabled
        self.updateScript()


    def init(self):
        pass


    def __del__(self):
        if __debug__: logging.debug('Deleted: ' + str(self))

