# -*- coding: UTF-8 -*-
from __future__ import print_function

import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client
from django.utils import six

from terminator.forms import *

# These are meant as high-level tests. The idea is to exercise a lot code in
# an attempt to test interaction with the Django components, primarily. This
# should still be improved to test correctness more.

class URLsA(TestCase):

    fixtures = ['test_data']

    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(username="test", email="test@test.com", password="test")
        self.user.save()

    def login(self):
        self.c.login(username='test', password='test')

    #TODO: consider using reverse(<viewname>) instead of hardcoding urls
    def test_plain_200_urls(self):
        for url in [
                '/',
                '/search/',
                '/advanced_search/',
                '/proposals/',
                '/feeds/all/',
                '/feeds/glossaries/',
                '/feeds/concepts/',
                '/feeds/translations/',
                '/feeds/comments/',
                '/autoterm/',
                '/profiles/',
                '/help/',
                '/accounts/login/',
                '/accounts/register/',
        ]:
            #print(url)
            response = self.c.get(url)
            self.assertEqual(response.status_code, 200)

    def test_plain_302_urls(self):
        for url in [
                '/import/',
                '/export/',
                '/admin/',
        ]:
            #print(url)
            response = self.c.get(url)
            self.assertEqual(response.status_code, 302)

    def test_post_403_urls(self):
        client = Client(enforce_csrf_checks=True)
        for url in [
                '/',  # proposal
                '/search/',
                '/advanced_search/',
                '/import/',
                '/export/',
                '/accounts/login/',
        ]:
            #print(url)
            response = client.post(url)
            self.assertEqual(response.status_code, 403)

    def test_user_200_urls(self):
        self.login()
        for url in [
                '/',
                '/export/',
                '/search/',
                '/advanced_search/',
                '/proposals/',
                '/feeds/all/',
                '/feeds/glossaries/',
                '/feeds/concepts/',
                '/feeds/translations/',
                '/feeds/comments/',
                '/autoterm/',
                '/profiles/',
                '/help/',
                ####
                '/import/',
                ###
                '/accounts/logout/', # last: now logged out
        ]:
            #print(url)
            response = self.c.get(url)
            self.assertEqual(response.status_code, 200)
        # test that the logout worked:
        self.test_plain_302_urls()

#    def test_user_302_urls(self):
#        for url in [
#                '/accounts/login/',
#                '/accounts/register/',
#        ]:
#            response = self.c.get(url)
#            self.assertEqual(response.status_code, 302)

class URLsB(TestCase):

    fixtures = ['test_data']

    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(username="test", email="test@test.com", password="test")
        self.user.save()

    def login(self):
        self.c.login(username='test', password='test')

    def test_simple_post(self):
        for url in [
                '/',  # proposal
                '/search/',
                '/advanced_search/',
#                '/import/',###
                '/accounts/login/',
                '/accounts/register/',
#                '/admin/',
        ]:
            #print url
            response = self.c.post(url, data={})
            self.assertEqual(response.status_code, 200)

    def test_invalid_suggestion(self):
        self.login()
        response = self.c.post('/', data={})
        for field in [
                "for_glossary",
                "language",
                "term",
                "definition",
        ]:
            self.assertFormError(response, "proposal_form", field, "This field is required.")


    def test_valid_suggestion(self):
        self.login()
        response = self.c.post('/', data={
                "for_glossary": 1,
                "language": 'en',
                "term": "asdf",
                "definition": "asdf",
        })
        self.assertContains(response, "Thank you")

    def test_profile_detail(self):
        response = self.c.get('/profiles/test/')
        self.assertContains(response, 'test')
        response = self.c.get('/profiles/test/', {"page": 2})
        self.assertContains(response, 'test')
        response = self.c.get('/profiles/test/', {"page": "abc"})
        self.assertContains(response, 'test')

    def test_search(self):
        response = self.c.get('/search/', {"search_string": "abc"})
        self.assertEqual(response.status_code, 200)
        response = self.c.get('/advanced_search/', {
            "search_string": "abc",
            "filter_by_glossary": 1,
            "filter_by_language": "en",
            "filter_by_part_of_speech": 1,
            "filter_by_administrative_status": "preferredTerm-admn-sts",
            "also_show_partial_matches": True,
            })
        self.assertContains(response, "No results found.")
        response = self.c.get('/advanced_search/', {
            "search_string": "tab",
            "filter_by_glossary": 1,
            "filter_by_language": "en",
            })
        self.assertNotContains(response, "No results found.")

    def test_concept(self):
        response = self.c.get('/concepts/1/')
        self.assertNotContains(response, "Definition")
        self.assertNotContains(response, "External resources")
        self.assertNotContains(response, "Related")
        concept = Concept.objects.get(id=1)
        concept2 = Concept(id=200, glossary_id=1)
        concept2.save()
        concept.related_concepts.add(concept2)
        response = self.c.get('/concepts/1/')
        self.assertContains(response, "Related")

    def test_concept_in_language(self):
        response = self.c.get('/concepts/1/en/')
        self.assertNotContains(response, "Definition")
        self.assertNotContains(response, "External resources")
        concept = Concept.objects.get(id=1)
        concept_in_lang, created = ConceptInLanguage.objects.get_or_create(
                concept=concept,
                language_id="en",
        )
        concept_in_lang.summary = "Soomaaariii"
        concept_in_lang.is_finalized = True
        concept_in_lang.save()
        translation = concept.translation_set.get(language_id="en")
        translation.part_of_speech = PartOfSpeech.objects.get(tbx_representation="noun")
        translation.is_finalized = True
        translation.save()
        definition = Definition(concept=concept, language_id="en", text="xxxx")
        definition.save()
        response = self.c.get('/concepts/1/en/')
        self.assertContains(response, "Definition")
        self.assertContains(response, "Noun")

    def test_concept_source(self):
        response = self.c.get('/concepts_source/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "search")
        self.assertNotContains(response, "buscar")
        self.assertNotContains(response, "Finalise term information")
        self.assertNotContains(response, "Enter correction or alternative term")
        self.assertNotContains(response, "Submit")

        self.login()
        response = self.c.get('/concepts_source/1/')
        self.assertEqual(response.status_code, 200)
        # This user has no rights for this Glossary
        self.assertNotContains(response, "Finalise term information")
        self.assertNotContains(response, "Submit")

        self.c.login(username='usuario', password='usuario')
        response = self.c.get('/concepts_source/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finalise term information")
        self.assertContains(response, "Add corrected or alternative term")
        self.assertContains(response, "Submit")

        response = self.c.post('/concepts_source/1/', data={
            "translation": "SEARCHxxx",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "search")
        self.assertContains(response, "SEARCHxxx")

        response = self.c.post('/concepts_source/1/', data={
            "translation": "SEARCHyyy",
            "definition": "definizione uno",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "search")
        self.assertContains(response, "SEARCHxxx")
        self.assertContains(response, "SEARCHyyy")
        self.assertContains(response, "definizione uno")

        response = self.c.post('/concepts_source/1/', data={
            "definition": "newer definition",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "newer definition")
        self.assertNotContains(response, "definizione uno")

        # too long
        response = self.c.post('/concepts_source/1/', data={
            "translation": "x"*200,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "xxxxxxxxxx")

        # duplicate
        response = self.c.post('/concepts_source/1/', data={
            "translation": "SEARCHxxx",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errornote")
        self.assertContains(response, "already present")
        self.assertContains(response, "SEARCHxxx")

    def test_definition_history(self):
        self.c.login(username='usuario', password='usuario')
        response = self.c.get('/concepts_source/1/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "today")
        self.assertContains(response, "usuario", count=2) #header

        response = self.c.post('/concepts_source/1/', data={
            "definition": "Long definition...",
        })
        self.assertContains(response, "today")
        self.assertContains(response, "usuario", count=4) #header + history

    def test_concept_target(self):
        # language not added to glossary
        response = self.c.get('/concepts/2/gl/edit')
        self.assertEqual(response.status_code, 404)
        gl = Language.objects.get(iso_code='gl')
        glossary = Glossary.objects.get(pk=1)
        glossary.other_languages.add(gl)

        response = self.c.get('/concepts/2/gl/edit')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Galician")
        self.assertContains(response, "xanela")
        self.assertNotContains(response, "Submit")

        self.login()
        response = self.c.get('/concepts/2/gl/edit')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Galician")
        self.assertContains(response, "xanela")
        # This user has no rights for this Glossary
        self.assertNotContains(response, "Finalise term information")
        self.assertNotContains(response, "Submit")

        self.c.login(username='usuario', password='usuario')
        response = self.c.get('/concepts_source/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finalise term information")
        self.assertContains(response, "Add corrected or alternative term")
        self.assertContains(response, "Submit")

        response = self.c.post('/concepts/2/gl/edit', data={
            "translation": "SEARCHxxx",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "search")
        self.assertContains(response, "SEARCHxxx")

        response = self.c.post('/concepts/2/gl/edit', data={
            "translation": "SEARCHyyy",
            "definition": "definizione uno",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "search")
        self.assertContains(response, "SEARCHxxx")
        self.assertContains(response, "SEARCHyyy")
        self.assertContains(response, "definizione uno")

        response = self.c.post('/concepts/2/gl/edit', data={
            "definition": "newer definition",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "successnote")
        self.assertContains(response, "newer definition")
        self.assertNotContains(response, "definizione uno")

        # too long
        response = self.c.post('/concepts/2/gl/edit', data={
            "translation": "x"*200,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "xxxxxxxxxx")

        # duplicate
        response = self.c.post('/concepts/2/gl/edit', data={
            "translation": "SEARCHxxx",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errornote")
        self.assertContains(response, "already present")
        self.assertContains(response, "SEARCHxxx")


    def test_glossaries(self):
        response = self.c.get('/glossaries/1/')
        self.assertContains(response, "Concepts")

#        response = self.c.post('/glossaries/1/', data={
#            'collaboration_role': 'S', # Specialist
#        })
#        self.assertNotContains(response, "You will receive a message")

        self.login()
        response = self.c.get('/glossaries/1/')
        self.assertContains(response, "Glossary collaborators")

        glossary = Glossary.objects.get(pk=1)
        glossary.assign_owner_permissions(self.user)
        glossary.save()
        response = self.c.get('/glossaries/1/')
        self.assertContains(response, "edit this glossary")

        if settings.FEATURES.get('collaboration', True):
            response = self.c.post('/glossaries/1/', data={
                'collaboration_role': 'S', # Specialist
            })
            self.assertContains(response, "You will receive a message")
            response = self.c.post('/glossaries/1/', data={
                'collaboration_role': 'S',
            })
            self.assertContains(response, "You already sent")
            response = self.c.post('/glossaries/1/', data={
                'subscribe_to_this_glossary': True,
            })

        if settings.FEATURES.get('subscription', True):
            self.assertContains(response, "You have subscribed")
            response = self.c.post('/glossaries/1/', data={}) # empty form
            self.assertEqual(response.status_code, 200)

#    def test_glossary_admin(self):
#        self.admin = User.objects.create_superuser(username="test2", email="test2@test.com", password="ẗest2")
#        self.c.login(username='test2', password='test2')
#        response = self.c.post('/admin/terminator/glossary/add/', data={
#            "name": "test",
#            "description": "description",
#        })
#        print response.content
#        self.assertContains(response, "success")


class TBXURLs(TestCase):

    fixtures = ['test_data']

    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(username="test", email="test@test.com", password="test")
        self.user.save()

    def login(self):
        self.c.login(username='test', password='test')

    def is_tbx(self, response):
        assert "attachment;" in response['Content-Disposition']
        assert "tbx" in response['Content-Disposition']
        self.assertContains(response, '<martif type="TBX"')

    def not_tbx(self, response):
        assert 'Content-Disposition' not in response
        self.assertNotContains(response, '<martif type="TBX"')

    def test_autoterm(self):
        response = self.c.get('/autoterm/gl/', data={})
        self.is_tbx(response)

    def test_export(self):
        self.login()
        response = self.c.get('/export/', data={"from_glossaries": 1})
        self.assertContains(response, 'Export')
        self.assertNotContains(response, "This field is required")

        for export_terms in ("", "all", "preferred", "preferred+admitted", "preferred+admitted+not_recommended"):
            response = self.c.post('/export/', data={
                "from_glossaries": 1,
                "export_terms": export_terms,
            })
            self.is_tbx(response)

    def test_export_externalresources(self):
        self.login()
        response = self.c.post('/export/', data={
            "from_glossaries": 2,
            "export_terms": "all",
        })
        self.is_tbx(response)
        self.assertNotContains(response, 'xref')

        r = ExternalResource(concept_id=7, language=None, link_type_id="externalCrossReference")
        r.save()
        response = self.c.post('/export/', data={
            "from_glossaries": 2,
            "export_terms": "all",
        })
        self.is_tbx(response)
        self.assertContains(response, 'xref')

    def test_tbx_import(self):
        self.login()
        response = self.c.post('/import/', data={})
        for field in [
                "name",
                "description",
                "source_language",
                "imported_file",
        ]:
            self.assertFormError(response, "import_form", field, "This field is required.")
            self.assertNotContains(response, "succesful")
        for filename in [
                'empty.tbx',
                'small.tbx', # first "fail"
                'small.tbx', # then pass, if we add the language
                'most.tbx',
                ]:
            with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
                response = self.c.post('/import/', {
                    "name": "test name",
                    "description": "test description",
                    "source_language": 'en',
                    'imported_file': f
                })
            if b"no Language with that code" in response.content:
                # first attempt to import a file with Zulu
                Language(iso_code="zu").save()
                self.assertNotContains(response, "succesful")
                continue
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "succesful")
            self.assertNotContains(response, "This field is required.")
            glossary = Glossary.objects.get(name="test name")
            if filename == 'most.tbx':
                self.assertEqual(glossary.source_language.iso_code, 'en')
                self.assertSequenceEqual(glossary.other_languages.values_list('iso_code', flat=True), ('zu',))
            Glossary.delete(glossary)

            with open(os.path.join(os.path.dirname(__file__), 'empty.tbx'), 'r') as f:
                response = self.c.post('/import/', {
                    "name": "empty",
                    "description": "empty",
                    "source_language": 'en',
                    'imported_file': f
                })
                f.seek(0)
                response = self.c.post('/import/', {
                    "name": "empty",
                    "description": "empty",
                    "source_language": 'en',
                    'imported_file': f
                })
                self.assertNotContains(response, "succesful")
                self.assertContains(response, "Already exists a glossary with the given name. You should provide another one.")


class AdminFormTests(TestCase):
    fixtures = ['test_data']

    def test_glossary_admin(self):
        form = TerminatorGlossaryAdminForm({
            "name": "test",
            "description": "description",
            "source_language": "en",
        })
        self.assertTrue(form.is_valid())

    def test_concept_admin(self):
        form = TerminatorConceptAdminForm({
            "glossary": 1,
        })
        self.assertTrue(form.is_valid())

        form = TerminatorConceptAdminForm({
            "glossary": 1,
            "subject_field": 3,
        })
        self.assertEqual(form.errors, {
            "subject_field": ["Only specify subject fields from the glossary's subject fields."],
        })
        self.assertTrue(not form.is_valid())
        form = TerminatorConceptAdminForm({
            "glossary": 1,
            "subject_field": 999,
        })
        self.assertEqual(form.errors, {
            "subject_field": ["Select a valid choice. That choice is not one of the available choices."],
        })
        self.assertTrue(not form.is_valid())

        glossary = Glossary.objects.get(pk=1)
        glossary.subject_fields.add(1)
        form = TerminatorConceptAdminForm({
            "glossary": 1,
            "subject_field": 1,
        })
        self.assertTrue(form.is_valid(), str(form))

        form = TerminatorConceptAdminForm({
            "glossary": 1,
            "broader_concept": 4,
        })
        self.assertEqual(form.errors, {
            "broader_concept": ["Only specify broader concepts from the same glossary."],
        })
        self.assertTrue(not form.is_valid(), str(form))

        form = TerminatorConceptAdminForm({
            "glossary": 1,
            "related_concepts": [4],
        })
        self.assertEqual(form.errors, {
            "related_concepts": ["Only specify related concepts from the same glossary."],
        })
        self.assertTrue(not form.is_valid(), str(form))

    def test_translation_admin(self):
        form = TerminatorTranslationAdminForm({
            "language": "en",
            "part_of_speech": 1,
            "concept": 1,
            "translation_text": "asdfasdfasdf",
        })
        self.assertTrue(form.is_valid(), str(form))


# Some infrastructure to test models with some of the boilerplate shared.
class SharedTests(object):

    klass = None

    @classmethod
    def setUpClass(cls):
        # subclasses must instantiate self.model with the necessary parameters
        if cls.klass:
            cls.model = cls.klass()

        # some reusable models that are required by a few of the classes
        cls.user = User.objects.create_user(username="test", email="test@test.com", password="test")
        cls.user.save()
        cls.language = Language(iso_code='en')
        cls.language.save()
        cls.glossary = Glossary(name="test glossaryx", source_language=cls.language)
        cls.glossary.save()
        cls.concept = Concept(glossary=cls.glossary)
        cls.concept.save()
        cls.translation = Translation(concept=cls.concept, language=cls.language)
        cls.translation.save()
        cls.pos = PartOfSpeech()
        cls.pos.save()

    @classmethod
    def tearDownClass(cls):
        User.delete(cls.user)
        PartOfSpeech.delete(cls.pos)
        Glossary.delete(cls.glossary)
        Language.delete(cls.language)
        Concept.delete(cls.concept)
        Translation.delete(cls.translation)

    def test_str(self):
        text = six.text_type(self.model)

    def test_save(self):
        self.model.save()


class POSTest(SharedTests, TestCase):
    klass = PartOfSpeech
    @classmethod
    def setUpClass(cls):
        super(POSTest, cls).setUpClass()
        cls.model = cls.pos

    def test_extra_methods(self):
        self.model.allows_grammatical_gender_for_language(self.language)
        self.model.allows_grammatical_number_for_language(self.language)

class GenderTest(SharedTests, TestCase):
    klass = GrammaticalGender

class NumberTest(SharedTests, TestCase):
    klass = GrammaticalNumber

class LanguageTestB(SharedTests, TestCase):
    klass = Language

    def test_extra_methods(self):
        self.model.allows_part_of_speech(self.pos)
        gender = GrammaticalGender()
        number = GrammaticalNumber()
        reason = AdministrativeStatusReason()
        self.model.allows_grammatical_gender(gender)
        self.model.allows_grammatical_number(number)
        self.model.allows_administrative_status_reason(reason)

class POSForLanguageTest(SharedTests, TestCase):
    klass = PartOfSpeechForLanguage
    @classmethod
    def setUpClass(cls):
        super(POSForLanguageTest, cls).setUpClass()
        cls.model = PartOfSpeechForLanguage(language=cls.language, part_of_speech=cls.pos)

class AdministrativeStatusTestB(SharedTests, TestCase):
    klass = AdministrativeStatus

class AdministrativeStatusReasonTest(SharedTests, TestCase):
    klass = AdministrativeStatusReason

class ExternalLinkTypeTest(SharedTests, TestCase):
    klass = ExternalLinkType

class GlossaryTest(SharedTests, TestCase):
    klass = Glossary
    @classmethod
    def setUpClass(cls):
        super(GlossaryTest, cls).setUpClass()
        cls.model = cls.glossary

#    def test_create_glossary_empty_name(self):
#         ###should fail
#        g = Glossary.objects.create(name="")
#        g.save()

    def test_extra_methods(self):
        self.model.assign_specialist_permissions(self.user)
        self.model.assign_terminologist_permissions(self.user)
        self.model.assign_owner_permissions(self.user)

class ConceptTest(SharedTests, TestCase):
    klass = Concept

    @classmethod
    def setUpClass(cls):
        super(ConceptTest, cls).setUpClass()
        cls.model = cls.concept

    def test_repr_cache(self):
        tr = self.translation
        tr.translation_text = u"abcd"
        tr.save()
        self.model.refresh_from_db()
        repr_cache = self.model.repr_cache
        assert repr_cache.startswith('#')
        assert u' abcd' in repr_cache

        tr = Translation(
                concept = self.model,
                language=tr.language,
                translation_text='xyz',
                administrative_status_id='preferredTerm-admn-sts',
        )
        tr.save()
        self.model.refresh_from_db()
        repr_cache = self.model.repr_cache
        assert repr_cache.startswith('#')
        assert u' abcd' in repr_cache
        assert 'xyz, abcd' in repr_cache

        s = AdministrativeStatus(tbx_representation='deprecatedTerm-admn-sts')
        s.save()
        tr.administrative_status_id = 'deprecatedTerm-admn-sts'
        tr.save()
        self.model.refresh_from_db()
        repr_cache = self.model.repr_cache
        assert 'abcd, xyz' in repr_cache


class ConceptInLanguageTest(SharedTests, TestCase):
    klass = ConceptInLanguage
    @classmethod
    def setUpClass(cls):
        super(ConceptInLanguageTest, cls).setUpClass()
        cls.model = ConceptInLanguage(concept=cls.concept, language=cls.language)

    def test_extra_methods(self):
        self.model.get_absolute_url()

class TranslationTest(SharedTests, TestCase):
    klass = Translation
    @classmethod
    def setUpClass(cls):
        super(TranslationTest, cls).setUpClass()
        cls.model = cls.translation

class DefinitionTest(SharedTests, TestCase):
    klass = Definition

    @classmethod
    def setUpClass(cls):
        super(DefinitionTest, cls).setUpClass()
        cls.model = Definition(concept=cls.concept, language=cls.language)

class ExternalResourceTest(SharedTests, TestCase):
    klass = ExternalResource
    @classmethod
    def setUpClass(cls):
        super(ExternalResourceTest, cls).setUpClass()
        link_type = ExternalLinkType(tbx_representation="asdf")
        link_type.save()
        cls.model = ExternalResource(concept=cls.concept, language=cls.language, link_type=link_type)
        cls.model.save()


class ProposalTest(SharedTests, TestCase):
    klass = Proposal
    @classmethod
    def setUpClass(cls):
        super(ProposalTest, cls).setUpClass()
        cls.model = Proposal(language=cls.language, for_glossary=cls.glossary)

class ContextSentenceTest(SharedTests, TestCase):
    klass = ContextSentence

    @classmethod
    def setUpClass(cls):
        super(ContextSentenceTest, cls).setUpClass()
        cls.model = ContextSentence(translation=cls.translation)

class CorpusExampleTest(SharedTests, TestCase):
    klass = CorpusExample

    @classmethod
    def setUpClass(cls):
        super(CorpusExampleTest, cls).setUpClass()
        cls.model = CorpusExample(translation=cls.translation)

class CollaborationRequestTest(SharedTests, TestCase):
    klass = CollaborationRequest

    @classmethod
    def setUpClass(cls):
        super(CollaborationRequestTest, cls).setUpClass()
        cls.model.user = cls.user
        cls.model.for_glossary = cls.glossary
