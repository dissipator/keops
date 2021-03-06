
from collections import OrderedDict
import json
from django import forms
from keops.forms import extjs
from .forms import View

class FieldLine(object):
    def __init__(self, form, fields):
        self.form = form
        self.fields = fields
    
    def __iter__(self):
        for field in self.fields:
            yield (field, self.form.widgets[field])

class Fieldset(object):
    def __init__(self, name, form, fieldset):
        self.name = name
        self.form = form
        self.fieldset = fieldset
        lines = fieldset['fields']
        self.lines = []
        for line in lines:
            if not isinstance(line, (tuple, list)):
                line = (line,)
            self.lines.append(line)
    
    def __iter__(self):
        for line in self.lines:
            yield FieldLine(self.form, line)
            
class TabPage(object):
    def __init__(self, name, form, fieldsets):
        self.form = form
        self.name = name
        self.fieldsets = fieldsets
        
    def __iter__(self):
        for name, fieldset in self.fieldsets:
            yield Fieldset(name, self.form, fieldset)
            
class ModelAdmin(View):
    template = 'keops/forms/model_form.js'
    list_template = 'keops/forms/list_form.js'
    fields = ()
    exclude = ()
    readonly_fields = ()
    list_display = ()
    pages = ()
    search_fields = ()
    columns = 2
    widgets = {}
    formfield_overrides = None

    toolbar_actions = ['create', 'read', 'update', 'delete', 'print', 'delete', 'search']

    actions = []
    model = None
    title = None
    label = None
    help_text = ''

    def __init__(self, admin=None):
        self.admin = admin
        self._prepared = False
        if self.model:
            self._prepare()
        
    def contribute_to_class(self, cls, name):
        cls._admin = self
        self.model = cls
        if self.admin:
            dsgn_attrs = dict(self.admin.__dict__.copy())
            # ignore internal items
            attrs = [k for k in dsgn_attrs if not k.startswith('__')]
            for attr in attrs:
                setattr(self, attr, dsgn_attrs[attr])
            del self.admin
        self._prepare()
        
    def _prepare(self):
        if self.model._meta.abstract:
            return
        from django.db import models
        model_fields = sorted(self.model._meta.concrete_fields + self.model._meta.many_to_many)
        if not self.fields:
            self.fields = [f.name for f in model_fields if not f.name in self.exclude and not isinstance(f, 
                (models.AutoField, models.OneToOneField)) and getattr(f, 'custom_attrs', {}).get('visible', True)]
        if not self.list_display:
            self.list_display = [f.name for f in self.model._meta.concrete_fields if not f.name in self.exclude and not isinstance(f, 
                (models.AutoField, models.OneToOneField, models.ManyToManyField)) and getattr(f, 'custom_attrs', {}).get('visible', True)]

        if not self.pages:
            pages = OrderedDict()
            
        for field in model_fields:
            if not field.name in self.fields:
                continue
            if not self.pages:
                attrs = getattr(field, 'custom_attrs', {})
                page = pages.setdefault(str(attrs.get('page', None) or ''), OrderedDict())
                fieldset = page.setdefault(str(attrs.get('fieldset', None) or ''), {'fields': []})
                fieldset['fields'].append(field.name)

        if not self.pages and pages:
            for page, fieldsets in pages.items():
                pages[page] = tuple(fieldsets.items())
            self.pages = tuple(pages.items())

        if self.search_fields:
            # set search field to __icontains
            for i, f in enumerate(self.search_fields):
                if not '__' in f:
                    self.search_fields[i] = '%s__icontains' % f
        elif not self.search_fields or not self.display_expression:
            search_fields = ''
            for f in self.fields:
                field = self.model._meta.get_field_by_name(f)[0]
                if isinstance(field, models.CharField):
                    search_fields = ['%s__icontains']
                    break
            self.search_fields = self.search_fields or search_fields or (self.fields and [self.fields[0]]) or ()
            
        self.title = self.title or self.model._meta.verbose_name_plural
        self.label = self.label or self.model._meta.verbose_name
            
    def _prepare_form(self):
        if self._prepared:
            return
        for field in self.model._meta.concrete_fields + self.model._meta.many_to_many:
            if not field.name in self.fields:
                continue
            if not field.name in self.widgets:
                self.widgets[field.name] = field.custom_attrs.get('widget', None) or field.formfield()
        self._prepared = True

    def __iter__(self):
        self._prepare_form()
        for page, fieldsets in self.pages:
            yield TabPage(page, self, fieldsets)
            
    def get_form(self, request):
        return forms.models.modelform_factory(self.model, fields=self.fields, exclude=self.exclude, widgets=self.widgets)
    
    def _prepare_context(self, request, context):
        context.update({
            'model': self.model,
            'json': json,
            'extjs': extjs,
            'model_name': '%s.%s' % (self.model._meta.app_label, self.model._meta.model_name),
        })
        
    def view(self, request, view_type, **kwargs):
        if view_type == 'list':
            c = self.list_view
        else:
            self._prepare_change_view(request, kwargs)
            c = super(ModelAdmin, self).view
        return c(request, **kwargs)
    
    def _prepare_change_view(self, request, context):
        context['items'] = json.dumps(extjs.get_form_items(self))
        context['fields'] = json.dumps(['pk'] + list(self.fields))
        pk = request.GET.get('pk')
        if pk:
            context['pk'] = pk
        self._prepare_context(request, context)

    def list_view(self, request, **kwargs):
        self._prepare_form()
        kwargs['items'] = json.dumps([extjs.grid_column(name, self.widgets[name]) for name in self.list_display])
        kwargs['fields'] = json.dumps(self.list_display)
        self._prepare_context(request, kwargs)
        return self.render(request, self.list_template, kwargs)

    def add_view(self, request, **kwargs):
        kwargs['state'] = 'create'
        self.view(request, **kwargs)

    def edit_view(self, request, **kwargs):
        kwargs['state'] = 'write'
        self.view(request, **kwargs)
        
    def get_queryset(self, request):
        return self.model.objects.all()

    def get_form_field(self, field):
        self._prepare_form()
        return self.widgets[field]
