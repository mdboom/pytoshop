#
# From https://github.com/simphony/traitlet-documenter
# but heavily modified to avoid the problematic ast/astor part.
#


from sphinx.ext.autodoc import ClassLevelDocumenter

import traitlets as t


class ClassTraitletDocumenter(ClassLevelDocumenter):

    objtype = 'traitletattribute'
    directivetype = 'attribute'
    member_order = 60

    # must be higher than other attribute documenters
    priority = 12

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        """
        Check that the documented member is a trait instance.
        """
        return isinstance(member, t.TraitType)

    def document_members(self, all_members=False):
        pass

    def add_content(self, more_content, no_docstring=False):
        """
        If the help attribute is defined, add the help content,
        otherwise, add the info content.

        If the default value is found in the definition, add the
        default value as well
        """
        # Never try to get a docstring from the trait object.
        super(ClassTraitletDocumenter, self).add_content(
            more_content, no_docstring=True)

        if hasattr(self, 'get_sourcename'):
            sourcename = self.get_sourcename()
        else:
            sourcename = u'<autodoc>'

        # Get help message, if defined, otherwise, add the info
        if self.object.help:
            self.add_line(self.object.help, sourcename)
        else:
            self.add_line(self.object.info(), sourcename)

        default_value = self.object.default_value
        if default_value == t.Undefined:
            if self.object.allow_none:
                default_value = None

        if default_value != t.Undefined:
            self.add_line('', sourcename)
            self.add_line(
                'Default: {}'.format(default_value),
                sourcename)

    def add_directive_header(self, sig):
        """ Add the sphinx directives.

        Add the 'attribute' directive with the annotation option
        set to the traitlet type

        """
        ClassLevelDocumenter.add_directive_header(self, sig)
        if hasattr(self, 'get_sourcename'):
            sourcename = self.get_sourcename()
        else:
            sourcename = u'<autodoc>'

        trait_type = type(self.object).__name__
        self.add_line(
            '   :annotation: = {0}'.format(trait_type), sourcename)


def setup(app):
    """
    Add the TraitletDocumenter in the current sphinx autodoc instance.
    """
    app.add_autodocumenter(ClassTraitletDocumenter)
