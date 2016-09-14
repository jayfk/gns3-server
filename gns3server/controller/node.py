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

import aiohttp
import asyncio
import copy
import uuid
import os


from .compute import ComputeConflict
from .ports.port_factory import PortFactory, DynamipsPortFactory
from ..utils.images import images_directories
from ..utils.qt import qt_font_to_style


import logging
log = logging.getLogger(__name__)


class Node:
    # This properties are used only on controller and are not forwarded to the compute
    CONTROLLER_ONLY_PROPERTIES = ["x", "y", "z", "width", "height", "symbol", "label", "console_host",
                                  "port_name_format", "first_port_name", "port_segment_size", "ports"]

    def __init__(self, project, compute, name, node_id=None, node_type=None, **kwargs):
        """
        :param project: Project of the node
        :param compute: Compute server where the server will run
        :param name: Node name
        :param node_id: UUID of the node (integer)
        :param node_type: Type of emulator
        :param kwargs: Node properties
        """

        assert node_type

        if node_id is None:
            self._id = str(uuid.uuid4())
        else:
            self._id = node_id

        self._project = project
        self._compute = compute
        self._node_type = node_type

        self._label = None
        self._name = None
        self.name = name
        self._console = None
        self._console_type = None
        self._properties = {}
        self._command_line = None
        self._node_directory = None
        self._status = "stopped"
        self._x = 0
        self._y = 0
        self._z = 0
        self._symbol = None
        if node_type == "iou":
            self._port_name_format = "Ethernet{adapter}/{port}"
            self._port_by_adapter = 4
        else:
            self._port_name_format = "Ethernet{0}"
            self._port_by_adapter = 1
        self._port_segment_size = 0
        self._first_port_name = None

        # This properties will be recompute
        ignore_properties = ("width", "height")

        # Update node properties with additional elements
        for prop in kwargs:
            if prop not in ignore_properties:
                try:
                    setattr(self, prop, kwargs[prop])
                except AttributeError as e:
                    log.critical("Can't set attribute %s", prop)
                    raise e

        if self._symbol is None:
            self.symbol = ":/symbols/computer.svg"

    @property
    def id(self):
        return self._id

    @property
    def status(self):
        return self._status

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = self._project.update_node_name(self, new_name)
        # The text in label need to be always the node name
        if self.label and self._label["text"] != self._name:
            self._label["text"] = self._name
            self._label["x"] = None  # Center text

    @property
    def node_type(self):
        return self._node_type

    @property
    def console(self):
        return self._console

    @console.setter
    def console(self, val):
        self._console = val

    @property
    def console_type(self):
        return self._console_type

    @console_type.setter
    def console_type(self, val):
        self._console_type = val

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, val):
        self._properties = val

    @property
    def project(self):
        return self._project

    @property
    def compute(self):
        return self._compute

    @property
    def host(self):
        """
        :returns: Domain or ip for console connection
        """
        return self._compute.host

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        self._x = val

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        self._y = val

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, val):
        self._z = val

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, val):
        self._symbol = val
        try:
            self._width, self._height, filetype = self._project.controller.symbols.get_size(val)
        # If symbol is invalid we replace it by default
        except (ValueError, OSError):
            self.symbol = ":/symbols/computer.svg"
        if self._label is None:
            # Apply to label user style or default
            try:
                style = qt_font_to_style(
                    self._project.controller.settings["GraphicsView"]["default_label_font"],
                    self._project.controller.settings["GraphicsView"]["default_label_color"])
            except KeyError:
                style = "font-size: 10;font-familly: Verdana"

            self._label = {
                "y": round(self._height / 2 + 10) * -1,
                "text": self._name,
                "style": style,
                "x": None,  # None: mean the client should center it
                "rotation": 0
            }

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, val):
        # The text in label need to be always the node name
        val["text"] = self._name
        self._label = val

    @property
    def port_name_format(self):
        return self._port_name_format

    @port_name_format.setter
    def port_name_format(self, val):
        self._port_name_format = val

    @property
    def port_segment_size(self):
        return self._port_segment_size

    @port_segment_size.setter
    def port_segment_size(self, val):
        self._port_segment_size = val

    @property
    def first_port_name(self):
        return self._first_port_name

    @first_port_name.setter
    def first_port_name(self, val):
        self._first_port_name = val

    @asyncio.coroutine
    def create(self):
        """
        Create the node on the compute server
        """
        data = self._node_data()
        data["node_id"] = self._id
        trial = 0
        while trial != 6:
            try:
                response = yield from self._compute.post("/projects/{}/{}/nodes".format(self._project.id, self._node_type), data=data)
            except ComputeConflict as e:
                if e.response.get("exception") == "ImageMissingError":
                    res = yield from self._upload_missing_image(self._node_type, e.response["image"])
                    if not res:
                        raise e
                else:
                    raise e
            else:
                self.parse_node_response(response.json)
                return True
            trial += 1

    @asyncio.coroutine
    def update(self, **kwargs):
        """
        Update the node on the compute server

        :param kwargs: Node properties
        """

        # When updating properties used only on controller we don't need to call the compute
        update_compute = False

        old_json = self.__json__()

        compute_properties = None
        # Update node properties with additional elements
        for prop in kwargs:
            if getattr(self, prop) != kwargs[prop]:
                if prop not in self.CONTROLLER_ONLY_PROPERTIES:
                    update_compute = True

                # We update properties on the compute and wait for the anwser from the compute node
                if prop == "properties":
                    compute_properties = kwargs[prop]
                else:
                    setattr(self, prop, kwargs[prop])

        # We send notif only if object has changed
        if old_json != self.__json__():
            self.project.controller.notification.emit("node.updated", self.__json__())
        if update_compute:
            data = self._node_data(properties=compute_properties)
            response = yield from self.put(None, data=data)
            self.parse_node_response(response.json)
        self.project.dump()

    def parse_node_response(self, response):
        """
        Update the object with the remote node object
        """
        for key, value in response.items():
            if key == "console":
                self._console = value
            elif key == "node_directory":
                self._node_directory = value
            elif key == "command_line":
                self._command_line = value
            elif key == "status":
                self._status = value
            elif key == "console_type":
                self._console_type = value
            elif key == "name":
                self.name = value
            elif key in ["node_id", "project_id", "console_host"]:
                pass
            else:
                self._properties[key] = value

    def _node_data(self, properties=None):
        """
        Prepare node data to send to the remote controller

        :param properties: If properties is None use actual property otherwise use the parameter
        """
        if properties:
            data = copy.copy(properties)
        else:
            data = copy.copy(self._properties)
        data["name"] = self._name
        if self._console:
            # console is optional for builtin nodes
            data["console"] = self._console
        if self._console_type:
            data["console_type"] = self._console_type

        # None properties are not be send. Because it can mean the emulator doesn't support it
        for key in list(data.keys()):
            if data[key] is None or data[key] is {} or key in self.CONTROLLER_ONLY_PROPERTIES:
                del data[key]
        return data

    @asyncio.coroutine
    def destroy(self):
        yield from self.delete()

    @asyncio.coroutine
    def start(self):
        """
        Start a node
        """
        yield from self.post("/start")

    @asyncio.coroutine
    def stop(self):
        """
        Stop a node
        """
        try:
            yield from self.post("/stop")
        # We don't care if a compute is down at this step
        except (aiohttp.errors.ClientOSError, aiohttp.errors.ClientHttpProcessingError, aiohttp.web.HTTPNotFound, aiohttp.web.HTTPConflict):
            pass

    @asyncio.coroutine
    def suspend(self):
        """
        Suspend a node
        """
        yield from self.post("/suspend")

    @asyncio.coroutine
    def reload(self):
        """
        Suspend a node
        """
        yield from self.post("/reload")

    @asyncio.coroutine
    def post(self, path, data=None):
        """
        HTTP post on the node
        """
        if data:
            return (yield from self._compute.post("/projects/{}/{}/nodes/{}{}".format(self._project.id, self._node_type, self._id, path), data=data))
        else:
            return (yield from self._compute.post("/projects/{}/{}/nodes/{}{}".format(self._project.id, self._node_type, self._id, path)))

    @asyncio.coroutine
    def put(self, path, data=None):
        """
        HTTP post on the node
        """
        if path is None:
            path = "/projects/{}/{}/nodes/{}".format(self._project.id, self._node_type, self._id)
        else:
            path = "/projects/{}/{}/nodes/{}{}".format(self._project.id, self._node_type, self._id, path)
        if data:
            return (yield from self._compute.put(path, data=data))
        else:
            return (yield from self._compute.put(path))

    @asyncio.coroutine
    def delete(self, path=None):
        """
        HTTP post on the node
        """
        if path is None:
            return (yield from self._compute.delete("/projects/{}/{}/nodes/{}".format(self._project.id, self._node_type, self._id)))
        else:
            return (yield from self._compute.delete("/projects/{}/{}/nodes/{}{}".format(self._project.id, self._node_type, self._id, path)))

    @asyncio.coroutine
    def _upload_missing_image(self, type, img):
        """
        Search an image on local computer and upload it to remote compute
        if the image exists
        """
        for directory in images_directories(type):
            image = os.path.join(directory, img)
            if os.path.exists(image):
                self.project.controller.notification.emit("log.info", {"message": "Uploading missing image {}".format(img)})
                with open(image, 'rb') as f:
                    yield from self._compute.post("/{}/images/{}".format(self._node_type, os.path.basename(img)), data=f, timeout=None)
                self.project.controller.notification.emit("log.info", {"message": "Upload finished for {}".format(img)})
                return True
        return False

    @asyncio.coroutine
    def dynamips_auto_idlepc(self):
        """
        Compute the idle PC for a dynamips node
        """
        return (yield from self._compute.get("/projects/{}/{}/nodes/{}/auto_idlepc".format(self._project.id, self._node_type, self._id), timeout=240)).json

    @asyncio.coroutine
    def dynamips_idlepc_proposals(self):
        """
        Compute a list of potential idle PC
        """
        return (yield from self._compute.get("/projects/{}/{}/nodes/{}/idlepc_proposals".format(self._project.id, self._node_type, self._id), timeout=240)).json

    def _list_ports(self):
        """
        Generate the list of port display in the client
        if the compute has sent a list we return it (use by
        node where you can not personnalize the port naming).
        """
        ports = []
        # Some special cases
        if self._node_type == "atm_switch":
            for adapter_number in range(0, len(self.properties["mappings"])):
                ports.append(PortFactory("ATM{}".format(adapter_number), adapter_number, adapter_number, 0, "atm"))
            return ports
        elif self._node_type == "frame_relay_switch":
            for adapter_number in range(0, len(self.properties["mappings"])):
                ports.append(PortFactory("FrameRelay{}".format(adapter_number), adapter_number, adapter_number, 0, "frame_relay"))
            return ports
        elif self._node_type == "dynamips":
            return DynamipsPortFactory(self.properties)

        interface_number = segment_number = 0
        if "serial_adapters" in self.properties:
            for adapter_number in range(0, self.properties["serial_adapters"]):
                for port_number in range(0, self._port_by_adapter):
                    ports.append(PortFactory("Serial{}/{}".format(adapter_number, port_number), adapter_number, adapter_number, port_number, "serial"))

        if "ethernet_adapters" in self.properties:
            ethernet_adapters = self.properties["ethernet_adapters"]
        else:
            ethernet_adapters = self.properties.get("adapters", 1)

        for adapter_number in range(0, ethernet_adapters):
            for port_number in range(0, self._port_by_adapter):
                if self._first_port_name and adapter_number == 0:
                    port_name = self._first_port_name
                else:
                    port_name = self._port_name_format.format(
                        interface_number,
                        segment_number,
                        adapter=adapter_number,
                        port=port_number,
                        port0=interface_number,
                        port1=1 + interface_number,
                        segment0=segment_number,
                        segment1=1 + segment_number)
                    interface_number += 1
                    if self._port_segment_size and interface_number % self._port_segment_size == 0:
                        segment_number += 1
                        interface_number = 0

                ports.append(PortFactory(port_name, adapter_number, adapter_number, port_number, "ethernet"))
        return ports

    def __repr__(self):
        return "<gns3server.controller.Node {} {}>".format(self._node_type, self._name)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id and other.project.id == self.project.id

    def __json__(self, topology_dump=False):
        """
        :param topology_dump: Filter to keep only properties require for saving on disk
        """
        if topology_dump:
            return {
                "compute_id": str(self._compute.id),
                "node_id": self._id,
                "node_type": self._node_type,
                "name": self._name,
                "console": self._console,
                "console_type": self._console_type,
                "properties": self._properties,
                "label": self._label,
                "x": self._x,
                "y": self._y,
                "z": self._z,
                "width": self._width,
                "height": self._height,
                "symbol": self._symbol,
                "port_name_format": self._port_name_format,
                "port_segment_size": self._port_segment_size,
                "first_port_name": self._first_port_name
            }
        return {
            "compute_id": str(self._compute.id),
            "project_id": self._project.id,
            "node_id": self._id,
            "node_type": self._node_type,
            "node_directory": self._node_directory,
            "name": self._name,
            "console": self._console,
            "console_host": str(self._compute.host),
            "console_type": self._console_type,
            "command_line": self._command_line,
            "properties": self._properties,
            "status": self._status,
            "label": self._label,
            "x": self._x,
            "y": self._y,
            "z": self._z,
            "width": self._width,
            "height": self._height,
            "symbol": self._symbol,
            "port_name_format": self._port_name_format,
            "port_segment_size": self._port_segment_size,
            "first_port_name": self._first_port_name,
            "ports": [port.__json__() for port in self._list_ports()]
        }
