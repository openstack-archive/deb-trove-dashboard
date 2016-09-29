# Copyright 2016 IBM Corp.
#
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


# The slug of the panel to be added to HORIZON_CONFIG. Required.
PANEL = 'ng_database_backups'
# The slug of the dashboard the PANEL associated with. Required.
PANEL_DASHBOARD = 'project'
# The slug of the panel group the PANEL is associated with.
PANEL_GROUP = 'database'

# If set to True, this settings file will not be added to the settings.
DISABLED = True

# Python panel class of the PANEL to be added.
ADD_PANEL = ('trove_dashboard.content.ng_database_backups.panel.NGBackups')
ADD_ANGULAR_MODULES = ['horizon.dashboard.project.backups']

ADD_SCSS_FILES = ['dashboard/project/ngbackups/backups.scss']

ADD_JS_FILES = [
    'dashboard/project/ngbackups/backups.module.js',
    'dashboard/project/ngbackups/table/table.controller.js',
    'dashboard/project/ngbackups/table/table.config.js',
    'app/core/openstack-service-api/trove.service.js'
]

ADD_JS_SPEC_FILES = [
    'dashboard/project/ngbackups/backups.module.spec.js',
    'dashboard/project/ngbackups/table/table.controller.spec.js'
]
