{
    'name': 'Core uninstall hook fix',
    'version': '18.0.1.0.0',
    'summary': 'Repairs the uninstall_hook lookup that breaks every module uninstall.',
    'category': 'Technical',
    'description': '''
Core uninstall hook fix
=======================

Odoo commit 9982fd9fd ("[FIX] core: commit after uninstalling each module",
2026-10-13) rewrote the uninstall loop in ``odoo/modules/loading.py`` and
changed the manifest lookup from ``pkg.info.get('uninstall_hook')`` to
``graph[name].manifest.get('uninstall_hook')``.

``graph[name]`` is an ``odoo.modules.graph.Node``. ``Node`` exposes the
manifest as ``.info`` (alias ``.data``) and has no ``.manifest`` attribute,
so the lookup raises::

    AttributeError: 'Node' object has no attribute 'manifest'

Consequence: **every** uninstall of a module that declares an
``uninstall_hook`` fails with an RPC_ERROR. In a standard database that
includes sale_management, website, stock, project, hr_contract,
hr_timesheet, account_edi_ubl_cii, account_payment, sale_project and
sale_timesheet.

Master is unaffected: it replaced ``graph.py`` with ``module_graph.py``,
where ``ModuleNode.manifest`` does exist. The backport to 18.0/19.0 kept the
new attribute name while still using the old ``Node`` class.

This module installs a ``manifest`` property on ``graph.Node`` that aliases
``info``, so the core call site resolves again. The shim is idempotent and
becomes a no-op once Odoo fixes the call site upstream - at that point this
module can simply be uninstalled.

Remove this module as soon as the Odoo package no longer carries the bug.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/core_uninstall_hook_fix',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
