from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic import TemplateView

from standup.status.forms import StatusizeForm
from standup.status.models import Status, Team, Project, StandupUser
from standup.status.utils import enddate, startdate


class PaginateStatusesMixin(object):
    def paginate_statuses(self, per_page=20):
        qs = self.get_status_queryset()
        page = self.request.GET.get('page')
        paginator = Paginator(qs, per_page)
        try:
            statuses = paginator.page(page)
        except PageNotAnInteger:
            statuses = paginator.page(1)
        except EmptyPage:
            statuses = paginator.page(paginator.num_pages)

        return statuses

    def get_status_queryset(self):
        qs = Status.objects.filter(reply_to=None)
        start = startdate(self.request)
        if start:
            end = enddate(self.request)
            if not end:
                end = start

            qs = qs.filter(created__range=(start, end))

        return qs

    def get_context_data(self, **kwargs):
        cxt = super().get_context_data(**kwargs)
        cxt['statuses'] = self.paginate_statuses()
        return cxt


class HomeView(PaginateStatusesMixin, TemplateView):
    template_name = 'status/index.html'


class WeeklyView(PaginateStatusesMixin, TemplateView):
    template_name = 'status/weekly.html'

    def get_status_queryset(self):
        qs = super().get_status_queryset()
        return qs.order_by('user_id', '-created')


class TeamView(PaginateStatusesMixin, DetailView):
    template_name = 'status/team.html'
    model = Team
    context_object_name = 'team'

    def get_status_queryset(self):
        return self.object.statuses()


class ProjectView(PaginateStatusesMixin, DetailView):
    template_name = 'status/project.html'
    model = Project
    context_object_name = 'project'

    def get_status_queryset(self):
        return self.object.statuses.filter(reply_to=None)


class StatusView(PaginateStatusesMixin, TemplateView):
    template_name = 'status/status.html'

    def get_status_queryset(self):
        return Status.objects.filter(pk=self.kwargs['pk'])


class UserView(PaginateStatusesMixin, DetailView):
    template_name = 'status/user.html'
    model = StandupUser
    context_object_name = 'suser'

    def get_status_queryset(self):
        return self.object.statuses.filter(reply_to=None)


@require_POST
def statusize(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    data = request.POST.dict()
    data['user'] = request.user.profile.id
    form = StatusizeForm(data)
    if form.is_valid():
        form.save()
    else:
        messages.error(request, 'Form error. Please try again.')
        messages.error(request, form.errors)

    referrer = request.META.get('HTTP_REFERER', '/')
    return HttpResponseRedirect(data.get('redirect_to', referrer))


home_view = HomeView.as_view()
