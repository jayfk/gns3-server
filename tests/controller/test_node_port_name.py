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

import pytest
import uuid

from tests.utils import AsyncioMagicMock

from gns3server.controller.node import Node
from gns3server.controller.project import Project


@pytest.fixture
def compute():
    s = AsyncioMagicMock()
    s.id = "http://test.com:42"
    return s


@pytest.fixture
def project(controller):
    return Project(str(uuid.uuid4()), controller=controller)


@pytest.fixture
def node(compute, project):
    node = Node(project, compute, "demo",
                node_id=str(uuid.uuid4()),
                node_type="vpcs",
                console_type="vnc",
                properties={"startup_script": "echo test"})
    return node


def test_list_ports(node):
    """
    List port by default
    """
    assert node.__json__()["ports"] == [
        {
            "name": "Ethernet0",
            "short_name": "e0/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "ethernet"
        }
    ]


def test_list_ports_port_name_format(node):
    """
    Support port name format
    """
    node._first_port_name = None
    node._port_name_format = "eth{}"
    assert node.__json__()["ports"][0]["name"] == "eth0"
    node._port_name_format = "eth{port0}"
    assert node.__json__()["ports"][0]["name"] == "eth0"
    node._port_name_format = "eth{port1}"
    assert node.__json__()["ports"][0]["name"] == "eth1"

    node._first_port_name = ""
    node._port_segment_size = 2
    node._port_name_format = "eth{segment0}/{port0}"
    node.properties["adapters"] = 8
    assert node.__json__()["ports"][6]["name"] == "eth3/0"
    assert node.__json__()["ports"][7]["name"] == "eth3/1"

    node._first_port_name = "mgnt0"
    assert node.__json__()["ports"][0]["name"] == "mgnt0"
    assert node.__json__()["ports"][1]["name"] == "eth0/0"


def test_list_ports_adapters(node):
    """
    List port using adapters properties
    """
    node.properties["adapters"] = 2
    assert node.__json__()["ports"] == [
        {
            "name": "Ethernet0",
            "short_name": "e0/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet1",
            "short_name": "e1/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 1,
            "link_type": "ethernet"
        }
    ]


def test_list_ports_atm_switch(project, compute):
    """
    List port for atm switch
    """
    node = Node(project, compute, "demo",
                node_id=str(uuid.uuid4()),
                node_type="atm_switch")
    node.properties["mappings"] = {
        "1:0:100": "10:0:200"
    }

    assert node.__json__()["ports"] == [
        {
            "name": "ATM0",
            "short_name": "a0/0",
            "data_link_types": {"ATM": "DLT_ATM_RFC1483"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "serial"
        }
    ]


def test_list_ports_frame_relay_switch(project, compute):
    """
    List port for frame relay switch
    """
    node = Node(project, compute, "demo",
                node_id=str(uuid.uuid4()),
                node_type="frame_relay_switch")
    node.properties["mappings"] = {
        "1:0:100": "10:0:200"
    }

    assert node.__json__()["ports"] == [
        {
            "name": "FrameRelay0",
            "short_name": "s0/0",
            "data_link_types": {"Frame Relay": "DLT_FRELAY"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "serial"
        }
    ]


def test_list_ports_iou(compute, project):
    """
    IOU has a special behavior 4 port by adapters
    """
    node = Node(project, compute, "demo",
                node_id=str(uuid.uuid4()),
                node_type="iou")
    node.properties["serial_adapters"] = 2
    node.properties["ethernet_adapters"] = 3
    assert node.__json__()["ports"] == [
        {
            "name": "Serial0/0",
            "short_name": "s0/0",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "serial"
        },
        {
            "name": "Serial0/1",
            "short_name": "s0/1",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 1,
            "adapter_number": 0,
            "link_type": "serial"
        },
        {
            "name": "Serial0/2",
            "short_name": "s0/2",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 2,
            "adapter_number": 0,
            "link_type": "serial"
        },
        {
            "name": "Serial0/3",
            "short_name": "s0/3",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 3,
            "adapter_number": 0,
            "link_type": "serial"
        },
        {
            "name": "Serial1/0",
            "short_name": "s1/0",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 0,
            "adapter_number": 1,
            "link_type": "serial"
        },
        {
            "name": "Serial1/1",
            "short_name": "s1/1",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 1,
            "adapter_number": 1,
            "link_type": "serial"
        },
        {
            "name": "Serial1/2",
            "short_name": "s1/2",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 2,
            "adapter_number": 1,
            "link_type": "serial"
        },
        {
            "name": "Serial1/3",
            "short_name": "s1/3",
            "data_link_types": {
                "Frame Relay": "DLT_FRELAY",
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL"
            },
            "port_number": 3,
            "adapter_number": 1,
            "link_type": "serial"
        },
        {
            "name": "Ethernet0/0",
            "short_name": "e0/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet0/1",
            "short_name": "e0/1",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 1,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet0/2",
            "short_name": "e0/2",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 2,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet0/3",
            "short_name": "e0/3",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 3,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet1/0",
            "short_name": "e1/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet1/1",
            "short_name": "e1/1",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 1,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet1/2",
            "short_name": "e1/2",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 2,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet1/3",
            "short_name": "e1/3",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 3,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet2/0",
            "short_name": "e2/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 2,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet2/1",
            "short_name": "e2/1",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 1,
            "adapter_number": 2,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet2/2",
            "short_name": "e2/2",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 2,
            "adapter_number": 2,
            "link_type": "ethernet"
        },
        {
            "name": "Ethernet2/3",
            "short_name": "e2/3",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 3,
            "adapter_number": 2,
            "link_type": "ethernet"
        }
    ]


def test_list_ports_dynamips(project, compute):
    """
    List port for dynamips
    """
    node = Node(project, compute, "demo",
                node_id=str(uuid.uuid4()),
                node_type="dynamips")
    node.properties["slot0"] = "C7200-IO-FE"
    node.properties["slot1"] = "GT96100-FE"
    node.properties["wic0"] = "WIC-2T"

    assert node.__json__()["ports"] == [
        {
            "name": "FastEthernet0/0",
            "short_name": "f0/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 0,
            "link_type": "ethernet"
        },
        {
            "name": "FastEthernet1/0",
            "short_name": "f1/0",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 0,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "FastEthernet1/1",
            "short_name": "f1/1",
            "data_link_types": {"Ethernet": "DLT_EN10MB"},
            "port_number": 1,
            "adapter_number": 1,
            "link_type": "ethernet"
        },
        {
            "name": "Serial0/0",
            "short_name": "s0/0",
            "data_link_types": {
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL",
                "Frame Relay": "DLT_FRELAY"},
            "port_number": 0,
            "adapter_number": 2,
            "link_type": "serial"
        },
        {
            "name": "Serial0/1",
            "short_name": "s0/1",
            "data_link_types": {
                "Cisco HDLC": "DLT_C_HDLC",
                "Cisco PPP": "DLT_PPP_SERIAL",
                "Frame Relay": "DLT_FRELAY"},
            "port_number": 1,
            "adapter_number": 2,
            "link_type": "serial"
        }
    ]
