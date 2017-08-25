# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel (<http://www.vertel.se>).
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

from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import workflow
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

class BankingExportPain(models.AbstractModel):
    _inherit = 'banking.export.sepa.wizard'

    @api.model
    def generate_initiating_party_block(self, parent_node, gen_args):
        payment = self.payment_order_ids[0]
        if not payment.mode.is_seb_payment:
            return super(BankingExportPain, self).generate_initiating_party_block(parent_node, gen_args)
        my_company_name = self._prepare_field(
            'Company Name',
            'self.payment_order_ids[0].mode.bank_id.partner_id.name',
            {'self': self}, gen_args.get('name_maxsize'), gen_args=gen_args)
        initiating_party_1_8 = etree.SubElement(parent_node, 'InitgPty')
        initiating_party_name = etree.SubElement(initiating_party_1_8, 'Nm')
        initiating_party_name.text = my_company_name
        payment = self.payment_order_ids[0]
        initiating_party_identifier = (
            payment.mode.initiating_party_identifier or
            payment.company_id.initiating_party_identifier)
        initiating_party_issuer = (
            payment.mode.initiating_party_issuer or
            payment.company_id.initiating_party_issuer)
        if initiating_party_identifier:
            iniparty_id = etree.SubElement(initiating_party_1_8, 'Id')
            iniparty_org_id = etree.SubElement(iniparty_id, 'OrgId')
            iniparty_org_other = etree.SubElement(iniparty_org_id, 'Othr')
            iniparty_org_other_id = etree.SubElement(iniparty_org_other, 'Id')
            iniparty_org_other_id.text = initiating_party_identifier
            scheme = etree.SubElement(iniparty_org_other, 'SchmeNm')
            cd = etree.SubElement(scheme, 'Cd')
            cd.text = 'BANK'
            if initiating_party_issuer:
                iniparty_org_other_issuer = etree.SubElement(
                    iniparty_org_other, 'Issr')
                iniparty_org_other_issuer.text = initiating_party_issuer
        elif self._must_have_initiating_party(gen_args):
            raise Warning(
                _("Missing 'Initiating Party Issuer' and/or "
                    "'Initiating Party Identifier' for the company '%s'. "
                    "Both fields must have a value.")
                % payment.company_id.name)
        return True
    
    @api.model
    def _validate_bban_seb(self, bban):
        """
        When clearing number begins with “8”
        8CCCCznnnnnnnnn (always 15 digits)
        (C=5 digit clearing number
        n=account number
        z= fill with zeroes (0) up to 15 digits)
        
        When clearing number begins with “7”
        7CCCnnnnnnn (always 11 digits)
        (C=4 digit clearing number
        n=account number)
        """
        bban = ''.join([x if x.isdigit() else ''for x in bban])
        if bban[0] == 8:
            accnr = bban[5:]
            bban = bban[:5] + ''.join(['0' for x in range(len(accnr) + 5)]) + accnr
        elif bban[0] == 7:
            accnr = bban[4:]
            bban = bban[:4] + ''.join(['0' for x in range(len(accnr) + 4)]) + accnr
        _logger.warn('bban: %s' % bban)
        return bban
    
    @api.model
    def _validate_bgnr_seb(self, bgnr):
        """
        Bankgiro number nnnnnnnn
        (7 or 8 digit number)
        """
        bgnr = ''.join([x if x.isdigit() else ''for x in bgnr])
        if len(bgnr) not in (7, 8):
            raise Warning(_("This Bankgiro number is not valid : %s") % bgnr)
        return bgnr
    
    @api.model
    def _prepare_field(self, field_name, field_value, eval_ctx, max_size=0, gen_args=None):
        """This function is designed to be inherited !"""
        _logger.warn('field_name: %s' % field_name)
        _logger.warn('field_value: %s' % field_value)
        _logger.warn('eval_ctx: %s' % eval_ctx)
        _logger.warn('gen_args: %s' % gen_args)
        res = super(BankingExportPain, self)._prepare_field(field_name, field_value, eval_ctx, max_size, gen_args)
        _logger.warn('_prepare_field res: %s' % res)
        return res

    @api.model
    def generate_party_block(
            self, parent_node, party_type, order, name, iban, bic,
            eval_ctx, gen_args):
        payment = self.payment_order_ids[0]
        #~ _logger.warn('generate_party_block eval_ctx: %s' % eval_ctx)
        if not payment.mode.is_seb_payment:
            return super(BankingExportPain, self).generate_party_block(
            parent_node, party_type, order, name, iban, bic, eval_ctx, gen_args)
        assert order in ('B', 'C'), "Order can be 'B' or 'C'"
        if party_type == 'Cdtr':
            party_type_label = 'Creditor'
        elif party_type == 'Dbtr':
            party_type_label = 'Debtor'
        party_name = self._prepare_field(
            '%s Name' % party_type_label, name, eval_ctx,
            gen_args.get('name_maxsize'), gen_args=gen_args)
        _logger.warn(iban)
        _logger.warn('.'.join(iban.split('.')[:-1] + ['state']))
        bank_state = self._prepare_field(
                '%s Bank type' % party_type_label,
                '.'.join(iban.split('.')[:-1] + ['state']),
                eval_ctx, gen_args=gen_args)
        if bank_state == 'iban':
            piban = self._prepare_field(
                '%s IBAN' % party_type_label, iban, eval_ctx, gen_args=gen_args)
            viban = self._validate_iban(piban)
        elif bank_state == 'bg':
            piban = self._prepare_field(
                '%s Bankgiro' % party_type_label, "''.join([c if c.isdigit() else '' for c in " + iban + '])', eval_ctx, gen_args=gen_args)
            viban = self._validate_bgnr_seb(piban)
        elif bank_state == 'pg':
            piban = self._prepare_field(
                '%s Postgiro' % party_type_label, "''.join([c if c.isdigit() else '' for c in " + iban + '])', eval_ctx, gen_args=gen_args)
            viban = self._validate_bban_seb(piban)
        elif bank_state == 'bank':
            piban = self._prepare_field(
                '%s Bank account' % party_type_label, "''.join([c if c.isdigit() else '' for c in " + iban + '])', eval_ctx, gen_args=gen_args)
            viban = self._validate_bban_seb(piban)
        else:
            raise Warning(_("Unknown bank account type: %s") % bank_state)
        # At C level, the order is : BIC, Name, IBAN
        # At B level, the order is : Name, IBAN, BIC
        if order == 'B':
            gen_args['initiating_party_country_code'] =  self._prepare_field(
                '%s country code' % party_type_label,
                '.'.join(name.split('.')[:-1] + ['country_id', 'code']),
                eval_ctx, gen_args=gen_args)
        elif order == 'C':
            self.generate_party_agent(
                parent_node, party_type, party_type_label,
                order, party_name, viban, bic, eval_ctx, gen_args)
        party = etree.SubElement(parent_node, party_type)
        party_nm = etree.SubElement(party, 'Nm')
        party_nm.text = party_name
        party_pstladr = etree.SubElement(party, 'PstlAdr')
        party_country = self._prepare_field(
            '%s Country' % party_type_label,
            '.'.join(name.split('.')[:-1] + ['country_id', 'code']),
            eval_ctx, 5, gen_args=gen_args)
        party_pstladr_ctry = etree.SubElement(party_pstladr, 'Ctry')
        party_pstladr_ctry.text = party_country
        party_account = etree.SubElement(
            parent_node, '%sAcct' % party_type)
        party_account_id = etree.SubElement(party_account, 'Id')
        if bank_state == 'iban':
            party_account_iban = etree.SubElement(party_account_id, 'IBAN')
            party_account_iban.text = viban
        else:
            party_account_othr = etree.SubElement(party_account_id, 'Othr')
            party_account_othr_id = etree.SubElement(party_account_othr, 'Id')
            party_account_othr_id.text = viban
            scheme = etree.SubElement(party_account_othr, 'SchmeNm')
            if bank_state == 'bg':
                prtry = etree.SubElement(scheme, 'Prtry')
                prtry.text = 'BGNR'
            else:
                cd = etree.SubElement(scheme, 'Cd')
                cd.text = 'BBAN'
        if order == 'B':
            self.generate_party_agent(
                parent_node, party_type, party_type_label,
                order, party_name, viban, bic, eval_ctx, gen_args)
        return True

    @api.model
    def generate_start_payment_info_block_seb(
            self, parent_node, payment_info_ident,
            priority, local_instrument, sequence_type, requested_date,
            eval_ctx, gen_args):
        payment_info_2_0 = etree.SubElement(parent_node, 'PmtInf')
        payment_info_identification_2_1 = etree.SubElement(
            payment_info_2_0, 'PmtInfId')
        payment_info_identification_2_1.text = self._prepare_field(
            'Payment Information Identification',
            payment_info_ident, eval_ctx, 35, gen_args=gen_args)
        payment_method_2_2 = etree.SubElement(payment_info_2_0, 'PmtMtd')
        payment_method_2_2.text = gen_args['payment_method']
        nb_of_transactions_2_4 = False
        control_sum_2_5 = False
        if gen_args.get('pain_flavor') != 'pain.001.001.02':
            batch_booking_2_3 = etree.SubElement(payment_info_2_0, 'BtchBookg')
            batch_booking_2_3.text = unicode(self.batch_booking).lower()
        # The "SEPA Customer-to-bank
        # Implementation guidelines" for SCT and SDD says that control sum
        # and nb_of_transactions should be present
        # at both "group header" level and "payment info" level
            nb_of_transactions_2_4 = etree.SubElement(
                payment_info_2_0, 'NbOfTxs')
            control_sum_2_5 = etree.SubElement(payment_info_2_0, 'CtrlSum')
        payment_type_info_2_6 = etree.SubElement(
            payment_info_2_0, 'PmtTpInf')
        if priority and gen_args['payment_method'] != 'DD':
            instruction_priority_2_7 = etree.SubElement(
                payment_type_info_2_6, 'InstrPrty')
            instruction_priority_2_7.text = priority
        service_level_2_8 = etree.SubElement(
            payment_type_info_2_6, 'SvcLvl')
        service_level_code_2_9 = etree.SubElement(service_level_2_8, 'Cd')
        service_level_code_2_9.text = eval_ctx['svclvl_cd']
        if local_instrument:
            local_instrument_2_11 = etree.SubElement(
                payment_type_info_2_6, 'LclInstrm')
            local_instr_code_2_12 = etree.SubElement(
                local_instrument_2_11, 'Cd')
            local_instr_code_2_12.text = local_instrument
        if sequence_type:
            sequence_type_2_14 = etree.SubElement(
                payment_type_info_2_6, 'SeqTp')
            sequence_type_2_14.text = sequence_type

        if gen_args['payment_method'] == 'DD':
            request_date_tag = 'ReqdColltnDt'
        else:
            request_date_tag = 'ReqdExctnDt'
        requested_date_2_17 = etree.SubElement(
            payment_info_2_0, request_date_tag)
        requested_date_2_17.text = requested_date
        return payment_info_2_0, nb_of_transactions_2_4, control_sum_2_5

    @api.multi
    def create_sepa(self):
        """Creates the SEPA Credit Transfer file. That's the important code!"""
        if not self.payment_order_ids[0].mode.is_seb_payment:
            return super(BankingExportPain, self).create_sepa()
        pain_flavor = self.payment_order_ids[0].mode.type.code
        convert_to_ascii = \
            self.payment_order_ids[0].mode.convert_to_ascii
        if pain_flavor == 'pain.001.001.03':
            bic_xml_tag = 'BIC'
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"
            # and we put 70 and not 140
            name_maxsize = 70
            root_xml_tag = 'CstmrCdtTrfInitn'
        else:
            raise Warning(
                _("Payment Type Code '%s' is not supported. The only "
                  "Payment Type Codes supported for SEPA Credit Transfers "
                  "are 'pain.001.001.02', 'pain.001.001.03', "
                  "'pain.001.001.04', 'pain.001.001.05'"
                  " and 'pain.001.003.03'.") %
                pain_flavor)
        gen_args = {
            'bic_xml_tag': bic_xml_tag,
            'name_maxsize': name_maxsize,
            'convert_to_ascii': convert_to_ascii,
            'payment_method': 'TRF',
            'file_prefix': 'sct_',
            'pain_flavor': pain_flavor,
            'pain_xsd_file':
            'account_banking_sepa_credit_transfer/data/%s.xsd'
            % pain_flavor,
        }
        pain_ns = {
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            None: 'urn:iso:std:iso:20022:tech:xsd:%s' % pain_flavor,
        }
        xml_root = etree.Element('Document', nsmap=pain_ns)
        pain_root = etree.SubElement(xml_root, root_xml_tag)
        pain_03_to_05 = [
            'pain.001.001.03',
            'pain.001.001.04',
            'pain.001.001.05',
            'pain.001.003.03'
        ]
        # A. Group header
        group_header_1_0, nb_of_transactions_1_6, control_sum_1_7 = \
            self.generate_group_header_block(pain_root, gen_args)
        transactions_count_1_6 = 0
        total_amount = 0.0
        amount_control_sum_1_7 = 0.0
        lines_per_group = {}
        # key = (requested_date, priority)
        # values = list of lines as object
        for payment_order in self.payment_order_ids:
            total_amount = total_amount + payment_order.total
            for line in payment_order.bank_line_ids:
                priority = line.priority
                # The field line.date is the requested payment date
                # taking into account the 'date_prefered' setting
                # cf account_banking_payment_export/models/account_payment.py
                # in the inherit of action_open()
                key = (line.date, priority, self.seb_svclvl_cd(line))
                if key in lines_per_group:
                    lines_per_group[key].append(line)
                else:
                    lines_per_group[key] = [line]
        for (requested_date, priority, svclvl_cd), lines in lines_per_group.items():
            # B. Payment info
            payment_info_2_0, nb_of_transactions_2_4, control_sum_2_5 = \
                self.generate_start_payment_info_block_seb(
                    pain_root,
                    "self.payment_order_ids[0].reference + '-' "
                    "+ requested_date.replace('-', '')  + '-' + priority + '-' + svclvl_cd",
                    priority, False, False, requested_date, {
                        'self': self,
                        'priority': priority,
                        'requested_date': requested_date,
                        'svclvl_cd': svclvl_cd,
                    }, gen_args)
            self.generate_party_block(
                payment_info_2_0, 'Dbtr', 'B',
                'self.payment_order_ids[0].mode.bank_id.partner_id.'
                'name',
                'self.payment_order_ids[0].mode.bank_id.acc_number',
                'self.payment_order_ids[0].mode.bank_id.bank.bic or '
                'self.payment_order_ids[0].mode.bank_id.bank_bic',
                {'self': self},
                gen_args)
            charge_bearer_2_24 = etree.SubElement(payment_info_2_0, 'ChrgBr')
            charge_bearer_2_24.text = self.charge_bearer
            transactions_count_2_4 = 0
            amount_control_sum_2_5 = 0.0
            for line in lines:
                transactions_count_1_6 += 1
                transactions_count_2_4 += 1
                # C. Credit Transfer Transaction Info
                credit_transfer_transaction_info_2_27 = etree.SubElement(
                    payment_info_2_0, 'CdtTrfTxInf')
                payment_identification_2_28 = etree.SubElement(
                    credit_transfer_transaction_info_2_27, 'PmtId')
                end2end_identification_2_30 = etree.SubElement(
                    payment_identification_2_28, 'EndToEndId')
                end2end_identification_2_30.text = self._prepare_field(
                    'End to End Identification', 'line.name',
                    {'line': line}, 35, gen_args=gen_args)
                currency_name = self._prepare_field(
                    'Currency Code', 'line.currency.name',
                    {'line': line}, 3, gen_args=gen_args)
                amount_2_42 = etree.SubElement(
                    credit_transfer_transaction_info_2_27, 'Amt')
                instructed_amount_2_43 = etree.SubElement(
                    amount_2_42, 'InstdAmt', Ccy=currency_name)
                instructed_amount_2_43.text = '%.2f' % line.amount_currency
                amount_control_sum_1_7 += line.amount_currency
                amount_control_sum_2_5 += line.amount_currency
                if not line.bank_id:
                    raise Warning(
                        _("Bank account is missing on the bank payment line "
                            "of partner '%s' (reference '%s').")
                        % (line.partner_id.name, line.name))
                self.generate_party_block(
                    credit_transfer_transaction_info_2_27, 'Cdtr',
                    'C', 'line.partner_id.name', 'line.bank_id.acc_number',
                    'line.bank_id.bank.bic or '
                    'line.bank_id.bank_bic', {'line': line}, gen_args)
                self.generate_remittance_info_block(
                    credit_transfer_transaction_info_2_27, line, gen_args)
            if pain_flavor in pain_03_to_05:
                nb_of_transactions_2_4.text = unicode(transactions_count_2_4)
                control_sum_2_5.text = '%.2f' % amount_control_sum_2_5
        if pain_flavor in pain_03_to_05:
            nb_of_transactions_1_6.text = unicode(transactions_count_1_6)
            control_sum_1_7.text = '%.2f' % amount_control_sum_1_7
        else:
            nb_of_transactions_1_6.text = unicode(transactions_count_1_6)
            control_sum_1_7.text = '%.2f' % amount_control_sum_1_7
        return self.finalize_sepa_file_creation(
            xml_root, total_amount, transactions_count_1_6, gen_args)
    
    def seb_svclvl_cd(self, line):
        """Check if this is a domestic or international (SEPA) payment."""
        if self.payment_order_ids[0].mode.bank_id.partner_id.country_id == line.partner_id.country_id:
            return 'NURG'
        else:
            return 'SEPA'
