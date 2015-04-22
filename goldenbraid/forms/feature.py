from operator import itemgetter

from django import forms
from django.db.models import Q
from django.forms.widgets import Select
from django.core.exceptions import ValidationError

from goldenbraid.models import Feature, Cvterm
from goldenbraid.tags import VECTOR_TYPE_NAME
from goldenbraid.settings import SEARCH_MENU_TYPE_CHOICES


def features_to_choices(features, blank_line=True):
    choices = [('', '')] if blank_line else []

    for feat in features:
        uniquename = feat.uniquename.encode('utf-8')
        if feat.name:
            show = u'{0} - {1}'.format(feat.uniquename, feat.name)
        else:
            show = uniquename
        choices.append((uniquename, show))
    choices = sorted(choices, key=itemgetter(0))
    return choices


def _prepare_feature_kind():
    'It prepares the feature kind select choices to put in the type widget'
    if SEARCH_MENU_TYPE_CHOICES:
        kinds = SEARCH_MENU_TYPE_CHOICES
    else:
        kinds = Feature.objects.distinct('type').values('type__name')
        kinds = [kind['type__name'] for kind in kinds]
    if VECTOR_TYPE_NAME in kinds:
        kinds.pop(kinds.index(VECTOR_TYPE_NAME))

    feature_kinds = [(kind, kind.replace('_', ' ')) for kind in kinds]

    feature_kinds.insert(0, ('', ''))  # no kind
    return feature_kinds


def get_all_vectors_as_choices(user):
    vectors = Feature.objects.filter(type__name=VECTOR_TYPE_NAME)
    if user.is_authenticated():
        vectors = vectors.filter(Q(featureperm__owner__username=user) |
                                 Q(featureperm__is_public=True))
    else:
        vectors = vectors.filter(featureperm__is_public=True)
    return features_to_choices(vectors, blank_line=True)


class VectorForm(forms.Form):
    'Form to add vectors to db'
    name = forms.CharField(max_length=255, required=False)
    description = forms.CharField(max_length=255)
    reference = forms.CharField(max_length=255, required=False)
    enzyme_in = forms.CharField(max_length=255)
    enzyme_out = forms.CharField(max_length=255)
    resistance = forms.CharField(max_length=255)
    gbfile_label = 'Select a GenBank-formatted local file on your computer'
    gbfile = forms.FileField(label=gbfile_label, required=True)


class FeatureForm(forms.Form):
    'Form to add features to db'
    name = forms.CharField(max_length=255, required=False)
    description = forms.CharField(max_length=255, required=False)
    reference = forms.CharField(max_length=255, required=False)

    type_choices = _prepare_feature_kind()
    type = forms.CharField(max_length=100, widget=Select(choices=type_choices))

    vector = forms.CharField(max_length=100, widget=Select(choices=[]))

    gbfile_label = 'Select a GenBank-formatted local file on your computer'
    gbfile = forms.FileField(label=gbfile_label, required=True)

    def clean_type(self):
        'It validates the type field'
        type_str = self.cleaned_data['type']
        try:
            Cvterm.objects.get(name=type_str)
        except Cvterm.DoesNotExist:
            raise ValidationError('This type does not exist in the database')
        return type_str

    def clean_vector(self):
        '''It validates the vector.

        If the feature is a vector it does not validate anything
        if feature is not a vector if validates that the vector
        is in the database'''
        vector = self.cleaned_data['vector']
        error_in_type = self.errors.get('type', False)
        if error_in_type:
            return vector
        type_str = self.cleaned_data['type']

        if type_str != VECTOR_TYPE_NAME:
            try:
                vector_type = Cvterm.objects.get(name=VECTOR_TYPE_NAME)
                Feature.objects.get(uniquename=vector, type=vector_type)
            except Feature.DoesNotExist:
                raise ValidationError('The given vector does not exist')

        else:
            if vector:
                raise ValidationError('A vector does not have a vector')

        return vector


def create_feature_validator(field_name):

    def validator(self):
        uniquename_str = self.cleaned_data[field_name]
        try:
            Feature.objects.get(uniquename=uniquename_str)
        except Feature.DoesNotExist:
            msg = 'This feature does not exist in the database'
            raise ValidationError(msg)
        return uniquename_str

    return validator


class FeatureManagementForm(forms.Form):
    feature = forms.CharField(max_length=30, widget=forms.HiddenInput())
    action = forms.CharField(max_length=30, widget=forms.HiddenInput())

    def clean_action(self):
        action = self.cleaned_data['action']
        if action in ('delete', 'make_public', 'make_private'):
            return action
        raise ValidationError('action must be delete or make_public')

    def clean_feature(self):
        return create_feature_validator('feature')(self)
