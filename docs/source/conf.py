# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../'))

import datetime
import codecs
import os.path

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

def get_short_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__short_version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

# -- Project information -----------------------------------------------------

company = f"Teledyne LeCroy Xena"
year = datetime.datetime.today().year
month = datetime.datetime.today().month
project = f"Xena Cable Performance Optimization Methodology"
copyright = f"{year}, {company}"
author = company
title = f"Xena Cable Performance Optimization Methodology"
output_basename = f"xoa_cpom_doc"

# The full version, including alpha/beta/rc tags.
release = get_version("../../xoa_cpom/__init__.py")

# The short X.Y version.
version = get_short_version("../../xoa_cpom/__init__.py")


# -- General configuration -----------------------------------------------------

# A boolean that decides whether module names are prepended to all object names 
# (for object types where a “module” of some kind is defined), e.g. for py:function directives. 
add_module_names = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# A string that determines how domain objects (e.g. functions, classes, attributes, etc.) are displayed in their table of contents entry.
# Use domain to allow the domain to determine the appropriate number of parents to show. For example, the Python domain would show Class.method() and function(), leaving out the module. level of parents. This is the default setting.
# Use hide to only show the name of the element without any parents (i.e. method()).
# Use all to show the fully-qualified name for the object (i.e. module.Class.method()), displaying all parents.
toc_object_entries_show_parents = 'hide'

# The suffix(es) of source filenames.
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# If true, figures, tables and code-blocks are automatically numbered if they have a caption. 
# The numref role is enabled. Obeyed so far only by HTML and LaTeX builders. Default is False.
numfig = True

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# These patterns also affect html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The master toctree document.
master_doc = 'index'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.extlinks',
    "sphinx_inline_tabs",
    'sphinx_copybutton',
    "sphinx_remove_toctrees",
    'sphinx_rtd_theme',
    'sphinxcontrib.googleanalytics',
]

# -- autodoc configuration

# 'signature' – Show typehints in the signature (default)
# 'description' – Show typehints as content of the function or method The typehints of overloaded functions or methods will still be represented in the signature.
# 'none' – Do not show typehints
# 'both' – Show typehints in the signature and as content of the function or method
autodoc_typehints = "none"

# 'fully-qualified' – Show the module name and its name of typehints
# 'short' – Suppress the leading module names of the typehints (ex. io.StringIO -> StringIO)
autodoc_typehints_format = 'short'

# This value controls the docstrings inheritance. 
# If set to True the docstring for classes or methods, if not explicitly set, is inherited from parents.
autodoc_inherit_docstrings =False

# The default options for autodoc directives. 
# They are applied to all autodoc directives automatically. 
# It must be a dictionary which maps option names to the values.
autodoc_default_options = {
    'member-order': 'bysource',
    'private-members': False,
    'undoc-members': False,
    'show-inheritance': False
}

# -- autosectionlabel configuration

# True to prefix each section label with the name of the document it is in, followed by a colon. 
# For example, index:Introduction for a section called Introduction that appears in document index.rst. 
# Useful for avoiding ambiguity when the same section heading appears in different documents.
autosectionlabel_prefix_document = True


# -- Options for HTML output -----------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Output file base name for HTML help builder.
htmlhelp_basename = output_basename

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = title

# The path to the HTML logo image in the static path, or URL to the logo, or ''.
# html_logo = './_static/xoa_logo.png'

html_favicon = './_static/favicon.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If true, “(C) Copyright …” is shown in the HTML footer.
# html_show_copyright = True

# If true, “Created using Sphinx” is shown in the HTML footer
# html_show_sphinx = False

# If true, the index is generated twice: once as a single page with all the entries, 
# and once as one page per starting letter. Default is False.
# html_split_index = True

# Theme config for sphinx_rtd_theme
html_show_sphinx =  False
html_show_sourcelink = False
html_logo = './_static/tlc_w1.png'
html_context = {
    "display_github": False
}
html_theme_options = {
    'analytics_anonymize_ip': False,
    'flyout_display': 'hidden',
    'version_selector': True,
    'language_selector': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': 'view',
    'style_nav_header_background': '#0076c0',
    'navigation_depth': 3,
}
googleanalytics_enabled = True
googleanalytics_id = 'G-3B4BJE8D9D'
html_css_files = ["custom.css"]

# -- Options for Texinfo output -----------------------------------------------------

# This config value contains the locations and names of other projects that should be linked to in this documentation.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

intersphinx_disabled_domains = ['std']

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, output_basename, title, author, output_basename, title, 'Miscellaneous'),
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']


# -- Options for LaTeX output -----------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
'papersize': 'a4paper',

# The font size ('10pt', '11pt' or '12pt').
'pointsize': '12pt',

# Additional stuff for the LaTeX preamble.
# 'preamble': '',

# Latex figure (float) alignment
#'figure_align': 'htbp',

'makeindex': r'\usepackage[columns=1]{idxlayout}\makeindex',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [(master_doc, f"{output_basename}.tex", title, author, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = './_static/tlc_pdf.png'

# -- Options for manual page output -----------------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, output_basename, title, [author], 1)
]


# -- Options for EPUB output -----------------------------------------------------
epub_title = title + ' ' + release
epub_author = author
epub_publisher = 'https://xenanetworks.com'
epub_copyright = copyright
epub_show_urls = 'footnote'
epub_basename = output_basename

# Remove auto-generated API docs from sidebars. They take too long to build.
remove_from_toctrees = ["api_doc/_autosummary/*"]