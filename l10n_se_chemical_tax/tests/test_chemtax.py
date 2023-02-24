from odoo import fields
from odoo.tests import common
import logging

_logger = logging.getLogger(__name__)

class TestChemTax(common.SavepointCase):


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_product = cls.env["product.product"].create({            
            'categ_id': 8,
            'name': 'Anpassningsbart skrivbord (CONFIG)',
            'product_tmpl_id': 9,
            'product_variant_ids': [37, 38, 12, 13, 14],
            'sale_line_warn': 'no-message',
            'tracking': 'none',
            'type': 'consu',
            'uom_id': 1,
            'uom_po_id': 1,
            'chemical_max_tax': 479.0,
            'weight': 0.5,           


        })


    def test_chemtest(self): 
        self.test_product._chemical_compute()
        self.assertEqual(self.test_product.chemical_tax, 90.5)
