# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView, FormView
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied

from users.models import Lageruser, Department, DepartmentUser
from users.forms import DepartmentAddUserForm
from Lagerregal import settings
from Lagerregal.utils import PaginationMixin
from devices.forms import ViewForm, VIEWSORTING, FilterForm
from permission.decorators import permission_required
from django.shortcuts import get_object_or_404


class DepartmentList(PaginationMixin, ListView):
    model = Department
    context_object_name = 'department_list'

    def get_queryset(self):
        sections = Department.objects.all()
        self.filterstring = self.kwargs.pop("filter", None)

        # filter departments
        if self.filterstring:
            sections = sections.filter(name__icontains=self.filterstring)

        self.viewsorting = self.kwargs.pop("sorting", "name")

        # sort view by ID or name
        if self.viewsorting in [s[0] for s in VIEWSORTING]:
            sections = sections.order_by(self.viewsorting)

        return sections


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DepartmentList, self).get_context_data(**kwargs)
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments"))]
        context["viewform"] = ViewForm(initial={"viewsorting": self.viewsorting})

        # filtering
        if self.filterstring:
            context["filterform"] = FilterForm(initial={"filterstring": self.filterstring})
        else:
            context["filterform"] = FilterForm()

        # add page number to breadcrumbs, if there are multiple pages
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])

        return context


class DepartmentDetail(DetailView):
    model = Department
    context_object_name = 'department'
    template_name = "users/department_detail.html"

    def get_context_data(self, **kwargs):
        context = super(DepartmentDetail, self).get_context_data(**kwargs)
        # show users of department
        context['department_users'] = DepartmentUser.objects.select_related("user").filter(department=self.object)

        if "department" in settings.LABEL_TEMPLATES:
            context["label_js"] = ""
            for attribute in settings.LABEL_TEMPLATES["section"][1]:
                if attribute == "id":
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1:07d}');".format(attribute, getattr(
                        context["department"], attribute))
                else:
                    context["label_js"] += "\n" + "label.setObjectText('{0}', '{1}');".format(attribute, getattr(
                        context["department"], attribute))

        # adds department name to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments")),
            (reverse("department-detail", kwargs={"pk": context["object"].pk}), context["object"].name)]

        return context


class DepartmentCreate(CreateView):
    model = Department
    success_url = reverse_lazy('department-list')
    template_name = 'devices/base_form.html'
    fields = "__all__"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DepartmentCreate, self).get_context_data(**kwargs)
        context['type'] = "section"

        # adds "create new department" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("section-list"), _("Departments")),
            ("", _("Create new department"))]

        return context

    def form_valid(self, form):
        '''method for providing form element to get name of new department'''
        response = super(DepartmentCreate, self).form_valid(form)
        department_user = DepartmentUser(user=self.request.user, department=self.object, role="a")
        department_user.save()

        return response


@permission_required('users.change_department', raise_exception=True)
class DepartmentUpdate(UpdateView):
    model = Department
    success_url = reverse_lazy('department-list')
    template_name = 'devices/base_form.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DepartmentUpdate, self).get_context_data(**kwargs)

        # adds "Edit" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments")),
            (reverse("department-detail", kwargs={"pk": self.object.pk}), self.object),
            ("", _("Edit"))]

        return context


@permission_required('users.delete_department', raise_exception=True)
class DepartmentDelete(DeleteView):
    model = Department
    success_url = reverse_lazy('department-list')
    template_name = 'devices/base_delete.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DepartmentDelete, self).get_context_data(**kwargs)

        # should add "Delet" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments")),
            (reverse("department-detail", kwargs={"pk": self.object.pk}), self.object),
            ("", _("Delete"))]

        return context

######################################################################################################################
#                                       department related user actions                                              #
######################################################################################################################

class DepartmentAddUser(FormView):
    form_class = DepartmentAddUserForm
    template_name = 'devices/base_form.html'

    def get_success_url(self):
        return reverse("department-detail", kwargs={"pk": self.department.pk})


    def get_context_data(self, **kwargs):
        self.department = get_object_or_404(Department, id=self.kwargs.get("pk", ""))

        # check permission to add user
        if not self.request.user.has_perm("users.add_department_user", self.department):
            raise PermissionDenied

        context = super(DepartmentAddUser, self).get_context_data(**kwargs)
        context["form"].fields["department"].initial = self.department
        context["form"].fields["user"].queryset = Lageruser.objects.exclude(departments__id=self.department.id)

        # adds "Add User" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments")),
            (reverse("department-detail", kwargs={"pk": self.department.pk}), self.department),
            ("", _("Add User"))]

        return context

    def form_valid(self, form):
        self.department = get_object_or_404(Department, id=self.kwargs.get("pk", ""))

        if not self.department in form.cleaned_data["user"].departments.all():
            department_user = DepartmentUser(user=form.cleaned_data["user"], department=form.cleaned_data["department"],
                                            role=form.cleaned_data["role"])
            department_user.save()
            if form.cleaned_data["user"].main_department == None:
                form.cleaned_data["user"].main_department = form.cleaned_data["department"]

        return HttpResponseRedirect(reverse("department-detail", kwargs={"pk": self.department.pk}))


@permission_required('users.delete_department_user', raise_exception=True)
class DepartmentDeleteUser(DeleteView):
    model = DepartmentUser
    template_name = 'devices/base_delete.html'

    def get_success_url(self):
        return reverse("department-detail", kwargs={"pk": self.object.department.pk})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DepartmentDeleteUser, self).get_context_data(**kwargs)

        # should add "Delete" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("department-list"), _("Departments")),
            (reverse("department-detail", kwargs={"pk": self.object.department.pk}), self.object.department),
            ("", _("Remove User"))]
        return context
