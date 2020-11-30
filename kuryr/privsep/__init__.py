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

from oslo_privsep import capabilities
from oslo_privsep import priv_context

sys_admin_pctxt = priv_context.PrivContext(
    'kuryr',
    cfg_section='kuryr_sys_admin',
    pypath=__name__ + '.sys_admin_pctxt',
    capabilities=[capabilities.CAP_NET_ADMIN],
)
