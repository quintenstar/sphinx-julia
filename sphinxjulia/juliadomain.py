from docutils import nodes
from docutils.parsers.rst import Directive

from sphinx import addnodes
from sphinx.locale import l_
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.docfields import DocFieldTransformer
from . import model, modelparser, translators_html, translators_latex, query


class JuliaDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    doc_field_types = []

    def run(self):
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name
        self.env = self.state.document.settings.env
        modelnode = self.parse_arguments()
        scope = self.env.ref_context.get('jl:scope', [])
        docname = self.env.docname
        dictionary = self.env.domaindata['jl'][self.objtype]
        modelnode["ids"] = [modelnode.uid(scope)]
        modelnode.register(docname, scope, dictionary)
        self.parse_content(modelnode)
        DocFieldTransformer(self).transform_all(modelnode)
        return [modelnode]

    def parse_arguments(self):
        return modelparser.parse(self.objtype, self.arguments[0])

    def parse_content(self, modelnode):
        self.state.nested_parse(self.content, self.content_offset, modelnode)


class Module(JuliaDirective):
    final_argument_whitespace = False

    def parse_content(self, modelnode):
        if 'jl:scope' not in self.env.ref_context:
            self.env.ref_context['jl:scope'] = []
        self.env.ref_context['jl:scope'].append(modelnode.name)
        JuliaDirective.parse_content(self, modelnode)
        self.env.ref_context['jl:scope'].pop()


class Function(JuliaDirective):
    doc_field_types = [
        TypedField('parameter', label=l_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='obj', typenames=('paramtype', 'type'),
                   can_collapse=True),
        TypedField('kwparam', label=l_('Keyword Parameters'),
                   names=('kwparam', 'kwparameter', 'kwarg', 'kwargument'),
                   typerolename='obj', typenames=('kwparamtype', 'kwtype'),
                   can_collapse=True),
        GroupedField('exceptions', label=l_('Exceptions'), rolename='exc',
                     names=('raises', 'raise', 'exception', 'except'),
                     can_collapse=True),
        Field('returnvalue', label=l_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=l_('Return type'), has_arg=False,
              names=('rtype',), bodyrolename='obj'),
    ]
# <<<<<<< Updated upstream
# =======

#     def before_content(self):
#         print()
#         print("is called")
#         env = self.state.document.settings.env
#         #if env.config.julia_docstring_show_type:
#         l = []
#         for arg in self.function["arguments"]:
#             if arg["type"]:
#                 l.append(":type {name}: :class:`{type}`\n".format(**arg))
#         for arg in self.function["kwarguments"]:
#             if arg["type"]:
#                 l.append(":kwtype {name}: :class:`{type}`\n".format(**arg))
#         self.content.append(ViewList(l))
# >>>>>>> Stashed changes


class Abstract(JuliaDirective):
    pass


class Type(JuliaDirective):
    pass


class JuliaXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode['jl:scope'] = env.ref_context.get('jl:scope', []).copy()
        if not has_explicit_title:
            title = title.lstrip('.')    # only has a meaning for the target
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot+1:]
        return title, target


class JuliaDomain(Domain):
    """
    Julia language domain.
    """
    name = 'jl'
    label = 'Julia'
    object_types = {
        'function': ObjType(l_('function'), 'func'),
        'type': ObjType(l_('type'), 'type'),
        'abstract': ObjType(l_('abstract'), 'abstract'),
        'module': ObjType(l_('module'), 'mod'),
    }

    directives = {
        'function': Function,
        'abstract': Abstract,
        'type': Type,
        'module': Module,
    }

    roles = {
        'func': JuliaXRefRole(fix_parens=False),
        'type':  JuliaXRefRole(),
        'abstract': JuliaXRefRole(),
        'mod':    JuliaXRefRole(),
    }

    initial_data = {
        # name -> [{docname, scope, uid}, ...]
        "module": {},
        "abstract": {},
        "type": {},
        # name -> [{docname, scope, templateparameters, signature, uid}]
        "function": {},
    }
    indices = [
        # JuliaModuleIndex,
    ]

    def find_obj(self, rolename, node, targetstring):
        for typename, objtype in self.object_types.items():
            if rolename in objtype.roles:
                break
        else:
            return []
        basescope = node['jl:scope']
        dictionaries = self.env.domaindata['jl']
        return query.find_object_by_string(typename, basescope,
                                           targetstring, dictionaries)

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        matches = self.find_obj(typ, node, target)
        if not matches:
            return None
        elif len(matches) > 1:
            env.warn_node(
                'more than one target found for cross-reference '
                '%r: %s' % (target, ', '.join(match["uid"] for match in matches)),
                node)
        match = matches[0]
        return make_refnode(builder, fromdocname,
                            match["docname"], match["uid"],
                            contnode, target)


def update_builder(app):
    app.env.juliaparser = modelparser.JuliaParser()
    # translator = app.builder.translator_class
    # translator.first_kwordparam = True
    # _visit_desc_parameterlist = translator.visit_desc_parameterlist
    # def visit_desc_parameterlist(self, node):
    #     self.first_kwordparam = True
    #     _visit_desc_parameterlist(self, node)
    # translator.visit_desc_parameterlist = visit_desc_parameterlist


def setup(app):
    # app.add_config_value('julia_signature_show_qualifier', True, 'html')
    # app.add_config_value('julia_signature_show_type', True, 'html')
    # app.add_config_value('julia_signature_show_default', True, 'html')
    # app.add_config_value('julia_docstring_show_type', True, 'html')

    for name in ["Module", "Abstract", "Type", "Function"]:
        htmltranslator = translators_html.TranslatorFunctions[name]
        latextranslator = translators_latex.TranslatorFunctions[name]
        modelclass = getattr(model, name)
        app.add_node(modelclass,
                     html=htmltranslator,
                     latex=latextranslator,
                     )
    app.connect('builder-inited', update_builder)
    app.add_domain(JuliaDomain)
