# coding: utf-8

from django.views.generic import ListView, DetailView
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404

from devices.models import Device
from devices.forms import ViewForm, FilterForm, DeviceGroupFilterForm


class PublicDeviceListView(ListView):
    filterstring = ""
    groupfilter = None
    viewsorting = None
    template_name = "devices/public_devices_list.html"

    def get_queryset(self):
        query_dict = settings.PUBLIC_DEVICES_FILTER
        if len(query_dict) == 0:
            raise ImproperlyConfigured

        devices = Device.objects.filter(**query_dict)
        self.filterstring = self.kwargs.pop("filter", None)

        # filter by given filterstring
        if self.filterstring:
            devices = devices.filter(name__icontains=self.filterstring)
        self.viewsorting = self.kwargs.pop("sorting", "name")

        # sort view by name or ID
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            devices = devices.order_by(self.viewsorting)
        self.groupfilter = self.kwargs.pop("group", "all")

        # sort by group
        if self.groupfilter != "all":
            devices = devices.filter(group__id=self.groupfilter)

        return devices.values("id", "name", "inventorynumber", "devicetype__name", "room__name",
                                  "room__building__name",
                                  "group__name", "currentlending__owner__username", "currentlending__duedate")

    def get_context_data(self, **kwargs):
        context = super(PublicDeviceListView, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [(reverse("public-device-list"), _("Public Devices"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})

        # filtering
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()
        context["groupfilterform"] = DeviceGroupFilterForm(initial={"groupfilter": self.groupfilter})

        # add page number to breadcrumbs if there are multiple pages
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])

        context["nochrome"] = self.request.GET.get("nochrome", False)

        return context


class PublicDeviceDetailView(DetailView):
    template_name = "devices/device_detail.html"
    context_object_name = "device"

    def get_queryset(self):
        query_dict = settings.PUBLIC_DEVICES_FILTER
        if len(query_dict) == 0:
            raise ImproperlyConfigured

        devices = Device.objects.prefetch_related("room", "room__building", "manufacturer", "devicetype").filter(
            **query_dict)
        devices = devices.filter(id=self.kwargs.get("pk", None))

        if devices.count() != 1:
            raise Http404

        return devices

    def get_context_data(self, **kwargs):
        context = super(PublicDeviceDetailView, self).get_context_data(**kwargs)

        # adds "Public Devices" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("public-device-list"), _("Public Devices")),
            (reverse("public-device-detail", kwargs={"pk": context["device"].pk}), context["device"].name)]
        context["nochrome"] = self.request.GET.get("nochrome", False)

        return context

