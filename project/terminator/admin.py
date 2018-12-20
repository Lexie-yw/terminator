# -*- coding: UTF-8 -*-
#
# Copyright 2011, 2013 Leandro Regueiro
#
# This file is part of Terminator.
#
# Terminator is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Terminator is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Terminator. If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.utils import quote
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy, ungettext, ugettext as _

from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user
from guardian.utils import clean_orphan_obj_perms
from simple_history.admin import SimpleHistoryAdmin

from terminator.forms import (TerminatorConceptAdminForm,
                              TerminatorGlossaryAdminForm,
                              TerminatorTranslationAdminForm,
                              ConceptInLanguageAdminForm)
from terminator.models import *


try:
    from functools import lru_cache
except ImportError:
    from django.utils.lru_cache import lru_cache


class PartOfSpeechForLanguageInline(admin.TabularInline):
    model = PartOfSpeechForLanguage
    extra = 1

    def get_queryset(self, request):
        qs = super(PartOfSpeechForLanguageInline, self).get_queryset(request)
        qs = qs.select_related("part_of_speech")
        return qs


class AdministrativeStatusReasonForLanguageInline(admin.TabularInline):
    model = AdministrativeStatusReason.languages.through
    extra = 1
    verbose_name = _("Administrative status reason for language")
    verbose_name_plural = _("Administrative status reasons for language")

    def get_queryset(self, request):
        qs = super(AdministrativeStatusReasonForLanguageInline, self).get_queryset(request)
        qs = qs.select_related("administrativestatusreason")
        return qs


class LanguageAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'iso_code', 'description')
    ordering = ('iso_code',)
    search_fields = ['name', 'iso_code']
    filter_horizontal = ('grammatical_genders', 'grammatical_numbers')
    inlines = (PartOfSpeechForLanguageInline,
               AdministrativeStatusReasonForLanguageInline)


admin.site.register(Language, LanguageAdmin)


class PartOfSpeechAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'tbx_representation', 'description')
    ordering = ('name',)
    inlines = (PartOfSpeechForLanguageInline,)


admin.site.register(PartOfSpeech, PartOfSpeechAdmin)


class AdministrativeStatusReasonAdmin(admin.ModelAdmin):
    save_on_top = True
    filter_horizontal = ('languages',)


admin.site.register(AdministrativeStatusReason,
                    AdministrativeStatusReasonAdmin)


class ChangePermissionFromQS(object):
    """A mixin to determine change permission from the queryset.

    You must implement get_queryset() to filter by the appropriate
    permissions."""

    @lru_cache()
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return self.get_queryset(request).exists()
        # if obj is not None, it exists in get_queryset(), so the user has the
        # required permission
        return True


class GlossaryAdmin(ChangePermissionFromQS, GuardedModelAdmin):
    save_on_top = True
    form = TerminatorGlossaryAdminForm
    filter_horizontal = ('subscribers','subject_fields',)
    list_display = ('name', 'description')
    ordering = ('name',)
    search_fields = ['name']

    def get_queryset(self, request):
        qs = super(GlossaryAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return get_objects_for_user(request.user,
                                    ['is_owner_for_this_glossary'], qs, False)

    def get_exclude(self, request, obj=None):
        if not obj:
            return ["subject_fields"]
        return []


    def save_model(self, request, obj, form, change):
        super(GlossaryAdmin, self).save_model(request, obj, form, change)

        if not change:
            obj.assign_terminologist_permissions(request.user)
            obj.assign_lexicographer_permissions(request.user)
            obj.assign_owner_permissions(request.user)

    def delete_model(self, request, obj):
        super(GlossaryAdmin, self).delete_model(request, obj)
        # Remove all orphaned per object permissions after deleting the
        # glossary instance.
        clean_orphan_obj_perms()

    def get_fields(self, request, obj=None):
        fields = super(GlossaryAdmin, self).get_fields(request, obj)
        if not settings.FEATURES.get('subscription', True):
            # This saves a bit of time, and removes the field which will be
            # confusing if the feature is disabled.
            if 'subscribers' in fields:
                fields = list(fields)
                fields.remove('subscribers')
        return fields

    def response_change(self, request, obj):
        return HttpResponseRedirect(obj.get_absolute_url())


admin.site.register(Glossary, GlossaryAdmin)


class DefinitionInline(admin.TabularInline):
    model = Definition
    extra = 0
    fields = ('language', 'text', 'is_finalized', 'source')
    readonly_fields = ('is_finalized', )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('language',)
        return self.readonly_fields

    def get_queryset(self, request):
        qs = super(DefinitionInline, self).get_queryset(request)
        qs = qs.order_by('-is_finalized', 'language_id')
        return qs

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class ExternalResourceInline(admin.TabularInline):
    model = ExternalResource
    extra = 0
    fields =("address", "link_type", "description")

    def get_queryset(self, request):
        qs = super(ExternalResourceInline, self).get_queryset(request)
        qs = qs.filter(language=None)
        return qs

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class ConceptAdmin(ChangePermissionFromQS, admin.ModelAdmin):
    save_on_top = True
    form = TerminatorConceptAdminForm
    filter_horizontal = ('related_concepts',)
    list_display = ('id', 'glossary', 'repr_cache', 'subject_field', 'broader_concept')
    search_fields = ['id', 'repr_cache']
    ordering = ('id',)
    list_filter = [('glossary', admin.RelatedOnlyFieldListFilter)]
    inlines = [DefinitionInline, ExternalResourceInline]
    readonly_fields = ('glossary',)
    fieldsets = (
            (None, {
                'fields': (('glossary', 'subject_field'), 'related_concepts', 'broader_concept'),
            }),
    )

    @lru_cache()
    def user_has_access(self, user, glossary):
        return user.has_perm("is_lexicographer_in_this_glossary", glossary)

    @lru_cache()
    def has_add_permission(self, request):
        allowed = super(ConceptAdmin, self).has_add_permission(request)
        glossary_id = self._glossary_parameter(request)
        if glossary_id:
            glossary = Glossary.objects.get(pk=glossary_id)
            return self.user_has_access(request.user, glossary)
        return allowed

    def has_delete_permission(self, request, obj=None):
        allowed = super(ConceptAdmin, self).has_delete_permission(request, obj)
        if obj:
            return self.user_has_access(request.user, obj.glossary)
        return allowed

    def get_readonly_fields(self, request, obj=None):
        # Glossary should be readonly, except when adding a new model.
        if obj:
            return self.readonly_fields
        fields = list(self.readonly_fields)
        fields.remove('glossary')
        return fields

    def get_fieldsets(self, request, obj=None):
        if obj or self._glossary_parameter(request):
            return self.fieldsets
        # We need to know the glossary: we can't afford to load all the concept
        # fields without filtering. If there is no obj, we'll redirect to edit
        # this after adding.
        return (
            (None, {
                'description': _("Related concepts can be specified after adding the concept."),
                'fields': ('glossary',),
            }),
        )

    def _glossary_parameter(self, request):
        return request.GET.get('glossary', None)

    def _glossaries_for(self, request):
        if not "_glossaries_qs" in dir(self):
            self._glossaries_qs = get_objects_for_user(request.user,
                                        ['is_lexicographer_in_this_glossary'],
                                        Glossary, False)
        return self._glossaries_qs

    def get_queryset(self, request):
        qs = super(ConceptAdmin, self).get_queryset(request).select_related(
               "glossary")
        if request.user.is_superuser:
            return qs
        return qs.filter(glossary__in=self._glossaries_for(request))

    def _concepts_in(self, glossary_id):
        return Concept.objects.filter(glossary_id=glossary_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        glossary_id = self._glossary_parameter(request)

        if not glossary_id:
            if db_field.name == "glossary":
                # only show glossaries where the user has permission
                kwargs["queryset"] = self._glossaries_for(request)
            return super(ConceptAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

        # we have a glossary_id
        if db_field.name == "glossary":
            # Only show the single glossary, since the other fields will
            # only be valid for that glossary. But only do this if the user has
            # the necessary permission for glossary_id!
            kwargs["queryset"] = self._glossaries_for(request).filter(id=glossary_id)
            #kwargs["disabled"] = True # doesn't work :-(
        elif db_field.name == "broader_concept":
            kwargs["queryset"] = self._concepts_in(glossary_id)
        elif db_field.name == "subject_field":
            kwargs["queryset"] = Glossary.objects.get(id=glossary_id).subject_fields

        return super(ConceptAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        glossary_id = self._glossary_parameter(request)
        if not glossary_id:
            return super(ConceptAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

        # only show concepts from this glossary
        if db_field.name == "related_concepts":
            kwargs["queryset"] = self._concepts_in(glossary_id)
        return super(ConceptAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def response_add(self, request, obj, post_url_continue=None):
        if self._glossary_parameter(request):
            # The user added this to a specific glossary, probably from the
            # glossary detail page. All fields were available, so let's go
            # back to the concept's page.
            return HttpResponseRedirect(obj.get_absolute_url())
        else:
            # Let's now edit the rest of the fields since we know the glossary
            opts = obj._meta
            pk_value = obj._get_pk_val()
            obj_url = reverse(
                'admin:%s_%s_change' % (opts.app_label, opts.model_name),
                args=(quote(pk_value),),
                current_app=self.admin_site.name,
            )
            return HttpResponseRedirect(obj_url)

    def response_change(self, request, obj):
        return HttpResponseRedirect(obj.get_absolute_url())

admin.site.register(Concept, ConceptAdmin)


class ConceptLanguageMixin(object):
    """Provides some features for models with concept and language.

    This can be mixed into ModelAdmins where the model has a concept and
    language field. If the GET parameters concept and language are passed
    to the admin add form, it will limit the query to those two objects and
    not display any other alternatives. It is therefore a way to add
    a model with these foreign fields prescribed by the URL.

    Only superusers can add without these parameters."""

    raw_id_fields = ("concept",)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        try:
            self.get_concept_qs(request)
            return True
        except PermissionDenied:
            return False

    def get_readonly_fields(self, request, obj=None):
        # Concept and language should be readonly, except when adding a new
        # model.
        if obj:
            return self.readonly_fields
        fields = list(self.readonly_fields)
        fields.remove('concept')
        if 'language' in fields:
            # optional in ExternalResource
            fields.remove('language')
        return fields

    def get_concept_qs(self, request):
        obj_id = request.GET.get('concept', None)
        if obj_id:
            try:
                qs = Concept.objects.filter(pk=obj_id)
                concept = qs.first()
                if request.user.has_perm("is_lexicographer_in_this_glossary", concept.glossary):
                    return qs
            except Concept.DoesNotExist:
                raise PermissionDenied
        if request.user.is_superuser:
            return Concept.objects
        raise PermissionDenied

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "concept":
            kwargs["queryset"] = self.get_concept_qs(request)
        elif db_field.name == "language":
            obj_id = request.GET.get('language', None)
            if obj_id:
                kwargs["queryset"] = Language.objects.filter(pk=obj_id)
        return super(ConceptLanguageMixin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RelatedGlossaryListFilter(admin.SimpleListFilter):
    # A list filter for concept__glossary
    title = _('Glossary')
    parameter_name = 'glossary'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            glossaries = Glossary.objects.all()
        else:
            glossaries = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return [(glossary.pk, glossary.name) for glossary in glossaries]

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(concept__glossary__pk=self.value())
        return queryset


class ConceptInLanguageAdmin(ChangePermissionFromQS, admin.ModelAdmin):
    form = ConceptInLanguageAdminForm
    can_add = False
    readonly_fields = ("concept", "language", "translations_html", "definition_html")
    fields = (("concept", "language"), "translations_html", "definition_html", "summary", "is_finalized")
    list_display = ("concept", "language", 'is_finalized', 'date_html')
    list_filter = ('language', RelatedGlossaryListFilter, 'is_finalized', 'date')
    ordering = ('concept', 'language')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super(ConceptInLanguageAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_lexicographer_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(concept__glossary__in=inner_qs)

    def response_change(self, request, obj):
        return HttpResponseRedirect(obj.get_absolute_url())

admin.site.register(ConceptInLanguage, ConceptInLanguageAdmin)


class ContextSentenceInline(admin.TabularInline):
    model = ContextSentence
    extra = 1


class CorpusExampleInline(admin.TabularInline):
    model = CorpusExample
    extra = 1


class TranslationAdmin(ChangePermissionFromQS, ConceptLanguageMixin, admin.ModelAdmin):
    save_on_top = True
    form = TerminatorTranslationAdminForm
    # if changing the fieldsets, review get_fieldsets() as well
    fieldsets = (
            (None, {
                'fields': (('concept', 'language'), 'translation_text'),
            }),
            (_('Grammatical information'), {
                'fields': ('part_of_speech', 'grammatical_gender',
                    'grammatical_number')
            }),
            (_("Workflow status"), {
                'fields': (
                    'is_finalized',
                    ('administrative_status', 'administrative_status_reason'),
                    'note',
                ),
            }),
    )
    readonly_fields = ('concept', 'language')
    list_display = ('translation_text', 'language', 'concept', 'part_of_speech', 'administrative_status', 'is_finalized',)
    ordering = ('concept',)
    list_filter = [
        'language', RelatedGlossaryListFilter, 'is_finalized', 'administrative_status',
        'part_of_speech'
    ]
    search_fields = ['translation_text']
    inlines = [ContextSentenceInline, CorpusExampleInline]
    list_select_related = ('language', 'concept', 'part_of_speech', 'administrative_status')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Terms should be handled in the main app, not the admin.
            return self.readonly_fields + ("translation_text",)

        return super(TranslationAdmin, self).get_readonly_fields(request, obj)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(TranslationAdmin, self).get_fieldsets(request, obj)
        if not obj:
            return fieldsets

        # simplify by removing fields that can only get invalid values here
        # (the language relationships first need to be updated)
        language = obj.language
        fields = list(fieldsets[1][1]['fields'])
        if "grammatical_gender" in fields and not language.grammatical_genders.exists():
            fields.remove("grammatical_gender")
        if "grammatical_number" in fields and not language.grammatical_numbers.exists():
            fields.remove("grammatical_number")

        fieldsets[1][1]['fields'] = fields

        fields = list(fieldsets[2][1]['fields'][1])
        if "administrative_status_reason" in fields and \
                not language.administrativestatusreason_set.exists():
            fields.remove("administrative_status_reason")
            fieldsets[2][1]['fields'] = ('is_finalized', fields, 'note')

        return fieldsets

    @lru_cache()
    def get_queryset(self, request):
        qs = super(TranslationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(concept__glossary__in=inner_qs)


    def response_change(self, request, obj):
        return HttpResponseRedirect(obj.get_absolute_url())

admin.site.register(Translation, TranslationAdmin)


class TranslationOfConceptAdmin(TranslationAdmin):
    """A simpler form for translations of a concept in a language."""
    save_on_top = False
    list_display = ('translation_text', 'part_of_speech', 'administrative_status', 'is_finalized',)
    ordering = ('translation_text',)
    list_filter = [
        'is_finalized', 'administrative_status',
    ]
    show_full_result_count = False
    actions_selection_counter = False



myadmin = admin.AdminSite(name='myadmin')
myadmin.register(Translation, TranslationOfConceptAdmin)


class DefinitionAdmin(ChangePermissionFromQS, ConceptLanguageMixin, SimpleHistoryAdmin):
    save_on_top = True
    list_display = ('text', 'concept', 'language', 'is_finalized')
    ordering = ('concept',)
    list_filter = ['language', RelatedGlossaryListFilter, 'is_finalized']
    readonly_fields = ('concept', 'language',)
    search_fields = ['text']
    actions = ['mark_finalized']
    fieldsets = (
            (None, {
                'fields': (('concept', 'language'), 'text', 'source', 'is_finalized'),
            }),
    )

    def get_queryset(self, request):
        qs = super(DefinitionAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(concept__glossary__in=inner_qs)

    def response_change(self, request, obj):
        return HttpResponseRedirect(obj.get_absolute_url())

    def mark_finalized(modeladmin, request, queryset):
        queryset.update(is_finalized=True)
    mark_finalized.short_description = _(u"Mark selected definitions as finalized")

admin.site.register(Definition, DefinitionAdmin)



class AdministrativeStatusAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'tbx_representation', 'allows_reason', 'description')
    ordering = ('name',)

admin.site.register(AdministrativeStatus, AdministrativeStatusAdmin)



class ProposalAdmin(ChangePermissionFromQS, admin.ModelAdmin):
    save_on_top = True
    list_display = ('term', 'language', 'definition', 'sent_date', 'for_glossary')
    ordering = ('sent_date',)
    list_filter = [
            ('language', admin.RelatedOnlyFieldListFilter),
            ('for_glossary', admin.RelatedOnlyFieldListFilter),
            'sent_date',
            ('user', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['term', 'definition']
    actions = ['convert_proposals']

    def get_queryset(self, request):
        qs = super(ProposalAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_lexicographer_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(for_glossary__in=inner_qs)

    def convert_proposals(self, request, queryset):
        for proposal in queryset:
            concept = Concept(glossary=proposal.for_glossary)
            concept.save()
            translation = Translation(concept=concept,
                                      language=proposal.language,
                                      translation_text=proposal.term)
            translation.save()
            definition = Definition(concept=concept,
                                    language=proposal.language,
                                    text=proposal.definition)
            definition.save()
            obj_display = force_unicode(proposal)
            self.log_deletion(request, proposal, obj_display)
            #TODO maybe notify by email the users that sent the proposals
        rows_deleted = len(queryset)
        queryset.delete()
        self.message_user(request, ungettext('%(count)d proposal was '
                                             'successfully converted to '
                                             'translations and definitions in '
                                             'a new concept.',
                                             '%(count)d proposals were '
                                             'successfully converted to '
                                             'translations and definitions in '
                                             'a new concept.', rows_deleted) %
                                             {'count': rows_deleted})
    convert_proposals.short_description = _("Convert selected proposals to "
                                            "Translations and Definitions in "
                                            "a new concept")

if settings.FEATURES.get('proposals', False):
    admin.site.register(Proposal, ProposalAdmin)



class ExternalResourceAdmin(ConceptLanguageMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = ('address', 'concept', 'language', 'link_type', 'description')
    ordering = ('concept',)
    list_filter = [
            ('language', admin.RelatedOnlyFieldListFilter),
            RelatedGlossaryListFilter,
            ('link_type', admin.RelatedOnlyFieldListFilter),
    ]
    list_select_related = ('concept', 'language', 'link_type')
    search_fields = ['description', 'address']
    readonly_fields = ('concept',)
    fieldsets = (
            (None, {
                'fields': (('concept', 'language'), 'address', 'link_type', 'description'),
            }),
    )

    def get_queryset(self, request):
        qs = super(ExternalResourceAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(concept__glossary__in=inner_qs)

admin.site.register(ExternalResource, ExternalResourceAdmin)



class GrammaticalGenderAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'tbx_representation', 'description')
    ordering = ('name',)

admin.site.register(GrammaticalGender, GrammaticalGenderAdmin)



class GrammaticalNumberAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'tbx_representation', 'description')
    ordering = ('name',)

admin.site.register(GrammaticalNumber, GrammaticalNumberAdmin)



class ExternalLinkTypeAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'tbx_representation', 'description')
    ordering = ('name',)

admin.site.register(ExternalLinkType, ExternalLinkTypeAdmin)



class ContextSentenceAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('text', 'translation')
    ordering = ('translation',)
    fields = ('translation', 'text')
    readonly_fields = ('translation',)
    list_filter = ['translation__concept__glossary']

    def get_queryset(self, request):
        qs = super(ContextSentenceAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(translation__concept__glossary__in=inner_qs)

admin.site.register(ContextSentence, ContextSentenceAdmin)



class CorpusExampleAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('translation', 'address', 'description')
    ordering = ('translation',)
    fields = ('translation', 'address', 'description')
    readonly_fields = ('translation',)
    list_filter = ['translation__concept__glossary']

    def get_queryset(self, request):
        qs = super(CorpusExampleAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_terminologist_in_this_glossary'],
                                        Glossary, False)
        return qs.filter(translation__concept__glossary__in=inner_qs)

admin.site.register(CorpusExample, CorpusExampleAdmin)



class CollaborationRequestAdmin(ChangePermissionFromQS, admin.ModelAdmin):
    save_on_top = True
    list_display = ('for_glossary', 'user', 'collaboration_role', 'sent_date')
    ordering = ('sent_date',)
    list_filter = ['collaboration_role', ('for_glossary', admin.RelatedOnlyFieldListFilter), 'sent_date', 'user'] # many users?
    search_fields = ['user__username']
    actions = ['accept_collaboration_requests']

    def get_queryset(self, request):
        qs = super(CollaborationRequestAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        inner_qs = get_objects_for_user(request.user,
                                        ['is_owner_for_this_glossary'],
                                        Glossary, False)
        return qs.filter(for_glossary__in=inner_qs)

    #TODO replace the delete admin action with a wrapper around the default one
    # in order to send an email to all the collaboration request users telling
    # them that their requests were not approved.

    def delete_model(self, request, obj):
        # Send email messages only if allowed in the settings
        if settings.SEND_NOTIFICATION_EMAILS:
            mail_subject = _('[Terminator] collaboration request rejected')
            mail_body_data = {
                'role': obj.get_collaboration_role_display(),
                'glossary': obj.for_glossary
            }
            full_mail_text = (_('Your collaboration request as \"%(role)s\" '
                               'for glossary \"%(glossary)s\" was rejected by '
                               'the glossary owners.') % mail_body_data)
            send_mail(mail_subject, full_mail_text,
                      'donotreply@donotreply.com', [obj.user.email],
                      fail_silently=False)
        super(CollaborationRequestAdmin, self).delete_model(request, obj)

    def accept_collaboration_requests(self, request, queryset):
        for collaboration_request in queryset:
            collaboration_request.user.is_staff = True # Because we need to ensure this users will can enter the admin site to work
            mail_message = ""

            if collaboration_request.collaboration_role in ("T", "L", "O"):
                mail_message += _("Now you can manage translations, "
                                  "definitions, external resources, context "
                                  "sentences and corpus examples inside this "
                                  "glossary.")
                collaboration_request.for_glossary.assign_terminologist_permissions(collaboration_request.user)

            if collaboration_request.collaboration_role  in ("L", "O"):
                mail_message += _("\n\nAlso you can manage concepts and "
                                  "concept proposals for this glossary.")
                collaboration_request.for_glossary.assign_lexicographer_permissions(collaboration_request.user)

            if collaboration_request.collaboration_role == "O":
                mail_message += _("\n\nAs glossary owner you can modify or "
                                  "delete the glossary and manage its "
                                  "collaboration requests as well.")
                collaboration_request.for_glossary.assign_owner_permissions(collaboration_request.user)

            # Send email messages only if allowed in the settings
            if settings.SEND_NOTIFICATION_EMAILS:
                mail_subject = _("[Terminator] collaboration request accepted")
                mail_body_data = {
                    'role': collaboration_request.get_collaboration_role_display(),
                    'glossary': collaboration_request.for_glossary
                }
                mail_text = (_("Your collaboration request as \"%(role)s\" "
                               "for glossary \"%(glossary)s\" was accepted.") %
                             mail_body_data)
                full_mail_text = mail_text + mail_message
                send_mail(mail_subject, full_mail_text,
                          'donotreply@donotreply.com',
                          [collaboration_request.user.email],
                          fail_silently=False)
            obj_display = force_unicode(collaboration_request)
            self.log_deletion(request, collaboration_request, obj_display)
        rows_deleted = len(queryset)
        queryset.delete()
        # Translators: This message appears after executing the action in admin
        self.message_user(request, ungettext("%(count)d collaboration request "
                                             "was successfully accepted.",
                                             "%(count)d collaboration "
                                             "requests were successfully "
                                             "accepted.", rows_deleted) %
                                             {'count': rows_deleted})
    accept_collaboration_requests.short_description = _("Accept selected %(verbose_name_plural)s")

if settings.FEATURES.get('collaboration', False):
    admin.site.register(CollaborationRequest, CollaborationRequestAdmin)



