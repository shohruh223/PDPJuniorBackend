from .branch import BranchAdmin
from .mentor import MentorAdmin
from .portfolio import PortfolioAdmin
from .news import NewsAdmin
from .month_hero import MonthHeroAdmin
from .coin import CoinProductAdmin, CoinOrderAdmin
from .gallery import GalleryPostAdmin
from .payment import StudentPaymentHistoryAdmin
from .marks import StudentMarkAdmin
from .test import TestSessionAdmin, TestSessionQuestionAdmin, TestSessionAnswerAdmin
from .question import *
from .auth import *


from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from app.admin.mixins import RowActionsAdminMixin


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class GroupAdmin(RowActionsAdminMixin, DjangoGroupAdmin):
    pass


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
