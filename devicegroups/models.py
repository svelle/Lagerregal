from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from reversion import revisions as reversion

from users.models import Department

# Create your models here.

class Devicegroup(models.Model):
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Devicegroup')
        verbose_name_plural = _('Devicegroups')
        permissions = (
            ("read_devicegroup", _("Can read Devicegroup")),
        )

    def get_absolute_url(self):
        return reverse('devicegroup-detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        return reverse('devicegroup-edit', kwargs={'pk': self.pk})


reversion.register(Devicegroup)
