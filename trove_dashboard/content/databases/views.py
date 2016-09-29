# Copyright 2013 Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Views for managing database instances.
"""
from collections import OrderedDict
import logging

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

import six

from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import tables as horizon_tables
from horizon import tabs as horizon_tabs
from horizon.utils import memoized
from horizon import workflows as horizon_workflows
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils

from trove_dashboard import api
from trove_dashboard.content.databases import forms
from trove_dashboard.content.databases import tables
from trove_dashboard.content.databases import tabs
from trove_dashboard.content.databases import workflows

LOG = logging.getLogger(__name__)


class IndexView(horizon_tables.DataTableView):
    table_class = tables.InstancesTable
    template_name = 'project/databases/index.html'
    page_title = _("Instances")

    def has_more_data(self, table):
        return self._more

    @memoized.memoized_method
    def get_flavors(self):
        try:
            flavors = api.trove.flavor_list(self.request)
        except Exception:
            flavors = []
            msg = _('Unable to retrieve database size information.')
            exceptions.handle(self.request, msg)
        return OrderedDict((six.text_type(flavor.id), flavor)
                           for flavor in flavors)

    def _extra_data(self, instance):
        flavor = self.get_flavors().get(instance.flavor["id"])
        if flavor is not None:
            instance.full_flavor = flavor
        instance.host = tables.get_host(instance)
        return instance

    def get_data(self):
        marker = self.request.GET.get(
            tables.InstancesTable._meta.pagination_param)
        # Gather our instances
        try:
            instances = api.trove.instance_list(self.request, marker=marker)
            self._more = instances.next or False
        except Exception:
            self._more = False
            instances = []
            msg = _('Unable to retrieve database instances.')
            exceptions.handle(self.request, msg)
        map(self._extra_data, instances)
        return instances


class LaunchInstanceView(horizon_workflows.WorkflowView):
    workflow_class = workflows.LaunchInstance
    template_name = "project/databases/launch.html"
    page_title = _("Launch Database")

    def get_initial(self):
        initial = super(LaunchInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.project_id
        initial['user_id'] = self.request.user.id
        return initial


class DBAccess(object):
    def __init__(self, name, access):
        self.name = name
        self.access = access


class CreateUserView(horizon_forms.ModalFormView):
    form_class = forms.CreateUserForm
    form_id = "create_user_form"
    modal_header = _("Create User")
    modal_id = "create_user_modal"
    template_name = 'project/databases/create_user.html'
    submit_label = "Create User"
    submit_url = 'horizon:project:databases:create_user'
    success_url = 'horizon:project:databases:detail'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['instance_id'],))

    def get_context_data(self, **kwargs):
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instance_id = self.kwargs['instance_id']
        return {'instance_id': instance_id}


class EditUserView(horizon_forms.ModalFormView):
    form_class = forms.EditUserForm
    form_id = "edit_user_form"
    modal_header = _("Edit User")
    modal_id = "edit_user_modal"
    template_name = 'project/databases/edit_user.html'
    submit_label = "Apply Changes"
    submit_url = 'horizon:project:databases:edit_user'
    success_url = 'horizon:project:databases:detail'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['instance_id'],))

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['user_name'] = self.kwargs['user_name']
        args = (self.kwargs['instance_id'], self.kwargs['user_name'])
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instance_id = self.kwargs['instance_id']
        user_name = self.kwargs['user_name']
        host = tables.parse_host_param(self.request)
        return {'instance_id': instance_id, 'user_name': user_name,
                'host': host}


class AccessDetailView(horizon_tables.DataTableView):
    table_class = tables.AccessTable
    template_name = 'project/databases/access_detail.html'
    page_title = _("Database Access for: {{ user_name }}")

    @memoized.memoized_method
    def get_data(self):
        instance_id = self.kwargs['instance_id']
        user_name = self.kwargs['user_name']
        try:
            databases = api.trove.database_list(self.request, instance_id)
        except Exception:
            databases = []
            redirect = reverse('horizon:project:databases:detail',
                               args=[instance_id])
            exceptions.handle(self.request,
                              _('Unable to retrieve databases.'),
                              redirect=redirect)
        try:
            granted = api.trove.user_list_access(
                self.request, instance_id, user_name)
        except Exception:
            granted = []
            redirect = reverse('horizon:project:databases:detail',
                               args=[instance_id])
            exceptions.handle(self.request,
                              _('Unable to retrieve accessible databases.'),
                              redirect=redirect)

        db_access_list = []
        for database in databases:
            if database in granted:
                access = True
            else:
                access = False

            db_access = DBAccess(database.name, access)
            db_access_list.append(db_access)

        return sorted(db_access_list, key=lambda data: (data.name))

    def get_context_data(self, **kwargs):
        context = super(AccessDetailView, self).get_context_data(**kwargs)
        context["db_access"] = self.get_data()
        return context


class AttachConfigurationView(horizon_forms.ModalFormView):
    form_class = forms.AttachConfigurationForm
    form_id = "attach_config_form"
    modal_header = _("Attach Configuration Group")
    modal_id = "attach_config_modal"
    template_name = "project/databases/attach_config.html"
    submit_label = "Attach Configuration"
    submit_url = 'horizon:project:databases:attach_config'
    success_url = reverse_lazy('horizon:project:databases:index')

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.trove.instance_get(self.request, instance_id)
        except Exception:
            msg = _('Unable to retrieve instance details.')
            redirect = reverse('horizon:project:databases:index')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = (super(AttachConfigurationView, self)
                   .get_context_data(**kwargs))
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instance = self.get_object()
        return {'instance_id': self.kwargs['instance_id'],
                'datastore': instance.datastore.get('type', ''),
                'datastore_version': instance.datastore.get('version', '')}


class DetailView(horizon_tabs.TabbedTableView):
    tab_group_class = tabs.InstanceDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ instance.name }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        instance = self.get_data()
        table = tables.InstancesTable(self.request)
        context["instance"] = instance
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(instance)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            LOG.info("Obtaining instance for detailed view ")
            instance_id = self.kwargs['instance_id']
            instance = api.trove.instance_get(self.request, instance_id)
            instance.host = tables.get_host(instance)
        except Exception:
            msg = _('Unable to retrieve details '
                    'for database instance: %s') % instance_id
            exceptions.handle(self.request, msg,
                              redirect=self.get_redirect_url())
        try:
            instance.full_flavor = api.trove.flavor_get(
                self.request, instance.flavor["id"])
        except Exception:
            LOG.error('Unable to retrieve flavor details'
                      ' for database instance: %s' % instance_id)
        return instance

    def get_tabs(self, request, *args, **kwargs):
        instance = self.get_data()
        return self.tab_group_class(request, instance=instance, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:databases:index')


class CreateDatabaseView(horizon_forms.ModalFormView):
    form_class = forms.CreateDatabaseForm
    form_id = "create_database_form"
    modal_header = _("Create Database")
    modal_id = "create_database_modal"
    template_name = 'project/databases/create_database.html'
    submit_label = _("Create Database")
    submit_url = 'horizon:project:databases:create_database'
    success_url = 'horizon:project:databases:detail'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['instance_id'],))

    def get_context_data(self, **kwargs):
        context = super(CreateDatabaseView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instance_id = self.kwargs['instance_id']
        return {'instance_id': instance_id}


class ResizeVolumeView(horizon_forms.ModalFormView):
    form_class = forms.ResizeVolumeForm
    form_id = "resize_volume_form"
    modal_header = _("Resize Database Volume")
    modal_id = "resize_volume_modal"
    template_name = 'project/databases/resize_volume.html'
    submit_label = "Resize Database Volume"
    submit_url = 'horizon:project:databases:resize_volume'
    success_url = reverse_lazy('horizon:project:databases:index')
    page_title = _("Resize Database Volume")

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.trove.instance_get(self.request, instance_id)
        except Exception:
            msg = _('Unable to retrieve instance details.')
            redirect = reverse('horizon:project:databases:index')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(ResizeVolumeView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instance = self.get_object()
        return {'instance_id': self.kwargs['instance_id'],
                'orig_size': instance.volume.get('size', 0)}


class ResizeInstanceView(horizon_forms.ModalFormView):
    form_class = forms.ResizeInstanceForm
    form_id = "resize_instance_form"
    modal_header = _("Resize Database Instance")
    modal_id = "resize_instance_modal"
    template_name = 'project/databases/resize_instance.html'
    submit_label = "Resize Database Instance"
    submit_url = 'horizon:project:databases:resize_instance'
    success_url = reverse_lazy('horizon:project:databases:index')
    page_title = _("Resize Database Instance")

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']

        try:
            instance = api.trove.instance_get(self.request, instance_id)
            flavor_id = instance.flavor['id']
            flavors = {}
            for i, j in self.get_flavors():
                flavors[str(i)] = j

            if flavor_id in flavors:
                instance.flavor_name = flavors[flavor_id]
            else:
                flavor = api.trove.flavor_get(self.request, flavor_id)
                instance.flavor_name = flavor.name
            return instance
        except Exception:
            redirect = reverse('horizon:project:databases:index')
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(ResizeInstanceView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def get_flavors(self, *args, **kwargs):
        try:
            flavors = api.trove.flavor_list(self.request)
            return instance_utils.sort_flavor_list(self.request, flavors)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve flavors.'),
                              redirect=redirect)

    def get_initial(self):
        initial = super(ResizeInstanceView, self).get_initial()
        obj = self.get_object()
        if obj:
            initial.update({'instance_id': self.kwargs['instance_id'],
                            'old_flavor_id': obj.flavor['id'],
                            'old_flavor_name': getattr(obj,
                                                       'flavor_name', ''),
                            'flavors': self.get_flavors()})
        return initial


class PromoteToReplicaSourceView(horizon_forms.ModalFormView):
    form_class = forms.PromoteToReplicaSourceForm
    form_id = "promote_to_replica_source_form"
    modal_header = _("Promote to Replica Source")
    modal_id = "promote_to_replica_source_modal"
    template_name = 'project/databases/promote_to_replica_source.html'
    submit_lable = _("Promote")
    submit_url = 'horizon:project:databases:promote_to_replica_source'
    success_url = reverse_lazy('horizon:project:databases:index')

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            replica = api.trove.instance_get(self.request, instance_id)
            replica_source = api.trove.instance_get(self.request,
                                                    replica.replica_of['id'])
            instances = {'replica': replica,
                         'replica_source': replica_source}
            return instances
        except Exception:
            msg = _('Unable to retrieve instance details.')
            redirect = reverse('horizon:project:databases:index')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = \
            super(PromoteToReplicaSourceView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['replica'] = self.get_initial().get('replica')
        context['replica'].ip = \
            self.get_initial().get('replica').ip[0]
        context['replica_source'] = self.get_initial().get('replica_source')
        context['replica_source'].ip = \
            self.get_initial().get('replica_source').ip[0]
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        instances = self.get_object()
        return {'instance_id': self.kwargs['instance_id'],
                'replica': instances['replica'],
                'replica_source': instances['replica_source']}


class EnableRootInfo(object):
    def __init__(self, instance_id, instance_name, enabled, password=None):
        self.id = instance_id
        self.name = instance_name
        self.enabled = enabled
        self.password = password


class ManageRootView(horizon_tables.DataTableView):
    table_class = tables.ManageRootTable
    template_name = 'project/databases/manage_root.html'
    page_title = _("Manage Root Access")

    @memoized.memoized_method
    def get_data(self):
        instance_id = self.kwargs['instance_id']
        try:
            instance = api.trove.instance_get(self.request, instance_id)
        except Exception:
            redirect = reverse('horizon:project:databases:detail',
                               args=[instance_id])
            exceptions.handle(self.request,
                              _('Unable to retrieve instance details.'),
                              redirect=redirect)
        try:
            enabled = api.trove.root_show(self.request, instance_id)
        except Exception:
            redirect = reverse('horizon:project:databases:detail',
                               args=[instance_id])
            exceptions.handle(self.request,
                              _('Unable to determine if instance root '
                                'is enabled.'),
                              redirect=redirect)

        root_enabled_list = []
        root_enabled_info = EnableRootInfo(instance.id,
                                           instance.name,
                                           enabled.rootEnabled)
        root_enabled_list.append(root_enabled_info)
        return root_enabled_list

    def get_context_data(self, **kwargs):
        context = super(ManageRootView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context
