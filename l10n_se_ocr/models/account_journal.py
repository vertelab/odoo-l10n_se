from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pdfplumber
from base64 import b64decode
import tempfile


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _create_invoice_from_attachment(self, attachment_ids=None):
        """
        Create invoices from the attachments (for instance a Factur-X XML file)
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        invoices = self.env['account.move']

        for attachment in attachments:
            self._get_ocr_attachment(attachment)
            attachment.write({'res_model': 'mail.compose.message'})
            decoders = self.env['account.move']._get_create_invoice_from_attachment_decoders()
            invoice = False
            for decoder in sorted(decoders, key=lambda d: d[0]):
                invoice = decoder[1](attachment)
                if invoice:
                    break
            if not invoice:
                invoice = self.env['account.move'].create({})
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
            invoices += invoice
        return invoices

    def _get_ocr_attachment(self, attachment):
        attachment.ocr2index()
        all_text = ''
        with tempfile.NamedTemporaryFile('w+b', suffix='.pdf') as tmpfile:
            bytes = b64decode(attachment.datas, validate=True)
            tmpfile.write(bytes)
            tmpfile.seek(0)
            with pdfplumber.open(tmpfile.name) as pdf:
                page_content = pdf.pages[0].extract_text(layout=True)
                # page_content = pdf.pages[0].extract_table()
                print(page_content)
                # all_text = all_text + '\n' + page_content
        print(all_text)
