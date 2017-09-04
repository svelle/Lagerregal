from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.db.transaction import atomic
from reversion import revisions as reversion

from locations.models import Section
from devices.models import Device, Room, Building
from devices.forms import ViewForm, VIEWSORTING, FilterForm
from Lagerregal.utils import PaginationMixin


class SectionList(PaginationMixin, ListView):
    model = Section
    context_object_name = 'section_list'

    def get_queryset(self):
        '''method for selecting all sections (sorted) matching the filter'''
        sections = Section.objects.all()
        self.filterstring = self.kwargs.pop("filter", None)

        # filtering by filterstring
        if self.filterstring:
            sections = sections.filter(name__icontains=self.filterstring)

        self.viewsorting = self.kwargs.pop("sorting", "name")

        # sorting by ID or name
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            sections = sections.order_by(self.viewsorting)

        return sections


    def get_context_data(self, **kwargs):
        '''method for getting context data like page number, section'''
        # Call the base implementation first to get a context
        context = super(SectionList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Sections"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})

        # filtering
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()

        # view page number in breadcrumbs
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])

        return context


class SectionCreate(CreateView):
    model = Section
    success_url = reverse_lazy('section-list')
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        '''method for getting context data'''
        # Call the base implementation first to get a context
        context = super(SectionCreate, self).get_context_data(**kwargs)
        context['type'] = "section"

        # add "create new section" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Section")),
            ("", _("Create new section"))]

        return context


class SectionDetail(DetailView):
    model = Section
    context_object_name = 'section'
    template_name = "locations/section_detail.html"

    def get_context_data(self, **kwargs):
        '''method for getting context data for sections and breadcrumbs'''
        # Call the base implementation first to get a context
        context = super(SectionDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        # show related room details and devices
        context["merge_list"] = Section.objects.exclude(pk=context["object"].pk).order_by("name")
        context['device_list'] = Device.objects.filter(room__section=context["object"], archived=None,
                                                       trashed=None).values("id", "name", "inventorynumber",
                                                                            "devicetype__name")

        if "section" in settings.LABEL_TEMPLATES:
            context["label_js"] = ""
            for attribute in settings.LABEL_TEMPLATES["section"][1]:
                if attribute == "id":
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1:07d}');".format(attribute, getattr(
                        context["section"], attribute))
                else:
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1}');".format(attribute, getattr(
                        context["section"], attribute))

        # add section to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Sections")),
            (reverse("section-detail", kwargs={"pk": context["object"].pk}), context["object"].name)]

        return context


class SectionUpdate(UpdateView):
    model = Section
    success_url = reverse_lazy('section-list')
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SectionUpdate, self).get_context_data(**kwargs)

        context["breadcrumbs"] = [
            (reverse("section-list"), _("Section")),
            (reverse("section-edit", kwargs={"pk": self.object.pk}), self.object)]

        return context


class SectionDelete(DeleteView):
    model = Section
    success_url = reverse_lazy('section-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SectionDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Sections")),
            (reverse("section-delete", kwargs={"pk": self.object.pk}), self.object)]
        return context


class SectionMerge(View):
    model = Section

    def get(self, request, *args, **kwargs):
        context = {}
        context["oldobject"] = get_object_or_404(self.model, pk=kwargs["oldpk"])
        context["newobject"] = get_object_or_404(self.model, pk=kwargs["newpk"])
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Sections")),
            (reverse("section-detail", kwargs={"pk": context["oldobject"].pk}), context["oldobject"].name),
            ("", _("Merge with {0}".format(context["newobject"].name)))]
        return render(request, 'devices/base_merge.html', context)

    @atomic
    def post(self, request, *args, **kwargs):
        oldobject = get_object_or_404(self.model, pk=kwargs["oldpk"])
        newobject = get_object_or_404(self.model, pk=kwargs["newpk"])
        rooms = Room.objects.filter(section=oldobject)
        for room in rooms:
            room.section = newobject
            reversion.set_comment(_("Merged Section {0} into {1}".format(oldobject, newobject)))
            room.save()
        oldobject.delete()
        return HttpResponseRedirect(newobject.get_absolute_url())

class RoomList(PaginationMixin, ListView):
    model = Room
    context_object_name = 'room_list'

    def get_queryset(self):
        rooms = Room.objects.select_related("building").all()
        self.filterstring = self.kwargs.pop("filter", None)
        if self.filterstring:
            rooms = rooms.filter(name__icontains=self.filterstring)
        self.viewsorting = self.kwargs.pop("sorting", "name")
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            rooms = rooms.order_by(self.viewsorting)
        return rooms

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RoomList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [(reverse("room-list"), _("Rooms"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])
        return context


class RoomDetail(DetailView):
    model = Room
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RoomDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["merge_list"] = Room.objects.exclude(pk=context["room"].pk).order_by("name").values("id", "name",
                                                                                                    "building__name")
        context['device_list'] = Device.objects.select_related().filter(room=context["room"], archived=None,
                                                                        trashed=None).values("id", "name",
                                                                                             "inventorynumber",
                                                                                             "devicetype__name")

        if "room" in settings.LABEL_TEMPLATES:
            context["label_js"] = ""
            for attribute in settings.LABEL_TEMPLATES["room"][1]:
                if attribute == "id":
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1:07d}');".format(attribute, getattr(
                        context["room"], attribute))
                else:
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1}');".format(attribute,
                                                                                              getattr(context["room"],
                                                                                                      attribute))

        context["breadcrumbs"] = [
            (reverse("room-list"), _("Rooms")),
            (reverse("room-detail", kwargs={"pk": context["room"].pk}), context["room"].name)]
        return context


class RoomCreate(CreateView):
    model = Room
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RoomCreate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Create new Room"
        context['type'] = "room"
        context["breadcrumbs"] = [
            (reverse("room-list"), _("Rooms")),
            ("", _("Create new room"))]
        return context


class RoomUpdate(UpdateView):
    model = Room
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RoomUpdate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Update"
        context["breadcrumbs"] = [
            (reverse("room-list"), _("Rooms")),
            (reverse("room-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Edit"))]
        return context


class RoomDelete(DeleteView):
    model = Room
    success_url = reverse_lazy('room-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RoomDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("room-list"), _("Rooms")),
            (reverse("room-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Delete"))]
        return context


class RoomMerge(View):
    model = Room

    def get(self, request, *args, **kwargs):
        context = {"oldobject": get_object_or_404(self.model, pk=kwargs["oldpk"]),
                   "newobject": get_object_or_404(self.model, pk=kwargs["newpk"])}
        context["breadcrumbs"] = [
            (reverse("room-list"), _("Rooms")),
            (reverse("room-detail", kwargs={"pk": context["oldobject"].pk}), context["oldobject"].name),
            ("", _("Merge with {0}".format(context["newobject"].name)))]
        return render(request, 'devices/base_merge.html', context)

    @atomic
    def post(self, request, *args, **kwargs):
        oldobject = get_object_or_404(self.model, pk=kwargs["oldpk"])
        newobject = get_object_or_404(self.model, pk=kwargs["newpk"])
        devices = Device.objects.filter(room=oldobject)
        for device in devices:
            device.room = newobject
            reversion.set_comment(_("Merged Room {0} into {1}".format(oldobject, newobject)))
            device.save()
        oldobject.delete()
        return HttpResponseRedirect(newobject.get_absolute_url())


class BuildingList(PaginationMixin, ListView):
    model = Building
    context_object_name = 'building_list'

    def get_queryset(self):
        '''method for getting sorted list of buildings matching filter'''
        buildings = Building.objects.all()
        self.filterstring = self.kwargs.pop("filter", None)

        # filtering
        if self.filterstring:
            buildings = buildings.filter(name__icontains=self.filterstring)

        self.viewsorting = self.kwargs.pop("sorting", "name")

        # sort list of buildings by name or ID
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            buildings = buildings.order_by(self.viewsorting)

        return buildings

    def get_context_data(self, **kwargs):
        '''method for getting context data'''
        # Call the base implementation first to get a context
        context = super(BuildingList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [(reverse("building-list"), _("Buildings"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})

        # filtering
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()

        return context


class BuildingDetail(DetailView):
    model = Building
    context_object_name = 'building'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BuildingDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["merge_list"] = Building.objects.exclude(pk=context["building"].pk).order_by("name")
        context['device_list'] = Device.objects.select_related().filter(room__building=context["building"],
                                                                        archived=None, trashed=None).values("id",
                                                                                                            "name",
                                                                                                            "inventorynumber",
                                                                                                            "devicetype__name",
                                                                                                            "room__name")

        if "building" in settings.LABEL_TEMPLATES:
            context["label_js"] = ""
            for attribute in settings.LABEL_TEMPLATES["building"][1]:
                if attribute == "id":
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1:07d}');".format(attribute, getattr(
                        context["building"], attribute))
                else:
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1}');".format(attribute, getattr(
                        context["building"], attribute))

        # add name of building to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("building-list"), _("Buildings")),
            (reverse("building-detail", kwargs={"pk": context["building"].pk}), context["building"].name)]
        return context


class BuildingCreate(CreateView):
    model = Building
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BuildingCreate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Create new Building"
        context['type'] = "building"

        # add "create new building" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("building-list"), _("Buildings")),
            ("", _("Create new building"))]

        return context


class BuildingUpdate(UpdateView):
    model = Building
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        '''method for getting context data to update breadcrumbs'''
        # Call the base implementation first to get a context
        context = super(BuildingUpdate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['actionstring'] = "Update"

        # add "edit" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("building-list"), _("Buildings")),
            (reverse("building-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Edit"))]

        return context


class BuildingDelete(DeleteView):
    model = Building
    success_url = reverse_lazy('building-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        '''method for getting contexdt data to expand breadcrumbs'''
        # Call the base implementation first to get a context
        context = super(BuildingDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("building-list"), _("Buildings")),
            (reverse("building-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Delete"))]

        return context


class BuildingMerge(View):
    model = Building

    def get(self, request, *args, **kwargs):
        '''method for getting data of building to merge'''
        context = {"oldobject": get_object_or_404(self.model, pk=kwargs["oldpk"]),
                   "newobject": get_object_or_404(self.model, pk=kwargs["newpk"])}

        # add name of building to merge to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("building-list"), _("Buildings")),
            (reverse("building-detail", kwargs={"pk": context["oldobject"].pk}), context["oldobject"].name),
            ("", _("Merge with {0}".format(context["newobject"].name)))]

        return render(request, 'devices/base_merge.html', context)

    @atomic
    def post(self, request, *args, **kwargs):
        oldobject = get_object_or_404(self.model, pk=kwargs["oldpk"])
        newobject = get_object_or_404(self.model, pk=kwargs["newpk"])
        rooms = Room.objects.filter(building=oldobject)

        # update room data
        for room in rooms:
            room.building = newobject
            room.save()

        oldobject.delete()

        return HttpResponseRedirect(newobject.get_absolute_url())
