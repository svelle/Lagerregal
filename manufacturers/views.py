# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from reversion import revisions as reversion
from django.utils.translation import ugettext_lazy as _
from django.db.transaction import atomic
from django.conf import settings

from devices.models import Device, Manufacturer
from devices.forms import ViewForm, VIEWSORTING,  FilterForm
from Lagerregal.utils import PaginationMixin


class ManufacturerList(PaginationMixin, ListView):
    model = Manufacturer
    context_object_name = 'manufacturer_list'

    def get_queryset(self):
        manufacturers = Manufacturer.objects.all()
        self.filterstring = self.kwargs.pop("filter", None)

        # filter by given filterstring
        if self.filterstring:
            manufacturers = manufacturers.filter(name__icontains=self.filterstring)

        self.viewsorting = self.kwargs.pop("sorting", "name")

        # sort view by name or ID
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            manufacturers = manufacturers.order_by(self.viewsorting)

        return manufacturers

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManufacturerList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [(reverse("manufacturer-list"), _("Manufacturers"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})

        # filtering
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()

        # add page number to breadcrumbs if there are multiple pages
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])

        return context


class ManufacturerDetail(DetailView):
    model = Manufacturer
    context_object_name = 'object'
    template_name = "devices/manufacturer_detail.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManufacturerDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        # adds list of related devices
        context["merge_list"] = Manufacturer.objects.exclude(pk=context["object"].pk).order_by("name")
        context['device_list'] = Device.objects.filter(manufacturer=context["object"], archived=None,
                                                       trashed=None).values("id", "name", "inventorynumber",
                                                                            "devicetype__name", "room__name",
                                                                            "room__building__name")
        # use label template if existing
        if "manufacturer" in settings.LABEL_TEMPLATES:
            context["label_js"] = ""
            for attribute in settings.LABEL_TEMPLATES["manufacturer"][1]:
                if attribute == "id":
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1:07d}');".format(attribute, getattr(
                        context["manufacturer"], attribute))
                else:
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1}');".format(attribute, getattr(
                        context["manufacturer"], attribute))

        # adds manufacturer to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("manufacturer-list"), _("Manufacturers")),
            (reverse("manufacturer-detail", kwargs={"pk": context["object"].pk}), context["object"].name)]

        return context


class ManufacturerCreate(CreateView):
    model = Manufacturer
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManufacturerCreate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Create new Manufacturer"
        context['type'] = "manufacturer"

        # adds "Create new manufacturer" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("manufacturer-list"), _("Manufacturers")),
            ("", _("Create new manufacturer"))]

        return context


class ManufacturerUpdate(UpdateView):
    model = Manufacturer
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManufacturerUpdate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Update"

        # adds "Edit" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("manufacturer-list"), _("Manufacturers")),
            (reverse("manufacturer-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Edit"))]

        return context


class ManufacturerDelete(DeleteView):
    model = Manufacturer
    success_url = reverse_lazy('manufacturer-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManufacturerDelete, self).get_context_data(**kwargs)

        # should add "Delete" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("manufacturer-list"), _("Manufacturers")),
            (reverse("manufacturer-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Delete"))]

        return context


class ManufacturerMerge(View):
    model = Manufacturer

    def get(self, request, *args, **kwargs):
        context = {"oldobject": get_object_or_404(self.model, pk=kwargs["oldpk"]),
                   "newobject": get_object_or_404(self.model, pk=kwargs["newpk"])}

        # adds "Merge with manufacturer name" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("manufacturer-list"), _("Manufacturers")),
            (reverse("manufacturer-detail", kwargs={"pk": context["oldobject"].pk}), context["oldobject"].name),
            ("", _("Merge with {0}".format(context["newobject"].name)))]

        return render(request, 'devices/base_merge.html', context)

    @atomic
    def post(self, request, *args, **kwargs):
        oldobject = get_object_or_404(self.model, pk=kwargs["oldpk"])
        newobject = get_object_or_404(self.model, pk=kwargs["newpk"])
        devices = Device.objects.filter(manufacturer=oldobject)

        # adds all devices of the old manufacturer to the new manufacturer
        for device in devices:
            device.manufacturer = newobject
            reversion.set_comment(_("Merged Manufacturer {0} into {1}".format(oldobject, newobject)))
            device.save()
        oldobject.delete()

        return HttpResponseRedirect(newobject.get_absolute_url())
