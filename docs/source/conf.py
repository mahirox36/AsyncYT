# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "AsyncYT"
copyright = "2025, MahiroX36"
author = "MahiroX36"

version = ""
p = subprocess.Popen(
    ["git", "describe", "--tags", "--abbrev=0"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
out, err = p.communicate()
if out:
    version = out.decode("utf-8").strip()[1:]
else:
    print(  # noqa: T201
        "Could not get version from git:", err.decode("utf-8").strip(), file=sys.stderr
    )
    version = "0.0.0"

# The full version, including alpha/beta/rc tags.
release = version
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
