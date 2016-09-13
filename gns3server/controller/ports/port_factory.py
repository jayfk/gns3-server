#!/usr/bin/env python
#
# Copyright (C) 2016 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from .atm_port import ATMPort
from .frame_relay_port import FrameRelayPort
from .gigabitethernet_port import GigabitEthernetPort
from .fastethernet_port import FastEthernetPort
from .ethernet_port import EthernetPort
from .serial_port import SerialPort


import logging
log = logging.getLogger(__name__)

PORTS = {
    'atm': ATMPort,
    'frame_relay': FrameRelayPort,
    'fastethernet': FastEthernetPort,
    'gigabitethernet': GigabitEthernetPort,
    'ethernet': EthernetPort,
    'serial': SerialPort
}


class PortFactory:
    """
    Factory to create an Port object based on the type
    """

    def __new__(cls, name, adapter_number, port_number, port_type, **kwargs):
        return PORTS[port_type](name, adapter_number, port_number, **kwargs)
