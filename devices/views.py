# coding: utf-8
import datetime

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, FormView, TemplateView
from django.views.generic.detail import SingleObjectTemplateResponseMixin, BaseDetailView, SingleObjectMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.auth.models import Group
from django.shortcuts import render
from reversion.models import Version
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.contrib import messages
from django.utils.timezone import utc
from django.utils import timezone
from reversion import revisions as reversion
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db.models.query import QuerySet


from devices.models import Device, Template, Lending, Note, Bookmark, Picture
from devicetypes.models import TypeAttribute, TypeAttributeValue
from network.models import IpAddress
from mail.models import MailTemplate, MailHistory
from devices.forms import IpAddressForm, SearchForm, LendForm, DeviceViewForm, IpAddressPurposeForm
from devices.forms import DeviceForm, DeviceMailForm, VIEWSORTING_DEVICES, \
    DeviceStorageForm, ReturnForm
from devicetags.forms import DeviceTagForm
from users.models import Lageruser, Department
from Lagerregal.utils import PaginationMixin
from devicetags.models import Devicetag
from permission.decorators import permission_required
from django.db.models import Q


@permission_required('devices.read_device', raise_exception=True)
class DeviceList(PaginationMixin, ListView):
    context_object_name = 'device_list'
    template_name = 'devices/device_list.html'
    viewfilter = None
    viewsorting = None

    def post(self, request):
        '''post-requesting the detail-view of device by id'''
        if 'deviceid' in request.POST:
            return HttpResponseRedirect(reverse('device-detail', kwargs={'pk':request.POST['deviceid']}))
        else:
            return HttpResponseRedirect(reverse('device-list'))

    def get_queryset(self):
        '''method for query results and display it depending on existing filters (viewfilter, department)'''
        self.viewfilter = self.kwargs.get("filter", "active")
        devices = None
        lendings = None

        # filtering devices by status
        # possible status: all, active, lent, archived, trash, overdue,
        # return soon, short term, bookmarked
        if self.viewfilter == "all":
            devices = Device.objects.all()
        elif self.viewfilter == "available":
            devices = Device.active().filter(currentlending=None)
        elif self.viewfilter == "lent":
            lendings = Lending.objects.filter(returndate=None)
        elif self.viewfilter == "archived":
            devices = Device.objects.exclude(archived=None)
        elif self.viewfilter == "trashed":
            devices = Device.objects.exclude(trashed=None)
        elif self.viewfilter == "overdue":
            lendings = Lending.objects.filter(returndate=None, duedate__lt=datetime.date.today())
        elif self.viewfilter == "returnsoon":
            soon = datetime.date.today() + datetime.timedelta(days=10)
            lendings = Lending.objects.filter(returndate=None, duedate__lte=soon,
                                              duedate__gt=datetime.date.today())
        elif self.viewfilter == "temporary":
            devices = Device.active().filter(templending=True)
        elif self.viewfilter == "bookmark":
            if self.request.user.is_authenticated:
                devices = self.request.user.bookmarks.all()
        else:
            devices = Device.active()

        # filtering by department
        if self.request.user.departments.count() > 0:
            self.departmentfilter = self.kwargs.get("department", "my")
        else:
            self.departmentfilter = self.kwargs.get("department", "all")

        if self.departmentfilter != "all" and self.departmentfilter != "my":
            try:
                departmentid = int(self.departmentfilter)
                self.departmentfilter = Department.objects.get(id=departmentid)
            except:
                self.departmentfilter = Department.objects.get(name=self.departmentfilter)

        if self.departmentfilter == "my":
            self.departmentfilter = self.request.user.departments.all()

        # filtering lent or overdue devices
        if self.viewfilter == "lent" or self.viewfilter == "overdue" or self.viewfilter == "returnsoon":
            if isinstance(self.departmentfilter, (list, tuple, QuerySet)):
                lendings = lendings.filter(owner__departments__in=self.departmentfilter)
                self.departmentfilter = "my"
            elif self.departmentfilter != "all":
                lendings = lendings.filter(owner__departments=self.departmentfilter)
                self.departmentfilter = self.departmentfilter.id
            lendings = lendings.exclude(~Q(device__department__in=self.request.user.departments.all()) &
                                        ~Q(device=None), device__is_private=True)
            return lendings.values("device__id", "device__name", "device__inventorynumber",
                                   "device__devicetype__name", "device__room__name", "device__group",
                                   "device__room__building__name", "owner__username", "owner__id",
                                   "duedate", "smalldevice")
        else:
            if isinstance(self.departmentfilter, (list, tuple, QuerySet)):
                devices = devices.filter(department__in=self.departmentfilter)
                self.departmentfilter = "my"
            elif self.departmentfilter != "all":
                devices = devices.filter(department=self.departmentfilter)
                self.departmentfilter = self.departmentfilter.id
            devices = devices.exclude(~Q(department__in=self.request.user.departments.all()), is_private=True)
            self.viewsorting = self.kwargs.get("sorting", "name")
            if self.viewsorting in [s[0] for s in VIEWSORTING_DEVICES]:
                devices = devices.order_by(self.viewsorting)

            return devices.values("id", "name", "inventorynumber", "devicetype__name", "room__name",
                                  "room__building__name",
                                  "group__name", "currentlending__owner__username", "currentlending__duedate")

    def get_context_data(self, **kwargs):
        '''method for getting context data (filter, time, templates, breadcrumbs)'''
        context = super(DeviceList, self).get_context_data(**kwargs)

        # getting filters
        context["viewform"] = DeviceViewForm(initial={
            'viewfilter': self.viewfilter,
            "viewsorting": self.viewsorting,
            "departmentfilter": self.departmentfilter
        })

        context["today"] = datetime.datetime.today()
        context["template_list"] = Template.objects.all()
        context["viewfilter"] = self.viewfilter
        context["breadcrumbs"] = [[reverse("device-list"), _("Devices")]]

        # add page number to breadcrumbs
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])
        return context


@permission_required('devices.read_device', raise_exception=True)
class DeviceDetail(DetailView):
    # get related data to chosen device
    queryset = Device.objects \
        .select_related("manufacturer", "devicetype", "currentlending", "currentlending__owner", "department",
                        "room", "room__building") \
        .prefetch_related("pictures", )
    context_object_name = 'device'
    object = None

    def get_object(self, queryset=None):
        if self.object is not None:
            return self.object

        pk = self.kwargs.get(self.pk_url_kwarg)
        queryset = self.queryset.filter(pk=pk)
        self.object = queryset.get()

        return self.object


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DeviceDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books

        # ip context data
        context['ipaddressform'] = IpAddressForm()
        context["ipaddressform"].fields["ipaddresses"].queryset = IpAddress.objects.filter(
            department=self.object.department, device=None, user=None)

        # tag context data
        context['tagform'] = DeviceTagForm()
        context['tagform'].fields["tags"].queryset = Devicetag.objects.exclude(devices=context["device"])

        # lending history, eidt history, mail history
        context["lending_list"] = Lending.objects.filter(device=context["device"])\
                                      .select_related("owner").order_by("-pk")[:10]
        context["version_list"] = Version.objects.filter(object_id=context["device"].id,
                                                         content_type_id=ContentType.objects.get(
                                                             model='device').id) \
                                      .select_related("revision", "revision__user").order_by("-pk")[:10]
        context["mail_list"] = MailHistory.objects.filter(device=context["device"])\
                                   .select_related("sent_by").order_by("-pk")[:10]


        context["today"] = datetime.datetime.utcnow().replace(tzinfo=utc)
        context["weekago"] = context["today"] - datetime.timedelta(days=7)
        context["attributevalue_list"] = TypeAttributeValue.objects.filter(device=context["device"])
        context["lendform"] = LendForm()
        mailinitial = {}

        # get user infos if device is lend
        if context["device"].currentlending is not None:
            currentowner = context["device"].currentlending.owner
            mailinitial["owner"] = currentowner
            mailinitial["emailrecipients"] = ("u" + str(currentowner.id), currentowner.username)
        try:
            mailinitial["mailtemplate"] = MailTemplate.objects.get(usage="reminder")
            mailinitial["emailsubject"] = mailinitial["mailtemplate"].subject
            mailinitial["emailbody"] = mailinitial["mailtemplate"].body
        except:
            # maybe there should be something to do if there is an exception???
            pass

        # mail context data
        context["mailform"] = DeviceMailForm(initial=mailinitial)
        context["mailform"].fields["mailtemplate"].queryset = MailTemplate.objects.filter(
            department__in=self.request.user.departments.all())

        versions = reversion.get_for_object(context["device"])

        if len(versions) != 0:
            context["lastedit"] = versions[0]

        if self.object.department:
            dep = self.object.department.name
        else:
            dep = "all"

        if dep in settings.LABEL_TEMPLATES:
            if "device" in settings.LABEL_TEMPLATES[dep]:
                context["display_printbutton"] = True
                context["label_path"] = settings.LABEL_TEMPLATES[dep]["device"][0]
                context["label_js"] = ""
                for attribute in settings.LABEL_TEMPLATES[dep]["device"][1]:
                    if attribute == "id":
                        context["label_js"] += u"\nlabel.setObjectText('{0}', '{1:07d}');".format(attribute,
                                                                                                  getattr(
                                                                                                      context["device"],
                                                                                                      attribute))
                    else:
                        context["label_js"] += u"\nlabel.setObjectText('{0}', '{1}');".format(attribute,
                                                                                              getattr(context["device"],
                                                                                                      attribute))
        # add data to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["device"].pk}), context["device"].name)]

        return context

#### to do
@permission_required('devices.change_device', raise_exception=True)
class DeviceIpAddressRemove(View):
    template_name = 'devices/unassign_ipaddress.html'

    def get(self, request, *args, **kwargs):
        context = {"device": get_object_or_404(Device, pk=kwargs["pk"]),
                   "ipaddress": get_object_or_404(IpAddress, pk=kwargs["ipaddress"])}
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["device"].pk}), context["device"].name),
            ("", _("Unassign IP-Addresses"))]

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        device = get_object_or_404(Device, pk=kwargs["pk"])
        ipaddress = get_object_or_404(IpAddress, pk=kwargs["ipaddress"])
        ipaddress.device = None
        ipaddress.purpose = None
        reversion.set_comment(_("Removed from Device {0}".format(device.name)))
        ipaddress.save()

        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceIpAddress(FormView):
    template_name = 'devices/assign_ipaddress.html'
    form_class = IpAddressForm
    success_url = "/devices"

    def get_context_data(self, **kwargs):
        context = super(DeviceIpAddress, self).get_context_data(**kwargs)
        device = context["form"].cleaned_data["device"]
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": device.pk}), device.name),
            ("", _("Assign IP-Addresses"))]

        return context

    def form_valid(self, form):
        ipaddresses = form.cleaned_data["ipaddresses"]
        device = form.cleaned_data["device"]

        if device.archived is not None:
            messages.error(self.request, _("Archived Devices can't get new IP-Addresses"))
            return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))

        reversion.set_comment(_("Assigned to Device {0}".format(device.name)))
        for ipaddress in ipaddresses:
            ipaddress.device = device
            ipaddress.save()

        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceIpAddressPurpose(FormView):
    template_name = 'devices/assign_ipaddress.html'
    form_class = IpAddressPurposeForm
    success_url = "/devices"

    def get_context_data(self, **kwargs):
        context = super(DeviceIpAddressPurpose, self).get_context_data(**kwargs)
        device = get_object_or_404(Device, pk=self.kwargs["pk"])
        ipaddress = get_object_or_404(IpAddress, pk=self.kwargs["ipaddress"])
        if ipaddress.purpose:
            context["form"].fields["purpose"].initial = ipaddress.purpose
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": device.pk}), device.name),
            ("", _("Set Purpose for {0}").format(ipaddress.address))]
        return context

    def form_valid(self, form):
        purpose = form.cleaned_data["purpose"]
        device = get_object_or_404(Device, pk=self.kwargs["pk"])
        ipaddress = get_object_or_404(IpAddress, pk=self.kwargs["ipaddress"])
        reversion.set_comment(_("Assigned to Device {0}".format(device.name)))
        ipaddress.purpose = purpose
        ipaddress.save()

        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.read_device', raise_exception=True)
class DeviceLendingList(PaginationMixin, ListView):
    context_object_name = 'lending_list'
    template_name = 'devices/device_lending_list.html'

    def get_queryset(self):
        deviceid = self.kwargs["pk"]
        device = get_object_or_404(Device, pk=deviceid)
        return Lending.objects.filter(device=device).order_by("-pk")

    def get_context_data(self, **kwargs):
        context = super(DeviceLendingList, self).get_context_data(**kwargs)
        context["device"] = get_object_or_404(Device, pk=self.kwargs["pk"])
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["device"].pk}), context["device"].name),
            ("", _("Lending"))]
        return context


@permission_required('devices.add_device', raise_exception=True)
class DeviceCreate(CreateView):
    model = Device
    template_name = 'devices/device_form.html'
    form_class = DeviceForm

    def get_initial(self):
        initial = super(DeviceCreate, self).get_initial()
        creator = self.request.user.pk
        templateid = self.kwargs.pop("templateid", None)
        if templateid is not None:
            initial += get_object_or_404(Template, pk=templateid).get_as_dict()
        copyid = self.kwargs.pop("copyid", None)
        if copyid is not None:
            for key, value in get_object_or_404(Device, pk=copyid).get_as_dict().items():
                initial[key] = value
            initial["deviceid"] = copyid
        initial["creator"] = creator

        if self.request.user.main_department:
            initial["department"] = self.request.user.main_department
            department = self.request.user.main_department
        else:
            department = None

        try:
            initial["emailtemplate"] = MailTemplate.objects.get(usage="new", department=department)
            initial["emailrecipients"] = [obj.content_type.name[0].lower() + str(obj.object_id) for obj in
                                          initial["emailtemplate"].default_recipients.all()]
            initial["emailsubject"] = initial["emailtemplate"].subject
            initial["emailbody"] = initial["emailtemplate"].body
        except Exception as e:
            print(e)
        return initial

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DeviceCreate, self).get_context_data(**kwargs)
        context["form"].fields["department"].queryset = self.request.user.departments.all()
        context["form"].fields["emailtemplate"].queryset = MailTemplate.objects.filter(
            department__in=self.request.user.departments.all())
        context['actionstring'] = "Create new Device"
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            ("", _("Create new device"))]
        return context

    def form_valid(self, form):
        if form.cleaned_data["department"]:
            if not form.cleaned_data["department"] in self.request.user.departments.all():
                return HttpResponseBadRequest()
        form.cleaned_data["creator"] = self.request.user
        reversion.set_comment(_("Created"))
        r = super(DeviceCreate, self).form_valid(form)
        for key, value in form.cleaned_data.iteritems():
            if key.startswith("attribute_") and value != "":
                attributenumber = key.split("_")[1]
                typeattribute = get_object_or_404(TypeAttribute, pk=attributenumber)
                attribute = TypeAttributeValue()
                attribute.device = self.object
                attribute.typeattribute = typeattribute
                attribute.value = value
                attribute.save()
        if form.cleaned_data["emailrecipients"] and form.cleaned_data["emailtemplate"]:
            recipients = []
            for recipient in form.cleaned_data["emailrecipients"]:
                if recipient[0] == "g":
                    group = get_object_or_404(Group, pk=recipient[1:])
                    recipients += group.lageruser_set.all().values_list("email")[0]
                else:
                    recipients.append(get_object_or_404(Lageruser, pk=recipient[1:]).email)
            recipients = list(set(recipients))
            template = form.cleaned_data["emailtemplate"]
            if form.cleaned_data["emailedit"]:
                template.subject = form.cleaned_data["emailsubject"]
                template.body = form.cleaned_data["emailbody"]
            template.send(request=self.request, recipients=recipients,
                          data={"device": self.object, "user": self.request.user})
            messages.success(self.request, _('Mail successfully sent'))

        messages.success(self.request, _('Device was successfully created.'))
        return r


@permission_required('devices.change_device', raise_exception=True)
class DeviceUpdate(UpdateView):
    model = Device
    template_name = 'devices/device_form.html'
    form_class = DeviceForm

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DeviceUpdate, self).get_context_data(**kwargs)
        context["form"].fields["department"].queryset = self.request.user.departments.all()
        context['actionstring'] = _("Update")
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["device"].pk}), context["device"].name),
            ("", _("Edit"))]
        context["template_list"] = MailTemplate.objects.filter(department__in=self.request.user.departments.all())
        context["form"].fields["emailtemplate"].queryset = MailTemplate.objects.filter(
            department__in=self.request.user.departments.all())
        return context

    def form_valid(self, form):
        if form.cleaned_data["department"]:
            if not form.cleaned_data["department"] in self.request.user.departments.all():
                return HttpResponseBadRequest()
        deviceid = self.kwargs["pk"]
        device = self.object
        if device.archived is not None:
            messages.error(self.request, _("Archived Devices can't be edited"))
            return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))

        if form.cleaned_data["comment"] == "":
            reversion.set_comment(_("Updated"))
        else:
            reversion.set_comment(form.cleaned_data["comment"])


        if device.devicetype is not None:
            if form.cleaned_data["devicetype"] is None or device.devicetype.pk != form.cleaned_data["devicetype"].pk:
                TypeAttributeValue.objects.filter(device=device.pk).delete()
        for key, value in form.cleaned_data.iteritems():
            if key.startswith("attribute_") and value != "":
                attributenumber = key.split("_")[1]
                typeattribute = get_object_or_404(TypeAttribute, pk=attributenumber)
                try:
                    attribute = TypeAttributeValue.objects.filter(device=device.pk).get(typeattribute=attributenumber)
                except:
                    attribute = TypeAttributeValue()
                    attribute.device = device
                    attribute.typeattribute = typeattribute
                attribute.value = value
                attribute.save()
            elif key.startswith("attribute_") and value == "":
                attributenumber = key.split("_")[1]
                try:
                    TypeAttributeValue.objects.filter(device=device.pk).get(typeattribute=attributenumber).delete()
                except:
                    pass

        if form.cleaned_data["emailrecipients"] and form.cleaned_data["emailtemplate"]:
            recipients = []
            for recipient in form.cleaned_data["emailrecipients"]:
                if recipient[0] == "g":
                    group = get_object_or_404(Group, pk=recipient[1:])
                    recipients += group.lageruser_set.all().values_list("email")[0]
                else:
                    recipients.append(get_object_or_404(Lageruser, pk=recipient[1:]).email)
            recipients = list(set(recipients))
            template = form.cleaned_data["emailtemplate"]
            if form.cleaned_data["emailedit"]:
                template.subject = form.cleaned_data["emailsubject"]
                template.body = form.cleaned_data["emailbody"]
            template.send(request=self.request, recipients=recipients,
                          data={"device": device, "user": self.request.user})
            messages.success(self.request, _('Mail successfully sent'))

        messages.success(self.request, _('Device was successfully updated.'))
        return super(DeviceUpdate, self).form_valid(form)


@permission_required('devices.delete_device', raise_exception=True)
class DeviceDelete(DeleteView):
    model = Device
    success_url = reverse_lazy('device-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DeviceDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["object"].pk}), context["object"].name),
            ("", _("Delete"))]
        return context


@permission_required('devices.lend_device', raise_exception=True)
class DeviceLend(FormView):
    template_name = 'devices/base_form.html'
    form_class = LendForm

    def get_context_data(self, **kwargs):
        context = super(DeviceLend, self).get_context_data(**kwargs)
        context['actionstring'] = "Mark device as lend"
        context['form_scripts'] = "$('#id_owner').select2();"
        if "device" in self.request.POST:
            deviceid = self.request.POST["device"]
            if deviceid != "":
                device = get_object_or_404(Device, pk=deviceid)
                context["breadcrumbs"] = [
                    (reverse("device-list"), _("Devices")),
                    (reverse("device-detail", kwargs={"pk": device.pk}), device.name),
                    ("", _("Lend"))]
                return context

        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            ("", _("Lend"))]
        return context

    def form_valid(self, form):
        lending = Lending()
        device = None
        if form.cleaned_data["device"] and form.cleaned_data["device"] != "":
            device = form.cleaned_data["device"]
            if device.archived is not None:
                messages.error(self.request, _("Archived Devices can't be lent"))
                return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))

            if form.cleaned_data["room"]:
                device.room = form.cleaned_data["room"]
                try:
                    template = MailTemplate.objects.get(usage="room")
                except:
                    template = None
                if not template == None:
                    recipients = []
                    for recipient in template.default_recipients.all():
                        recipient = recipient.content_object
                        if isinstance(recipient, Group):
                            recipients += recipient.lageruser_set.all().values_list("email")[0]
                        else:
                            recipients.append(recipient.email)
                    template.send(self.request, recipients, {"device": device, "user": self.request.user})
                    messages.success(self.request, _('Mail successfully sent'))
                reversion.set_comment(_("Device lent and moved to room {0}").format(device.room))
            lending.device = form.cleaned_data["device"]
        else:
            lending.smalldevice = form.cleaned_data["smalldevice"]
        lending.owner = get_object_or_404(Lageruser, pk=form.cleaned_data["owner"].pk)
        lending.duedate = form.cleaned_data["duedate"]
        lending.save()
        messages.success(self.request, _('Device is marked as lend to {0}').format(
            get_object_or_404(Lageruser, pk=form.cleaned_data["owner"].pk)))
        if form.cleaned_data["device"]:
            device.currentlending = lending
            device.save()
            return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))
        else:
            return HttpResponseRedirect(reverse("userprofile", kwargs={"pk": lending.owner.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceInventoried(View):
    def get(self, request, **kwargs):
        deviceid = kwargs["pk"]
        device = get_object_or_404(Device, pk=deviceid)
        device.inventoried = timezone.now()
        device.save()
        messages.success(request, _('Device is marked as inventoried.'))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))

    def post(self, request, **kwargs):
        return self.get(request, **kwargs)


@permission_required('devices.lend_device', raise_exception=True)
class DeviceReturn(FormView):
    template_name = 'devices/base_form.html'
    form_class = ReturnForm

    def get_context_data(self, **kwargs):
        context = super(DeviceReturn, self).get_context_data(**kwargs)
        context['actionstring'] = "Mark device as returned"

        lending = get_object_or_404(Lending, pk=self.kwargs["lending"])

        if lending.device:
            device_name = lending.device.name
        else:
            device_name = lending.smalldevice
            del context["form"].fields["room"]

        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            ("", _("Return {0}").format(device_name))]
        return context

    def form_valid(self, form):
        device = None
        owner = None
        lending = get_object_or_404(Lending, pk=self.kwargs["lending"])
        if lending.device and lending.device != "":
            device = lending.device
            device.currentlending = None
            device.save()
            if form.cleaned_data["room"]:
                device.room = form.cleaned_data["room"]
                try:
                    template = MailTemplate.objects.get(usage="room")
                except:
                    template = None
                if not template == None:
                    recipients = []
                    for recipient in template.default_recipients.all():
                        recipient = recipient.content_object
                        if isinstance(recipient, Group):
                            recipients += recipient.lageruser_set.all().values_list("email")[0]
                        else:
                            recipients.append(recipient.email)
                    template.send(self.request, recipients, {"device": device, "user": self.request.user})
                    messages.success(self.request, _('Mail successfully sent'))
                reversion.set_comment(_("Device returned and moved to room {0}").format(device.room))
        else:
            owner = lending.owner
        lending.returndate = datetime.datetime.now()
        lending.save()
        messages.success(self.request, _('Device is marked as returned'))
        if device != None:
            return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))
        else:
            return HttpResponseRedirect(reverse("userprofile", kwargs={"pk": owner.pk}))


@permission_required('devices.lend_device', raise_exception=True)
class DeviceMail(FormView):
    template_name = 'devices/base_form.html'
    form_class = DeviceMailForm

    def get_context_data(self, **kwargs):
        context = super(DeviceMail, self).get_context_data(**kwargs)

        # Add in a QuerySet of all the books
        context['form_scripts'] = "$('#id_owner').select2();"
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": self.device.pk}), self.device.name),
            ("", _("Send Mail"))]
        return context

    def get_initial(self):
        deviceid = self.kwargs["pk"]
        self.device = get_object_or_404(Device, pk=deviceid)
        return {}

    def form_valid(self, form):
        deviceid = self.kwargs["pk"]
        device = get_object_or_404(Device, pk=deviceid)
        template = form.cleaned_data["mailtemplate"]
        recipients = []
        for recipient in form.cleaned_data["emailrecipients"]:
            if recipient[0] == "g":
                group = get_object_or_404(Group, pk=recipient[1:])
                recipients += group.lageruser_set.all().values_list("email")[0]
            else:
                recipients.append(get_object_or_404(Lageruser, pk=recipient[1:]).email)
        recipients = list(set(recipients))
        template.subject = form.cleaned_data["emailsubject"]
        template.body = form.cleaned_data["emailbody"]
        template.send(self.request, recipients, {"device": device, "user": self.request.user})
        if template.usage == "reminder" or template.usage == "overdue":
            device.currentlending.duedate_email = datetime.datetime.utcnow().replace(tzinfo=utc)
            device.currentlending.save()
        messages.success(self.request, _('Mail successfully sent'))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceArchive(SingleObjectTemplateResponseMixin, BaseDetailView):
    model = Device
    template_name = 'devices/device_archive.html'

    def post(self, request, **kwargs):
        device = self.get_object()
        if device.archived == None:
            device.archived = datetime.datetime.utcnow().replace(tzinfo=utc)
            device.room = None
            device.currentlending = None
            for ip in device.ipaddress_set.all():
                ip.device = None
                ip.save()
        else:
            device.archived = None
        device.save()
        reversion.set_comment(_("Device was archived".format(device.name)))
        messages.success(request, _("Device was archived."))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceTrash(SingleObjectTemplateResponseMixin, BaseDetailView):
    model = Device
    template_name = 'devices/device_trash.html'

    def post(self, request, **kwargs):
        device = self.get_object()
        if device.trashed == None:
            device.trashed = datetime.datetime.utcnow().replace(tzinfo=utc)
            device.room = None
            device.currentlending = None
            for ip in device.ipaddress_set.all():
                ip.device = None
                ip.save()

            try:
                template = MailTemplate.objects.get(usage="trashed")
            except:
                template = None
            if not template == None:
                recipients = []
                for recipient in template.default_recipients.all():
                    recipient = recipient.content_object
                    if isinstance(recipient, Group):
                        recipients += recipient.lageruser_set.all().values_list("email")[0]
                    else:
                        recipients.append(recipient.email)
                template.send(self.request, recipients, {"device": device, "user": self.request.user})
                messages.success(self.request, _('Mail successfully sent'))
        else:
            device.trashed = None
        device.save()

        reversion.set_comment(_("Device was trashed".format(device.name)))
        messages.success(request, _("Device was trashed."))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.change_device', raise_exception=True)
class DeviceStorage(SingleObjectMixin, FormView):
    model = Device
    form_class = DeviceStorageForm
    template_name = 'devices/device_storage.html'

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(DeviceStorage, self).get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        device = self.get_object()
        try:
            if device.department:
                dep = device.department.name
            else:
                dep = "all"
            roomid = settings.STORAGE_ROOM[dep]
            room = get_object_or_404(Room, id=roomid)
        except:
            messages.error(self.request,
                           _("Could not move to storage. No room specified. Please contact your administrator."))
            return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))
        device.room = room
        device.save()
        for ipaddress in device.ipaddress_set.all():
            ipaddress.device = None
            ipaddress.save()
        if form.cleaned_data["send_mail"]:
            try:
                template = MailTemplate.objects.get(usage="room")
            except:
                template = None
            if not template == None:
                recipients = []
                for recipient in template.default_recipients.all():
                    recipient = recipient.content_object
                    if isinstance(recipient, Group):
                        recipients += recipient.lageruser_set.all().values_list("email")[0]
                    else:
                        recipients.append(recipient.email)
                template.send(self.request, recipients, {"device": device, "user": self.request.user})
                messages.success(self.request, _('Mail successfully sent'))

        messages.success(self.request, _("Device was moved to storage."))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


@permission_required('devices.read_device', raise_exception=True)
class DeviceBookmark(SingleObjectTemplateResponseMixin, BaseDetailView):
    model = Device

    def post(self, request, **kwargs):
        device = self.get_object()
        if device.bookmarkers.filter(id=request.user.id).exists():
            bookmark = Bookmark.objects.get(user=request.user, device=device)
            bookmark.delete()
            messages.success(request, _("Bookmark was removed"))
        else:
            bookmark = Bookmark(device=device, user=request.user)
            bookmark.save()
            messages.success(request, _("Device was bookmarked."))
        return HttpResponseRedirect(reverse("device-detail", kwargs={"pk": device.pk}))


class TemplateList(PaginationMixin, ListView):
    model = Template
    context_object_name = 'template_list'

    def get_context_data(self, **kwargs):
        context = super(TemplateList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("template-list"), _("Templates")), ]

        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])
        return context


class TemplateCreate(CreateView):
    model = Template
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(TemplateCreate, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("template-list"), _("Templates")),
            ("", _("Create new devicetemplate"))]
        return context


class TemplateUpdate(UpdateView):
    model = Template
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(TemplateUpdate, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("template-list"), _("Templates")),
            ("", _("Edit: {0}".format(self.object.templatename)))]
        return context


class TemplateDelete(DeleteView):
    model = Template
    success_url = reverse_lazy('device-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        context = super(TemplateDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("template-list"), _("Templates")),
            ("", _("Delete: {0}".format(self.object.templatename)))]
        return context


class NoteCreate(CreateView):
    model = Note
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_initial(self):
        initial = super(NoteCreate, self).get_initial()
        initial["device"] = get_object_or_404(Device, pk=self.kwargs["pk"])
        initial["creator"] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(NoteCreate, self).get_context_data(**kwargs)
        device = get_object_or_404(Device, pk=self.kwargs["pk"])
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": device.pk}), device),
            ("", _("Notes")),
            ("", _("Create new note"))]
        return context


class NoteUpdate(UpdateView):
    model = Note
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_success_url(self):
        return reverse_lazy("device-detail", kwargs={"pk": self.object.device.pk})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(NoteUpdate, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["object"].device.pk}), context["object"].device.name),
            ("", _("Edit"))]
        return context


class NoteDelete(DeleteView):
    model = Note
    template_name = 'devices/base_delete.html'

    def get_success_url(self):
        return reverse_lazy("device-detail", kwargs={"pk": self.object.device.pk})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(NoteDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["object"].device.pk}), context["object"].device.name),
            ("", _("Delete"))]
        return context


class PictureCreate(CreateView):
    model = Picture
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_initial(self):
        initial = super(PictureCreate, self).get_initial()
        initial["device"] = get_object_or_404(Device, pk=self.kwargs["pk"])
        initial["creator"] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super(PictureCreate, self).get_context_data(**kwargs)
        device = get_object_or_404(Device, pk=self.kwargs["pk"])
        context["enctype"] = "multipart/form-data"
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": device.pk}), device),
            ("", _("Notes")),
            ("", _("Create new note"))]
        return context


class PictureUpdate(UpdateView):
    model = Picture
    template_name = 'devices/base_form.html'
    fields = '__all__'

    def get_success_url(self):
        return reverse_lazy("device-detail", kwargs={"pk": self.object.device.pk})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(PictureUpdate, self).get_context_data(**kwargs)
        context["enctype"] = "multipart/form-data"
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["object"].device.pk}), context["object"].device.name),
            ("", _("Edit"))]
        return context


class PictureDelete(DeleteView):
    model = Picture
    template_name = 'devices/base_delete.html'

    def get_success_url(self):
        return reverse_lazy("device-detail", kwargs={"pk": self.object.device.pk})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(PictureDelete, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("device-list"), _("Devices")),
            (reverse("device-detail", kwargs={"pk": context["object"].device.pk}), context["object"].device.name),
            ("", _("Delete"))]
        return context


class Search(TemplateView):
    template_name = 'devices/search.html'
    form_class = SearchForm

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(Search, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [("", _("Search"))]
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        searchlist = self.request.POST["searchname"].split(" ")
        for i, item in enumerate(searchlist):
            if "." in item:
                is_ip = True
                for element in item.split("."):
                    try:
                        intelement = int(element)
                        if not (0 <= intelement <= 255):
                            is_ip = False
                    except:
                        is_ip = False
                if is_ip:
                    searchlist[i] = "ipaddress: " + item
            elif len(item) == 7:
                try:
                    int(item)
                    searchlist[i] = "id: " + item
                except:
                    pass
        context["searchterm"] = " ".join(searchlist)

        return render(request, self.template_name, context)


