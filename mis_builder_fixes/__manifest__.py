{
    'name': 'MIS Builder fixes',
    'version': '1.0.0',
    'summary': 'Collection of fixes for mis_builder bugs',
    'category': 'Technical',
    'description': """
        Fixes for known mis_builder issues:

        1. Annotation init guard: Prevents crash during registry preloading
           when mis.report.instance.annotation.init() tries to CREATE INDEX
           on a table that does not yet exist.

        2. KPI expression assertion: Handles stale KPI expression_ids when
           subkpis have been removed from a report, preventing an
           AssertionError in _get_expressions().
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'depends': ['mis_builder'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
