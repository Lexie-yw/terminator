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

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms.widgets import Textarea, TextInput, URLInput, Select
from django.utils.translation import ugettext_lazy as _

from guardian.models import UserObjectPermission

from terminator.models import *


class SearchForm(forms.Form):
    search_string = forms.CharField(
            max_length=100,
            min_length=2,
            label=_("Search string"),
            widget=TextInput(attrs={"placeholder": _("Term to search for")}),
    )


class AdvancedSearchForm(SearchForm):
    also_show_partial_matches = forms.BooleanField(required=False,
        label=_("Also show partial matches")
    )
    filter_by_glossary = forms.ModelChoiceField(
        queryset=Glossary.objects.all(), required=False,
        label=_("Filter by glossary")
    )
    filter_by_language = forms.ModelChoiceField(
        queryset=Language.objects.all(), required=False,
        label=_("Filter by language")
    )
    filter_by_part_of_speech = forms.ModelChoiceField(
        queryset=PartOfSpeech.objects.all(), required=False,
        label=_("Filter by part of speech")
    )
    #TODO Perhaps for the filter_by_administrative_status field it would be
    # better to put a checkbox for each one, or a MultipleChoices field. Both
    # approachs would require changes in the view.
    filter_by_administrative_status = forms.ModelChoiceField(
        queryset=AdministrativeStatus.objects.all(), required=False,
        label=_("Filter by administrative status")
    )


class ImportForm(forms.ModelForm):
    imported_file = forms.FileField(label=_("File"))

    class Meta:
        model = Glossary
        exclude = ('other_languages', 'subscribers', 'subject_fields')

    def clean(self):
        super(forms.ModelForm, self).clean()
        cleaned_data = self.cleaned_data
        if Glossary.objects.filter(name=cleaned_data.get("name")):
            msg = _(u"Already exists a glossary with the given name. You should provide another one.")
            self._errors["name"] = self.error_class([msg])
            # This field is no longer valid. So remove it from the cleaned data.
            del cleaned_data["name"]
        # Always return the full collection of cleaned data.
        return cleaned_data


class ExportForm(forms.Form):
    from_glossaries = forms.ModelMultipleChoiceField(queryset=Glossary.objects.all(), label=_("From glossaries"))
    for_languages = forms.ModelMultipleChoiceField(queryset=Language.objects.all(), required=False, label=_("For languages"))
    #TODO In the for_languages field show only the languages present on the
    # chosen glossaries. Perhaps show a cloud of checkboxes?
    #also_not_finalized_concepts = forms.BooleanField(required=False, label=_("Also not finalized concepts"))
    export_terms = forms.ChoiceField(
            required=False,
            label=_("Terms to export"),
            choices=(
                   ('all', _("all terms")),
                   ('preferred', _("only preferred terms")),
                   ('preferred+admitted', _("preferred and admitted terms")),
                   ('preferred+admitted+not_recommended', _("preferred, admitted and not recommended terms")),
            )
    )
    export_not_finalized_definitions = forms.BooleanField(required=False, label=_("Include non-finalized definitions"))


class SubscribeForm(forms.Form):
    subscribe_to_this_glossary = forms.BooleanField(initial=False, label=_("Subscribe to this glossary"))


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ('for_glossary', 'language', 'term', 'definition',)


class CollaborationRequestForm(forms.ModelForm):
    class Meta:
        model = CollaborationRequest
        fields = ('collaboration_role',)


class ExternalResourceForm(forms.ModelForm):
    class Meta:
        model = ExternalResource
        fields = ('address', 'link_type', 'description')
        labels = {
                'address': "",
                'description': "",
                'link_type': "",
        }
        widgets = {
                'address': URLInput(attrs={
                        "placeholder": "https://en.wikipedia.org/wiki/..."
                }),
                'description': Textarea(attrs={
                        "placeholder": _("Enter a description of the linked resource..."),
                        "rows": 2,
                        "cols": 50,
                }),
        }

    def __init__(self, *args, **kwargs):
        super(ExternalResourceForm, self).__init__(*args, **kwargs)
        self.fields['link_type'].empty_label = _("Type of link...")


class TerminatorGlossaryAdminForm(forms.ModelForm):
    terminologists = forms.ModelMultipleChoiceField(
            widget=FilteredSelectMultiple(_("Terminologists"), False),
            queryset=User.objects.all().order_by("username"),
            label=_("Terminologists"),
            required=False,
    )
    lexicographers = forms.ModelMultipleChoiceField(
            widget=FilteredSelectMultiple(_("Lexicographers"), False),
            queryset=User.objects.all().order_by("username"),
            label=_("Lexicographers"),
            required=False,
    )
    owners = forms.ModelMultipleChoiceField(
            widget=FilteredSelectMultiple(_("Owners"), False),
            queryset=User.objects.all().order_by("username"),
            label=_("Owners"),
            required=False,
    )

    class Meta:
        fields = '__all__'
        model = Glossary

    def __init__(self, *args, **kwargs):
        super(TerminatorGlossaryAdminForm, self).__init__(*args, **kwargs)

        # avoid repeated queries
        users_qs = User.objects.filter(is_active=True).order_by("username")
        users = [(u.pk, u.username) for u in users_qs]
        for field in (
                "subscribers",
                "terminologists",
                "lexicographers",
                "owners",
                ):
            self.fields[field].choices = users
        languages_qs = Language.objects.all().order_by("iso_code")
        languages = [(l.pk, l.name) for l in languages_qs]
        self.fields["source_language"].choices = languages

        if self.instance.id:
            source_lang_id = self.instance.source_language_id
            languages = [l for l in languages if l[0] != source_lang_id]
            # only provide concepts in this glossary
            self.fields['subject_fields'].queryset = Concept.objects.filter(
                    glossary=self.instance,
            )
            for name, users in self.get_collaborators().items():
                self.fields[name].initial = users

        self.fields["other_languages"].choices = languages

    def get_collaborators(self):
        # This is what we want:
        # user_dict = get_users_with_perms(self, attach_perms=True, with_group_users=False)
        # for user, perms in user_dict: if 'xxx' in perms: ...
        # XXX: attach_perms=True makes this very slow with lots of users
        # https://github.com/django-guardian/django-guardian/issues/494
        # Also see terminator.models.Glossary.get_collaborators()

        # Hand-written to use a single query. This is not exactly
        # equivalent, since we are not checking group permissions.
        glossary_ctype = ContentType.objects.get_for_model(Glossary)
        owners = set()
        lexicographers = set()
        terminologists = set()
        permissions = (
                "is_owner_for_this_glossary",
                "is_lexicographer_in_this_glossary",
                "is_terminologist_in_this_glossary",
        )
        permission_lines = UserObjectPermission.objects.filter(
                permission__codename__in=permissions,
                content_type=glossary_ctype,
                object_pk=self.instance.id,
        ).select_related("user", "permission")
        for line in permission_lines:
            perm = line.permission.codename
            if perm == "is_owner_for_this_glossary":
                owners.add(line.user)
            elif perm == "is_lexicographer_in_this_glossary":
                lexicographers.add(line.user)
            elif perm == "is_terminologist_in_this_glossary":
                terminologists.add(line.user)
        return {
                "owners": owners,
                "lexicographers": lexicographers,
                "terminologists": terminologists,
        }

    def clean(self):
        super(forms.ModelForm, self).clean()

        cleaned_data = self.cleaned_data
        name = cleaned_data.get("name")
        subject_fields = cleaned_data.get("subject_fields")
        source_language = cleaned_data.get("source_language")
        other_languages = cleaned_data.get("other_languages")

        if subject_fields and name:
            subject_fields = list(subject_fields)
            glossary = Glossary.objects.get(name=name)
            for subject_field in subject_fields:
                if subject_field.glossary_id != glossary.id:
                    msg = _(u"Specify only concepts that belong to the chosen glossary.")
                    self._errors["subject_fields"] = self.error_class([msg])
                    # This field is no longer valid. So remove it from the
                    # cleaned data.
                    del cleaned_data["subject_fields"]
                    break
            #TODO When removing a subject field from the list of subject
            # fields for a given glossary make sure that this concept is not
            # the subject field or other concepts in the glossary.

        if other_languages:
            if source_language in other_languages:
                msg = _(u"The source language can not be among the other languages.")
                self._errors['other_languages'] = self.error_class([msg])
                del cleaned_data["other_languages"]

        # Always return the full collection of cleaned data.
        return cleaned_data


class TerminatorConceptAdminForm(forms.ModelForm):
    class Meta:
        fields = '__all__'
        model = Concept

    def __init__(self, *args, **kwargs):
        super(TerminatorConceptAdminForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            # only provide concepts from the glossary's subject_fields
            self.fields['subject_field'].queryset = self.instance.glossary.subject_fields
            # only provide concepts in this glossary
            concepts = Concept.objects.filter(
                    glossary_id=self.instance.glossary_id,
                    repr_cache__gt='',
            ).exclude(pk=self.instance.pk).values_list("id", "repr_cache")
            self.fields['related_concepts'].choices = concepts
            self.fields['broader_concept'].choices = [('', _('None'))] + list(concepts)

        self.queryset = Concept.objects.all().select_related("glossary")

    def clean(self):
        super(TerminatorConceptAdminForm, self).clean()

        cleaned_data = self.cleaned_data
        glossary = cleaned_data.get("glossary")
        if not glossary:
            msg = _(u"Indicate the glossary containing the concept.")
            self._errors["glossary"] = self.error_class([msg])
            # We don't delete, since the glossary isn't there
        if self.instance.glossary_id:
            glossary = glossary or self.instance.glossary
        subject_field = cleaned_data.get("subject_field")

        if subject_field and glossary:
            # We only show the right ones, but this is still good validation:
            if not subject_field.glossary == glossary:
                msg = _(u"Only specify subject fields from the same glossary.")
                self._errors["subject_field"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["subject_field"]
            elif not subject_field in subject_field.glossary.subject_fields.all():
                msg = _(u"Only specify subject fields from the glossary's subject fields.")
                self._errors["subject_field"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["subject_field"]
            elif self.instance and subject_field == self.instance:
                msg = _(u"You can't set a relationship between a concept and itself.")
                self._errors["subject_field"] = self.error_class([msg])
                del cleaned_data["subject_field"]


        broader_concept = cleaned_data.get("broader_concept")
        if broader_concept and glossary:
            if not broader_concept.glossary == glossary:
                msg = _(u"Only specify broader concepts from the same glossary.")
                self._errors["broader_concept"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["broader_concept"]
            elif self.instance and broader_concept.id == self.instance.id:
                msg = _(u"You can't set a relationship between a concept and itself.")
                self._errors["broader_concept"] = self.error_class([msg])
                del cleaned_data["broader_concept"]

        related_concepts = cleaned_data.get("related_concepts")
        if related_concepts and glossary:
            for related_concept in related_concepts:
                if not related_concept.glossary == glossary:
                    msg = _(u"Only specify related concepts from the same glossary.")
                    self._errors["related_concepts"] = self.error_class([msg])
                    # This field is no longer valid. So remove it from the
                    # cleaned data.
                    del cleaned_data["related_concepts"]
                elif self.instance and related_concept == self.instance:
                    msg = _(u"You can't set a relationship between a concept and itself.")
                    self._errors["related_concept"] = self.error_class([msg])
                    del cleaned_data["related_concept"]

        # Always return the full collection of cleaned data.
        return cleaned_data


class ConceptInLanguageAdminForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = ConceptInLanguage


class ConceptInLanguageForm(forms.Form):
    translation = forms.CharField(
                        label="",
                        required=False,
                        max_length=100,
                        widget=TextInput(
                            attrs={
                                "placeholder": _("Add corrected or alternative term..."),
                                "class": "translation",
                            })
                       )
    definition = forms.CharField(label="", required=False, widget=Textarea(
                            attrs={
                                "placeholder": _("Enter a definition..."),
                                "rows": 7,
                                "cols": 50,
                                "class": "definition",
                            })
                       )


class TerminatorTranslationAdminForm(forms.ModelForm):
    """A form for handling/validating the full Translation model."""
    class Meta:
        fields = '__all__'
        model = Translation

    def __init__(self, *args, **kwargs):
        super(TerminatorTranslationAdminForm, self).__init__(*args, **kwargs)
        if not "instance" in kwargs:
            # Not editing
            return

        language = self.instance.language
        for field, qs in (
                ("part_of_speech", language.parts_of_speech),
                ("grammatical_gender", language.grammatical_genders),
                ("grammatical_number", language.grammatical_numbers),
                ("administrative_status_reason", language.administrativestatusreason_set),
            ):
            if field in self.fields:
                self.fields[field].queryset = qs

    def clean(self):
        super(forms.ModelForm, self).clean()

        cleaned_data = self.cleaned_data
        language = cleaned_data.get("language")
        if language is None and self.instance is not None:
            language = self.instance.language
        part_of_speech = cleaned_data.get("part_of_speech")

        # Check that the specified Part of Speech is allowed by the chosen
        # language.
        if language and part_of_speech:
            # Only do something if both fields are valid so far.
            if not language.allows_part_of_speech(part_of_speech):
                msg = _(u"Specify only parts of speech allowed by the chosen language.")
                self._errors["part_of_speech"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["part_of_speech"]

        grammatical_gender = cleaned_data.get("grammatical_gender")
        # Check that Grammatical Gender is only specified when given a Part
        # of Speech.
        if not part_of_speech and grammatical_gender:
            msg = _(u"Don't specify a grammatical gender without specifying a part of speech.")
            self._errors["grammatical_gender"] = self.error_class([msg])
            # This field is no longer valid. So remove it from the cleaned data.
            del cleaned_data["grammatical_gender"]

        # Check that the Part of Speech allows specifying a Grammatical Gender
        # for the chosen language, and check that the chosen language allows
        # using the specified Grammatical Gender.
        if language and part_of_speech and grammatical_gender:
            msg = u""
            if not part_of_speech.allows_grammatical_gender_for_language(language):
                msg = _(u"The specified part of speech doesn't allow specifying a grammatical gender for the chosen language.")
            if not language.allows_grammatical_gender(grammatical_gender):
                msg += unicode(_(u"The chosen language doesn't allow specifying this grammatical gender."))
            if msg:
                self._errors["grammatical_gender"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["grammatical_gender"]

        grammatical_number = cleaned_data.get("grammatical_number")
        # Check that Grammatical Number is only specified when given a Part
        # of Speech.
        if not part_of_speech and grammatical_number:
            msg = _(u"Don't specify a grammatical number without specifying a part of speech.")
            self._errors["grammatical_number"] = self.error_class([msg])
            # This field is no longer valid. So remove it from the cleaned data.
            del cleaned_data["grammatical_number"]

        # Check that the Part of Speech allows specifying a Grammatical Number
        # for the chosen language, and check that the chosen language allows
        # using the specified Grammatical Number.
        if language and part_of_speech and grammatical_number:
            msg = u""
            if not part_of_speech.allows_grammatical_number_for_language(language):
                msg = _(u"The specified part of speech doesn't allow specifying a grammatical number for the chosen language.")
            if not language.allows_grammatical_number(grammatical_number):
                msg += unicode(_(u"The chosen language doesn't allow specifying this grammatical number."))
            if msg:
                self._errors["grammatical_number"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["grammatical_number"]

        administrative_status = cleaned_data.get("administrative_status")
        administrative_status_reason = cleaned_data.get("administrative_status_reason")
        # Check that Administrative Status Reason is only specified when
        # given an Administrative Status.
        if not administrative_status and administrative_status_reason:
            msg = _(u"Don't specify an administrative status reason without specifying an administrative status.")
            self._errors["administrative_status_reason"] = self.error_class([msg])
            # This field is no longer valid. So remove it from the cleaned data.
            del cleaned_data["administrative_status_reason"]

        # Check that the Administrative Status allows specifying an
        # Administrative Status Reason, and check that the chosen language
        # allows using the specified Administrative Status Reason.
        if language and administrative_status and administrative_status_reason:
            msg = u""
            if not administrative_status.allows_reason:
                msg = _(u"The specified Administrative status doesn't allow specifying an administrative status reason.")
            elif not language.allows_reason(administrative_status_reason):
                msg += unicocde(_(u"The chosen language doesn't allow specifying this administrative status reason."))
            if msg:
                self._errors["administrative_status_reason"] = self.error_class([msg])
                # This field is no longer valid. So remove it from the cleaned
                # data.
                del cleaned_data["administrative_status_reason"]

        is_finalized = cleaned_data.get("is_finalized")
        # Check that the is_finalized is not set to True when the Part of
        # Speech or the Administrative Status are not set.
        if is_finalized and (not administrative_status or not part_of_speech):
            msg = _(u"You cannot set 'is finalized' to True unless an administrative status and a part of speech are set.")
            self._errors["is_finalized"] = self.error_class([msg])
            # This field is no longer valid. So remove it from the cleaned data.
            del cleaned_data["is_finalized"]

        # Always return the full collection of cleaned data.
        return cleaned_data
