from odoo import models, fields, api
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.osv import expression
from odoo.tools import html_escape
from odoo.exceptions import RedirectWarning

from lxml import etree
import base64
import io
import logging
import pathlib
import re

import pdfplumber
from base64 import b64decode
import tempfile


_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _decode_attachment(self, attachment):
        """Decodes an ir.attachment and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :param attachment:  An ir.attachment record.
        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        to_process = []

        # XML attachments received by mail have a 'text/plain' mimetype.
        # Therefore, if content start with '<?xml', it is considered as XML.
        is_text_plain_xml = 'text/plain' in attachment.mimetype and content.startswith(b'<?xml')
        if 'pdf' in attachment.mimetype:
            # pdf_processing = self._decode_pdf(attachment.name, content)
            # print('pdf_processing', pdf_processing)
            # if not pdf_processing:
            pdf_processing = self._process_pdf_matter(attachment)
            to_process.extend(pdf_processing)
            # odoo_pdf_process = to_process.extend(self._decode_pdf(attachment.name, content))
        elif 'xml' in attachment.mimetype or is_text_plain_xml:
            to_process.extend(self._decode_xml(attachment.name, content))
        else:
            to_process.extend(self._decode_binary(attachment.name, content))
        return to_process

    def _process_pdf_matter(self, attachment):
        import fitz
        # from ParseTab import ParseTab
        doc = fitz.Document('/home/ayomir/Downloads/INV_2022_11_0001.pdf')
        page_no = 1
        page = doc.load_page(0)
        print(page.search_for('Invoice'))

        tab = ParseTab(page, [0, ymin, 9999, ymax])


        # all_text = ''
        # with tempfile.NamedTemporaryFile('w+b', suffix='.pdf') as tmpfile:
        #     bytes = b64decode(attachment.datas, validate=True)
        #     tmpfile.write(bytes)
        #     tmpfile.seek(0)
        #     with pdfplumber.open(tmpfile.name) as pdf:
        #         page_content = pdf.pages[0].extract_text(layout=True)
        #         # page_content = pdf.pages[0].extract_table()
        #         print(page_content)
        #         # all_text = all_text + '\n' + page_content
        # print(all_text)
        # if re.search('Azure', all_text):
        #     print()
        return []