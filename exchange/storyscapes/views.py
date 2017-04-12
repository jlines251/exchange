from .models.base import Story
from django.http import HttpResponse
import json

from geonode.maps.models import Map, MapSnapshot
from geonode.maps.views import clean_config

from .models.base import StoryChapter

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from geonode.utils import resolve_object

from geonode.layers.views import _PERMISSION_MSG_GENERIC, _PERMISSION_MSG_VIEW, _PERMISSION_MSG_DELETE

_PERMISSION_MSG_LOGIN = 'You must be logged in to save this story'
_PERMISSION_MSG_SAVE = 'You are not permitted to save or edit this story'


def save_story(request, storyid):
    if not request.user.is_authenticated():
        return HttpResponse(
                _PERMISSION_MSG_LOGIN,
                status=401,
                content_type="text/plain"
        )

    story_obj = Story.objects.get(id=storyid)
    if not request.user.has_perm('change_resourcebase', story_obj):
        return HttpResponse(
                _PERMISSION_MSG_SAVE,
                status=401,
                content_type="text/plain"
        )

    try:
        story_obj.update_from_viewer(request.body)
        return HttpResponse(json.dumps(story_obj.viewer_json(request.user)))
    except ValueError as e:
        return HttpResponse(
                "The server could not understand the request." + str(e),
                content_type="text/plain",
                status=400
        )


def new_chapter_json(request):

    '''
    Exracted from geonode.maps.views.new_map_json
    :param request:
    :return:
    '''

    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to save new maps',
                content_type="text/plain",
                status=401
            )

        map_obj = Map(owner=request.user, zoom=0,
                      center_x=0, center_y=0)
        map_obj.save()
        map_obj.set_default_permissions()

        # If the body has been read already, use an empty string.
        # See https://github.com/django/django/commit/58d555caf527d6f1bdfeab14527484e4cca68648
        # for a better exception to catch when we move to Django 1.7.
        try:
            body = request.body

            if isinstance(body, basestring):
                body = json.loads(body)
                story_id = body.get('story_id', 0)
                story_obj = Story.objects.get(id=story_id)
                mapping = StoryChapter()
                mapping.chapter_index = body['chapter_index']
                mapping.map = map_obj
                mapping.story = story_obj
                mapping.save()

        except Exception as e:
            print e
            body = ''

        try:
            map_obj.update_from_viewer(body)
            MapSnapshot.objects.create(
                config=clean_config(body),
                map=map_obj,
                user=request.user)
        except ValueError as e:
            return HttpResponse(str(e), status=400)
        else:
            return HttpResponse(
                json.dumps({'id': map_obj.id}),
                status=200,
                content_type='application/json'
            )
    else:
        return HttpResponse(status=405)


def draft_view(request, story_id, template='composer/editor.html'):

    story_obj = _resolve_story(request, story_id, 'base.change_resourcebase', _PERMISSION_MSG_SAVE)

    config = story_obj.viewer_json(request.user)

    return render_to_response(template, RequestContext(request, {
        'config': json.dumps(config),
        'story': story_obj
    }))

@login_required
def story_draft(request, storyid, template):
    return draft_view(request, storyid, template)


def _resolve_story(request, id, permission='base.change_resourcebase',
                 msg=_PERMISSION_MSG_GENERIC, **kwargs):
    '''
    Resolve the Map by the provided typename and check the optional permission.
    '''
    if id.isdigit():
        key = 'pk'
    else:
        key = 'urlsuffix'
    return resolve_object(request, Story, {key: id}, permission=permission,
                          permission_msg=msg, **kwargs)


def new_story_json(request):
    if not request.user.is_authenticated():
        return HttpResponse(
                'You must be logged in to save new maps',
                content_type="text/plain",
                status=401
        )
    story_obj = Story(owner=request.user)
    story_obj.save()

    try:
        body = request.body
    except Exception:
        body = ''

    try:
        story_obj.update_from_viewer(body)
    except ValueError as e:
        return HttpResponse(str(e), status=400)
    else:
        return HttpResponse(
                json.dumps({'id': story_obj.id}),
                status=200,
                content_type='application/json'
        )
