from django.template.context import RequestContext
from django.core.context_processors import csrf
from django import forms
from django.shortcuts import render_to_response
from django.core.exceptions import ValidationError
from Bio import SeqIO

from goldenbraid.models import Cvterm, Feature, Db, Dbxref, Featureprop
from goldenbraid.settings import DB, REBASE_FILE
from goldenbraid.tags import (GOLDEN_DB, VECTOR_TYPE_NAME,
                              DESCRIPTION_TYPE_NAME, ENZYME_IN_TYPE_NAME,
                              ENZYME_OUT_TYPE_NAME, ENZYME_TYPE_NAME,
                              RESISTANCE_TYPE_NAME, REFERENCE_TYPE_NAME)
from django.db.utils import IntegrityError
from django.http import HttpResponseServerError


def _parse_rebase_file(fpath):
    'It parses the rebase enzyme file and return a list with all the enzymes'
    enzymes = []
    for line in  open(fpath):
        line = line.strip()
        if not line:
            continue
        if line.startswith('<1>') or line.startswith('<2>'):
            enzymes.extend(line[3:].split(','))
    return [enz.upper() for enz in enzymes]


class FeatureForm(forms.Form):
    'Form to add features to db'
    name = forms.CharField(max_length=255, required=False)
    description = forms.CharField(max_length=255, required=False)
    reference = forms.CharField(max_length=255, required=False)
    type = forms.CharField()
    vector = forms.CharField(required=False)
    enzyme_in = forms.CharField(required=False)
    # TODO we have to change the widgte to allow multiple values
    # Now we do spliting the text with a comma
    enzyme_out = forms.CharField(required=False)
    resistance = forms.CharField(required=False)

    gbfile_label = 'Select a GenBank-formatted local file on your computer'
    gbfile = forms.FileField(label=gbfile_label, required=True)

#    def clean_uniquename(self):
#        'It checks that the unique name is unique in database'
#        uniquename = self.cleaned_data['uniquename']
#        try:
#            Feature.objects.using(DB).get(uniquename=uniquename)
#        except Feature.DoesNotExist:
#            return uniquename
#        raise ValidationError('There is already a feature with this uniquename')

    def clean_type(self):
        'It validates the type field'
        type_str = self.cleaned_data['type']
        try:
            Cvterm.objects.using(DB).get(name=type_str)
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
                vector_type = Cvterm.objects.using(DB).get(name=VECTOR_TYPE_NAME)
                Feature.objects.using(DB).get(uniquename=vector,
                                              type=vector_type)
            except Feature.DoesNotExist:
                raise ValidationError('The given vector does not exist')

        else:
            if vector:
                raise ValidationError('A vector does not have a vector')

        return vector

    def _validate_enzyme(self, kind):
        '''It validates the vector.

        If the feature is a vector it does not validate anything
        if feature is not a vector it validates that the vector
        is in the database'''
        # TODO. change how we deal with two enzymes for the same field
        enzymes = self.cleaned_data['enzyme_{}'.format(kind)].split(',')
        error_in_type = self.errors.get('type', False)
        error_in_vector = self.errors.get('vector', False)

        if error_in_type or error_in_vector:
            return enzymes

        type_ = self.cleaned_data['type']
        if type_ == VECTOR_TYPE_NAME:
            if enzymes[0] == u'':
                err = 'A vector must have a enzyme {}'.format(kind)
                raise ValidationError(err)
            existing_enzymes = _parse_rebase_file(REBASE_FILE)
            errors = []
            for enzyme in enzymes:
                if enzyme.upper() not in existing_enzymes:
                    err = 'This enzyme: {} is not a known enzyme'
                    err = err.format(enzyme)
                    errors.append(err)
            if errors:
                raise ValidationError('\n'.join(errors))

        else:
            if enzymes:
                err = 'Only vectors have enzyme {}'.format(kind)
                raise ValidationError(err)

        return enzymes

    def clean_enzyme_in(self):
        '''It validates the in enzyme'''
        return self._validate_enzyme('in')

    def clean_enzyme_out(self):
        '''It validates the out enzyme'''
        return self._validate_enzyme('out')

    # Validate that a vector must have a resistance,
    # only vectors have resistance and
    # if the resistance exists or not

    def clean_resistance(self):
        '''It validates the in resistance'''
        resistance = self.cleaned_data['resistance']
        error_in_type = self.errors.get('type', False)
        error_in_vector = self.errors.get('vector', False)

        if error_in_type or error_in_vector:
            return resistance

        type_ = self.cleaned_data['type']
        if type_ == VECTOR_TYPE_NAME:
            if not resistance:
                raise ValidationError('A vector must have a resistance')

        else:
            if resistance:
                raise ValidationError('Only vectors have resistance')
        return resistance


def add_feature(database, name, type_name, vector, genbank, props):
    'it adds a feature to the database'

    seq = SeqIO.read(genbank, 'gb')
    residues = str(seq.seq)
    name = name
    uniquename = seq.id
    type_ = Cvterm.objects.using(database).get(name=type_name)
    db = Db.objects.using(database).get(name=GOLDEN_DB)
    try:
        dbxref = Dbxref.objects.using(database).create(db=db,
                                                       accession=uniquename)
    except IntegrityError as error:
        raise IntegrityError('feature already in db' + str(error))

    vector_type = Cvterm.objects.using(database).get(name=VECTOR_TYPE_NAME)
    if vector and type_ == vector_type:
        # already checked in form validation
        raise RuntimeError("a vector feature can't  have a vector")

    if vector:
        vector = Feature.objects.using(database).get(uniquename=vector,
                                               type=vector_type)
    else:
        vector = None
    try:
        feature = Feature.objects.using(database).create(uniquename=uniquename,
                                                   name=name, type=type_,
                                                   residues=residues,
                                                  dbxref=dbxref, vector=vector)
    except IntegrityError as error:
        raise IntegrityError('feature already in db' + str(error))

    for type_name, values in props.items():
        try:
            type_ = Cvterm.objects.using(DB).get(name=type_name)
        except Cvterm.DoesNotExist:
            msg = 'Trying to add a property which cvterm does not exist'
            raise RuntimeError(msg)
        rank = 0
        for value in values:
            Featureprop.objects.using(DB).create(feature=feature, type=type_,
                                             value=value, rank=rank)
            rank += 1
    return feature


def add_feature_from_form(form_data):
    'With this function we add a feature to the database'
    props = {}
    vector_type = Cvterm.objects.using(DB).get(name=VECTOR_TYPE_NAME)
    feature_type_name = form_data['type']
    if form_data['description']:
        props[DESCRIPTION_TYPE_NAME] = [form_data['description']]
    if form_data['reference']:
        props[REFERENCE_TYPE_NAME] = [form_data['reference']]
    if feature_type_name == vector_type.name:
        props[ENZYME_IN_TYPE_NAME] = form_data['enzyme_in']
        props[ENZYME_OUT_TYPE_NAME] = form_data['enzyme_out']
        props[RESISTANCE_TYPE_NAME] = [form_data['resistance']]

    feature = add_feature(database=DB,
                          name=form_data['name'], type_name=feature_type_name,
                          vector=form_data['vector'],
                          genbank=form_data['gbfile'],
                          props=props)

    return feature


def add_feature_view(request):
    'The add feature view'
    context = RequestContext(request)
    context.update(csrf(request))
    if request.method == 'POST':
        request_data = request.POST
    else:
        request_data = None

    if request_data:
        form = FeatureForm(request_data, request.FILES)
        if form.is_valid():
            feat_form_data = form.cleaned_data
            try:
                feature = add_feature_from_form(feat_form_data)
            except IntegrityError as error:
                if 'feature already in db' in error:
                    # TODO choose a template
                    return render_to_response('feature_template.html',
                                              {},
                                    context_instance=RequestContext(request))
                else:
                    return HttpResponseServerError()
            except Exception as error:
                return HttpResponseServerError()
            # if everithing os fine we show the just added feature
            return render_to_response('feature_template.html',
                                          {'feature': feature},
                                          context_instance=RequestContext(request))

    else:
        form = FeatureForm()
    context['form'] = form
    template = 'feature_add_template.html'
    return render_to_response(template, context)


def feature_view(request, uniquename):
    'The feature view'
    try:
        feature = Feature.objects.using(DB).get(uniquename=uniquename)
    except Feature.DoesNotExist:
        feature = None
    return render_to_response('feature_template.html', {'feature': feature},
                              context_instance=RequestContext(request))
