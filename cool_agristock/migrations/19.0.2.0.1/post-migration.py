def migrate(cr, version):
    cr.execute("""
        UPDATE res_partner AS partner
           SET cool_agristock_is_supplier = TRUE
         WHERE EXISTS (
             SELECT 1
               FROM cool_agristock_external_id_mapping AS mapping
              WHERE mapping.res_model = 'res.partner'
                AND mapping.res_id = partner.id
                AND mapping.company_id = partner.company_id
         )
    """)
