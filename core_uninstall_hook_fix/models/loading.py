"""Repair the module uninstall hook lookup in Odoo 18.

Odoo commit 9982fd9fd ("[FIX] core: commit after uninstalling each module",
2026-10-13) rewrote the uninstall loop in ``odoo/modules/loading.py`` and
changed the manifest lookup from::

    for pkg in pkgs:
        uninstall_hook = pkg.info.get('uninstall_hook')

to::

    for name in removing_modules:
        if (uninstall_hook := graph[name].manifest.get('uninstall_hook')):

``graph[name]`` is a ``odoo.modules.graph.Node``, and ``Node`` exposes the
manifest as ``.info`` (alias ``.data``). It has no ``.manifest`` attribute,
so the lookup raises ``AttributeError: 'Node' object has no attribute
'manifest'`` and **every** uninstall of a module that declares an
``uninstall_hook`` fails with an RPC_ERROR.

Master is not affected: it replaced ``graph.py`` with ``module_graph.py``,
where ``ModuleNode.manifest`` does exist. The backport to 18.0/19.0 kept the
new attribute name while still using the old ``Node`` class.

This module wraps ``odoo.modules.loading.load_modules`` and, before calling
the original, teaches ``Node`` to answer ``.manifest`` with its ``.info``
mapping. That is a one-line shim, it is idempotent, and it disappears by
itself once Odoo fixes the call site upstream.
"""

import logging

from odoo.modules import graph as module_graph
from odoo.modules import loading as module_loading

_logger = logging.getLogger(__name__)


def _patch_node_manifest():
    """Give ``graph.Node`` a ``manifest`` property aliasing ``info``.

    Idempotent: the property is only installed once, and only when the
    attribute is genuinely missing.
    """
    node = module_graph.Node
    if "manifest" in node.__dict__ or hasattr(node, "manifest"):
        return False
    node.manifest = property(lambda self: self.info)
    _logger.info(
        "core_uninstall_hook_fix: graph.Node.manifest now aliases Node.info"
    )
    return True


_patch_node_manifest()

_original_load_modules = module_loading.load_modules


def _load_modules(*args, **kwargs):
    # Re-apply on every load: a registry reload may have rebuilt the class
    # hierarchy, and the shim costs nothing when it is already in place.
    _patch_node_manifest()
    return _original_load_modules(*args, **kwargs)


module_loading.load_modules = _load_modules
