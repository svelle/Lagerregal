from django.db import models
from devices.models import Device
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
import reversion

# Create your models here.
class Devicetag(models.Model):

    name = models.CharField(max_length=200)
    devices = models.ManyToManyField(Device, related_name="tags")

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Devicetag')
        verbose_name_plural = _('Devicegtag')
        permissions = (
            ("read_devicetag", _("Can read Devicetag")),
        )

    def get_absolute_url(self):
        return reverse('devicetag-edit', kwargs={'pk': self.pk})

    def get_edit_url(self):
        return reverse('devicetag-edit', kwargs={'pk': self.pk})
