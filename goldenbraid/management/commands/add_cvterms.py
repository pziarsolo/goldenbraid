'''
Created on 2013 urt 15

@author: peio
'''
import csv

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

from goldenbraid.management.commands.db_utils import (get_or_load_cv,
                                                      get_or_load_cvterm)

from goldenbraid.settings import DB

MANDATORY_FIELDS = ('cv', 'name', 'definition')
FAIL_IF_EXISTS = False


def split_csv_items(string, dialect):
    'It splits the items found in the string according to the csv dialect'
    items = string.split(dialect.delimiter)
    quotechar = dialect.quotechar
    if quotechar:
        stripped_items = []
        for item in items:
            if item[0] == quotechar:
                item = item[1:]
            if item[-1] == quotechar:
                item = item[:-1]
            stripped_items.append(item)
        items = stripped_items
    return items


class fallback_dialect(csv.excel):
    delimiter = '\t'
    skipinitialspace = True
    doublequote = False
    lineterminator = '\n'


class Command(BaseCommand):
    args = '<cvterm_file>'
    help = 'Adds the given cvterm file to the chado database'

    def handle(self, *args, **options):
        'Adds the given cvterms to the chado database'
        if not args:
            raise CommandError('No cvterm file given')
        else:
            cvterms_fpath = args[0]
        try:
            run_command(open(cvterms_fpath), DB, load_cvterms, MANDATORY_FIELDS)
        except Exception as error:
            raise CommandError(str(error))


def run_command(fhand, database, loader_func, mandatory_fields):
    'it runs a command loading a csv file into the database'
    fhand.seek(0)
    file_sample = fhand.read(1024)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(file_sample)
    except Exception:
        dialect = fallback_dialect

    fhand.seek(0)
    header = fhand.readline().strip()
    col_names = [col_n.lower() for col_n in split_csv_items(header, dialect)]
    for req_col in mandatory_fields:
        if req_col not in col_names:
            msg = 'Column %s is required, but not found in header' % req_col
            raise RuntimeError(msg)

    with transaction.commit_on_success():
        reader = csv.DictReader(fhand, fieldnames=col_names, dialect=dialect)
        loader_func(database, reader)


def load_cvterms(database, reader):
    '''It adds the cvterms to the pseudo chado database

    It asumes that the cv is already loaded in the database.

    The file should have one cvterm per line with this order:

    cvname, cvterm_name, definition
    '''
    for line in reader:
        try:
            cv_name = line['cv']
            name = line['name']
            definition = line['definition']
        except KeyError:
            msg = 'Malformed line: ' + str(line)
            raise RuntimeError(msg)
        cv = get_or_load_cv(database, name=cv_name)
        get_or_load_cvterm(database, cv, name, definition)