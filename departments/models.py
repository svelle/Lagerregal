# from django.db import models
# from django.utils.translation import ugettext_lazy as _
#
# class Department(models.Model):
#     name = models.CharField(max_length=40, unique=True)
#
#     def __unicode__(self):
#         return self.name
#
#     class Meta:
#         verbose_name = _('Department')
#         verbose_name_plural = _('Departments')
#         permissions = (
#             ("read_department", _("Can read Departments")),
#             ("add_department_user", _("Can add a User to a Department")),
#             ("delete_department_user", _("Can remove a User from a Department")),
#         )