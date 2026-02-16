# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - Sphinx 문서 설정
"""

import os
import sys

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
project = 'SQM 재고관리 시스템'
copyright = '2024, SQM Korea'
author = 'SQM Development Team'
version = '3.8.7'
release = '3.6.8'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    # 'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = []

# 언어 설정
language = 'ko'

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_title = 'SQM 재고관리 시스템 API 문서'

# -- Extension configuration -------------------------------------------------

# Napoleon 설정 (Google/NumPy 스타일 docstring)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc 설정
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'

# Intersphinx 설정
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}

# Sphinx TODO 확장 설정
todo_include_todos = True

# 모듈 모킹 (tkinter 등 GUI 모듈)
autodoc_mock_imports = [
    'tkinter', 
    'ttkbootstrap', 
    'PIL',
    'pdfplumber',
    'fitz',
    'google.genai'
]
