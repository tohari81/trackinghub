from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from io import StringIO
import base64
import os
import logging
from suds.client import Client
import xml.etree.ElementTree as ET
import requests
import json
from datetime import timedelta  
from datetime import datetime
from datetime import date
import math

_logger = logging.getLogger(__name__)

class KurirSAP(models.Model):
    _name           = 'bmri.kurir_sap'
    _description    = 'Kurir SAP'
    _inherit        = 'mail.thread'
    _rec_name       = 'code'

    code            = fields.Char(track_visibility='always', string='Code')    

    @api.multi
    def calculate_service(self, delivery):
        kode_asal   = self.env['bmri.kurir_sap_area'].search([('zip_code','=',delivery.surat_line_idx.jenis_product.pickup_point.zip)], limit=1).tariff_code
        kode_tujuan = self.env['bmri.kurir_sap_area'].search([('zip_code','=',delivery.zipcode)], limit=1).tariff_code

        if not kode_tujuan :
            if delivery.city :
                kota = delivery.city.replace('(Kota Administrasi)', '').replace('KOTA ADM.', '').replace('KOTA', '').replace('KABUPATEN', '').replace('KAB', '').replace('(Kab)', '').replace('(Kota)', '').replace('(Kabupaten)', '').strip()
                kode_tujuan = self.env['bmri.kurir_sap_area'].search([('city_name','=ilike',kota)], limit=1).tariff_code
                _logger.error('kota : --' + str(kota)+'--')

        if not kode_tujuan :
            kode_tujuan = 'JK00'

        delivery.write({'partner_code_from'    : kode_asal, 'partner_code_to'      : kode_tujuan})

    @api.multi
    def tracking_prioritas_1(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation
        API_KEY     = self.env['bmri.url_config'].search([('url_config_line_idx','=',rekanan_id),('url_type_id','=','API_KEY'),('state','=',operation)]).url_value
        TRACKING    = 'http://track.coresyssap.com/shipment/tracking/awb?awb_no=' + str(delivery.partner_number)
        headers     = {'api_key':API_KEY}    
        request_res = requests.get(url = TRACKING, headers=headers)

        delivery.write({'sys_check' : datetime.now(),'sys_msg': '[1] \n' + str(request_res.text) + '\n' + str(TRACKING)+ '\n' + str(headers)})

        return request_res.text 

    @api.multi
    def tracking_prioritas_2(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation
        API_KEY     = self.env['bmri.url_config'].search([('url_config_line_idx','=',rekanan_id),('url_type_id','=','API_KEY'),('state','=',operation)]).url_value
        TRACKING    = 'http://track.coresyssap.com/shipment/tracking/reference?reference_no=' + str(delivery.partner_number)
        headers     = {'api_key':API_KEY}    
        request_res = requests.get(url = TRACKING, headers=headers)

        delivery.write({'sys_check' : datetime.now(),'sys_msg': '[2] \n' + str(request_res.text) + '\n' + str(TRACKING)+ '\n' + str(headers)})

        return request_res.text 

    @api.multi
    def tracking_prioritas_3(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation
        API_KEY     = self.env['bmri.url_config'].search([('url_config_line_idx','=',rekanan_id),('url_type_id','=','API_KEY'),('state','=',operation)]).url_value
        TRACKING    = 'http://track.coresyssap.com/shipment/tracking/reference?reference_no=' + str(delivery.reff)
        headers     = {'api_key':API_KEY}    
        request_res = requests.get(url = TRACKING, headers=headers)

        delivery.write({'sys_check' : datetime.now(),'sys_msg': '[3] \n' + str(request_res.text) + '\n' + str(TRACKING)+ '\n' + str(headers)})

        return request_res.text 

    @api.multi
    def tracking_prioritas_4(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation
        API_KEY     = self.env['bmri.url_config'].search([('url_config_line_idx','=',rekanan_id),('url_type_id','=','API_KEY'),('state','=',operation)]).url_value
        TRACKING    = 'http://track.coresyssap.com/shipment/tracking/awb?awb_no=' + str(delivery.reff)
        headers     = {'api_key':API_KEY}    
        request_res = requests.get(url = TRACKING, headers=headers)

        delivery.write({'sys_check' : datetime.now(),'sys_msg': '[4] \n' + str(request_res.text) + '\n' + str(TRACKING)+ '\n' + str(headers)})

        return request_res.text 

    @api.multi
    def tracking(self, delivery):
        # if (delivery.state != 'delivered') :
        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation

        pastebin_url = self.tracking_prioritas_1(delivery)
        if (pastebin_url == '[]') or (pastebin_url=='"-"') :
            pastebin_url =  self.tracking_prioritas_2(delivery)
            if (pastebin_url == '[]') or (pastebin_url=='"-"') :
                pastebin_url =  self.tracking_prioritas_3(delivery)
                if (pastebin_url == '[]') or (pastebin_url=='"-"') :
                    pastebin_url =  self.tracking_prioritas_4(delivery)

        # delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})

        if (pastebin_url=='[]') or (pastebin_url=='') or (pastebin_url=='"-"') :
            delivery.write({'sys_check' : datetime.now()})
        else :

            delivery.rpx_log_line.unlink()

            try :

                loaded_json = json.loads(pastebin_url)
                last_date   = ''
                last_state  = ''

                for x in loaded_json:

                    cekpoin_kurir   = x['rowstate_name'].rstrip()

                    state_map       = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id
                    kode_state_map  = state_map.on_bmri
                    surat_state_map = state_map.on_system

                    # if delivery.state not in ['delivered','retur'] :
                    if delivery.state not in ['delivered'] :
                        delivery.write({'state': surat_state_map})

                    delivery.rpx_log_line.create({
                        'rpx_log_line_id'   : delivery.id,
                        'code'              : x['tracking_id'],
                        'state'             : kode_state_map,
                        'description'       : x['rowstate_name'],
                        'location'          : x['counter_name'],
                        'handle_by'         : x['user_inp'],
                        'date'              : x['create_date'],
                    })
                    if (surat_state_map == 'delivered') :
                        delivery.write( {'rpx_delivery_date'     : x['create_date'],
                                        'rpx_delivery_to'       : x['receiver_name'],
                                        'rpx_received_by'       : x['pod_receiver_name'],
                                        'rpx_rcv_relation'      : x['pod_relation_name'],
                                        'rpx_longitude'         : x['longitude'],
                                        'rpx_latitude'          : x['latitude'],
                                        'rpx_image_foto'        : x['pod_camera'] if  'pod_camera' in x else '', 
                                        'rpx_image_signature'   : x['pod_signature'] if  'pod_signature' in x else ''
                                        })

                    if (surat_state_map == 'retur') :
                        try :
                            delivery.write({'state': 'retur', 'rpx_retur_status': last_state, 'tanggal_retur': last_date})
                        except Exception as e:
                            delivery.write({'state': 'retur', 'rpx_retur_status': x['description'], 'tanggal_retur': x['create_date']})

                    if (surat_state_map == 'undelivered') :
                        last_date   = x['create_date']
                        last_state  = x['pod_status_name']

                        if (x['pod_status_name'] in ['PINDAH','DITOLAK']) :
                            if delivery.state not in ['delivered','retur'] :
                                delivery.write({
                                    'state'             : 'retur', 
                                    'state_final'       : 'calc', 
                                    'rpx_retur_status'  : x['pod_status_name'], 
                                    'tanggal_retur'     : x['create_date']
                                    })

                if (delivery.state in ['undelivered','onkurir']) and (delivery.product_kode == 'BIL' ) :
                    datediff_delivery = abs((date.today() - delivery.tanggal_order).days)
                    delivery.write({'sys_msg' : str(datetime.now()) + '\n' + str(datediff_delivery) + '\n'+ str(pastebin_url)})
                    
                    if datediff_delivery >= 10 :
                        try :
                            last_update_date = last_date
                            last_update_state = last_state
                        except Exception as e:
                            last_update_date = ''
                            last_update_state = ''                        

                        if delivery.state not in ['delivered','retur'] :
                            delivery.write({'state': 'retur'})
                            delivery.write({'rpx_retur_status': last_update_state})
                            delivery.write({'tanggal_retur': last_update_date})
                            delivery.rpx_log_line.create({
                                'rpx_log_line_id'   : delivery.id,
                                'code'              : 'BMRI-' + str(delivery.id),
                                'state'             : 'RETUR',
                                'state_final'       : 'calc',
                                'description'       : last_update_state,
                                'location'          : 'SYSTEM',
                                'handle_by'         : 'SYSTEM',
                                'date'              : last_update_date,
                            })
            except Exception as e:    
                _logger.error("SAP TRACKING : " + str(pastebin_url) + ' : ' +str(e))

        # _logger.warning("TRACKING : " + str(delivery.reff) +" DONE")
        delivery.write({'sys_check'          : datetime.now()})
        self.env.cr.commit()

    @api.multi
    def tracking_void(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation

        pastebin_url =  self.tracking_prioritas_2(delivery)


        if (pastebin_url=='[]') or (pastebin_url=='') or (pastebin_url=='"-"') :
            # _logger.warning('TRACKING VOID [' + str(delivery.kode_kurir) + '] '+ str(delivery.partner_number) + ' : NO DATA RECEIVED')
            delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            # delivery.rpx_log_line.unlink()
        else :
            # delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            # _logger.info('TRACKING [' + str(delivery.kode_kurir) + '] process')

            delivery.rpx_log_line.unlink()

            loaded_json = json.loads(pastebin_url)
            for x in loaded_json:
                cekpoin_kurir   = x['rowstate_name'].rstrip()
                # kode_state_map  = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id.on_bmri
                # surat_state_map = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id.on_system

                state_map       = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id
                kode_state_map  = state_map.on_bmri
                surat_state_map = state_map.on_system

                if delivery.state != 'delivered' :
                    delivery.write({'state': surat_state_map})

                delivery.rpx_log_line.create({
                    'rpx_log_line_id'   : delivery.id,
                    'code'              : x['tracking_id'],
                    'state'             : kode_state_map,
                    'description'       : x['rowstate_name'],
                    'location'          : x['counter_name'],
                    'handle_by'         : x['user_inp'],
                    'date'              : x['create_date'],
                })
                if (x['rowstate_name'] == 'POD - DELIVERED') :
                    # delivery.write({'rpx_delivery_loc'      : x['destination']})
                    delivery.write( {'rpx_delivery_date'     : x['create_date'],
                                    'rpx_delivery_to'       : x['receiver_name'],
                                    'rpx_received_by'       : x['pod_receiver_name'],
                                    'rpx_rcv_relation'      : x['pod_relation_name'],
                                    'rpx_longitude'         : x['longitude'],
                                    'rpx_latitude'          : x['latitude']})
                    try:
                        delivery.write({'rpx_image_foto'        : x['pod_camera'], 'rpx_image_signature'   : x['pod_signature']})
                    except Exception as e:
                        print('Error : ' + str(x))

        # _logger.warning("TRACKING : " + str(delivery.reff) +" DONE")
        delivery.write({'sys_check'          : datetime.now()})
        self.env.cr.commit()

    @api.multi
    def tracking_reff(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation

        pastebin_url =  self.tracking_prioritas_3(delivery)


        if (pastebin_url=='[]') or (pastebin_url=='') or (pastebin_url=='"-"') :
            _logger.warning('TRACKING VOID [' + str(delivery.kode_kurir) + '] '+ str(delivery.partner_number) + ' : NO DATA RECEIVED')
            delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            # delivery.rpx_log_line.unlink()
        else :
            # delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            _logger.info('TRACKING [' + str(delivery.kode_kurir) + '] process')

            delivery.rpx_log_line.unlink()

            loaded_json = json.loads(pastebin_url)
            for x in loaded_json:
                cekpoin_kurir   = x['rowstate_name'].rstrip()
                # kode_state_map  = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id.on_bmri
                # surat_state_map = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id.on_system

                state_map       = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id
                kode_state_map  = state_map.on_bmri
                surat_state_map = state_map.on_system

                if delivery.state != 'delivered' :
                    delivery.write({'state': surat_state_map})

                delivery.rpx_log_line.create({
                    'rpx_log_line_id'   : delivery.id,
                    'code'              : x['tracking_id'],
                    'state'             : kode_state_map,
                    'description'       : x['rowstate_name'],
                    'location'          : x['counter_name'],
                    'handle_by'         : x['user_inp'],
                    'date'              : x['create_date'],
                })
                if (x['rowstate_name'] == 'POD - DELIVERED') :
                    # delivery.write({'rpx_delivery_loc'      : x['destination']})
                    delivery.write( {'rpx_delivery_date'     : x['create_date'],
                                    'rpx_delivery_to'       : x['receiver_name'],
                                    'rpx_received_by'       : x['pod_receiver_name'],
                                    'rpx_rcv_relation'      : x['pod_relation_name'],
                                    'rpx_longitude'         : x['longitude'],
                                    'rpx_latitude'          : x['latitude']})
                    try:
                        delivery.write({'rpx_image_foto'        : x['pod_camera'], 'rpx_image_signature'   : x['pod_signature']})
                    except Exception as e:
                        print('Error : ' + str(x))

        # _logger.warning("TRACKING : " + str(delivery.reff) +" DONE")
        delivery.write({'sys_check'          : datetime.now()})
        self.env.cr.commit()

    @api.multi
    def tracking_reff_awb(self, delivery):

        rekanan     = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)], limit=1)
        rekanan_id  = rekanan.id
        operation   = rekanan.operation

        pastebin_url =  self.tracking_prioritas_4(delivery)


        if (pastebin_url=='[]') or (pastebin_url=='') or (pastebin_url=='"-"') :
            _logger.warning('TRACKING VOID [' + str(delivery.kode_kurir) + '] '+ str(delivery.partner_number) + ' : NO DATA RECEIVED')
            delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            # delivery.rpx_log_line.unlink()
        else :
            # delivery.write({'sys_msg'          : str(datetime.now()) + ':' + str(pastebin_url)})
            _logger.info('TRACKING [' + str(delivery.kode_kurir) + '] process')

            delivery.rpx_log_line.unlink()

            loaded_json = json.loads(pastebin_url)
            for x in loaded_json:
                cekpoin_kurir   = x['rowstate_name'].rstrip()

                state_map       = self.env['bmri.checkpoint_map'].search([('partner_id','=',rekanan_id),('nama','=',cekpoin_kurir)], limit=1).checkpoint_id
                kode_state_map  = state_map.on_bmri
                surat_state_map = state_map.on_system

                if delivery.state != 'delivered' :
                    delivery.write({'state': surat_state_map})

                delivery.rpx_log_line.create({
                    'rpx_log_line_id'   : delivery.id,
                    'code'              : x['tracking_id'],
                    'state'             : kode_state_map,
                    'description'       : x['rowstate_name'],
                    'location'          : x['counter_name'],
                    'handle_by'         : x['user_inp'],
                    'date'              : x['create_date'],
                })


                # if (x['rowstate_name'] == 'POD - DELIVERED') :
                if (surat_state_map == 'delivered') :

                    # delivery.write({'rpx_delivery_loc'      : x['destination']})
                    delivery.write( {'rpx_delivery_date'     : x['create_date'],
                                    'rpx_delivery_to'       : x['receiver_name'],
                                    'rpx_received_by'       : x['pod_receiver_name'],
                                    'rpx_rcv_relation'      : x['pod_relation_name'],
                                    'rpx_longitude'         : x['longitude'],
                                    'rpx_latitude'          : x['latitude'],
                                    'rpx_image_foto'        : x['pod_camera'], 
                                    'rpx_image_signature'   : x['pod_signature']                                    
                                    })
                    try:
                        delivery.write({'rpx_image_foto'        : x['pod_camera'], 'rpx_image_signature'   : x['pod_signature']})
                    except Exception as e:
                        print('Error : ' + str(x))

        # _logger.warning("TRACKING : " + str(delivery.reff) +" DONE")
        delivery.write({'sys_check'          : datetime.now()})
        self.env.cr.commit()


    @api.multi
    def send_delivery_order(self, delivery):
        # kurir_id        = delivery.rekanan_id
        # operation_state = delivery.operation
        if delivery.bypass_area_mapping :
            _logger.warning(delivery.kode_kurir + " - " + delivery.product_kode + " - " + delivery.reff + " : bypass area mapping")
        else :
            self.calculate_service(delivery)

        kurir_id        = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)]).id
        operation_state = self.env['res.partner'].search([('kode','=',delivery.kode_kurir)]).operation

        API_KEY     = self.env['bmri.url_config'].search([('url_config_line_idx','=',kurir_id),('url_type_id','=','API_KEY'),('state','=',operation_state)]).url_value
        URL_ORDER   = self.env['bmri.url_config'].search([('url_config_line_idx','=',kurir_id),('url_type_id','=','URL_ORDER'),('state','=',operation_state)]).url_value
        # CUST_CODE   = self.env['bmri.url_config'].search([('url_config_line_idx','=',kurir_id),('url_type_id','=','CUST_CODE'),('state','=',operation_state)]).url_value

        data        = False

        for surat in delivery:
            if ((surat.api_status == False) or (surat.api_status == 'fail')) :
                SERVICE_MAP     = self.env['bmri.partner_service_map'].search([('partner_id','=',kurir_id),('product_id','=',surat.surat_line_idx.jenis_product.id),('order_id.kode','=',surat.jenis_order)], limit=1)
                if SERVICE_MAP :
                    SERVICE_CODE    = SERVICE_MAP.service_code
                    CUST_CODE       = SERVICE_MAP.customer_code
                else :
                    SERVICE_CODE    = 'INVALID SERVICE_CODE'
                    CUST_CODE       = 'INVALID CUST_CODE'

                if  surat.product_kode == 'CCO' : 
                    # if operation_state=='PRODUCTION' :
                    #     CUST_CODE   = "CGKN02395"
                    API_KEY     = "mdr#2020c@rd"

                    data = {
                        "customer_code"             : CUST_CODE,
                        "awb_no"                    : surat.emboss_number,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : 1,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : 'Phone : ' + str(surat.hand_phone) + ' Reff : ' + surat.reff,
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",      
                        "receiver_email"            : surat.periode,
                        "description_item"          : surat.product_kode,
                        "api_key"                   : API_KEY
                    }
                elif surat.product_kode == 'DCO' :
                    # if operation_state=='PRODUCTION' :
                    #     CUST_CODE = "CGK011591"

                    data = {
                        "customer_code"             : CUST_CODE,
                        # "awb_no"                    : "",
                        "awb_no"                    : surat.emboss_number,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : 1,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : '0',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        # "receiver_phone"            : surat.hand_phone,
                        "description_item"          : surat.product_kode,
                        "api_key"                   : API_KEY
                    }                           
                elif surat.product_kode == 'DCC' : 
                    if operation_state=='PRODUCTION' :
                        # CUST_CODE = "CGKN04517"
                        if surat.site == 'SURABAYA' :
                            pick_name         = 'Kantor Bank Mandiri Remote Card Productio',
                            pick_address      = 'Jl. A. Yani no. 282, Menanggal, Kec. Gayungan, Surabaya, Jatim',
                            pick_phone        = '0',
                            pick_email        = 'pulung.subuh@bankmandiri.co.id',
                            pick_postal_code  = '60243',
                            pick_district_code = 'JI28',

                        else :
                            pick_name         = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                            pick_address      = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                            pick_phone        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                            pick_email        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                            pick_postal_code  = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                            pick_district_code =surat.partner_code_from,

                    jumlah  = int(surat.jml_kirim)
                    berat   = jumlah * 0.006
                    berat_kg = math.ceil(berat)

                    data = {
                        "customer_code"             : CUST_CODE,
                        # "awb_no"                    : "",
                        "awb_no"                    : surat.reff,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : pick_name,
                        "pickup_address"            : pick_address,
                        "pickup_phone"              : pick_phone,
                        "pickup_email"              : pick_email,
                        "pickup_postal_code"        : pick_postal_code,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : pick_district_code,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : berat_kg,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : surat.hand_phone or '00000',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        "description_item"          : "Jumlah : " +str(surat.jml_kirim) + ", Site : " +str(surat.site)+ ", Product : " +str(surat.jenis)+ ", Keterangan : " +str(surat.site_desc), 
                        "api_key"                   : API_KEY
                    }     
                elif surat.product_kode == 'TKN' : 
                    if operation_state=='PRODUCTION' :
                        # CUST_CODE = "CGKN04517"
                        if surat.site == 'SURABAYA' :
                            pick_name         = 'Kantor Bank Mandiri Remote Card Productio',
                            pick_address      = 'Jl. A. Yani no. 282, Menanggal, Kec. Gayungan, Surabaya, Jatim',
                            pick_phone        = '0',
                            pick_email        = 'pulung.subuh@bankmandiri.co.id',
                            pick_postal_code  = '60243',
                            pick_district_code = 'JI28',

                        else :
                            pick_name         = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                            pick_address      = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                            pick_phone        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                            pick_email        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                            pick_postal_code  = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                            pick_district_code =surat.partner_code_from,

                    jumlah  = int(surat.jml_kirim)
                    berat   = jumlah * 0.006
                    berat_kg = math.ceil(berat)

                    data = {
                        "customer_code"             : CUST_CODE,
                        # "awb_no"                    : "",
                        "awb_no"                    : surat.reff,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : pick_name,
                        "pickup_address"            : pick_address,
                        "pickup_phone"              : pick_phone,
                        "pickup_email"              : pick_email,
                        "pickup_postal_code"        : pick_postal_code,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : pick_district_code,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : berat_kg,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : surat.hand_phone or '00000',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        "description_item"          : "Jumlah : " +str(surat.jml_kirim) + ", Site : " +str(surat.site)+ ", Product : " +str(surat.jenis)+ ", Keterangan : " +str(surat.site_desc), 
                        "api_key"                   : API_KEY
                    }                                  
                elif surat.product_kode == 'PCM' :
                    if operation_state=='PRODUCTION' :
                        # CUST_CODE = "CGKN04517"
                        if surat.site == 'SURABAYA' :
                            pick_name         = 'Kantor Bank Mandiri Remote Card Productio',
                            pick_address      = 'Jl. A. Yani no. 282, Menanggal, Kec. Gayungan, Surabaya, Jatim',
                            pick_phone        = '0',
                            pick_email        = 'pulung.subuh@bankmandiri.co.id',
                            pick_postal_code  = '60243',
                            pick_district_code = 'JI28',

                        else :
                            pick_name         = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                            pick_address      = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                            pick_phone        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                            pick_email        = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                            pick_postal_code  = self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                            pick_district_code =surat.partner_code_from,

                    jumlah  = int(surat.jml_kirim.replace(',', ''))
                    berat   = jumlah * 0.006
                    berat_kg = math.ceil(berat)

                    data = {
                        "customer_code"             : CUST_CODE,
                        # "awb_no"                    : "",
                        "awb_no"                    : surat.reff,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : pick_name,
                        "pickup_address"            : pick_address,
                        "pickup_phone"              : pick_phone,
                        "pickup_email"              : pick_email,
                        "pickup_postal_code"        : pick_postal_code,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : pick_district_code,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : berat_kg,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : surat.hand_phone or '00000',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        "description_item"          : "Jumlah : " +str(surat.jml_kirim) + ", Site : " +str(surat.site)+ ", Product : " +str(surat.jenis)+ ", Keterangan : " +str(surat.site_desc), 
                        "api_key"                   : API_KEY
                    }                                                                   
                elif surat.product_kode == 'THM' :

                    # str_jumlah = surat.jml_kirim.replace('Roll', '').strip()
                    # int_jumlah = int(str_jumlah)

                    # berat = math.ceil(0.06 * int_jumlah)
                    # jml_koli = round(int_jumlah / 100)

                    data = {
                        "customer_code"             : CUST_CODE,
                        "awb_no"                    : "",
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        # "quantity"                  : 1,
                        # "weight"                    : 1,
                        "quantity"                  : 1,
                        "weight"                    : surat.berat,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : surat.hand_phone or '00000',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : surat.home_phone,
                        "receiver_address_3"        : "",                
                        "description_item"          : "Jumlah : " +str(surat.jml_kirim) + ", Jenis : " +str(surat.jenis), 
                        "special_instruction"       : surat.mid_thermal,                        
                        "api_key"                   : API_KEY
                    }
                elif surat.product_kode == 'EDC' :

                    # str_jumlah = surat.jml_kirim.replace('Roll', '').strip()
                    # int_jumlah = int(str_jumlah)

                    # berat = math.ceil(0.06 * int_jumlah)
                    # jml_koli = round(int_jumlah / 100)
                    hand_phone = surat.hand_phone
                    if surat.hand_phone == '' :
                        hand_phone = '00000'

                    data = {
                        "customer_code"             : CUST_CODE,
                        # "customer_code"             : 'CGKN05286',
                        "awb_no"                    : "",
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        # "quantity"                  : 1,
                        # "weight"                    : 1,
                        "quantity"                  : 1,
                        "weight"                    : surat.berat,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : hand_phone or '00000',
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : surat.home_phone,
                        "receiver_address_3"        : "",                
                        "description_item"          : "Jumlah : " +str(surat.jml_kirim) + ", Jenis : " +str(surat.jenis), 
                        "api_key"                   : API_KEY
                    }                    
                elif surat.product_kode == 'BIL' :
                    # if operation_state=='PRODUCTION' :
                    #     CUST_CODE = "CGKN02396"

                    data = {
                        "customer_code"             : CUST_CODE,
                        "awb_no"                    : surat.reff,
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : 1,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4 + ' - ' + surat.city,
                        "receiver_phone"            : surat.hand_phone + ' - ' + surat.office_phone + ' - ' + surat.home_phone,
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        "description_item"          : surat.kota,
                        "special_instruction"       : surat.kota_det,                        
                        "api_key"                   : API_KEY
                    }    
                elif surat.product_kode in ['PIN','PHS'] :

                    data = {
                        "customer_code"             : CUST_CODE,
                        "awb_no"                    : "",
                        "reference_no"              : surat.reff,
                        "pickup_name"               : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "pickup_address"            : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "pickup_phone"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "pickup_email"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).email,
                        "pickup_postal_code"        : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "pickup_latitude"           : "",
                        "pickup_longitude"          : "",
                        "pickup_district_code"      : surat.partner_code_from,
                        "service_type_code"         : SERVICE_CODE,
                        "quantity"                  : 1,
                        "weight"                    : 1,
                        "volumetric"                : "0x0x0",
                        "shipment_type_code"        : "SHTDC",
                        "insurance_flag"            : 1,
                        "cod_flag"                  : 1,
                        "shipper_name"              : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).name,
                        "shipper_address"           : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).street,
                        "shipper_phone"             : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).phone,
                        "shipper_postal_code"       : self.env['res.partner'].search([('id','=',self.env.user.company_id.id)]).zip,
                        "destination_district_code" : surat.partner_code_to,
                        "receiver_name"             : surat.card_name,
                        "receiver_address"          : surat.addr1 + ' - ' + surat.addr2 + ' - ' + surat.addr3 + ' - ' + surat.addr4,
                        "receiver_phone"            : surat.hand_phone,
                        "receiver_address_2_1"      : surat.addr_alt1 + ' - ' + surat.addr_alt2,
                        "receiver_address_2_2"      : surat.addr_alt3 + ' - ' + surat.addr_alt4,
                        "receiver_address_2_3"      : surat.city_alt,
                        "receiver_phone_2"          : "",
                        "receiver_address_3"        : "",                
                        "description_item"          : surat.product_kode,
                        "api_key"                   : API_KEY
                    }                                                       
                else :
                    surat.write({'api_status': 'fail', 'api_reason': 'INVALID SERVICE KURIR'})
                    self.env.cr.commit()

                if data :
                    try:
                        headers = {'api_key':API_KEY}    
                        r = requests.post(url = URL_ORDER, data = data,headers=headers) 

                        pastebin_url = r.text 
                        surat.write({'sys_msg': str(pastebin_url) +'\n'+ str(data) +'\n'+ str(headers)})
                        # print(pastebin_url)

                        control = "fail"
                        j = json.loads(pastebin_url)
                        successStatus 	= json.dumps(j["status"])
                        jsonStatus 		= json.loads(successStatus)

                        if jsonStatus == control:
                            jsonmsg = json.dumps(j["msg"])
                            msg 	= json.loads(jsonmsg)

                            surat.write({'api_status': jsonStatus, 'partner_status': msg, 'api_reason': msg})

                        else :                        
                            jsonmsg = json.dumps(j["msg"])
                            msg 	= json.loads(jsonmsg)

                            jsonResSuccess = json.dumps(j["data"])
                            awbNUmber = json.loads(jsonResSuccess)
                            data_a= awbNUmber["awb_no"]

                            surat.write({'api_status': jsonStatus})
                            surat.write({'api_reason': msg})
                            surat.write({'partner_number': data_a})
                            surat.write({'partner_status': jsonStatus})
                            surat.write({'tanggal_api': datetime.now()})

                    except Exception as e:
                        # old_msg = str(surat.sys_msg) 
                        # surat.write({'sys_msg'      : old_msg + '\n' + str(e)})
                        # surat.write({'api_status'   : 'fail' })
                        # surat.write({'api_reason'   : 'API FAULT - Send Order' })

                        surat.write({'api_status': 'fail', 'api_reason': 'API FAULT - Send Order' })
                        surat.write({'sys_check' : datetime.now(),'sys_msg': str(e) + '\n' + ' - ' + '\n' +  str(data)+ '\n' +' - ' + '\n' + str(headers)})

        self.env.cr.commit()
        return True            

class AreaKurirSAP(models.Model):
    _name           = 'bmri.kurir_sap_area'
    _description    = 'Area Kurir SAP'
    _rec_name       = 'city_name'

    province_name       = fields.Char(string='Province')   
    city_name           = fields.Char(string='City')   
    district_name       = fields.Char(string='District')   
    subdistrict_name    = fields.Char(string='Subdistrict')   
    zip_code            = fields.Char(string='ZipCode')   
    tariff_code         = fields.Char(string='Tariff Code')   