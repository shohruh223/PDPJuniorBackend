from .branch import BranchAdmin
from .mentor import MentorAdmin
from .portfolio import PortfolioAdmin
from .month_hero import MonthHeroAdmin
from .coin import CoinProductAdmin, CoinOrderAdmin
from .gallery import GalleryPostAdmin
from .payment import StudentInvoiceAdmin, StudentPaymentHistoryAdmin
from .marks import StudentMarkAdmin
from .question import *
from .auth import *
from .test import *


from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group
from django.urls import path
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from app.admin.mixins import RowActionsAdminMixin
from app.admin.data_transfer_views import admin_db_export, admin_db_import


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class GroupAdmin(RowActionsAdminMixin, DjangoGroupAdmin):
    def get_model_perms(self, request):
        return {}


try:
    admin.site.unregister(BlacklistedToken)
except admin.sites.NotRegistered:
    pass


try:
    admin.site.unregister(OutstandingToken)
except admin.sites.NotRegistered:
    pass


admin.site.site_header = "PDP Junior boshqaruv paneli"
admin.site.site_title = "PDP Junior Admin"
admin.site.index_title = "Boshqaruv markazi"

_original_get_urls = admin.site.get_urls


def _get_urls():
    custom = [
        path(
            "data-transfer/export/",
            admin.site.admin_view(admin_db_export),
            name="pdp_db_export",
        ),
        path(
            "data-transfer/import/",
            admin.site.admin_view(admin_db_import),
            name="pdp_db_import",
        ),
    ]
    return custom + _original_get_urls()


admin.site.get_urls = _get_urls
