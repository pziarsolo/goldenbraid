from django.http import HttpResponse

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from django.forms.util import ErrorDict
from django.core.context_processors import csrf
from django.template.context import RequestContext
from django import forms
from django.shortcuts import render_to_response
from django.core.exceptions import ValidationError
from Bio import SeqIO
from django.forms.widgets import Select

from goldenbraid.domestication import domesticate, CATEGORIES

DEFAULT_MELTING_TEMP = 50


class DomesticationForm(forms.Form):
    seq = forms.FileField(max_length=100,
                           label='Add a genbank or a fast file')
    choices = [('', '')]
    for category_name in CATEGORIES.keys():
        choices.append((category_name, category_name))
    category = forms.CharField(max_length=100,
                              label='Choose a category to domesticate to',
                              widget=Select(choices=choices), required=False)
    prefix = forms.CharField(max_length=4,
                             label='custom prefix', required=False)
    suffix = forms.CharField(max_length=4,
                             label='custom prefix', required=False)

    def clean_category(self):
        category_name = self.cleaned_data['category']
        if not category_name:
            del self.cleaned_data['category']
            return
        if category_name not in CATEGORIES.keys():
            raise ValidationError('You must choose a valid category')
        return category_name

    def clean_seq(self):
        content = self.cleaned_data['seq'].chunks().next()
        self.cleaned_data['seq'].seek(0)
        if content.startswith('LOCUS') or content.startswith('>'):
            pass
        else:
            msg = 'The given file must be a fasta or a genbank file'
            raise ValidationError(msg)
        format_ = 'fasta' if content.startswith('>') else 'genbank'
        seq = SeqIO.read(self.cleaned_data['seq'], format_)
        if not _seq_is_dna(seq.seq):
            msg = 'The given file contains seqs with not allowed nucleotides'
            msg += ' ATGC'
            raise ValidationError(msg)
        if self._data_in(self.cleaned_data, 'category'):
            category = self.cleaned_data['category']
            if category in ('13-14-15-16 (CDS)', '13 (SP)', '12 (NT)',
                             '13-14-15 (CDS)'):
                if not _seq_has_codon_start(seq):
                    msg = 'The provided seq must start wit start codon in '
                    msg += 'order to use as choosen category'
                    raise ValidationError(msg)
            if category in ('13-14-15-16 (CDS)', '14-15-16 (CDS)', '16 (CT)'):
                if not _seq_has_codon_end(seq):
                    msg = 'The provided seq must end with a end codon in '
                    msg += 'order to use as choosen category'
                    raise ValidationError(msg)
            if category in ('13-14-15-16 (CDS)', '13 (SP)', '12 (NT)',
                            '13-14-15 (CDS)', '14-15-16 (CDS)', '16 (CT)'):
                if not _seq_has_codon_end(seq):
                    msg = 'The provided seq must be multiple of three in '
                    msg += 'order to use as choosen category'
                    raise ValidationError(msg)

        return seq

    def _clean_customtags(self, kind):
        tag = self.cleaned_data[kind]
        if not tag:
            del self.cleaned_data[kind]
            return tag
        if len(tag) != 4:
            raise ValidationError('{} tag must be of length 4'.format(kind))
        if not _seq_is_dna(tag):
            msg = 'The given tag seqs with not allowed nucleotides: ATGC'
            raise ValidationError(msg)
        return tag

    def clean_suffix(self):
        return self._clean_customtags('suffix')

    def clean_prefix(self):
        return self._clean_customtags('prefix')

    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors and
        self.cleaned_data.
        """
        self._errors = ErrorDict()
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        # If the form is permitted to be empty, and none of the form data has
        # changed from the initial data, short circuit any validation.
        if self.empty_permitted and not self.has_changed():
            return
        self._clean_fields()
        self._clean_form()
        self._post_clean()
        # custom validations
        self._multi_field_validation()
        if self._errors:
            del self.cleaned_data

    @staticmethod
    def _data_in(dictionary, key):
        return True if key in dictionary and dictionary[key] else False

    def _multi_field_validation(self):
        cleaned_data = self.cleaned_data
        try:
            if (not self._data_in(cleaned_data, 'category') and
                not self._data_in(cleaned_data, 'suffix') and
                not self._data_in(cleaned_data, 'prefix')):
                msg = 'At least we need category or prefix/suffix pair'
                raise ValidationError(msg)
        except ValidationError, e:
            name = 'category'
            self._errors[name] = self.error_class(e.messages)
            if name in self.cleaned_data:
                del self.cleaned_data[name]
            return

        try:
            if (self._data_in(cleaned_data, 'category') and
                (self._data_in(cleaned_data, 'suffix') or
                 self._data_in(cleaned_data, 'prefix'))):
                msg = 'Can not use category and prefix/suffix simoultaneously'
                raise ValidationError(msg)
        except ValidationError, e:
            name = 'category'
            self._errors[name] = self.error_class(e.messages)
            if name in self.cleaned_data:
                del self.cleaned_data[name]
            return

        try:
            if (not self._data_in(cleaned_data, 'category') and
                (not self._data_in(cleaned_data, 'suffix') or
                 not self._data_in(cleaned_data, 'prefix'))):
                msg = 'You must provide prefix and suffix together'
                raise ValidationError(msg)
        except ValidationError, e:
            if not self._data_in(cleaned_data, 'suffix'):
                name = 'suffix'
            else:
                name = 'prefix'
            self._errors[name] = self.error_class(e.messages)
            if name in self.cleaned_data:
                del self.cleaned_data[name]


def _seq_is_dna(string):
    len_sum = sum([string.count(l.upper()) + string.count(l.lower()) for l
                                                                  in ('ATCG')])
    return False if len_sum != len(string) else True


def _seq_has_codon_start(seq):
    start = seq[:3].upper()
    return True if start == 'ATG' else False


def _seq_has_codon_end(seq):
    end = seq[-3:].upper()
    return True if end in ('TAG', 'TAA', 'TGA') else False


def __is_seq_3_multiple(seq):
    return True if divmod(len(seq), 3)[1] == 0 else False


def domestication_view(request):
    context = RequestContext(request)
    context.update(csrf(request))
    if request.method == 'POST':
        request_data = request.POST
    elif request.method == 'GET':
        request_data = request.GET
    else:
        request_data = None
    if request_data:
        form = DomesticationForm(request_data, request.FILES)
        if form.is_valid():
            # do domestication
            seq = form.cleaned_data['seq']
            category = form.cleaned_data.get('category', None)
            if category is None:
                prefix = form.cleaned_data.get('prefix')
                suffix = form.cleaned_data.get('suffix')
            else:
                prefix = CATEGORIES[category][1]
                suffix = CATEGORIES[category][2]
            pcr = domesticate(seq, category, prefix, suffix,
                              min_melting_temp=DEFAULT_MELTING_TEMP)[0]
            return render_to_response('domestication_result.html',
                                      {'category': category,
                                       'prefix': prefix,
                                       'suffix': suffix,
                                       'pcrs': pcr},
                                context_instance=RequestContext(request))
    else:
        form = DomesticationForm()
    context['form'] = form

    template = 'domestication_template.html'
    mimetype = None
    return render_to_response(template, context, mimetype=mimetype)


def domestication_view_genbank(request):
    context = RequestContext(request)
    context.update(csrf(request))
    if request.method == 'POST':
        request_data = request.POST
    elif request.method == 'GET':
        request_data = request.GET
    else:
        request_data = None
    if request_data:
        form = DomesticationForm(request_data, request.FILES)
        if form.is_valid():
            # do domestication
            seq = form.cleaned_data['seq']
            category = form.cleaned_data.get('category', None)
            if category is None:
                prefix = form.cleaned_data.get('prefix')
                suffix = form.cleaned_data.get('suffix')
            else:
                prefix = CATEGORIES[category][1]
                suffix = CATEGORIES[category][2]
            seq = domesticate(seq, category, prefix, suffix)[1]
            return  HttpResponse(seq.format('genbank'), mimetype='text/plain')

    else:
        form = DomesticationForm()
    context['form'] = form

    template = 'domestication_template.html'
    mimetype = None
    return render_to_response(template, context, mimetype=mimetype)