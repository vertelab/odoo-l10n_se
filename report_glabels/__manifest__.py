# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Glabels Reports',
    'version': '14.1',
    'category': 'Reporting',
    'summary': 'Reports by glabels-engine',
    'description': """
        Extention of report using Glabels (http://glabels.org/). 
        GLabels is a GNU/Linux program for creating labels and business cards. 
        It is designed to work with various laser/ink-jet peel-off label
        and business card sheets that you’ll find at most office supply stores. 

        Glabels uses a template for the label design and are using a special
        notation, ${name}, for including fields from the database. When you
        design your labels use a dummy csv-file for your model you want 
        to tie the report to and the format "Text: coma separated Values
        (CSV) with keys on line 1". When the template is ready you can
        upload it to the report-record (or include it in the xml-record if
        you are building a module). There is a test report action that
        also lists all fields for the choosen model.
        
        This module needs Glabel to be installed on the server (for Ubuntu: 
        sudo apt install glabels)
        
        Test your template using glabels-batch-command:
        glabels-3-batch -o <out-file> -l -C -i <csv-file> <your template.glabels>
        
""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['base'],
    'external_dependencies': {'python': ['csv']},
# 'bin': ['glabels-3-batch']
    'data': [
             "report_view.xml",
             "wizard/report_test.xml",
             ],
    'demo': ['demo_report.xml',],
    "license" : "AGPL-3",
    'installable': True,
    'active': False,
    'application': True,
    'auto_install': False,
}
