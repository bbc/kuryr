# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

import kuryr.privsep

from oslo_concurrency import processutils
from oslo_config import cfg

from kuryr.lib import constants
from kuryr.lib import exceptions
from kuryr.lib import utils as lib_utils


@kuryr.privsep.sys_admin_pctxt.entrypoint
def _unbind_host_iface(ifname, endpoint_id, port_id, net_id, hwaddr, kind=None,
                       details=None):
    """Unbinds the interface

    :param ifname:      the name of the interface to configure
    :param endpoint_id: the identifier of the endpoint
    :param port_id:     the Neutron uuid of the port to which this interface
                        is to be unbound from
    :param net_id:      the Neutron uuid of the network the port is part of
    :param hwaddr:      the interface hardware address
    :param kind:        the Neutron port vif_type
    :param details:     Neutron vif details
    """
    if kind is None:
        kind = constants.FALLBACK_VIF_TYPE
    unbinding_exec_path = os.path.join(cfg.CONF.bindir, kind)
    if not os.path.exists(unbinding_exec_path):
        raise exceptions.BindingNotSupportedFailure(
            "vif_type({0}) is not supported. An unbinding script for this "
            "type can't be found".format(kind))
    stdout, stderr = processutils.execute(
        unbinding_exec_path, constants.UNBINDING_SUBCOMMAND, port_id, ifname,
        endpoint_id, hwaddr, details, net_id)
    return (stdout, stderr)


@kuryr.privsep.sys_admin_pctxt.entrypoint
def _configure_host_iface(ifname, endpoint_id, port_id, net_id, project_id,
                          hwaddr, kind=None, details=None):
    """Configures the interface that is placed on the default net ns

    :param ifname:      the name of the interface to configure
    :param endpoint_id: the identifier of the endpoint
    :param port_id:     the Neutron uuid of the port to which this interface
                        is to be bound
    :param net_id:      the Neutron uuid of the network the port is part of
    :param project_id:  the Keystone project the binding is made for
    :param hwaddr:      the interface hardware address
    :param kind:        the Neutron port vif_type
    :param details:     Neutron vif details
    """
    if kind is None:
        kind = constants.FALLBACK_VIF_TYPE
    binding_exec_path = os.path.join(cfg.CONF.bindir, kind)
    if not os.path.exists(binding_exec_path):
        raise exceptions.BindingNotSupportedFailure(
            "vif_type({0}) is not supported. A binding script for this type "
            "can't be found".format(kind))
    stdout, stderr = processutils.execute(
        binding_exec_path, constants.BINDING_SUBCOMMAND, port_id, ifname,
        endpoint_id, hwaddr, net_id, project_id,
        lib_utils.string_mappings(details))
    return stdout, stderr
