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
import pyroute2

from oslo_log import log
from oslo_utils import excutils

from kuryr.lib.binding.drivers import utils
from kuryr.lib import constants
from kuryr.lib import exceptions
from kuryr.lib import utils as lib_utils
from kuryr.privsep.ports import _configure_host_iface, _unbind_host_iface


KIND = 'veth'
LOG = log.getLogger(__name__)


def port_bind(endpoint_id, port, subnets, network=None, vm_port=None,
              segmentation_id=None, **kwargs):
    """Binds the Neutron port to the network interface on the host.

    :param endpoint_id:   the ID of the endpoint as string
    :param port:         the container Neutron port dictionary as returned by
                         python-neutronclient
    :param subnets:      an iterable of all the Neutron subnets which the
                         endpoint is trying to join
    :param network:      the Neutron network which the endpoint is trying to
                         join
    :param vm_port:      the Nova instance port dictionary, as returned by
                         python-neutronclient. Container port under binding is
                         running inside this instance (either ipvlan/macvlan or
                         a subport)
    :param segmentation_id: ID of the segment for container traffic isolation)
    :param kwargs:       Additional driver-specific arguments
    :returns: the tuple of the names of the veth pair and the tuple of stdout
              and stderr returned by processutils.execute invoked with the
              executable script for binding
    :raises: kuryr.common.exceptions.VethCreationFailure,
             processutils.ProcessExecutionError
    """
    ip = utils.get_ipdb()
    port_id = port['id']
    host_ifname, container_ifname = utils.get_veth_pair_names(port_id)
    mtu = utils.get_mtu_from_network(network)

    try:
        with ip.create(ifname=host_ifname, kind=KIND,
                       reuse=True, peer=container_ifname) as host_veth:
            if not utils.is_up(host_veth):
                host_veth.up()
        with ip.interfaces[container_ifname] as container_veth:
            utils._configure_container_iface(
                container_veth, subnets,
                fixed_ips=port.get(utils.FIXED_IP_KEY),
                mtu=mtu, hwaddr=port[utils.MAC_ADDRESS_KEY].lower())
    except pyroute2.CreateException:
        LOG.exception("Error happened during virtual device creation")
        raise exceptions.VethCreationFailure(
            'Virtual device creation failed.')
    except pyroute2.CommitException:
        LOG.exception("Error happened during configuring the container "
                      "virtual device networking")
        raise exceptions.VethCreationFailure(
            'Could not configure the container virtual device networking.')

    try:
        stdout, stderr = _configure_host_iface(
            host_ifname, endpoint_id, port_id,
            port['network_id'], port.get('project_id') or port['tenant_id'],
            port[utils.MAC_ADDRESS_KEY],
            kind=port.get(constants.VIF_TYPE_KEY),
            details=port.get(constants.VIF_DETAILS_KEY))
    except Exception:
        with excutils.save_and_reraise_exception():
            utils.remove_device(host_ifname)

    return host_ifname, container_ifname, (stdout, stderr)


def port_unbind(endpoint_id, neutron_port, **kwargs):
    """Unbinds the Neutron port from the network interface on the host.

    :param endpoint_id: the ID of the Docker container as string
    :param neutron_port: a port dictionary returned from python-neutronclient
    :param kwargs:       Additional driver-specific arguments
    :returns: the tuple of stdout and stderr returned by processutils.execute
              invoked with the executable script for unbinding
    :raises: processutils.ProcessExecutionError, pyroute2.NetlinkError
    """

    vif_type = neutron_port.get(constants.VIF_TYPE_KEY,
                                constants.FALLBACK_VIF_TYPE)
    vif_details = lib_utils.string_mappings(neutron_port.get(
                                            constants.VIF_DETAILS_KEY))

    port_id = neutron_port['id']
    ifname, _ = utils.get_veth_pair_names(port_id)

    mac_address = neutron_port['mac_address']
    network_id = neutron_port['network_id']
    stdout, stderr = _unbind_host_iface(ifname, endpoint_id, port_id,
                                        network_id, mac_address, vif_type,
                                        vif_details)
    try:
        utils.remove_device(ifname)
    except pyroute2.NetlinkError:
        LOG.exception("Error happened during deleting the veth pair")
        raise exceptions.VethDeletionFailure(
            'Deleting the veth pair failed.')
    return (stdout, stderr)
