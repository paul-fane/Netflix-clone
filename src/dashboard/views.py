from django.shortcuts import render

from playlists.models import MovieProxy
from suggestions.models import Suggestion

def home_view(request):
    context = {}
    user = request.user
    if not user.is_authenticated:
        return render(request, 'home.html', context)
    context['endless_path'] = '/'
    suggestion_qs = Suggestion.objects.filter(user=user, did_rate=False)
    max_movies = 50
    request.session['total-new-suggestions'] = suggestion_qs.count()
    if suggestion_qs.exists():
        movie_ids = suggestion_qs.order_by("-value").values_list('object_id', flat=True)
        qs = MovieProxy.objects.by_id_order(movie_ids)
        context['object_list'] = qs[:max_movies]
    else:
        context['object_list'] = MovieProxy.objects.all().order_by("?")[:max_movies]
    if request.htmx:
        return render(request, "movies/snippet/infinite.html", context)
    return render(request, "dashboard/main.html", context)