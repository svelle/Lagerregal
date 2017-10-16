from django.views.generic import DetailView, TemplateView, ListView
from reversion.models import Version
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.contrib.auth.models import Permission
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse


from users.models import Lageruser
from devices.models import Lending
from users.forms import SettingsForm, AvatarForm
from Lagerregal.utils import PaginationMixin
from network.models import IpAddress
from network.forms import UserIpAddressForm
from devices.forms import DepartmentFilterForm
from django.db.models import Q


class UserList(PaginationMixin, ListView):
    model = Lageruser
    context_object_name = 'user_list'
    template_name = "users/user_list.html"

    def get_queryset(self):
        users = Lageruser.objects.all()
        self.filterstring = self.kwargs.pop("filter", "")

        # filtering by department
        if self.request.user.departments.count() > 0:
            self.departmentfilter = self.kwargs.get("department", "my")
        else:
            self.departmentfilter = self.kwargs.get("department", "all")

        if self.departmentfilter != "all" and self.departmentfilter != "my":
            users = users.filter(departments__id=self.departmentfilter)
        elif self.departmentfilter == "my":
            users = users.filter(departments__in=self.request.user.departments.all())

        # filter by given filter string
        if self.filterstring != "":
            users = users.filter(Q(username__icontains=self.filterstring) |
                                 Q(first_name__icontains=self.filterstring) |
                                 Q(last_name__icontains=self.filterstring))

        return users

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserList, self).get_context_data(**kwargs)

        # adds "Users" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("user-list"), _("Users")), ]
        context["filterform"] = DepartmentFilterForm(initial={"filterstring": self.filterstring,
                                                              "departmentfilter": self.departmentfilter})

        # add page number to breadcrumbs if there are multiple pages
        if context["is_paginated"] and context["page_obj"].number > 1:
            context["breadcrumbs"].append(["", context["page_obj"].number])

        return context


class ProfileView(DetailView):
    model = Lageruser
    context_object_name = 'profileuser'

    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ProfileView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        # shows list of edits made by user
        context['edits'] = Version.objects.select_related("revision", "revision__user"
        ).filter(content_type_id=ContentType.objects.get(model='device').id,
                 revision__user=context["profileuser"]).order_by("-pk")

        # shows list of user lendings
        context['lendings'] = Lending.objects.select_related("device", "device__room", "device__room__building",
                                                             "owner").filter(owner=context["profileuser"],
                                                                             returndate=None)

        # shows list of user related ip-adresses
        context['ipaddresses'] = IpAddress.objects.filter(user=context["profileuser"])
        context['ipaddressform'] = UserIpAddressForm()
        context["ipaddressform"].fields["ipaddresses"].queryset = IpAddress.objects.filter(department__in=self.object.departments.all(), device=None, user=None)

        # shows list of users permission (group permission, user permission)
        context["permission_list"] = Permission.objects.all().values("name", "codename", "content_type__app_label")
        context["userperms"] = [x[0] for x in context["profileuser"].user_permissions.values_list("codename")]
        context["groupperms"] = [x.split(".")[1] for x in context["profileuser"].get_group_permissions()]

        # adds username to breadcrumbs
        context["breadcrumbs"] = [(reverse("user-list"), _("Users")), ("", context["profileuser"])]

        return context


class UserprofileView(TemplateView):
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UserprofileView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["profileuser"] = self.request.user

        # shows list of edits made by user
        context['edits'] = Version.objects.select_related("revision", "revision__user"
        ).filter(content_type_id=ContentType.objects.get(model='device').id,
                 revision__user=context["profileuser"]).order_by("-pk")

        # shows list users lendings
        context['lendings'] = Lending.objects.select_related("device", "device__room", "device__room__building",
                                                             "owner").filter(owner=context["profileuser"],
                                                                             returndate=None)

        # shows user related ip-adresses
        context['ipaddresses'] = IpAddress.objects.filter(user=context["profileuser"])
        context['ipaddressform'] = UserIpAddressForm()

        # shows list of users permissions (group permissions, user permissions)
        context["permission_list"] = Permission.objects.all().values("name", "codename", "content_type__app_label")
        context["userperms"] = [x[0] for x in context["profileuser"].user_permissions.values_list("codename")]
        context["groupperms"] = [x.split(".")[1] for x in context["profileuser"].get_group_permissions()]

        # adds user name to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("user-list"), _("Users")),
            (reverse("userprofile", kwargs={"pk": self.request.user.pk}), self.request.user), ]

        return context


class UsersettingsView(TemplateView):
    template_name = "users/settings.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(UsersettingsView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        if self.request.method != "POST":
            context['settingsform'] = SettingsForm(instance=self.request.user)
            context['avatarform'] = AvatarForm(instance=self.request.user)

        if "settingsform" in context:
            context['settingsform'].fields["main_department"].queryset = self.request.user.departments.all()

        # adds "Settings" to breadcrumbs
        context["breadcrumbs"] = [
            (reverse("userprofile", kwargs={"pk": self.request.user.pk}), self.request.user),
            ("", _("Settings"))]

        return context

    def post(self, request):
        context = self.get_context_data()
        context["settingsform"] = SettingsForm(instance=request.user)
        context["avatarform"] = AvatarForm(instance=request.user)
        context['settingsform'].fields["main_department"].queryset = self.request.user.departments.all()

        # handle language settings and use saved settings of user as default
        if "language" in request.POST:
            request.user.language = request.POST["language"]
            request.user.save()
            translation.activate(request.POST["language"])
            request.session[translation.LANGUAGE_SESSION_KEY] = request.POST["language"]
            return HttpResponseRedirect(reverse("usersettings"))

        # handle pagelength/ timezone/ theme settings and use saved settings of user as default
        elif "pagelength" in request.POST or "timezone" in request.POST or "theme" in request.POST:
            form = SettingsForm(request.POST)
            if form.is_valid():
                changed_data = False

                # change of pagelength settings
                if request.user.pagelength != form.cleaned_data["pagelength"]:
                    request.user.pagelength = form.cleaned_data["pagelength"]
                    changed_data = True

                # change of timezone settings
                if request.user.timezone != form.cleaned_data["timezone"]:
                    request.user.timezone = form.cleaned_data["timezone"]
                    changed_data = True

                # change of main department settings
                if request.user.main_department != form.cleaned_data["main_department"]:
                    request.user.main_department = form.cleaned_data["main_department"]
                    changed_data = True

                # change of theme settings
                if request.user.theme != form.cleaned_data["theme"]:
                    request.user.theme = form.cleaned_data["theme"]
                    changed_data = True

                # save changes
                if changed_data:
                    request.user.save()

                # save success message
                messages.success(self.request, _('Settings were successfully updated'))
            context["settingsform"] = form

        # handle given avatar
        elif "avatar" in request.FILES or "avatar" in request.POST:
            if request.user.avatar:
                tempavatar = request.user.avatar
            else:
                tempavatar = None

            form = AvatarForm(request.POST, request.FILES, instance=request.user)

            if form.is_valid():
                if form.cleaned_data["avatar_clear"] and request.user.avatar != None:
                    request.user.avatar.delete()
                    request.user.avatar = None
                    request.user.save()

                if tempavatar != None:
                    tempavatar.storage.delete(tempavatar)
                form.save()
            context["avatarform"] = form

        return render(request, self.template_name, context)


#######################################################################################################################
#                                                       Login                                                         #
#######################################################################################################################
@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html', redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    if request.method == "POST":
        redirect_to = request.GET.get(redirect_field_name, '')
        form = authentication_form(data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url("/")

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            request.session['django_language'] = request.user.language
            return HttpResponseRedirect(redirect_to)
    else:
        redirect_to = request.POST.get(redirect_field_name, '')
        form = authentication_form(request)

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }

    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)



