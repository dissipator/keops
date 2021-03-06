
from django.utils import six
from django.forms import forms

class View(object):
    template_name = 'keops/forms/view.html'

    def get_form(self):
        return self
    
    def render(self, request, template, context):
        from django.shortcuts import render
        context['form'] = self.get_form()
        return render(request, template, context)
    
    def view(self, request, **kwargs):
        """
        Render a form instance.
        """
        return self.render(request, self.template_name, kwargs)

class BaseForm(forms.BaseForm, View):
    pass

class Form(six.with_metaclass(forms.DeclarativeFieldsMetaclass, BaseForm)):
    pass
